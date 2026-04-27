#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
"""Generate a self-contained HTML report for an fstests results tree.

Walks workflows/fstests/results/last-run/<vm>/<section>/result.xml
xunit files, gathers per-test status (pass/fail/skip/notrun), duration,
and the surrounding test environment (kernel, mkfs/mount options,
scratch device). For each failed test, embeds the .out.bad diff, the
.full execution log, and the .dmesg kernel messages so a reviewer
can triage without leaving the page.

Pulls in the playbooks/python/lib/report library for the report shell,
matplotlib charts, and the system monitoring section (sysstat +
cpu_governor outputs written through to results/monitoring/<vm>/).

Usage:
    python3 visualize_results.py [results_dir]

Default results_dir is workflows/fstests/results.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Optional

# Locate kdevops top so we can import the report library.
THIS_FILE = Path(__file__).resolve()
KDEVOPS_TOP = THIS_FILE.parents[3]
sys.path.insert(0, str(KDEVOPS_TOP / "playbooks" / "python" / "lib"))

from report import charts, html, monitoring  # noqa: E402

try:
    from junitparser import Failure, JUnitXml, Skipped, TestSuite
except ImportError:
    print(
        "junitparser not available; install python3-junitparser "
        "(or pip install junitparser)",
        file=sys.stderr,
    )
    sys.exit(1)


# Cap individual log embeds at a generous size; truncated logs include
# a marker so the reviewer knows to inspect the file directly.
MAX_LOG_BYTES = 256 * 1024


def _read_capped(path: Path) -> Optional[str]:
    """Read up to MAX_LOG_BYTES; return None if missing."""
    if not path.is_file():
        return None
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if len(raw) <= MAX_LOG_BYTES:
        return raw.decode("utf-8", errors="replace")
    head = raw[: MAX_LOG_BYTES // 2].decode("utf-8", errors="replace")
    tail = raw[-(MAX_LOG_BYTES // 2):].decode("utf-8", errors="replace")
    omitted = len(raw) - MAX_LOG_BYTES
    return (
        f"{head}\n\n"
        f"... [truncated {omitted:,} bytes; see file for full content] ...\n\n"
        f"{tail}"
    )


def _testsuites_from_file(path: Path) -> list:
    """Return TestSuite objects from a result.xml regardless of root.

    junitparser >= 4 returns a JUnitXml wrapper for a <testsuite> root.
    Older versions return the TestSuite directly.
    """
    parsed = JUnitXml.fromfile(str(path))
    return [parsed] if isinstance(parsed, TestSuite) else list(parsed)


def _testcase_status(testcase) -> str:
    for r in testcase.result:
        if isinstance(r, Failure):
            return "fail"
        if isinstance(r, Skipped):
            return "skip"
    return "pass"


def _testcase_failure_msg(testcase) -> str:
    for r in testcase.result:
        if isinstance(r, Failure):
            return r.message or ""
    return ""


def _section_property(testsuite, key: str) -> Optional[str]:
    """Read a <property name="KEY" value="VAL"/> from the testsuite."""
    props = testsuite.properties()
    if props is None:
        return None
    for p in props:
        if p.name == key:
            return p.value
    return None


def _gather_run(last_run: Path) -> dict:
    """Walk last_run/<vm>/<section>/result.xml and collect everything.

    Returns a dict shaped like:
        {
            "kernel": "<from xunit KERNEL property>",
            "vms": {
                "<vm>": {
                    "sections": {
                        "<section>": {
                            "properties": {KEY: VAL, ...},
                            "tests": [{"name", "status", "duration",
                                       "fail_msg", "out_bad", "full",
                                       "dmesg"}, ...],
                            "totals": {"pass", "fail", "skip"},
                        }
                    }
                }
            },
            "totals": {"pass", "fail", "skip", "tests"},
        }
    """
    run = {
        "kernel": None,
        "vms": {},
        "totals": {"pass": 0, "fail": 0, "skip": 0, "tests": 0},
    }

    if not last_run.is_dir():
        return run

    for vm_dir in sorted(last_run.iterdir()):
        if not vm_dir.is_dir():
            continue
        # Skip kernel-named summary subdirs at this level.
        if vm_dir.name and vm_dir.name[0].isdigit():
            continue
        vm_data = run["vms"].setdefault(vm_dir.name, {"sections": {}})

        for section_dir in sorted(vm_dir.iterdir()):
            if not section_dir.is_dir():
                continue
            xml_path = section_dir / "result.xml"
            if not xml_path.is_file():
                continue
            section_name = section_dir.name

            sec_entry = vm_data["sections"].setdefault(
                section_name,
                {
                    "properties": {},
                    "tests": [],
                    "totals": {"pass": 0, "fail": 0, "skip": 0},
                },
            )

            for ts in _testsuites_from_file(xml_path):
                if run["kernel"] is None:
                    kver = _section_property(ts, "KERNEL")
                    if kver:
                        run["kernel"] = kver
                if not sec_entry["properties"]:
                    props = ts.properties()
                    if props is not None:
                        sec_entry["properties"] = {p.name: p.value for p in props}

                for tc in ts:
                    status = _testcase_status(tc)
                    sec_entry["totals"][status] += 1
                    run["totals"][status] += 1
                    run["totals"]["tests"] += 1

                    test_entry = {
                        "name": tc.name,
                        "status": status,
                        "duration": float(getattr(tc, "time", 0) or 0),
                        "fail_msg": _testcase_failure_msg(tc) if status == "fail" else "",
                        "out_bad": None,
                        "full": None,
                        "dmesg": None,
                    }

                    if status == "fail":
                        # Companion artefacts live at
                        # <section>/<group>/<test>.{out.bad,full,dmesg}
                        # where the testcase name is "generic/042".
                        if "/" in tc.name:
                            group, test_id = tc.name.split("/", 1)
                            base = section_dir / group / test_id
                            test_entry["out_bad"] = _read_capped(
                                base.with_suffix(".out.bad")
                            )
                            test_entry["full"] = _read_capped(
                                base.with_suffix(".full")
                            )
                            test_entry["dmesg"] = _read_capped(
                                base.with_suffix(".dmesg")
                            )
                    sec_entry["tests"].append(test_entry)

    return run


# ---- HTML rendering -----------------------------------------------------


def _stat_cards(report: html.Report, run: dict) -> None:
    totals = run["totals"]
    section_count = sum(
        len(vm["sections"]) for vm in run["vms"].values()
    )
    report.add_card("Kernel", run["kernel"] or "(unknown)")
    report.add_card("Total Tests", str(totals["tests"]))
    report.add_card("Passed", str(totals["pass"]))
    report.add_card("Failed", str(totals["fail"]))
    report.add_card("Skipped", str(totals["skip"]))
    report.add_card("Sections", str(section_count))


def _pass_fail_chart_html(run: dict) -> str:
    labels: list[str] = []
    passed: list[int] = []
    failed: list[int] = []
    for vm_name, vm in sorted(run["vms"].items()):
        for section, sec in sorted(vm["sections"].items()):
            labels.append(f"{vm_name}\n{section}")
            passed.append(sec["totals"]["pass"])
            failed.append(sec["totals"]["fail"])
    if not labels:
        return '<div class="no-data">No sections to chart</div>'
    png = charts.stacked_pass_fail(
        labels, passed, failed,
        title="Pass / fail per (vm, section)",
        ylabel="Test count",
    )
    return html.chart_block(
        html.embed_png(png) if png else None,
        no_data_msg="matplotlib not installed; chart skipped",
    )


def _format_log_block(label: str, body: Optional[str], path_hint: str) -> str:
    """Wrap a per-test artefact in a collapsible <details> block."""
    if not body:
        return (
            f'<details><summary>{escape(label)}</summary>'
            f'<p class="no-data">No {escape(path_hint)} captured for this test.</p>'
            '</details>'
        )
    return (
        f'<details><summary>{escape(label)} '
        f'<span style="color:#718096;font-weight:normal;">'
        f'({len(body):,} bytes — {escape(path_hint)})</span>'
        '</summary>'
        f'<pre style="background:#1a202c;color:#edf2f7;padding:14px;'
        'border-radius:6px;overflow-x:auto;max-height:600px;">'
        f'{escape(body)}</pre></details>'
    )


def _section_block(vm_name: str, section: str, sec: dict) -> str:
    parts: list[str] = []
    parts.append(f'<h3>{escape(vm_name)} / {escape(section)}</h3>')

    # Test environment (a subset of the most useful properties).
    keys_of_interest = [
        "KERNEL", "FSTYP", "ARCH", "CPUS", "MEM_KB", "TEST_DEV",
        "SCRATCH_DEV", "MKFS_OPTIONS", "MOUNT_OPTIONS",
        "SCRATCH_DEV_LBA_BYTES", "SCRATCH_DEV_PHYS_BLOCK_BYTES",
    ]
    rows = []
    for key in keys_of_interest:
        val = sec["properties"].get(key)
        if val:
            rows.append(f'<tr><td>{escape(key)}</td><td>{escape(str(val))}</td></tr>')
    if rows:
        parts.append("<h4>Environment</h4>")
        parts.append(
            "<table><thead><tr><th>Property</th><th>Value</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )

    # Tests table.
    rows = []
    for t in sec["tests"]:
        klass = {
            "pass": "success",
            "fail": "failure",
            "skip": "",
        }[t["status"]]
        rows.append(
            "<tr>"
            f"<td>{escape(t['name'])}</td>"
            f'<td class="{klass}">{escape(t["status"].upper())}</td>'
            f"<td>{t['duration']:.2f}s</td>"
            f"<td>{escape(t['fail_msg'])}</td>"
            "</tr>"
        )
    parts.append("<h4>Tests</h4>")
    parts.append(
        "<table><thead><tr>"
        "<th>Test</th><th>Status</th><th>Duration</th><th>Failure message</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )

    # Failures: full triage payload per failed test.
    failures = [t for t in sec["tests"] if t["status"] == "fail"]
    if failures:
        parts.append("<h4>Failure detail</h4>")
        for t in failures:
            parts.append(
                f'<details open><summary><strong class="failure">'
                f'{escape(t["name"])}</strong> — {escape(t["fail_msg"])}'
                '</summary>'
            )
            parts.append(_format_log_block(".out.bad (diff)", t["out_bad"], ".out.bad"))
            parts.append(_format_log_block(".full (test execution log)", t["full"], ".full"))
            parts.append(_format_log_block(".dmesg (kernel messages)", t["dmesg"], ".dmesg"))
            parts.append("</details>")

    return "\n".join(parts)


def _detail_section_html(run: dict) -> str:
    chunks: list[str] = []
    for vm_name, vm in sorted(run["vms"].items()):
        for section, sec in sorted(vm["sections"].items()):
            chunks.append(_section_block(vm_name, section, sec))
    return "\n".join(chunks) if chunks else '<div class="no-data">No sections found</div>'


def _summary_text_section(results_dir: Path) -> Optional[str]:
    """Embed last-run/<kernel>/xunit_results.txt if present."""
    last_run = results_dir / "last-run"
    for path in last_run.glob("*/xunit_results.txt"):
        content = _read_capped(path)
        if content:
            return (
                f'<pre style="background:#f7fafc;padding:14px;'
                'border-radius:6px;overflow-x:auto;">'
                f'{escape(content)}</pre>'
            )
    return None


def build_report(results_dir: Path) -> html.Report:
    last_run = results_dir / "last-run"
    monitoring_dir = results_dir / "monitoring"

    run = _gather_run(last_run)

    report = html.Report(
        title="fstests Run Report",
        timestamp=datetime.now(),
    )
    _stat_cards(report, run)

    summary_html = _summary_text_section(results_dir)
    if summary_html:
        report.add_section("Run summary", summary_html)

    report.add_section("Pass / fail by section", _pass_fail_chart_html(run))

    monitoring_html = monitoring.render_section(monitoring_dir)
    if monitoring_html:
        report.add_section("System monitoring", monitoring_html)

    report.add_section("Per-section detail", _detail_section_html(run))

    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "results_dir",
        nargs="?",
        default=str(KDEVOPS_TOP / "workflows" / "fstests" / "results"),
        help="Path to workflows/fstests/results (default: %(default)s)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output HTML path (default: <results_dir>/fstests-report.html)",
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir).resolve()
    if not results_dir.is_dir():
        print(f"results_dir not found: {results_dir}", file=sys.stderr)
        return 1

    report = build_report(results_dir)
    out_path = Path(args.output) if args.output else (results_dir / "fstests-report.html")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html.render(report))

    totals = report.stat_cards
    print(f"Report written to: {out_path}")
    for c in totals:
        print(f"  {c.label}: {c.value}")
    print(f"  Size: {out_path.stat().st_size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())

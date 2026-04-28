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
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Optional

# Locate kdevops top so we can import the report library.
THIS_FILE = Path(__file__).resolve()
KDEVOPS_TOP = THIS_FILE.parents[3]
sys.path.insert(0, str(KDEVOPS_TOP / "playbooks" / "python" / "lib"))

from report import charts, html, monitoring  # noqa: E402,F401

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


def _testcase_status_msg(testcase) -> str:
    """Return the message a Failure or Skipped result carries.

    xfstests' xunit emits <skipped message="..."> with the reason
    text from the test's .notrun file (e.g. missing test binary,
    kernel feature not enabled), and <failure message="..."> for
    fails. Either one is useful in the per-test table.
    """
    for r in testcase.result:
        if isinstance(r, (Failure, Skipped)):
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


def _parse_iso(stamp: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 timestamp emitted by xfstests' xunit writer."""
    if not stamp:
        return None
    try:
        return datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def _gather_run(results_dir: Path, kernel: Optional[str] = None) -> dict:
    """Walk <results>/<vm>/{kernel|last-run}/<section>/result.xml.

    The Phase B layout puts each run under its kernel name inside
    the per-VM directory, with a ``last-run`` symlink at that VM's
    root pointing to the most recent kernel:

        results_dir/qsu-xfs-crc/last-run -> 7.0.0-gABCDE
        results_dir/qsu-xfs-crc/7.0.0-gABCDE/xfs_crc/result.xml

    With ``kernel=None`` the gather follows each VM's ``last-run``
    symlink to read the most recent kernel; with ``kernel`` set to
    a specific name the gather reads ``<vm>/<kernel>/`` directly,
    so the report can be regenerated for an archived run without
    flipping the symlink. A VM without that kernel directory is
    skipped — the report reflects only the kernels that actually
    exist on disk.

    Returns a dict shaped like:
        {
            "kernel": "<from xunit KERNEL property>",
            "vms": {
                "<vm>": {
                    "kernel": "<from <vm>/last-kernel.txt>",
                    "sections": {
                        "<section>": {
                            "properties": {KEY: VAL, ...},
                            "tests": [{"name", "status", "duration",
                                       "fail_msg", "out_bad", "full",
                                       "dmesg"}, ...],
                            "totals": {"pass", "fail", "skip"},
                            "section_start_ts": datetime | None,
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

    if not results_dir.is_dir():
        return run

    for vm_dir in sorted(results_dir.iterdir()):
        if not vm_dir.is_dir():
            continue
        # Skip top-level files (last-kernel.txt at root, fstests-report*.html)
        # and any non-VM-named entries. A real VM dir has a last-run symlink
        # or at least one <kernel> subdir.
        if kernel is not None:
            run_dir = vm_dir / kernel
            per_vm_kernel = kernel
        else:
            run_dir = vm_dir / "last-run"
            # Per-VM kernel record (from <vm>/last-kernel.txt) so
            # the report can show which kernel each VM used.
            per_vm_kernel = None
            last_kernel_file = vm_dir / "last-kernel.txt"
            if last_kernel_file.is_file():
                per_vm_kernel = last_kernel_file.read_text().strip() or None
        if not run_dir.is_dir():
            continue

        vm_data = run["vms"].setdefault(
            vm_dir.name,
            {"kernel": per_vm_kernel, "sections": {}},
        )

        for section_dir in sorted(run_dir.iterdir()):
            if not section_dir.is_dir():
                continue
            # The monitoring/ subdir is a sibling of the section dirs
            # under <vm>/<kernel>/; skip it here, the monitoring
            # adapter renders it separately.
            if section_dir.name == "monitoring":
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
                    "section_start_ts": None,
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
                if sec_entry["section_start_ts"] is None:
                    raw_start = getattr(ts, "_elem", ts).get("start_timestamp")
                    sec_entry["section_start_ts"] = _parse_iso(raw_start)

                for tc in ts:
                    status = _testcase_status(tc)
                    sec_entry["totals"][status] += 1
                    run["totals"][status] += 1
                    run["totals"]["tests"] += 1

                    test_entry = {
                        "name": tc.name,
                        "status": status,
                        "duration": float(getattr(tc, "time", 0) or 0),
                        # Pull the <failure message> for fails and
                        # <skipped message> for skips so the table
                        # tells the reviewer *why* a non-pass result
                        # happened. .notrun files carry the same
                        # text xfstests writes into xunit.
                        "status_msg": _testcase_status_msg(tc),
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
    # Pass/Fail/Skip share one card so the gradient header collapses
    # from six tiles to four; the freed horizontal space lets the
    # auto-LOCALVERSION kernel string stay on one line in the
    # Kernel card without the clamp() font-size dropping further
    # than necessary.
    outcomes = (
        f"{totals['pass']} / {totals['fail']} / {totals['skip']}"
    )
    report.add_card("Kernel", run["kernel"] or "(unknown)")
    report.add_card("Total tests", str(totals["tests"]))
    report.add_card("Pass / Fail / Skip", outcomes)
    report.add_card("Sections", str(section_count))


# ---- A/B comparison ------------------------------------------------------


def _compute_ab_diff(run_a: dict, run_b: dict) -> dict:
    """Per-test status diff between two runs of the same workflow.

    Returns:
        {
            "tests": [
                {"vm", "section", "name", "a", "b", "kind"},
                ...
            ],   # only entries where a != b OR one side is missing
            "summary": {
                "regressions": int,    # pass on A, fail on B
                "fixes": int,          # fail on A, pass on B
                "new_skips": int,      # ran on A, skipped on B
                "now_running": int,    # skipped on A, ran on B
                "only_a": int,         # absent on B
                "only_b": int,         # absent on A
                "same": int,           # same outcome (count of unchanged)
            },
        }

    The rendering layer turns ``summary`` into stat cards and
    ``tests`` into a diff table at the top of the report.
    """
    summary = {
        "regressions": 0, "fixes": 0,
        "new_skips": 0, "now_running": 0,
        "only_a": 0, "only_b": 0,
        "same": 0,
    }
    diff_rows: list[dict] = []
    all_vms = set(run_a["vms"]) | set(run_b["vms"])
    for vm in sorted(all_vms):
        sec_a = run_a["vms"].get(vm, {}).get("sections", {})
        sec_b = run_b["vms"].get(vm, {}).get("sections", {})
        all_sections = set(sec_a) | set(sec_b)
        for section in sorted(all_sections):
            tests_a = {t["name"]: t for t in sec_a.get(section, {}).get("tests", [])}
            tests_b = {t["name"]: t for t in sec_b.get(section, {}).get("tests", [])}
            all_names = set(tests_a) | set(tests_b)
            for name in sorted(all_names):
                ta = tests_a.get(name)
                tb = tests_b.get(name)
                a_status = ta["status"] if ta else None
                b_status = tb["status"] if tb else None

                if a_status is None:
                    summary["only_b"] += 1
                    kind = "only_b"
                elif b_status is None:
                    summary["only_a"] += 1
                    kind = "only_a"
                elif a_status == b_status:
                    summary["same"] += 1
                    continue  # don't list unchanged in the diff table
                elif a_status == "pass" and b_status == "fail":
                    summary["regressions"] += 1
                    kind = "regression"
                elif a_status == "fail" and b_status == "pass":
                    summary["fixes"] += 1
                    kind = "fix"
                elif b_status == "skip" and a_status != "skip":
                    summary["new_skips"] += 1
                    kind = "new_skip"
                elif a_status == "skip" and b_status != "skip":
                    summary["now_running"] += 1
                    kind = "now_running"
                else:
                    kind = "other"

                diff_rows.append({
                    "vm": vm, "section": section, "name": name,
                    "a": a_status, "b": b_status, "kind": kind,
                })
    return {"tests": diff_rows, "summary": summary}


def _ab_stat_cards(
    report: html.Report,
    run_a: dict,
    run_b: dict,
    kernels: list[str],
    diff: dict,
) -> None:
    """Stat cards for A/B mode: per-kernel totals + diff highlights.

    Highlights what a reviewer is most likely to need to know first:
    regressions (pass→fail) get the failure colour; fixes (fail→pass)
    are the positive signal; new_skips and tests only on one side
    flag a coverage shift across the kernels rather than a
    correctness shift.
    """
    s = diff["summary"]
    report.add_card(f"A: {kernels[0]}", f"{run_a['totals']['tests']} tests")
    report.add_card(f"B: {kernels[1]}", f"{run_b['totals']['tests']} tests")
    report.add_card("Regressions (A→B)", str(s["regressions"]))
    report.add_card("Fixes (A→B)", str(s["fixes"]))
    report.add_card("New skips on B", str(s["new_skips"]))
    report.add_card(
        "Coverage diff",
        f"only A: {s['only_a']} / only B: {s['only_b']}",
    )


def _ab_diff_section_html(diff: dict, kernels: list[str]) -> str:
    """Top-of-report table listing every test where A and B disagree.

    Sorted by ``kind`` (regressions first, then new_skips, then
    fixes, then coverage shifts) so a reviewer reading top-down
    sees the most attention-worthy outcomes first.
    """
    if not diff["tests"]:
        return (
            '<div class="no-data" style="padding:12px;">'
            'No per-test outcome differences between '
            f'<code>{escape(kernels[0])}</code> and '
            f'<code>{escape(kernels[1])}</code>. Both kernels ran the '
            'same set of tests with the same pass/fail/skip outcomes.'
            '</div>'
        )

    kind_label = {
        "regression": "regression",
        "fix": "fix",
        "new_skip": "new skip",
        "now_running": "now running",
        "only_a": "only on A",
        "only_b": "only on B",
        "other": "changed",
    }
    kind_class = {
        "regression": "failure",
        "fix": "success",
        "new_skip": "",
        "now_running": "success",
        "only_a": "",
        "only_b": "",
        "other": "",
    }
    kind_order = {
        "regression": 0, "new_skip": 1, "now_running": 2,
        "fix": 3, "only_a": 4, "only_b": 5, "other": 6,
    }
    rows: list[str] = []
    for entry in sorted(
        diff["tests"],
        key=lambda e: (kind_order.get(e["kind"], 9), e["vm"], e["section"], e["name"]),
    ):
        a = (entry["a"] or "—").upper()
        b = (entry["b"] or "—").upper()
        klass = kind_class.get(entry["kind"], "")
        rows.append(
            "<tr>"
            f'<td><code>{escape(entry["vm"])}</code></td>'
            f'<td><code>{escape(entry["section"])}</code></td>'
            f'<td><code>{escape(entry["name"])}</code></td>'
            f'<td>{escape(a)}</td>'
            f'<td>{escape(b)}</td>'
            f'<td class="{klass}">{escape(kind_label[entry["kind"]])}</td>'
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>VM</th><th>Section</th><th>Test</th>"
        f"<th>A · {escape(kernels[0])}</th>"
        f"<th>B · {escape(kernels[1])}</th>"
        "<th>Change</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    )


def _ab_section_block(
    vm_name: str,
    section: str,
    sec_a: Optional[dict],
    sec_b: Optional[dict],
    kernels: list[str],
) -> str:
    """Per-(VM, section) detail block in A/B mode.

    Tests table grows two status columns (A and B) with
    classed cells highlighting regressions and fixes. Only tests
    that exist on at least one side are listed; rows where both
    sides match render in neutral styling so the eye is drawn to
    the divergent ones.
    """
    parts: list[str] = []
    parts.append(f'<h3>{escape(vm_name)} / {escape(section)}</h3>')

    tests_a = {t["name"]: t for t in (sec_a or {}).get("tests", [])} if sec_a else {}
    tests_b = {t["name"]: t for t in (sec_b or {}).get("tests", [])} if sec_b else {}
    all_names = sorted(set(tests_a) | set(tests_b))

    rows: list[str] = []
    for name in all_names:
        ta = tests_a.get(name)
        tb = tests_b.get(name)
        a_status = ta["status"] if ta else None
        b_status = tb["status"] if tb else None
        a_dur = f"{ta['duration']:.2f}s" if ta else "—"
        b_dur = f"{tb['duration']:.2f}s" if tb else "—"
        a_msg = ta["status_msg"] if ta else ""
        b_msg = tb["status_msg"] if tb else ""

        # Highlight regression on B's cell; fix on A's cell.
        a_klass = "failure" if a_status == "fail" else (
            "success" if a_status == "pass" else "")
        b_klass = "failure" if b_status == "fail" else (
            "success" if b_status == "pass" else "")
        if a_status == "pass" and b_status == "fail":
            b_klass = "failure"
        elif a_status == "fail" and b_status == "pass":
            a_klass = "failure"

        a_label = (a_status.upper() if a_status else "—")
        b_label = (b_status.upper() if b_status else "—")
        rows.append(
            "<tr>"
            f"<td><code>{escape(name)}</code></td>"
            f'<td class="{a_klass}">{escape(a_label)}</td>'
            f"<td>{escape(a_dur)}</td>"
            f'<td class="{b_klass}">{escape(b_label)}</td>'
            f"<td>{escape(b_dur)}</td>"
            f"<td>{escape(a_msg or b_msg)}</td>"
            "</tr>"
        )

    parts.append("<h4>Tests</h4>")
    parts.append(
        "<table><thead><tr>"
        "<th>Test</th>"
        f"<th>A · {escape(kernels[0])}</th><th>A duration</th>"
        f"<th>B · {escape(kernels[1])}</th><th>B duration</th>"
        "<th>Reason</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )

    # Failure detail: any test that failed on at least one kernel.
    # Show per-kernel .out.bad/.full/.dmesg artefacts side-by-side
    # so a reviewer triaging an A/B regression sees both runs'
    # diagnostics in the same block — including the case where A
    # failed and B passed (the "fix" case), which is useful for
    # the flaky-test diagnosis the user asked for.
    failure_names = sorted([
        n for n in all_names
        if (tests_a.get(n, {}).get("status") == "fail")
        or (tests_b.get(n, {}).get("status") == "fail")
    ])
    if failure_names:
        parts.append("<h4>Failure detail</h4>")
        for name in failure_names:
            ta = tests_a.get(name)
            tb = tests_b.get(name)
            a_status = (ta["status"].upper() if ta else "—")
            b_status = (tb["status"].upper() if tb else "—")
            parts.append(
                f'<details open><summary><strong class="failure">'
                f'{escape(name)}</strong> — '
                f'A · <code>{escape(a_status)}</code> · '
                f'B · <code>{escape(b_status)}</code>'
                '</summary>'
            )
            for label_kernel, t in (
                (f"A · {kernels[0]}", ta),
                (f"B · {kernels[1]}", tb),
            ):
                if not t or t["status"] != "fail":
                    continue
                parts.append(
                    f'<h5 style="margin:8px 0 4px 0;">{escape(label_kernel)} '
                    f'<span style="color:#718096;font-weight:normal;">— '
                    f'{escape(t["status_msg"])}</span></h5>'
                )
                parts.append(_format_log_block(
                    ".out.bad (diff)", t["out_bad"], ".out.bad"))
                parts.append(_format_log_block(
                    ".full (test execution log)", t["full"], ".full"))
                parts.append(_format_log_block(
                    ".dmesg (kernel messages)", t["dmesg"], ".dmesg"))
            parts.append("</details>")
    return "\n".join(parts)


def _ab_detail_section_html(
    run_a: dict, run_b: dict, kernels: list[str],
    hosts: Optional[set[str]] = None,
) -> str:
    chunks: list[str] = []
    all_vms = set(run_a["vms"]) | set(run_b["vms"])
    if hosts:
        all_vms &= hosts
    for vm in sorted(all_vms):
        sec_a = run_a["vms"].get(vm, {}).get("sections", {})
        sec_b = run_b["vms"].get(vm, {}).get("sections", {})
        all_sections = sorted(set(sec_a) | set(sec_b))
        for section in all_sections:
            chunks.append(_ab_section_block(
                vm, section,
                sec_a.get(section), sec_b.get(section),
                kernels,
            ))
    return "\n".join(chunks) if chunks else (
        '<div class="no-data">No sections found for the requested kernels</div>'
    )


def _git_log_lines(repo: Path, n: int = 20) -> Optional[list[str]]:
    """Return the last ``n`` commits of a git repo as 'sha date subject'.

    Falls back to None when the path isn't a git checkout, the git
    binary is unavailable, or the call fails — the caller treats
    None as "skip rendering this source's section".
    """
    if not repo.is_dir() or shutil.which("git") is None:
        return None
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo), "log",
             f"-{n}", "--pretty=format:%h %ad %s", "--date=short"],
            text=True, errors="replace", stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    return [line for line in out.splitlines() if line.strip()]


def _git_head(repo: Path) -> Optional[dict]:
    """Return the HEAD commit's metadata + dirty-tree state.

    Shape: ``{sha, author, date, subject, branch, dirty_files}``.
    ``dirty_files`` is a list of porcelain entries like
    ``" M tests/generic/042"``; an empty list means the working
    tree is clean. The renderer surfaces a non-empty dirty_files
    list as an explicit "this run was built from a modified source
    tree" warning so a reviewer doesn't assume the HEAD subject
    represents the actual code under test.
    """
    if not repo.is_dir() or shutil.which("git") is None:
        return None
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo), "log", "-1",
             "--pretty=format:%H%n%an <%ae>%n%ad%n%s", "--date=iso-strict"],
            text=True, errors="replace", stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, OSError):
        return None
    parts = out.split("\n", 3)
    if len(parts) != 4:
        return None
    head: dict = {
        "sha":     parts[0],
        "author":  parts[1],
        "date":    parts[2],
        "subject": parts[3],
        "branch":  None,
        "dirty_files": [],
    }
    try:
        head["branch"] = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
            text=True, errors="replace", stderr=subprocess.DEVNULL,
        ).strip() or None
    except (subprocess.CalledProcessError, OSError):
        pass
    try:
        status = subprocess.check_output(
            ["git", "-C", str(repo), "status", "--porcelain=v1"],
            text=True, errors="replace", stderr=subprocess.DEVNULL,
        )
        head["dirty_files"] = [
            line for line in status.splitlines() if line.strip()
        ]
    except (subprocess.CalledProcessError, OSError):
        pass
    return head


def _source_revisions_section(results_dir: Path) -> Optional[str]:
    """Render git HEAD + recent log for the kernel and fstests sources.

    The kdevops controller-mode bootlinux clone lives at
    ``<kdevops>/data/linux/`` and the user's fstests checkout path
    is recorded in ``extra_vars.yaml``. Both are accessible from
    where the report is rendered, so we run ``git log`` directly
    against them and embed the output.

    Useful in two ways:
      - confirms the *exact* source revision the kernel binary was
        built from (the auto-LOCALVERSION suffix in uname -r is
        only the short SHA; the subject line clarifies what the
        commit was)
      - lists the last N commits so a reader can scan whether the
        run included recent fixes or not — useful when a regression
        in the report could have been triaged by checking "did
        commit X land in the build?"

    Returns None if neither source is reachable.
    """
    # Resolve repo paths.
    kdevops_top = results_dir.parent.parent.parent
    kernel_repo = kdevops_top / "data" / "linux"
    fstests_repo: Optional[Path] = None
    extra_vars = kdevops_top / "extra_vars.yaml"
    if extra_vars.is_file():
        for line in extra_vars.read_text().splitlines():
            line = line.strip()
            if line.startswith("fstests_git:"):
                value = line.split(":", 1)[1].strip().strip('"').strip("'")
                if value and not value.startswith(("http", "git@", "git:")):
                    fstests_repo = Path(value).expanduser()
                break

    sources = []
    for label, repo in (
        ("Linux kernel", kernel_repo),
        ("xfstests",     fstests_repo),
    ):
        if repo is None:
            continue
        head = _git_head(repo)
        log = _git_log_lines(repo, n=15)
        if not head and not log:
            continue
        sources.append((label, repo, head, log))
    if not sources:
        return None

    parts: list[str] = []
    for label, repo, head, log in sources:
        parts.append(
            f'<h4>{escape(label)} '
            f'<code style="font-weight:normal;color:#4a5568;'
            f'font-size:0.9em;">{escape(str(repo))}</code></h4>'
        )
        if head and head["dirty_files"]:
            n = len(head["dirty_files"])
            files_block = "\n".join(
                escape(line) for line in head["dirty_files"]
            )
            parts.append(
                '<p class="failure" style="margin:4px 0 8px 0;">'
                f'⚠ Working tree is dirty — {n} file(s) modified, '
                'staged, or untracked. The HEAD commit below is '
                '<strong>not</strong> the exact source the run was '
                'built from.</p>'
                '<details open><summary><strong class="failure">'
                'git status --porcelain</strong></summary>'
                '<pre style="background:#1a202c;color:#edf2f7;'
                'padding:14px;border-radius:6px;overflow-x:auto;'
                f'font-size:0.85em;">{files_block}</pre>'
                '</details>'
            )
        if head:
            branch_row = (
                f'<tr><td>branch</td><td><code>{escape(head["branch"])}</code></td></tr>'
                if head.get("branch") else ""
            )
            parts.append(
                '<table><thead><tr><th>field</th><th>value</th></tr></thead>'
                '<tbody>'
                f'<tr><td>HEAD</td><td><code>{escape(head["sha"][:12])}</code></td></tr>'
                f'{branch_row}'
                f'<tr><td>subject</td><td>{escape(head["subject"])}</td></tr>'
                f'<tr><td>author</td><td>{escape(head["author"])}</td></tr>'
                f'<tr><td>date</td><td>{escape(head["date"])}</td></tr>'
                '</tbody></table>'
            )
        if log:
            entries = "\n".join(escape(line) for line in log)
            parts.append(
                f'<details><summary>Recent commits ({len(log)})</summary>'
                '<pre style="background:#1a202c;color:#edf2f7;padding:14px;'
                'border-radius:6px;overflow-x:auto;font-size:0.85em;">'
                f'{entries}</pre>'
                '</details>'
            )
    return "\n".join(parts)


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
            f"<td>{escape(t['status_msg'])}</td>"
            "</tr>"
        )
    parts.append("<h4>Tests</h4>")
    parts.append(
        "<table><thead><tr>"
        "<th>Test</th><th>Status</th><th>Duration</th><th>Reason</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table>"
    )

    # Failures: full triage payload per failed test.
    failures = [t for t in sec["tests"] if t["status"] == "fail"]
    if failures:
        parts.append("<h4>Failure detail</h4>")
        for t in failures:
            parts.append(
                f'<details open><summary><strong class="failure">'
                f'{escape(t["name"])}</strong> — {escape(t["status_msg"])}'
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


def _summary_text_section(
    results_dir: Path, kernel: Optional[str] = None,
) -> Optional[str]:
    """Embed each VM's xunit_results.txt summary near the top of the report.

    With ``kernel=None`` the path resolves through the per-VM
    last-run symlink so the report shows the most recent run's
    summary. With ``kernel`` set, the function reads
    ``<vm>/<kernel>/xunit_results.txt`` directly so an archived
    run can be inspected without changing any symlink.
    """
    sub = kernel if kernel is not None else "last-run"
    chunks: list[str] = []
    for vm_dir in sorted(results_dir.iterdir()):
        if not vm_dir.is_dir():
            continue
        path = vm_dir / sub / "xunit_results.txt"
        if not path.is_file():
            continue
        content = _read_capped(path)
        if not content:
            continue
        chunks.append(
            f'<h4>{escape(vm_dir.name)}</h4>'
            f'<pre style="background:#f7fafc;padding:14px;'
            'border-radius:6px;overflow-x:auto;">'
            f'{escape(content)}</pre>'
        )
    return "\n".join(chunks) if chunks else None


def _host_monitoring_dir(
    results_dir: Path, vm_name: str, kernel: Optional[str] = None,
) -> Path:
    """Per-VM monitoring directory for the requested run.

    With ``kernel=None`` the path resolves through the per-VM
    last-run symlink (most recent run). With ``kernel`` set, the
    path is ``<results>/<vm>/<kernel>/monitoring/`` directly, so
    an archived run's monitoring data is reachable without
    flipping any symlink.
    """
    sub = kernel if kernel is not None else "last-run"
    return results_dir / vm_name / sub / "monitoring"


def _build_test_timelines(
    run: dict, results_dir: Path, kernel: Optional[str] = None,
) -> dict[str, list[tuple[str, float, float, str]]]:
    """Compute per-host test intervals aligned to the sysstat x-axis.

    For each (vm, section), reconstruct each test's run interval from
    the xunit's section start_timestamp + cumulative testcase time.
    Then offset that against the host's first sysstat sample so the
    test timeline chart's x-axis matches the metric charts above it.
    Returns a dict {host: [(test_name, x_start, duration, status), ...]}.
    """
    timelines: dict[str, list[tuple[str, float, float, str]]] = {}
    for vm_name, vm in run["vms"].items():
        host_dir = _host_monitoring_dir(results_dir, vm_name, kernel=kernel)
        first_sample = monitoring.first_sample_timestamp(host_dir)
        if first_sample is None:
            continue
        intervals: list[tuple[str, float, float, str]] = []
        for section, sec in sorted(vm["sections"].items()):
            section_start = sec.get("section_start_ts")
            if section_start is None:
                continue
            cum = 0.0
            section_offset = (section_start - first_sample).total_seconds()
            for t in sec["tests"]:
                duration = float(t.get("duration", 0.0))
                intervals.append((
                    t["name"],
                    section_offset + cum,
                    duration,
                    t["status"],
                ))
                cum += duration
        if intervals:
            timelines[vm_name] = intervals
    return timelines


def build_ab_report(
    results_dir: Path,
    kernels: list[str],
    hosts: Optional[set[str]] = None,
) -> html.Report:
    """Build an A/B comparison report between exactly two kernels.

    Reads ``<vm>/<kernels[0]>/...`` as run A and
    ``<vm>/<kernels[1]>/...`` as run B for every VM that has both
    runs available. The top of the page surfaces the per-test diff
    (regressions, fixes, new skips, coverage shifts) so a reviewer
    sees what changed at-a-glance; below that, per-section detail
    tables grow two status columns (A and B) with regressions on
    B's column highlighted in the failure colour and fixes on A's
    column likewise — the eye is drawn to the divergent rows.

    Monitoring overlay (CPU/memory/run-queue/disk-I/O charts with
    both kernels' lines on a shared axis) lands as a follow-on
    commit; this commit covers the test-outcome side of the A/B
    comparison.
    """
    run_a = _gather_run(results_dir, kernel=kernels[0])
    run_b = _gather_run(results_dir, kernel=kernels[1])
    if hosts:
        run_a["vms"] = {k: v for k, v in run_a["vms"].items() if k in hosts}
        run_b["vms"] = {k: v for k, v in run_b["vms"].items() if k in hosts}

    diff = _compute_ab_diff(run_a, run_b)

    title_bits = [f"{kernels[0]} vs {kernels[1]}"]
    if hosts:
        title_bits.append(", ".join(sorted(hosts)))
    report = html.Report(
        title=f"fstests A/B Report — {' / '.join(title_bits)}",
        timestamp=datetime.now(),
    )
    _ab_stat_cards(report, run_a, run_b, kernels, diff)

    sources_html = _source_revisions_section(results_dir)
    if sources_html:
        report.add_section("Source revisions", sources_html)

    report.add_section(
        f"A/B summary — {kernels[0]} vs {kernels[1]}",
        _ab_diff_section_html(diff, kernels),
    )

    # Monitoring overlay: one chart per metric drawn with both
    # kernels' lines on a shared axis (per-metric colour, per-kernel
    # line style). Each VM contributes a per-kernel monitoring dir
    # and a per-kernel test-timeline so the underlay shading and
    # x-axis range stay consistent across both lines.
    host_kernel_dirs: dict[str, dict[str, Path]] = {}
    host_test_timelines_ab: dict[str, dict[str, list]] = {}
    for vm_name in sorted(set(run_a["vms"]) | set(run_b["vms"])):
        host_kernel_dirs[vm_name] = {
            k: _host_monitoring_dir(results_dir, vm_name, kernel=k)
            for k in kernels
        }
    timelines_a = _build_test_timelines(run_a, results_dir, kernel=kernels[0])
    timelines_b = _build_test_timelines(run_b, results_dir, kernel=kernels[1])
    for vm_name in host_kernel_dirs:
        host_test_timelines_ab[vm_name] = {}
        if vm_name in timelines_a:
            host_test_timelines_ab[vm_name][kernels[0]] = timelines_a[vm_name]
        if vm_name in timelines_b:
            host_test_timelines_ab[vm_name][kernels[1]] = timelines_b[vm_name]

    monitoring_html = monitoring.render_section_ab(
        host_kernel_dirs,
        kernels=kernels,
        host_test_timelines_ab=host_test_timelines_ab,
        allowed_hosts=hosts,
    )
    if monitoring_html:
        report.add_section("System monitoring (A/B overlay)", monitoring_html)

    report.add_section(
        "Per-section detail",
        _ab_detail_section_html(run_a, run_b, kernels, hosts=hosts),
    )
    return report


def build_report(
    results_dir: Path,
    hosts: Optional[set[str]] = None,
    kernel: Optional[str] = None,
) -> html.Report:
    """Build an HTML report from the fstests results tree.

    ``hosts`` is an optional whitelist of host (VM) names. When set,
    only those hosts are rendered — the per-section detail tables,
    the pass/fail chart, the system-monitoring host blocks, and the
    aggregate totals at the top of the page all narrow down to the
    selected set. Useful when several profiles share a results tree
    and a reviewer only cares about one (e.g. comparing the same
    workflow under two different mkfs/mount setups by rendering one
    report per host).

    ``kernel`` selects which run to render per VM. ``None`` means
    each VM's most recent run (resolved via the
    ``<vm>/last-run -> <kernel>`` symlink). A specific kernel name
    reads ``<vm>/<kernel>/...`` directly so archived runs can be
    re-rendered without flipping any symlink. VMs that lack the
    requested kernel are silently skipped — the report only
    surfaces what actually exists on disk.
    """
    run = _gather_run(results_dir, kernel=kernel)

    if hosts:
        run["vms"] = {k: v for k, v in run["vms"].items() if k in hosts}
        # Recompute run-wide totals from the filtered set so the
        # stat cards at the top reflect what the report actually
        # shows, not the unfiltered baseline.
        totals = {"pass": 0, "fail": 0, "skip": 0, "tests": 0}
        for vm in run["vms"].values():
            for sec in vm["sections"].values():
                for k, v in sec["totals"].items():
                    totals[k] += v
                totals["tests"] += sum(sec["totals"].values())
        run["totals"] = totals

    report_title = "fstests Run Report"
    title_bits: list[str] = []
    if kernel:
        title_bits.append(kernel)
    if hosts:
        title_bits.append(", ".join(sorted(hosts)))
    if title_bits:
        report_title += " — " + " / ".join(title_bits)
    report = html.Report(
        title=report_title,
        timestamp=datetime.now(),
    )
    _stat_cards(report, run)

    summary_html = _summary_text_section(results_dir, kernel=kernel)
    if summary_html:
        report.add_section("Run summary", summary_html)

    sources_html = _source_revisions_section(results_dir)
    if sources_html:
        report.add_section("Source revisions", sources_html)

    report.add_section("Pass / fail by section", _pass_fail_chart_html(run))

    test_timelines = _build_test_timelines(run, results_dir, kernel=kernel)
    host_monitoring_dirs = {
        vm_name: _host_monitoring_dir(results_dir, vm_name, kernel=kernel)
        for vm_name in run["vms"].keys()
    }
    monitoring_html = monitoring.render_section(
        host_monitoring_dirs,
        host_test_timelines=test_timelines,
        allowed_hosts=hosts,
    )
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
    parser.add_argument(
        "--host",
        action="append",
        default=[],
        metavar="HOST",
        help=(
            "Restrict the report to one host (VM) name; repeat the "
            "flag or pass a comma-separated list to include several. "
            "When unset all hosts under last-run/ are rendered."
        ),
    )
    parser.add_argument(
        "--kernel",
        default=None,
        metavar="KERNEL[,KERNEL]",
        help=(
            "Render the run archived under <vm>/<KERNEL>/ instead "
            "of following each VM's last-run symlink. Pass two "
            "comma-separated kernels (KERNEL_A,KERNEL_B) to render "
            "an A/B comparison report — regressions and fixes "
            "land at the top, per-section tables grow A/B status "
            "columns. VMs that don't have all requested kernel "
            "directories are silently skipped."
        ),
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir).resolve()
    if not results_dir.is_dir():
        print(f"results_dir not found: {results_dir}", file=sys.stderr)
        return 1

    # Accept "--host a,b" as a shortcut for "--host a --host b" so a
    # caller can pass a single argv entry (Makefile-friendly) and the
    # flag still feels natural when written by hand.
    hosts: set[str] = set()
    for raw in args.host:
        for h in raw.split(","):
            h = h.strip()
            if h:
                hosts.add(h)

    # --kernel accepts the same comma-separated form. One kernel
    # picks an archived single run; two kernels switch the report
    # to A/B mode; >2 is rejected because the diff/overlay model
    # is built around a 2-way comparison and a richer matrix view
    # would be a separate design.
    kernels: list[str] = []
    if args.kernel:
        for k in args.kernel.split(","):
            k = k.strip()
            if k:
                kernels.append(k)
    if len(kernels) > 2:
        print(
            f"--kernel takes at most 2 values for A/B mode, got {len(kernels)}: "
            + ", ".join(kernels),
            file=sys.stderr,
        )
        return 1

    if len(kernels) == 2:
        report = build_ab_report(
            results_dir, kernels=kernels, hosts=hosts or None,
        )
    else:
        report = build_report(
            results_dir,
            hosts=hosts or None,
            kernel=kernels[0] if kernels else None,
        )

    suffix_parts: list[str] = []
    if len(kernels) == 2:
        suffix_parts.append(f"{kernels[0]}-vs-{kernels[1]}")
    elif kernels:
        suffix_parts.append(kernels[0])
    if hosts:
        suffix_parts.append("_".join(sorted(hosts)))
    suffix = ("-" + "-".join(suffix_parts)) if suffix_parts else ""
    out_path = (
        Path(args.output) if args.output
        else (results_dir / f"fstests-report{suffix}.html")
    )
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

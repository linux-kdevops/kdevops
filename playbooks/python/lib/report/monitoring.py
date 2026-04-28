# SPDX-License-Identifier: copyleft-next-0.3.1
"""Render plots from the kdevops monitoring framework's output tree.

Layout convention written by playbooks/roles/monitoring/ and by the
nixos-qemu monitoring module:

    workflows/<workflow>/results/<vm>/<kernel>/monitoring/
    ├── sysstat/
    │   ├── sa-current           (binary sadc recording)
    │   └── sa-current.json      (sadf -j -- -A output)
    ├── cpu_governor/
    │   ├── start.json
    │   └── end.json
    ├── blockdev/
    │   ├── start.json           (sysfs-block + sysfs-class-nvme @ workflow start)
    │   └── end.json             (same surfaces @ workflow end)
    ├── nvme_ocp_smart/
    │   └── nvme_ocp_smart_<dev>_stats.txt
    ├── folio_migration/
    │   └── folio_migration_stats.txt
    └── fragmentation/
        ├── fragmentation_data.json
        └── fragmentation_plot.png

The <vm>/last-run -> <kernel> symlink at the per-VM root resolves
to the most-recent run, so a default-mode adapter can always walk
<vm>/last-run/monitoring/ to get the latest data without knowing
the kernel name.

This module knows how to walk that tree and produce HTML sections.
sysstat is the workhorse: its sa-current.json contains 14 metric
categories per sample; we plot a few of the most useful ones (CPU
load, memory, disk IO, run queue). Other monitor outputs that
already ship per-monitor PNGs are simply embedded as-is.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Optional

from . import charts, data, html


# Mapping from kernel ABI document name (the top-level key the
# monitor-blockdev collector emits) to the canonical sysfs path that
# document covers and the URL of the document itself. Adding a new
# surface to the collector only requires extending this dict — the
# renderer iterates whatever keys are present in the JSON. Keeping
# the path here (rather than embedding it in the JSON) means the
# label and the kernel ABI document name always agree, which was a
# specific reviewer ask: don't display "sysfs-class-nvme" next to
# "/sys/class/block/<dev>/device/" since the doc covers a different
# canonical path.
_BLOCKDEV_ABI_SURFACES = {
    "sysfs-block": {
        "path": "/sys/class/block/<dev>/",
        "doc": (
            "https://www.kernel.org/doc/Documentation/ABI/stable/"
            "sysfs-block"
        ),
    },
    "sysfs-class-nvme": {
        "path": "/sys/class/nvme/<ctrl>/",
        # /sys/class/nvme/<ctrl>/* is not covered by anything under
        # Documentation/ABI/{stable,testing}/. The attrs (model,
        # serial, firmware_rev, transport, ...) are documented only
        # in driver code (drivers/nvme/host/), so there is no stable
        # URL to link to and a constructed sysfs-class-nvme link
        # would 404. Keep the surface heading (it matches the
        # sysfs-class-<bus> naming convention) but skip the doc link.
        "doc": None,
    },
}


def has_data(host_monitoring_dirs: dict[str, Path]) -> bool:
    """True iff at least one (host, monitoring_dir) entry has data."""
    for d in host_monitoring_dirs.values():
        if d.is_dir() and any(d.iterdir()):
            return True
    return False


def _sysstat_samples(host_dir: Path) -> list[dict]:
    """Read sysstat sa-current.json and return the per-sample list."""
    j = data.read_json(host_dir / "sysstat" / "sa-current.json")
    if not j:
        return []
    hosts = j.get("sysstat", {}).get("hosts") or []
    if not hosts:
        return []
    return list(hosts[0].get("statistics") or [])


def _sample_index(samples: list[dict]) -> list[float]:
    """X-axis values for a sample series — second-offsets from sample 0."""
    if not samples:
        return []
    return [float(i * (samples[0]["timestamp"].get("interval", 1) or 1))
            for i in range(len(samples))]


def _sample_xlim(samples: list[dict]) -> Optional[tuple[float, float]]:
    """X-axis range for a sample series; None if no samples."""
    if not samples:
        return None
    interval = float(samples[0]["timestamp"].get("interval", 1) or 1)
    return (0.0, max(interval * (len(samples) - 1), interval))


def first_sample_timestamp(host_dir: Path) -> Optional[datetime]:
    """Wall-clock UTC timestamp of the first sysstat sample for a host.

    Returns None if no sysstat data is recorded for this host. Adapters
    use this to align test-run intervals with the sysstat chart x-axis,
    so the test timeline lines up visually with the CPU/memory/IO
    plots above it.
    """
    samples = _sysstat_samples(host_dir)
    if not samples:
        return None
    ts = samples[0]["timestamp"]
    date = ts.get("date")
    time_ = ts.get("time")
    if not date or not time_:
        return None
    try:
        return datetime.strptime(
            f"{date}T{time_}+0000", "%Y-%m-%dT%H:%M:%S%z",
        )
    except ValueError:
        return None


def _cpu_load_chart(
    host: str,
    samples: list[dict],
    *,
    test_intervals=None,
    chart_xlim=None,
) -> Optional[bytes]:
    """%user, %system, %iowait, %idle over time for the 'all' CPU."""
    xs = _sample_index(samples)
    series: dict[str, list[tuple[float, float]]] = {
        "user": [], "system": [], "iowait": [], "idle": [],
    }
    for x, sample in zip(xs, samples):
        for entry in sample.get("cpu-load") or []:
            if entry.get("cpu") != "all":
                continue
            for key in series:
                series[key].append((x, float(entry.get(key, 0.0))))
    return charts.timeline(
        series,
        title=f"CPU usage — {host}",
        xlabel="Seconds since start",
        ylabel="% of CPU time",
        test_intervals=test_intervals,
        chart_xlim=chart_xlim,
    )


def _memory_chart(
    host: str,
    samples: list[dict],
    *,
    test_intervals=None,
    chart_xlim=None,
) -> Optional[bytes]:
    """kbmemused / kbcached / kbavail over time."""
    xs = _sample_index(samples)
    series: dict[str, list[tuple[float, float]]] = {
        "memused": [], "cached": [], "available": [],
    }
    for x, sample in zip(xs, samples):
        mem = sample.get("memory") or {}
        # sadf -j wraps memory in a dict, not a list.
        if isinstance(mem, list):
            mem = mem[0] if mem else {}
        if "memused" in mem:
            series["memused"].append((x, float(mem["memused"]) / 1024.0))
        if "cached" in mem:
            series["cached"].append((x, float(mem["cached"]) / 1024.0))
        if "avail" in mem:
            series["available"].append((x, float(mem["avail"]) / 1024.0))
    return charts.timeline(
        series,
        title=f"Memory — {host}",
        xlabel="Seconds since start",
        ylabel="MiB",
        test_intervals=test_intervals,
        chart_xlim=chart_xlim,
    )


def _runqueue_chart(
    host: str,
    samples: list[dict],
    *,
    test_intervals=None,
    chart_xlim=None,
) -> Optional[bytes]:
    """Run queue length and load averages."""
    xs = _sample_index(samples)
    series: dict[str, list[tuple[float, float]]] = {
        "runq-sz": [], "ldavg-1": [], "ldavg-5": [],
    }
    for x, sample in zip(xs, samples):
        q = sample.get("queue") or {}
        if isinstance(q, list):
            q = q[0] if q else {}
        for key in series:
            if key in q:
                series[key].append((x, float(q[key])))
    return charts.timeline(
        series,
        title=f"Run queue + load — {host}",
        xlabel="Seconds since start",
        ylabel="Tasks / load avg",
        test_intervals=test_intervals,
        chart_xlim=chart_xlim,
    )


def _disk_io_chart(
    host: str,
    samples: list[dict],
    *,
    test_intervals=None,
    chart_xlim=None,
) -> Optional[bytes]:
    """Aggregate kB read/written per second across all disks."""
    xs = _sample_index(samples)
    series: dict[str, list[tuple[float, float]]] = {"read": [], "written": []}
    for x, sample in zip(xs, samples):
        disks = sample.get("disk") or []
        if not isinstance(disks, list):
            continue
        rk = sum(float(d.get("rkB", 0.0)) for d in disks)
        wk = sum(float(d.get("wkB", 0.0)) for d in disks)
        series["read"].append((x, rk))
        series["written"].append((x, wk))
    return charts.timeline(
        series,
        title=f"Disk I/O (aggregate) — {host}",
        xlabel="Seconds since start",
        ylabel="kB/s",
        test_intervals=test_intervals,
        chart_xlim=chart_xlim,
    )


def _load_blockdev(host_dir: Path) -> dict:
    """Read the workflow-start blockdev snapshot for one host.

    monitor-blockdev writes both start.json and end.json. The report
    cares about the configuration the workload ran *against*, so read
    start.json and ignore end.json (its only purpose right now is
    drift detection for cpu_governor-style "did anything change
    mid-run" follow-ups; left as a future enhancement).
    """
    p = host_dir / "blockdev" / "start.json"
    if not p.is_file():
        return {}
    try:
        return json.loads(p.read_text())
    except (OSError, json.JSONDecodeError):
        return {}


def _blockdev_flatten(dev: dict, prefix: str = "") -> dict[str, str]:
    """Flatten a single device record into ``{full/path: value}``.

    Subdirectories (queue/, device/, ...) become path-prefixed keys
    (``queue/scheduler``) so the diff/common logic works on a flat
    namespace and the rendered tables show the full sysfs-relative
    name of each attribute.
    """
    out: dict[str, str] = {}
    for k, v in dev.items():
        if isinstance(v, str):
            out[f"{prefix}{k}" if prefix else k] = v
        elif isinstance(v, dict):
            out.update(_blockdev_flatten(v, f"{prefix}{k}/"))
    return out


def _blockdev_split(devices: dict[str, dict]) -> tuple[dict, dict]:
    """Partition flattened attributes into common-vs-differing.

    A key is *common* only when every device reported it (so a missing
    file on one device cannot silently inherit another device's value)
    AND the reported byte-for-byte string is identical across every
    device (the collector strips trailing whitespace once and we do
    not normalise further, so a real ABI-level disagreement is never
    masked). Anything failing either condition lands in *differing*.
    """
    n = len(devices)
    by_key: dict[str, list[tuple[str, str]]] = {}
    for dev_name, dev in devices.items():
        for k, v in _blockdev_flatten(dev).items():
            by_key.setdefault(k, []).append((dev_name, v))
    common: dict[str, str] = {}
    differing: dict[str, dict[str, str]] = {}
    for key, observations in by_key.items():
        if len(observations) == n and len({v for _, v in observations}) == 1:
            common[key] = observations[0][1]
        else:
            differing[key] = {d: v for d, v in observations}
    return common, differing


def _blockdev_attr_table(attrs: dict[str, str]) -> str:
    rows = "".join(
        f'<tr><td><code>{escape(k)}</code></td>'
        f'<td><code>{escape(v)}</code></td></tr>'
        for k, v in sorted(attrs.items())
    )
    return (
        '<table><thead><tr><th>Attribute</th><th>Value</th></tr></thead>'
        f'<tbody>{rows}</tbody></table>'
    )


def _blockdev_pivot_table(
    differing: dict[str, dict[str, str]],
    devices: list[str],
) -> str:
    """Pivot table — rows=attribute, cols=device, cells=value.

    A "—" cell means the device did not report the attribute at all
    (file missing or unreadable). That is a deliberately distinct
    visual signal from a real differing value, so a reader can tell
    "it varies" apart from "it's only present on some devices".
    """
    head_cells = "".join(f"<th>{escape(d)}</th>" for d in devices)
    rows: list[str] = []
    for key in sorted(differing):
        per_dev = differing[key]
        cells = []
        for d in devices:
            v = per_dev.get(d)
            cells.append(
                f'<td><code>{escape(v)}</code></td>' if v is not None
                else '<td class="no-data">—</td>'
            )
        rows.append(
            f'<tr><td><code>{escape(key)}</code></td>{"".join(cells)}</tr>'
        )
    return (
        f'<table><thead><tr><th>Attribute</th>{head_cells}</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>'
    )


def _blockdev_device_summary(
    name: str,
    flat: dict[str, str],
    differing: dict[str, dict[str, str]],
) -> str:
    """Reality-grounded one-line summary for a per-device <details>.

    Lists the attributes that differ across the device set with the
    value this device actually reported, so the summary is grounded
    in real data rather than an editorial pick.

    Multi-line attributes (``uevent``, ``stat`` etc.) and long
    runtime counters are filtered out of the summary because they
    make the one-liner unreadable; they still show up in full
    inside the per-device table below. The cap of six short attrs
    keeps the summary scannable on hosts where many things differ
    (every NVMe namespace has its own dev/diskseq/wwid).
    """
    MAX_ATTRS = 6
    MAX_VALUE_CHARS = 48
    bits = [name]
    for k in sorted(differing):
        v = flat.get(k)
        if v is None or "\n" in v or len(v) > MAX_VALUE_CHARS:
            continue
        bits.append(f"{k}={v}")
        if len(bits) >= MAX_ATTRS + 1:  # +1 for the device name
            bits.append("…")
            break
    return escape(" — ".join(bits))


def _blockdev_surface(abi_name: str, devices: dict[str, dict]) -> str:
    """Render one ABI-document worth of devices as Common+Differing+per-device."""
    if not devices:
        return ""
    surface = _BLOCKDEV_ABI_SURFACES.get(abi_name) or {
        "path": "(unknown surface)",
        "doc": None,
    }
    common, differing = _blockdev_split(devices)
    device_names = sorted(devices.keys())
    n = len(device_names)

    parts: list[str] = []
    head = (
        f'<h5><code>{escape(abi_name)}</code> '
        f'<code style="font-weight:normal;color:#4a5568;">'
        f'{escape(surface["path"])}</code>'
    )
    if surface.get("doc"):
        head += (
            f' <a class="ext-link" href="{surface["doc"]}" '
            f'target="_blank" rel="noopener" '
            f'style="font-size:0.85em;">[kernel ABI]</a>'
        )
    head += '</h5>'
    parts.append(head)

    # All blocks default closed — a 50-attr Common table on every
    # host pushes the rest of the report off-screen. The headings
    # alone are enough to scan; expanding is one click away.
    if common:
        parts.append(
            '<details><summary><strong>Common</strong> '
            f'<span style="color:#718096;font-weight:normal;">'
            f'(identical across all {n} device(s) in this surface)'
            '</span></summary>'
        )
        parts.append(_blockdev_attr_table(common))
        parts.append('</details>')
    if differing:
        parts.append(
            '<details><summary><strong>Differing</strong> '
            f'<span style="color:#718096;font-weight:normal;">'
            f'({len(differing)} attribute(s) vary across devices)'
            '</span></summary>'
        )
        parts.append(_blockdev_pivot_table(differing, device_names))
        parts.append('</details>')

    # Per-device drill-down. Summary line shows the differing
    # values for this specific device (so a reader scanning the
    # collapsed list immediately sees what makes each one unique).
    # The body shows the *full* flattened attribute set for that
    # device, useful when troubleshooting a single device against
    # the kernel ABI document linked above.
    for dev_name in device_names:
        flat = _blockdev_flatten(devices[dev_name])
        summary = _blockdev_device_summary(dev_name, flat, differing)
        parts.append(f'<details><summary>{summary}</summary>')
        parts.append(_blockdev_attr_table(flat))
        parts.append('</details>')
    return "\n".join(parts)


def render_blockdev_section(host_dir: Path) -> Optional[str]:
    """Render this host's monitor-blockdev snapshot, or None if absent.

    Returns one sub-section per ABI surface present in the JSON,
    grouped by the kernel ABI document that defines its attributes.
    The collector auto-discovers files under each surface, so kernel
    additions show up without renderer changes.
    """
    data = _load_blockdev(host_dir)
    if not data:
        return None
    parts: list[str] = []
    parts.append(
        '<p style="margin:4px 0 8px 0;color:#4a5568;font-size:0.9em;">'
        'Snapshot taken when the workload started, grouped by the '
        'kernel ABI surface that defines each attribute. <strong>'
        'Common</strong> rows are identical across every device in '
        'the surface; <strong>Differing</strong> rows are pivoted '
        'per device (a "—" cell means the device did not report the '
        'attribute at all). The collector auto-discovers files under '
        'each surface, so kernel-added attributes appear without a '
        'script change.'
        '</p>'
    )
    for abi_name in sorted(data.keys()):
        chunk = _blockdev_surface(abi_name, data[abi_name])
        if chunk:
            parts.append(chunk)
    return "\n".join(parts) if len(parts) > 1 else None


# ---- Generic snapshot monitor rendering ----------------------------------
#
# Every snapshot-style monitor (boot_params, cpu_features,
# clocksource, vm_tuning, lsm, dmi, host_info) writes a JSON
# document to <host_dir>/<monitor>/{start,end}.json. The shapes
# differ but the rendering pattern is the same: flatten to
# {full/key: scalar}, pivot start vs end into Common (unchanged
# during the run) and Drift (changed mid-run), surface drift at
# the top so a reviewer notices it without expanding the section.


def _flatten_snapshot(d, prefix: str = "") -> dict[str, str]:
    """Flatten a snapshot JSON into ``{full/key: scalar}``.

    Nested dicts become ``parent/child`` keys. Lists are passed
    through as JSON-stringified values so they show up as a single
    row rather than expanding into N indexed rows. Scalars (str,
    int, float, bool, None) are kept as-is, stringified for HTML
    rendering downstream.
    """
    out: dict[str, str] = {}
    if not isinstance(d, dict):
        return out
    for k, v in d.items():
        full = f"{prefix}{k}" if prefix else str(k)
        if isinstance(v, dict):
            out.update(_flatten_snapshot(v, prefix=f"{full}/"))
        elif isinstance(v, list):
            out[full] = json.dumps(v, sort_keys=True)
        else:
            out[full] = "" if v is None else str(v)
    return out


def _parse_fastfetch(data):
    """Convert fastfetch's array-of-objects output into a dict.

    fastfetch --format json emits ``[{"type": "OS", "result": {...}}, ...]``;
    the host_info renderer wants a top-level dict keyed by module
    name so the rest of the pipeline (flatten + pivot) works the
    same way as the other snapshot monitors.
    """
    if not isinstance(data, list):
        return {}
    out: dict = {}
    for entry in data:
        if not isinstance(entry, dict):
            continue
        t = entry.get("type")
        if not t:
            continue
        if "error" in entry:
            out[t] = {"error": entry["error"]}
        else:
            r = entry.get("result")
            if isinstance(r, (dict, list, str, int, float, bool)) or r is None:
                out[t] = r if isinstance(r, dict) else {"value": r}
    return out


def _render_snapshot_section(
    host_dir: Path,
    monitor_name: str,
    title: str,
    *,
    parser=None,
    intro: Optional[str] = None,
) -> Optional[str]:
    """Render a snapshot monitor's start/end pivot as an HTML section.

    Returns None when the monitor produced no start.json (the
    monitor was disabled, the guest didn't have the data, or the
    file is unreadable). When start.json exists but end.json does
    not, the renderer treats the run as "still running" and only
    shows the start data without drift detection.
    """
    p_start = host_dir / monitor_name / "start.json"
    p_end = host_dir / monitor_name / "end.json"
    if not p_start.is_file():
        return None
    try:
        start_data = json.loads(p_start.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    end_data: object = {}
    if p_end.is_file():
        try:
            end_data = json.loads(p_end.read_text())
        except (OSError, json.JSONDecodeError):
            end_data = {}

    if parser is not None:
        start_data = parser(start_data)
        end_data = parser(end_data) if end_data else {}

    flat_start = _flatten_snapshot(start_data)
    flat_end = _flatten_snapshot(end_data)

    keys = sorted(set(flat_start) | set(flat_end))
    common: dict[str, str] = {}
    drift: dict[str, tuple[str, str]] = {}
    for k in keys:
        s = flat_start.get(k, "")
        e = flat_end.get(k, "")
        if not flat_end:
            common[k] = s  # no end snapshot yet — treat as common
        elif s == e:
            common[k] = s
        else:
            drift[k] = (s, e)

    parts: list[str] = [f"<h4>{escape(title)}</h4>"]
    if intro:
        parts.append(intro)
    if drift:
        parts.append(
            '<p class="failure" style="margin:4px 0 8px 0;">'
            f'⚠ {len(drift)} attribute(s) drifted between start and end '
            'of the run — expand the Drift block below to inspect.'
            '</p>'
        )

    summary_bits = []
    if common:
        summary_bits.append(f"{len(common)} stable")
    if drift:
        summary_bits.append(f"{len(drift)} drift")
    summary = ", ".join(summary_bits) or "no data"

    parts.append(
        f'<details><summary>Show <span style="color:#718096;'
        f'font-weight:normal;">({escape(summary)})</span></summary>'
    )

    if drift:
        rows = "".join(
            f'<tr><td><code>{escape(k)}</code></td>'
            f'<td><code>{escape(s)}</code></td>'
            f'<td><code>{escape(e)}</code></td></tr>'
            for k, (s, e) in sorted(drift.items())
        )
        parts.append(
            '<details open><summary><strong class="failure">Drift</strong></summary>'
            '<table><thead><tr><th>Attribute</th><th>start.json</th>'
            '<th>end.json</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            '</details>'
        )

    if common:
        rows = "".join(
            f'<tr><td><code>{escape(k)}</code></td>'
            f'<td><code>{escape(v)}</code></td></tr>'
            for k, v in sorted(common.items())
        )
        parts.append(
            '<details><summary><strong>Stable</strong></summary>'
            '<table><thead><tr><th>Attribute</th><th>Value</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>'
            '</details>'
        )

    parts.append('</details>')
    return "\n".join(parts)


def render_host_info_section(host_dir: Path) -> Optional[str]:
    """fastfetch — host identity (OS, CPU, BIOS, packages, ...)."""
    return _render_snapshot_section(
        host_dir, "host_info", "Host identity (fastfetch)",
        parser=_parse_fastfetch,
    )


def render_boot_params_section(host_dir: Path) -> Optional[str]:
    """Kernel boot parameters (cmdline, version, taint, ASLR)."""
    return _render_snapshot_section(
        host_dir, "boot_params", "Kernel boot parameters",
    )


def render_cpu_features_section(host_dir: Path) -> Optional[str]:
    """CPU features and mitigations (vulnerabilities, smt, microcode)."""
    return _render_snapshot_section(
        host_dir, "cpu_features", "CPU features and mitigations",
    )


def render_clocksource_section(host_dir: Path) -> Optional[str]:
    """Clocksource selection (current and available)."""
    return _render_snapshot_section(
        host_dir, "clocksource", "Clocksource",
    )


def render_vm_tuning_section(host_dir: Path) -> Optional[str]:
    """Virtual-memory tuning (THP and /proc/sys/vm/* sysctls)."""
    return _render_snapshot_section(
        host_dir, "vm_tuning", "Virtual-memory tuning",
    )


def render_lsm_section(host_dir: Path) -> Optional[str]:
    """Linux Security Module status and EFI presence."""
    return _render_snapshot_section(
        host_dir, "lsm", "Linux Security Module status",
    )


def render_dmi_section(host_dir: Path) -> Optional[str]:
    """DMI/firmware identity tree."""
    return _render_snapshot_section(
        host_dir, "dmi", "DMI / firmware identity",
    )


def _governor_section(host_dir: Path) -> str:
    """Render a small table of {start,end} CPU governors per CPU."""
    start = data.read_json(host_dir / "cpu_governor" / "start.json") or {}
    end = data.read_json(host_dir / "cpu_governor" / "end.json") or {}
    govs_start = (start.get("governors") or {})
    govs_end = (end.get("governors") or {})
    cpus = sorted(set(govs_start) | set(govs_end))
    if not cpus:
        return ""
    rows = []
    for cpu in cpus:
        s = govs_start.get(cpu, "")
        e = govs_end.get(cpu, "")
        cls = "" if s == e else "failure"
        rows.append(
            f'<tr><td>{escape(cpu)}</td><td>{escape(s)}</td>'
            f'<td class="{cls}">{escape(e)}</td></tr>'
        )
    return (
        "<table>"
        "<thead><tr><th>CPU</th><th>governor at start</th>"
        "<th>governor at end</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )


def render_host_section(
    host_dir: Path,
    test_timeline: Optional[list[tuple[str, float, float, str]]] = None,
) -> Optional[str]:
    """Render the per-host monitoring HTML, or None if empty.

    Per-metric headings are <h4> so they nest under the per-host
    <h3> the section renderer emits, which in turn nests under the
    enclosing <h2 class="section-title">. This keeps the TOC tree
    well-formed without collapsing chart titles into top-level
    entries.

    ``test_timeline`` is an optional list of (test_name, x_start,
    duration, status) tuples — when provided, an extra "Test
    execution timeline" chart renders below the metric charts with
    the same x-axis range so a reviewer can correlate test names
    with monitoring spikes.
    """
    host = host_dir.name
    body_parts: list[str] = []

    samples = _sysstat_samples(host_dir)
    xlim = _sample_xlim(samples)
    if samples:
        for plot_fn, label in (
            (_cpu_load_chart, "CPU usage"),
            (_memory_chart, "Memory"),
            (_runqueue_chart, "Run queue + load average"),
            (_disk_io_chart, "Disk I/O"),
        ):
            png = plot_fn(
                host, samples,
                test_intervals=test_timeline,
                chart_xlim=xlim,
            )
            body_parts.append(f"<h4>{escape(label)}</h4>")
            body_parts.append(html.chart_block(
                html.embed_png(png) if png else None,
                no_data_msg=f"{label} chart unavailable",
            ))

    if test_timeline:
        png = charts.test_timeline(
            test_timeline,
            title=f"Test execution timeline — {host}",
            chart_xlim=xlim,
        )
        body_parts.append("<h4>Test execution timeline</h4>")
        body_parts.append(html.chart_block(
            html.embed_png(png) if png else None,
            no_data_msg="Test timeline chart unavailable",
        ))

    governor_html = _governor_section(host_dir)
    if governor_html:
        body_parts.append("<h4>CPU governor</h4>")
        body_parts.append(governor_html)

    blockdev_html = render_blockdev_section(host_dir)
    if blockdev_html:
        body_parts.append("<h4>Storage device sysfs settings</h4>")
        body_parts.append(blockdev_html)

    # Per-monitor snapshot sections — one h4 per monitor, each
    # rendered as a Common/Drift pivot between start.json and
    # end.json. Order matches the Kconfig listing.
    for renderer in (
        render_host_info_section,
        render_boot_params_section,
        render_cpu_features_section,
        render_clocksource_section,
        render_vm_tuning_section,
        render_lsm_section,
        render_dmi_section,
    ):
        chunk = renderer(host_dir)
        if chunk:
            body_parts.append(chunk)

    if not body_parts:
        return None
    return "\n".join(body_parts)


# ---- A/B (two-kernel) per-host monitoring overlay ------------------------


def _cpu_load_series(samples: list[dict]) -> dict[str, list[tuple[float, float]]]:
    """Extract %user/%system/%iowait/%idle series for the 'all' CPU."""
    xs = _sample_index(samples)
    out: dict[str, list[tuple[float, float]]] = {
        "user": [], "system": [], "iowait": [], "idle": [],
    }
    for x, sample in zip(xs, samples):
        for entry in sample.get("cpu-load") or []:
            if entry.get("cpu") != "all":
                continue
            for key in out:
                out[key].append((x, float(entry.get(key, 0.0))))
    return out


def _memory_series(samples: list[dict]) -> dict[str, list[tuple[float, float]]]:
    xs = _sample_index(samples)
    out: dict[str, list[tuple[float, float]]] = {
        "memused": [], "cached": [], "available": [],
    }
    for x, sample in zip(xs, samples):
        mem = sample.get("memory") or {}
        if isinstance(mem, list):
            mem = mem[0] if mem else {}
        if "memused" in mem:
            out["memused"].append((x, float(mem["memused"]) / 1024.0))
        if "cached" in mem:
            out["cached"].append((x, float(mem["cached"]) / 1024.0))
        if "avail" in mem:
            out["available"].append((x, float(mem["avail"]) / 1024.0))
    return out


def _runqueue_series(samples: list[dict]) -> dict[str, list[tuple[float, float]]]:
    xs = _sample_index(samples)
    out: dict[str, list[tuple[float, float]]] = {
        "runq-sz": [], "ldavg-1": [], "ldavg-5": [],
    }
    for x, sample in zip(xs, samples):
        q = sample.get("queue") or {}
        if isinstance(q, list):
            q = q[0] if q else {}
        for key in out:
            if key in q:
                out[key].append((x, float(q[key])))
    return out


def _disk_io_series(samples: list[dict]) -> dict[str, list[tuple[float, float]]]:
    xs = _sample_index(samples)
    out: dict[str, list[tuple[float, float]]] = {"read": [], "written": []}
    for x, sample in zip(xs, samples):
        disks = sample.get("disk") or []
        if not isinstance(disks, list):
            continue
        rk = sum(float(d.get("rkB", 0.0)) for d in disks)
        wk = sum(float(d.get("wkB", 0.0)) for d in disks)
        out["read"].append((x, rk))
        out["written"].append((x, wk))
    return out


def render_host_section_ab(
    host_dirs: dict[str, Path],
    *,
    kernels: list[str],
    test_timelines: Optional[
        dict[str, list[tuple[str, float, float, str]]]
    ] = None,
) -> Optional[str]:
    """Per-host A/B monitoring block — overlay metric charts for two kernels.

    ``host_dirs`` maps each kernel name to that kernel's monitoring
    directory for this host (typically
    ``<results>/<vm>/<kernel>/monitoring/``). Both kernels' samples
    are loaded, fed to the four metric extractors, and rendered as
    overlay charts via charts.timeline_ab — the line colour identifies
    the metric, the line style identifies the kernel.

    Test execution timelines are rendered as separate strips (one per
    kernel) underneath so the per-kernel test-name labels stay legible.
    The CPU governor and blockdev sub-sections render once per kernel
    sequentially below; their natural shape (key/value tables, not
    time series) doesn't gain anything from overlay.
    """
    if not kernels or len(kernels) != 2:
        return None

    body_parts: list[str] = []
    timelines = test_timelines or {}

    samples_by_kernel = {k: _sysstat_samples(host_dirs[k]) for k in kernels}
    # Use the longer sample set's xlim so neither kernel is clipped.
    xlim_candidates = [
        _sample_xlim(samples_by_kernel[k]) for k in kernels
    ]
    xlim = max(
        (c for c in xlim_candidates if c is not None),
        default=None,
        key=lambda c: c[1],
    )

    if any(samples_by_kernel.values()):
        # Pick the kernel-A timeline as the underlay anchor; if absent,
        # fall back to kernel-B. Overlay timelines are rendered as
        # separate strips below so the underlay only needs one anchor.
        anchor_timeline = (
            timelines.get(kernels[0]) or timelines.get(kernels[1])
        )
        for extractor, label, ylabel in (
            (_cpu_load_series, "CPU usage",       "% of CPU time"),
            (_memory_series,    "Memory",         "MiB"),
            (_runqueue_series,  "Run queue + load average", "Tasks / load avg"),
            (_disk_io_series,   "Disk I/O",       "kB/s"),
        ):
            series_by_kernel = {
                k: extractor(samples_by_kernel[k]) for k in kernels
            }
            png = charts.timeline_ab(
                series_by_kernel,
                title=label,
                kernels=kernels,
                xlabel="Seconds since start",
                ylabel=ylabel,
                test_intervals=anchor_timeline,
                chart_xlim=xlim,
            )
            body_parts.append(f"<h4>{escape(label)}</h4>")
            body_parts.append(html.chart_block(
                html.embed_png(png) if png else None,
                no_data_msg=f"{label} chart unavailable",
            ))

    # Per-kernel test execution timeline strips.
    for kernel in kernels:
        intervals = timelines.get(kernel)
        if not intervals:
            continue
        png = charts.test_timeline(
            intervals,
            title=f"Test execution timeline · {kernel}",
            chart_xlim=xlim,
        )
        body_parts.append(f"<h4>Test execution timeline · {escape(kernel)}</h4>")
        body_parts.append(html.chart_block(
            html.embed_png(png) if png else None,
            no_data_msg="Test timeline chart unavailable",
        ))

    # Per-kernel governor + blockdev (sequential, not overlaid — the
    # data shape is key/value, comparison reads better as side-by-side
    # tables than as a chart).
    for kernel in kernels:
        gov_html = _governor_section(host_dirs[kernel])
        if gov_html:
            body_parts.append(f"<h4>CPU governor · {escape(kernel)}</h4>")
            body_parts.append(gov_html)
        bd_html = render_blockdev_section(host_dirs[kernel])
        if bd_html:
            body_parts.append(
                f"<h4>Storage device sysfs settings · {escape(kernel)}</h4>"
            )
            body_parts.append(bd_html)

    if not body_parts:
        return None
    return "\n".join(body_parts)


def render_section_ab(
    host_kernel_dirs: dict[str, dict[str, Path]],
    *,
    kernels: list[str],
    host_test_timelines_ab: Optional[
        dict[str, dict[str, list[tuple[str, float, float, str]]]]
    ] = None,
    allowed_hosts: Optional[set[str]] = None,
) -> Optional[str]:
    """A/B monitoring section — one overlay block per host, two kernels.

    ``host_kernel_dirs`` maps each host name to a per-kernel mapping
    of monitoring directories. Hosts that don't have *both* kernels'
    monitoring data are skipped — the chart only makes sense when
    both lines have something to plot.

    ``host_test_timelines_ab`` is an optional matching nested dict
    mapping host → kernel → intervals so the test-execution underlays
    align with the same x-axis as the metric overlay.
    """
    if not host_kernel_dirs:
        return None
    timelines_ab = host_test_timelines_ab or {}
    chunks: list[str] = []
    for host_name in sorted(host_kernel_dirs.keys()):
        if allowed_hosts is not None and host_name not in allowed_hosts:
            continue
        host_dirs = host_kernel_dirs[host_name]
        if not all(k in host_dirs and host_dirs[k].is_dir() for k in kernels):
            continue
        host_block = render_host_section_ab(
            host_dirs,
            kernels=kernels,
            test_timelines=timelines_ab.get(host_name),
        )
        if not host_block:
            continue
        chunks.append(f'<h3>{escape(host_name)}</h3>')
        chunks.append(host_block)
    return "\n".join(chunks) if chunks else None


def render_section(
    host_monitoring_dirs: dict[str, Path],
    host_test_timelines: Optional[
        dict[str, list[tuple[str, float, float, str]]]
    ] = None,
    allowed_hosts: Optional[set[str]] = None,
) -> Optional[str]:
    """Render the whole monitoring section (per-host blocks). None if empty.

    ``host_monitoring_dirs`` maps a host name (kdevops VM name) to
    its monitoring directory — typically
    ``<results>/<vm>/last-run/monitoring/`` for the most recent
    run, or ``<results>/<vm>/<kernel>/monitoring/`` when an adapter
    is rendering a specific historical kernel. Each monitoring dir
    contains the per-monitor subdirs (sysstat/, cpu_governor/,
    blockdev/, …); the per-VM scoping comes from the dict, not from
    a per-host subdir under one shared root, because the monitoring
    framework's output now lives next to the test artifacts of the
    same run.

    ``host_test_timelines`` is an optional mapping from host name to
    test-interval tuples. Adapters that know the workflow's test
    schedule (e.g. fstests parsing the xunit XML) build this and pass
    it in so each per-host block gets a matching timeline chart.

    ``allowed_hosts`` is an optional whitelist; hosts not in the set
    are skipped so the monitoring section narrows down to the same
    hosts the rest of the report renders for.
    """
    if not has_data(host_monitoring_dirs):
        return None
    timelines = host_test_timelines or {}
    chunks: list[str] = []
    for host_name in sorted(host_monitoring_dirs.keys()):
        if allowed_hosts is not None and host_name not in allowed_hosts:
            continue
        host_dir = host_monitoring_dirs[host_name]
        if not host_dir.is_dir():
            continue
        host_block = render_host_section(
            host_dir,
            test_timeline=timelines.get(host_name),
        )
        if not host_block:
            continue
        chunks.append(f'<h3>{escape(host_name)}</h3>')
        chunks.append(host_block)
    return "\n".join(chunks) if chunks else None

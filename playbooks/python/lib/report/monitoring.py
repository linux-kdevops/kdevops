# SPDX-License-Identifier: copyleft-next-0.3.1
"""Render plots from the kdevops monitoring framework's output tree.

Layout convention written by playbooks/roles/monitoring/ and by the
nixos-qemu monitoring module:

    workflows/<workflow>/results/monitoring/<host>/
    ├── sysstat/
    │   ├── sa-current           (binary sadc recording)
    │   └── sa-current.json      (sadf -j -- -A output)
    ├── cpu_governor/
    │   ├── start.json
    │   └── end.json
    ├── nvme_ocp_smart/
    │   └── nvme_ocp_smart_<dev>_stats.txt
    ├── folio_migration/
    │   └── folio_migration_stats.txt
    └── fragmentation/
        ├── fragmentation_data.json
        └── fragmentation_plot.png

This module knows how to walk that tree and produce HTML sections.
sysstat is the workhorse: its sa-current.json contains 14 metric
categories per sample; we plot a few of the most useful ones (CPU
load, memory, disk IO, run queue). Other monitor outputs that
already ship per-monitor PNGs are simply embedded as-is.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Optional

from . import charts, data, html


def has_data(monitoring_dir: Path) -> bool:
    """True iff at least one host subdir under monitoring_dir is non-empty."""
    if not monitoring_dir.is_dir():
        return False
    for host_dir in monitoring_dir.iterdir():
        if host_dir.is_dir() and any(host_dir.iterdir()):
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


def _cpu_load_chart(host: str, samples: list[dict]) -> Optional[bytes]:
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
    )


def _memory_chart(host: str, samples: list[dict]) -> Optional[bytes]:
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
    )


def _runqueue_chart(host: str, samples: list[dict]) -> Optional[bytes]:
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
    )


def _disk_io_chart(host: str, samples: list[dict]) -> Optional[bytes]:
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


def render_host_section(host_dir: Path) -> Optional[str]:
    """Render the per-host monitoring HTML, or None if empty.

    Per-metric headings are <h4> so they nest under the per-host
    <h3> the section renderer emits, which in turn nests under the
    enclosing <h2 class="section-title">. This keeps the TOC tree
    well-formed without collapsing chart titles into top-level
    entries.
    """
    host = host_dir.name
    body_parts: list[str] = []

    samples = _sysstat_samples(host_dir)
    if samples:
        for plot_fn, label in (
            (_cpu_load_chart, "CPU usage"),
            (_memory_chart, "Memory"),
            (_runqueue_chart, "Run queue + load average"),
            (_disk_io_chart, "Disk I/O"),
        ):
            png = plot_fn(host, samples)
            body_parts.append(f"<h4>{escape(label)}</h4>")
            body_parts.append(html.chart_block(
                html.embed_png(png) if png else None,
                no_data_msg=f"{label} chart unavailable",
            ))

    governor_html = _governor_section(host_dir)
    if governor_html:
        body_parts.append("<h4>CPU governor</h4>")
        body_parts.append(governor_html)

    if not body_parts:
        return None
    return "\n".join(body_parts)


def render_section(monitoring_dir: Path) -> Optional[str]:
    """Render the whole monitoring section (per-host blocks). None if empty."""
    if not has_data(monitoring_dir):
        return None
    chunks: list[str] = []
    for host_dir in sorted(monitoring_dir.iterdir()):
        if not host_dir.is_dir():
            continue
        host_block = render_host_section(host_dir)
        if not host_block:
            continue
        chunks.append(f'<h3>{escape(host_dir.name)}</h3>')
        chunks.append(host_block)
    return "\n".join(chunks) if chunks else None

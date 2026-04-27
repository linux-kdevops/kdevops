# SPDX-License-Identifier: copyleft-next-0.3.1
"""Multi-run comparison: delta tables and overlay charts.

Comparison takes a list of (label, results_dir) pairs (each typically
unpacked from a <kernel>.tar.xz archive) and produces a side-by-side
view. The library provides primitives only — workflow adapters decide
which metrics are interesting to compare and how to present deltas.
"""

from __future__ import annotations

import dataclasses
from html import escape
from pathlib import Path
from typing import Callable, Optional

from . import charts, html, manifest, monitoring


@dataclasses.dataclass
class Run:
    """One side of a comparison."""
    label: str
    results_dir: Path
    manifest: manifest.Manifest = dataclasses.field(default_factory=manifest.Manifest)


def load_run(label: str, results_dir: Path) -> Run:
    """Load a Run from a results directory. Reads the manifest if present."""
    return Run(
        label=label,
        results_dir=results_dir,
        manifest=manifest.Manifest.from_path(results_dir),
    )


def delta_table(
    runs: list[Run],
    rows: list[tuple[str, list[str]]],
    *,
    highlight_changed: bool = True,
) -> str:
    """Render a delta table.

    ``rows`` is a list of (row_label, [value_per_run]) pairs. When
    ``highlight_changed`` is True, the last column gets a CSS class
    indicating success (unchanged) or failure (changed) relative to
    the first column.
    """
    if not rows:
        return ""

    headers = "<th>Metric</th>" + "".join(
        f"<th>{escape(r.label)}</th>" for r in runs
    )
    body_rows = []
    for label, values in rows:
        cells = [f"<td>{escape(label)}</td>"]
        baseline = values[0] if values else ""
        for idx, v in enumerate(values):
            cls = ""
            # Only highlight columns AFTER the baseline (idx > 0) that
            # differ from it. The baseline column is reference, not a
            # delta, so it should not be flagged.
            if highlight_changed and idx > 0 and v != baseline:
                cls = " class=\"failure\""
            cells.append(f"<td{cls}>{escape(str(v))}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")

    return (
        "<table>"
        f"<thead><tr>{headers}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )


def overlay_metric(
    runs: list[Run],
    extract: Callable[[Run], list[tuple[float, float]]],
    *,
    title: str,
    xlabel: str = "Sample",
    ylabel: str = "Value",
) -> Optional[bytes]:
    """Plot the same metric from multiple runs on shared axes.

    ``extract`` is a callable that takes a Run and returns a sequence
    of (x, y) points; charts.timeline() draws them with a legend.
    """
    series: dict[str, list[tuple[float, float]]] = {}
    for run in runs:
        points = extract(run)
        if points:
            series[run.label] = points
    return charts.timeline(series, title=title, xlabel=xlabel, ylabel=ylabel)


def render_monitoring_overlay(
    runs: list[Run],
    *,
    host: str,
    metric: str,
) -> Optional[bytes]:
    """Overlay one sysstat metric ('user', 'memused', 'runq-sz', etc.)
    across runs for a single host. Returns None if the metric is not
    found in any run.
    """

    def _extract(run: Run) -> list[tuple[float, float]]:
        host_dir = run.results_dir / "monitoring" / host
        samples = monitoring._sysstat_samples(host_dir)
        if not samples:
            return []
        out: list[tuple[float, float]] = []
        interval = float(samples[0]["timestamp"].get("interval", 1) or 1)
        for i, sample in enumerate(samples):
            x = float(i * interval)
            for category in ("cpu-load", "memory", "queue", "disk"):
                bucket = sample.get(category)
                if bucket is None:
                    continue
                if isinstance(bucket, list):
                    for entry in bucket:
                        if metric in entry:
                            out.append((x, float(entry[metric])))
                            break
                elif isinstance(bucket, dict) and metric in bucket:
                    out.append((x, float(bucket[metric])))
        return out

    return overlay_metric(
        runs,
        _extract,
        title=f"{metric} across runs — {host}",
        xlabel="Seconds since start",
        ylabel=metric,
    )

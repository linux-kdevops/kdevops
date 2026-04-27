# SPDX-License-Identifier: copyleft-next-0.3.1
"""matplotlib helpers that return PNG bytes ready for HTML embedding.

All helpers return either bytes (encoded PNG) or None when matplotlib
is not installed. Callers should pass the result to html.embed_png()
or chart_block() and let the template fall back to a no-data message.
"""

from __future__ import annotations

from io import BytesIO
from typing import Optional

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    _AVAILABLE = True
except ImportError:
    _AVAILABLE = False


def available() -> bool:
    """Return True if matplotlib is importable."""
    return _AVAILABLE


def _save_close(fig) -> bytes:
    """Save a matplotlib Figure as PNG bytes and close it."""
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    return buf.getvalue()


def comparison_bar(
    labels: list[str],
    values: list[float],
    *,
    error_low: Optional[list[float]] = None,
    error_high: Optional[list[float]] = None,
    title: str,
    ylabel: str,
    xlabel: str = "",
    value_unit: str = "",
) -> Optional[bytes]:
    """Bar chart with optional asymmetric error bars and value labels."""
    if not _AVAILABLE or not labels:
        return None

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(labels))
    bars = ax.bar(x, values, 0.6, color="steelblue")

    if error_low is not None and error_high is not None:
        errs = [
            [v - lo for v, lo in zip(values, error_low)],
            [hi - v for v, hi in zip(values, error_high)],
        ]
        ax.errorbar(x, values, yerr=errs, fmt="none", color="black",
                    capsize=5, alpha=0.4, linewidth=1)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.grid(True, alpha=0.3, axis="y")

    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                f"{v:.1f}{value_unit}", ha="center", va="bottom",
                fontsize=9, fontweight="bold")

    plt.subplots_adjust(bottom=0.18, top=0.92)
    return _save_close(fig)


def box_plot(
    labels: list[str],
    datasets: list[list[float]],
    *,
    title: str,
    ylabel: str,
    xlabel: str = "",
) -> Optional[bytes]:
    """Box plot for distribution comparison across categories."""
    if not _AVAILABLE or not datasets:
        return None

    fig, ax = plt.subplots(figsize=(12, 6))
    bp = ax.boxplot(datasets, tick_labels=labels, patch_artist=True)
    colors = plt.cm.Set3(np.linspace(0, 1, len(datasets)))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3, axis="y")
    plt.xticks(rotation=45, ha="right")
    plt.subplots_adjust(bottom=0.18, top=0.92)
    return _save_close(fig)


def timeline(
    series: dict[str, list[tuple[float, float]]],
    *,
    title: str,
    xlabel: str = "Sample",
    ylabel: str = "Value",
) -> Optional[bytes]:
    """Multi-series line plot. ``series`` maps a label to (x, y) pairs."""
    if not _AVAILABLE or not series:
        return None

    fig, ax = plt.subplots(figsize=(14, 6))
    plotted_any = False
    for label, points in series.items():
        if not points:
            continue
        xs, ys = zip(*points)
        ax.plot(xs, ys, label=label, marker="o", markersize=3, linewidth=1)
        plotted_any = True

    if not plotted_any:
        plt.close(fig)
        return None

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)
    plt.subplots_adjust(bottom=0.12, top=0.92)
    return _save_close(fig)


def test_timeline(
    intervals: list[tuple[str, float, float, str]],
    *,
    title: str,
    xlabel: str = "Seconds since first sysstat sample",
    label_every: int = 10,
    chart_xlim: Optional[tuple[float, float]] = None,
) -> Optional[bytes]:
    """Horizontal carpet of test runs: name, start, duration, status.

    ``intervals`` is a list of ``(test_name, x_start, duration, status)``
    tuples; ``status`` is one of ``"pass"``, ``"fail"``, ``"skip"``.
    Each test renders as a horizontal segment colored by status. Names
    are labelled for every Nth test and always for failures so the
    readout stays legible at 50+ tests.

    When ``chart_xlim`` is provided the axis matches the sysstat
    charts' (0, max-sample) range so visual correlation between the
    timeline and the metric charts above it works at a glance.
    """
    if not _AVAILABLE or not intervals:
        return None

    fig, ax = plt.subplots(figsize=(14, 2.6))

    color_map = {
        "pass": "#48bb78",
        "fail": "#f56565",
        "skip": "#a0aec0",
    }
    for name, start, duration, status in intervals:
        ax.barh(
            0,
            max(duration, 0.5),  # tiny floor so 0-second tests stay visible
            left=start,
            color=color_map.get(status, "#cbd5e0"),
            edgecolor="white",
            linewidth=0.4,
        )

    # Label every Nth test + always failures.
    last_label_x = -1e9
    min_label_gap = (intervals[-1][1] + intervals[-1][2]) / 30 or 1.0
    for i, (name, start, duration, status) in enumerate(intervals):
        is_failure = status == "fail"
        is_periodic = (i % label_every == 0) or i == len(intervals) - 1
        if not (is_failure or is_periodic):
            continue
        x_center = start + duration / 2
        if (x_center - last_label_x) < min_label_gap and not is_failure:
            continue
        last_label_x = x_center
        short = name.split("/", 1)[-1] if "/" in name else name
        ax.text(
            x_center, 0.55, short,
            ha="center", va="bottom",
            fontsize=7,
            rotation=45,
            color="#c53030" if is_failure else "#2d3748",
            fontweight="bold" if is_failure else "normal",
        )

    ax.set_yticks([])
    ax.set_ylim(-0.5, 1.5)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    if chart_xlim is not None:
        ax.set_xlim(*chart_xlim)
    else:
        end = intervals[-1][1] + intervals[-1][2]
        ax.set_xlim(0, max(end, 1.0))

    # Legend
    from matplotlib.patches import Patch
    legend_handles = [
        Patch(color="#48bb78", label="pass"),
        Patch(color="#f56565", label="fail"),
        Patch(color="#a0aec0", label="skip"),
    ]
    ax.legend(handles=legend_handles, loc="upper right", fontsize=8,
              framealpha=0.85)

    plt.subplots_adjust(bottom=0.35, top=0.82, left=0.05, right=0.98)
    return _save_close(fig)


def stacked_pass_fail(
    labels: list[str],
    passed: list[int],
    failed: list[int],
    *,
    title: str,
    ylabel: str = "Count",
) -> Optional[bytes]:
    """Pass/fail stacked bar chart."""
    if not _AVAILABLE or not labels:
        return None

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(labels))
    ax.bar(x, passed, 0.6, color="#48bb78", label="Pass")
    ax.bar(x, failed, 0.6, bottom=passed, color="#f56565", label="Fail")

    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    plt.subplots_adjust(bottom=0.18, top=0.92)
    return _save_close(fig)

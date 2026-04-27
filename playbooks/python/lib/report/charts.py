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
    for label, points in series.items():
        if not points:
            continue
        xs, ys = zip(*points)
        ax.plot(xs, ys, label=label, marker="o", markersize=3, linewidth=1)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)
    plt.subplots_adjust(bottom=0.12, top=0.92)
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

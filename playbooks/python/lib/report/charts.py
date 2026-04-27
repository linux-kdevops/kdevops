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


# Time-series and timeline charts that align stacked under one another in
# the per-host monitoring section share these dimensions. Saving without
# bbox_inches="tight" keeps the rendered PNG width fixed at FIG_W * dpi
# regardless of how much the matplotlib auto-trim would have shaved off
# (legends, y-axis label widths) — otherwise the metric charts come out
# narrower than the timeline strip and visual correlation falls apart.
_TS_FIG_W = 14
_TS_DPI = 100
_TS_LEFT = 0.06
_TS_RIGHT = 0.985


def _save_close(fig, *, tight: bool = True) -> bytes:
    """Save a matplotlib Figure as PNG bytes and close it.

    Set ``tight=False`` to keep the figure at its declared figsize so
    sibling charts that subplots_adjust to identical left/right margins
    render at exactly the same pixel width.
    """
    buf = BytesIO()
    if tight:
        fig.savefig(buf, format="png", dpi=100, bbox_inches="tight")
    else:
        fig.savefig(buf, format="png", dpi=_TS_DPI)
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
    test_intervals: Optional[list[tuple[str, float, float, str]]] = None,
    chart_xlim: Optional[tuple[float, float]] = None,
) -> Optional[bytes]:
    """Multi-series line plot. ``series`` maps a label to (x, y) pairs.

    When ``test_intervals`` is provided (the same ``(name, start,
    duration, status)`` shape the test_timeline strip consumes), an
    underlay is drawn behind the data: a translucent red band for each
    failed test, a fainter gray band for skips, and thin vertical
    delimiters at every test start. This lets a reviewer trace a CPU
    or I/O spike back to a specific test without having to glance down
    at the timeline strip below.

    ``chart_xlim`` pins the x-axis range so all per-metric charts and
    the test_timeline strip beneath them share the same horizontal
    scale.
    """
    if not _AVAILABLE or not series:
        return None

    fig, ax = plt.subplots(figsize=(_TS_FIG_W, 6))

    # Test-execution underlay (drawn first so data plots on top).
    # Convention matches the timeline strip below: pass = green, fail
    # = red, skip = gray. Pass intervals get no fill (uncluttered
    # background), fail intervals a translucent red band, skip
    # intervals a translucent gray band with a hatched pattern so the
    # band stays visible against the neutral chart background and is
    # easy to tell apart from the red one. Thin vertical delimiters
    # mark every test start so the reviewer can see where each test
    # begins even on the pass-only stretches.
    if test_intervals:
        for _name, start, duration, status in test_intervals:
            width = max(duration, 0.5)
            if status == "fail":
                ax.axvspan(start, start + width,
                           alpha=0.20, color="#f56565",
                           linewidth=0, zorder=0)
            elif status == "skip":
                ax.axvspan(start, start + width,
                           alpha=0.35, facecolor="#a0aec0",
                           hatch="///", edgecolor="#718096",
                           linewidth=0, zorder=0)
        for _name, start, _duration, _status in test_intervals:
            ax.axvline(x=start, color="#cbd5e0", alpha=0.35,
                       linewidth=0.4, zorder=0)

    plotted_any = False
    for label, points in series.items():
        if not points:
            continue
        xs, ys = zip(*points)
        ax.plot(xs, ys, label=label, marker="o", markersize=3, linewidth=1,
                zorder=2)
        plotted_any = True

    if not plotted_any:
        plt.close(fig)
        return None

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3, zorder=1)

    # Combine the data-series legend with patches explaining the
    # test-status bands so the reviewer doesn't have to remember
    # what red and hatched-gray mean from the timeline strip below.
    series_handles, series_labels = ax.get_legend_handles_labels()
    if test_intervals:
        from matplotlib.patches import Patch
        band_handles = [
            Patch(facecolor="#f56565", alpha=0.20, linewidth=0,
                  label="failed test"),
            Patch(facecolor="#a0aec0", alpha=0.35, hatch="///",
                  edgecolor="#718096", linewidth=0,
                  label="skipped test"),
        ]
        ax.legend(series_handles + band_handles,
                  series_labels + [h.get_label() for h in band_handles],
                  loc="best", fontsize=9)
    else:
        ax.legend(loc="best", fontsize=9)

    if chart_xlim is not None:
        ax.set_xlim(*chart_xlim)
    fig.subplots_adjust(left=_TS_LEFT, right=_TS_RIGHT,
                        bottom=0.10, top=0.92)
    return _save_close(fig, tight=False)


def timeline_ab(
    series_by_kernel: dict[str, dict[str, list[tuple[float, float]]]],
    *,
    title: str,
    kernels: list[str],
    xlabel: str = "Sample",
    ylabel: str = "Value",
    test_intervals: Optional[list[tuple[str, float, float, str]]] = None,
    chart_xlim: Optional[tuple[float, float]] = None,
) -> Optional[bytes]:
    """Two-kernel overlay of a multi-series line plot.

    Same data shape as ``timeline()`` but each label is plotted twice
    (once per kernel) with a shared per-label colour and the kernel
    distinguished by line style: solid for A (kernels[0]), dashed
    for B (kernels[1]). The legend collapses to one entry per metric
    plus two key entries explaining the line-style convention so the
    chart stays readable when each metric has both kernels' lines on
    top of each other.

    ``series_by_kernel`` maps kernel name → ``{label: [(x, y), ...]}``
    just like the single-kernel ``timeline()`` series argument; passing
    a kernel with empty data degrades gracefully (only the kernel that
    has data shows up).
    """
    if not _AVAILABLE or not series_by_kernel or len(kernels) != 2:
        return None

    fig, ax = plt.subplots(figsize=(_TS_FIG_W, 6))

    # Test-execution underlay for the union of intervals (if both
    # kernels' timelines should be overlaid the caller can merge
    # them ahead of time; for now we accept one set).
    if test_intervals:
        for _name, start, duration, status in test_intervals:
            width = max(duration, 0.5)
            if status == "fail":
                ax.axvspan(start, start + width,
                           alpha=0.20, color="#f56565",
                           linewidth=0, zorder=0)
            elif status == "skip":
                ax.axvspan(start, start + width,
                           alpha=0.35, facecolor="#a0aec0",
                           hatch="///", edgecolor="#718096",
                           linewidth=0, zorder=0)
        for _name, start, _duration, _status in test_intervals:
            ax.axvline(x=start, color="#cbd5e0", alpha=0.35,
                       linewidth=0.4, zorder=0)

    # Stable per-label colour across both kernels.
    metric_color: dict[str, tuple] = {}
    cmap = plt.get_cmap("tab10")
    color_idx = 0
    plotted_any = False
    for kernel_idx, kernel in enumerate(kernels):
        linestyle = ("-", "--")[kernel_idx]
        marker = ("o", "s")[kernel_idx]
        per_kernel = series_by_kernel.get(kernel) or {}
        for label, points in per_kernel.items():
            if label not in metric_color:
                metric_color[label] = cmap(color_idx % 10)
                color_idx += 1
            if not points:
                continue
            xs, ys = zip(*points)
            ax.plot(xs, ys, color=metric_color[label],
                    linestyle=linestyle, marker=marker,
                    markersize=3, linewidth=1.2, zorder=2)
            plotted_any = True

    if not plotted_any:
        plt.close(fig)
        return None

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3, zorder=1)

    # Compose a two-part legend: metric → colour, kernel → linestyle.
    from matplotlib.lines import Line2D
    metric_handles = [
        Line2D([0], [0], color=metric_color[m], linewidth=2, label=m)
        for m in metric_color
    ]
    kernel_handles = [
        Line2D([0], [0], color="black", linestyle="-",  marker="o",
               markersize=3, label=f"A · {kernels[0]}"),
        Line2D([0], [0], color="black", linestyle="--", marker="s",
               markersize=3, label=f"B · {kernels[1]}"),
    ]
    ax.legend(handles=metric_handles + kernel_handles,
              loc="best", fontsize=9, ncol=1)

    if chart_xlim is not None:
        ax.set_xlim(*chart_xlim)
    fig.subplots_adjust(left=_TS_LEFT, right=_TS_RIGHT,
                        bottom=0.10, top=0.92)
    return _save_close(fig, tight=False)


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

    fig, ax = plt.subplots(figsize=(_TS_FIG_W, 2.6))

    color_map = {
        "pass": "#48bb78",
        "fail": "#f56565",
        "skip": "#a0aec0",
    }
    # Hatch skip bars so a single short skip among 50 tests stays
    # visible in the strip even when it shares the row with green
    # passes — the hatch line catches the eye where the gray fill
    # alone would not.
    for name, start, duration, status in intervals:
        ax.barh(
            0,
            max(duration, 0.5),  # tiny floor so 0-second tests stay visible
            left=start,
            color=color_map.get(status, "#cbd5e0"),
            edgecolor="white",
            hatch="///" if status == "skip" else None,
            linewidth=0.4,
        )

    # Label selection is duration-driven, not periodic, so a label
    # actually corresponds to a test that took long enough to leave
    # a visible mark in the metric charts above:
    #
    #   - failures, skips, and the first/last test are always
    #     labelled (they need attention or anchor the timeline).
    #   - any test taking >= LONG_TEST_S gets its own label.
    #   - shorter tests are skipped, but if a stretch of short
    #     consecutive tests accumulates more than GAP_BUDGET_S of
    #     unlabelled time the next test is labelled regardless of
    #     its duration so the strip never has a long blank corridor.
    #
    # ``label_every`` is kept in the signature for backward compat
    # with callers that already pass it, but is intentionally unused
    # — periodic markers landed on tests that happened to be short
    # and uneventful (the user's concern: "why is 31 labelled but
    # not 32?"), which is exactly the noise this rewrite removes.
    LONG_TEST_S = 3.0
    GAP_BUDGET_S = 5.0
    _ = label_every

    last_label_x = -1e9
    min_label_gap = (intervals[-1][1] + intervals[-1][2]) / 80 or 0.5
    unlabelled_run_s = 0.0
    for i, (name, start, duration, status) in enumerate(intervals):
        is_failure = status == "fail"
        is_skip = status == "skip"
        is_endpoint = i == 0 or i == len(intervals) - 1
        is_long = duration >= LONG_TEST_S
        is_attention = is_failure or is_skip or is_endpoint
        is_gap_bridge = (
            not is_attention
            and not is_long
            and unlabelled_run_s >= GAP_BUDGET_S
        )
        if not (is_attention or is_long or is_gap_bridge):
            unlabelled_run_s += duration
            continue

        x_center = start + duration / 2
        if (x_center - last_label_x) < min_label_gap and not (is_failure or is_skip):
            unlabelled_run_s += duration
            continue

        last_label_x = x_center
        unlabelled_run_s = 0.0
        short = name.split("/", 1)[-1] if "/" in name else name
        if is_failure:
            color, weight = "#c53030", "bold"
        elif is_skip:
            color, weight = "#4a5568", "bold"
        else:
            color, weight = "#2d3748", "normal"
        ax.text(
            x_center, 0.55, short,
            ha="center", va="bottom",
            fontsize=7,
            rotation=45,
            color=color, fontweight=weight,
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

    # Legend — match the band style so the hatch on "skip" shows up
    # in the legend the same way it does on the bars themselves.
    from matplotlib.patches import Patch
    legend_handles = [
        Patch(facecolor="#48bb78", edgecolor="white", label="pass"),
        Patch(facecolor="#f56565", edgecolor="white", label="fail"),
        Patch(facecolor="#a0aec0", edgecolor="white", hatch="///",
              label="skip"),
    ]
    ax.legend(handles=legend_handles, loc="upper right", fontsize=8,
              framealpha=0.85)

    fig.subplots_adjust(bottom=0.35, top=0.82,
                        left=_TS_LEFT, right=_TS_RIGHT)
    return _save_close(fig, tight=False)


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

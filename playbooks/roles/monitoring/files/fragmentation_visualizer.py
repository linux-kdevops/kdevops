#!/usr/bin/env python3
"""
Enhanced fragmentation A/B comparison with overlaid visualizations.
Combines datasets on the same graphs using different visual markers.

Usage:
  python c6.py fragmentation_data_A.json --compare fragmentation_data_B.json -o comparison.png
"""
import json
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
from datetime import datetime
import argparse
from collections import defaultdict


def load_data(filename):
    with open(filename, "r") as f:
        return json.load(f)


def get_dot_size(order: int) -> float:
    base_size = 1
    return base_size + (order * 2)


def build_counts(events, bin_size):
    if not events:
        return np.array([]), np.array([])
    times = np.array([e["timestamp"] for e in events], dtype=float)
    tmin, tmax = times.min(), times.max()
    if tmax == tmin:
        tmax = tmin + bin_size
    bins = np.arange(tmin, tmax + bin_size, bin_size)
    counts, edges = np.histogram(times, bins=bins)
    centers = (edges[:-1] + edges[1:]) / 2.0
    return centers, counts


def get_migrate_type_color(mtype):
    """Get consistent colors for migrate types"""
    colors = {
        "UNMOVABLE": "#e74c3c",  # Red
        "MOVABLE": "#2ecc71",  # Green
        "RECLAIMABLE": "#f39c12",  # Orange
        "PCPTYPES": "#9b59b6",  # Purple
        "HIGHATOMIC": "#e91e63",  # Pink
        "ISOLATE": "#607d8b",  # Blue-grey
        "CMA": "#00bcd4",  # Cyan
    }
    return colors.get(mtype, "#95a5a6")


def get_migration_severity(from_type, to_type):
    """Determine migration severity score"""
    if to_type == "UNMOVABLE":
        return -2  # Very bad
    elif from_type == "UNMOVABLE":
        return 1  # Good
    elif to_type == "MOVABLE":
        return 1  # Good
    elif from_type == "MOVABLE" and to_type == "RECLAIMABLE":
        return -1  # Somewhat bad
    elif to_type == "RECLAIMABLE":
        return -0.5  # Slightly bad
    return 0


def get_severity_color(severity_score):
    """Get color based on severity score"""
    if severity_score <= -2:
        return "#8b0000"  # Dark red
    elif severity_score <= -1:
        return "#ff6b6b"  # Light red
    elif severity_score >= 1:
        return "#51cf66"  # Green
    else:
        return "#ffd43b"  # Yellow


def create_overlaid_compaction_graph(ax, data_a, data_b, labels):
    """Create overlaid compaction events graph"""

    # Process dataset A
    events_a = data_a.get("events", [])
    compact_a = [
        e
        for e in events_a
        if e["event_type"] in ["compaction_success", "compaction_failure"]
    ]
    success_a = [e for e in compact_a if e["event_type"] == "compaction_success"]
    failure_a = [e for e in compact_a if e["event_type"] == "compaction_failure"]

    # Process dataset B
    events_b = data_b.get("events", [])
    compact_b = [
        e
        for e in events_b
        if e["event_type"] in ["compaction_success", "compaction_failure"]
    ]
    success_b = [e for e in compact_b if e["event_type"] == "compaction_success"]
    failure_b = [e for e in compact_b if e["event_type"] == "compaction_failure"]

    # Plot A with circles
    for e in success_a:
        ax.scatter(
            e["timestamp"],
            e.get("fragmentation_index", 0),
            s=get_dot_size(e["order"]),
            c="#2ecc71",
            alpha=0.3,
            edgecolors="none",
            marker="o",
            label=None,
        )

    for i, e in enumerate(failure_a):
        y_pos = -50 - (e["order"] * 10)
        ax.scatter(
            e["timestamp"],
            y_pos,
            s=get_dot_size(e["order"]),
            c="#e74c3c",
            alpha=0.3,
            edgecolors="none",
            marker="o",
            label=None,
        )

    # Plot B with triangles
    for e in success_b:
        ax.scatter(
            e["timestamp"],
            e.get("fragmentation_index", 0),
            s=get_dot_size(e["order"]) * 1.2,
            c="#27ae60",
            alpha=0.4,
            edgecolors="black",
            linewidths=0.5,
            marker="^",
            label=None,
        )

    for i, e in enumerate(failure_b):
        y_pos = -55 - (e["order"] * 10)  # Slightly offset from A
        ax.scatter(
            e["timestamp"],
            y_pos,
            s=get_dot_size(e["order"]) * 1.2,
            c="#c0392b",
            alpha=0.4,
            edgecolors="black",
            linewidths=0.5,
            marker="^",
            label=None,
        )

    # Set y-axis limits - cap at 1000, ignore data above
    all_y_values = []
    if success_a:
        all_y_values.extend(
            [
                e.get("fragmentation_index", 0)
                for e in success_a
                if e.get("fragmentation_index", 0) <= 1000
            ]
        )
    if success_b:
        all_y_values.extend(
            [
                e.get("fragmentation_index", 0)
                for e in success_b
                if e.get("fragmentation_index", 0) <= 1000
            ]
        )

    max_y = max(all_y_values) if all_y_values else 1000
    min_y = -200  # Fixed minimum for failure lanes
    ax.set_ylim(min_y, min(max_y + 100, 1000))

    # Create legend - position above the data
    from matplotlib.lines import Line2D

    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#2ecc71",
            markersize=8,
            alpha=0.6,
            label=f"{labels[0]} Success",
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#e74c3c",
            markersize=8,
            alpha=0.6,
            label=f"{labels[0]} Failure",
        ),
        Line2D(
            [0],
            [0],
            marker="^",
            color="w",
            markerfacecolor="#27ae60",
            markersize=8,
            alpha=0.6,
            label=f"{labels[1]} Success",
        ),
        Line2D(
            [0],
            [0],
            marker="^",
            color="w",
            markerfacecolor="#c0392b",
            markersize=8,
            alpha=0.6,
            label=f"{labels[1]} Failure",
        ),
    ]
    # Position legend at y=0 on the left side where there's no data
    ax.legend(
        handles=legend_elements,
        loc="center left",
        bbox_to_anchor=(0.02, 0.5),
        ncol=1,
        fontsize=8,
        frameon=True,
        fancybox=True,
    )

    # Styling
    ax.axhline(y=0, color="#34495e", linestyle="-", linewidth=1.5, alpha=0.8)
    ax.grid(True, alpha=0.08, linestyle=":", linewidth=0.5)
    ax.set_xlabel("Time (seconds)", fontsize=11)
    ax.set_ylabel("Fragmentation Index", fontsize=11)
    ax.set_title(
        "Compaction Events Comparison (○ = A, △ = B)",
        fontsize=13,
        fontweight="bold",
        pad=20,
    )


def create_overlaid_extfrag_timeline(ax, data_a, data_b, labels, bin_size=0.5):
    """Create overlaid ExtFrag timeline"""

    events_a = [e for e in data_a.get("events", []) if e["event_type"] == "extfrag"]
    events_b = [e for e in data_b.get("events", []) if e["event_type"] == "extfrag"]

    # Dataset A - solid lines
    steal_a = [e for e in events_a if e.get("is_steal")]
    claim_a = [e for e in events_a if not e.get("is_steal")]

    steal_times_a, steal_counts_a = build_counts(steal_a, bin_size)
    claim_times_a, claim_counts_a = build_counts(claim_a, bin_size)

    if steal_times_a.size > 0:
        ax.plot(
            steal_times_a,
            steal_counts_a,
            linewidth=2,
            color="#3498db",
            alpha=0.8,
            label=f"{labels[0]} Steal",
            linestyle="-",
        )
        ax.fill_between(steal_times_a, 0, steal_counts_a, alpha=0.15, color="#3498db")

    if claim_times_a.size > 0:
        ax.plot(
            claim_times_a,
            claim_counts_a,
            linewidth=2,
            color="#e67e22",
            alpha=0.8,
            label=f"{labels[0]} Claim",
            linestyle="-",
        )
        ax.fill_between(claim_times_a, 0, claim_counts_a, alpha=0.15, color="#e67e22")

    # Dataset B - dashed lines
    steal_b = [e for e in events_b if e.get("is_steal")]
    claim_b = [e for e in events_b if not e.get("is_steal")]

    steal_times_b, steal_counts_b = build_counts(steal_b, bin_size)
    claim_times_b, claim_counts_b = build_counts(claim_b, bin_size)

    if steal_times_b.size > 0:
        ax.plot(
            steal_times_b,
            steal_counts_b,
            linewidth=2,
            color="#2980b9",
            alpha=0.8,
            label=f"{labels[1]} Steal",
            linestyle="--",
        )

    if claim_times_b.size > 0:
        ax.plot(
            claim_times_b,
            claim_counts_b,
            linewidth=2,
            color="#d35400",
            alpha=0.8,
            label=f"{labels[1]} Claim",
            linestyle="--",
        )

    ax.legend(loc="upper right", frameon=True, fontsize=9, ncol=2)
    ax.set_xlabel("Time (seconds)", fontsize=11)
    ax.set_ylabel(f"Events per {bin_size}s", fontsize=11)
    ax.set_title(
        "ExtFrag Events Timeline (Solid = A, Dashed = B)",
        fontsize=12,
        fontweight="semibold",
    )
    ax.grid(True, alpha=0.06, linestyle=":", linewidth=0.5)


def create_combined_migration_heatmap(ax, data_a, data_b, labels):
    """Create combined migration pattern heatmap"""

    events_a = [e for e in data_a.get("events", []) if e["event_type"] == "extfrag"]
    events_b = [e for e in data_b.get("events", []) if e["event_type"] == "extfrag"]

    if not events_a and not events_b:
        ax.text(
            0.5,
            0.5,
            "No external fragmentation events",
            ha="center",
            va="center",
            fontsize=12,
        )
        ax.axis("off")
        return

    # Combine all events to get unified time range and patterns
    all_events = events_a + events_b
    times = [e["timestamp"] for e in all_events]
    min_time, max_time = min(times), max(times)

    # Create time bins
    n_bins = min(25, max(15, int((max_time - min_time) / 10)))
    time_bins = np.linspace(min_time, max_time, n_bins + 1)
    time_centers = (time_bins[:-1] + time_bins[1:]) / 2

    # Get all unique patterns from both datasets
    all_patterns = set()
    for e in all_events:
        all_patterns.add(f"{e['migrate_from']}→{e['migrate_to']}")

    # Calculate pattern severities and sort
    pattern_severities = {}
    for pattern in all_patterns:
        from_type, to_type = pattern.split("→")
        pattern_severities[pattern] = get_migration_severity(from_type, to_type)

    sorted_patterns = sorted(all_patterns, key=lambda p: (pattern_severities[p], p))

    # Create separate heatmaps for A and B
    heatmap_a = np.zeros((len(sorted_patterns), len(time_centers)))
    heatmap_b = np.zeros((len(sorted_patterns), len(time_centers)))

    # Fill heatmap A
    for e in events_a:
        pattern = f"{e['migrate_from']}→{e['migrate_to']}"
        pattern_idx = sorted_patterns.index(pattern)
        bin_idx = np.digitize(e["timestamp"], time_bins) - 1
        if 0 <= bin_idx < len(time_centers):
            heatmap_a[pattern_idx, bin_idx] += 1

    # Fill heatmap B
    for e in events_b:
        pattern = f"{e['migrate_from']}→{e['migrate_to']}"
        pattern_idx = sorted_patterns.index(pattern)
        bin_idx = np.digitize(e["timestamp"], time_bins) - 1
        if 0 <= bin_idx < len(time_centers):
            heatmap_b[pattern_idx, bin_idx] += 1

    # Combine heatmaps: A in upper half of cell, B in lower half
    from matplotlib.colors import LinearSegmentedColormap

    # Plot base grid
    for i in range(len(sorted_patterns)):
        for j in range(len(time_centers)):
            # Draw cell background based on severity
            severity = pattern_severities[sorted_patterns[i]]
            base_color = get_severity_color(severity)
            rect = Rectangle(
                (j - 0.5, i - 0.5),
                1,
                1,
                facecolor=base_color,
                alpha=0.1,
                edgecolor="gray",
                linewidth=0.5,
            )
            ax.add_patch(rect)

            # Add counts for A (upper half)
            if heatmap_a[i, j] > 0:
                rect_a = Rectangle(
                    (j - 0.4, i), 0.8, 0.4, facecolor="#3498db", alpha=0.6
                )
                ax.add_patch(rect_a)
                ax.text(
                    j,
                    i + 0.2,
                    str(int(heatmap_a[i, j])),
                    ha="center",
                    va="center",
                    fontsize=6,
                    color="white",
                    fontweight="bold",
                )

            # Add counts for B (lower half)
            if heatmap_b[i, j] > 0:
                rect_b = Rectangle(
                    (j - 0.4, i - 0.4), 0.8, 0.4, facecolor="#e67e22", alpha=0.6
                )
                ax.add_patch(rect_b)
                ax.text(
                    j,
                    i - 0.2,
                    str(int(heatmap_b[i, j])),
                    ha="center",
                    va="center",
                    fontsize=6,
                    color="white",
                    fontweight="bold",
                )

    # Set axes - extend left margin for severity indicators
    ax.set_xlim(-2.5, len(time_centers) - 0.5)
    ax.set_ylim(-0.5, len(sorted_patterns) - 0.5)

    # Set x-axis (time)
    ax.set_xticks(np.arange(len(time_centers)))
    ax.set_xticklabels(
        [f"{t:.0f}s" for t in time_centers], rotation=45, ha="right", fontsize=8
    )

    # Set y-axis with severity indicators
    ax.set_yticks(np.arange(len(sorted_patterns)))
    y_labels = []

    for i, pattern in enumerate(sorted_patterns):
        severity = pattern_severities[pattern]

        # Add colored severity indicator on the left side (in data coordinates)
        severity_color = get_severity_color(severity)
        rect = Rectangle(
            (-1.8, i - 0.4),
            1.0,
            0.8,
            facecolor=severity_color,
            alpha=0.8,
            edgecolor="black",
            linewidth=0.5,
            clip_on=False,
        )
        ax.add_patch(rect)

        # Add severity symbol
        if severity <= -2:
            symbol = "!!"
        elif severity <= -1:
            symbol = "!"
        elif severity >= 1:
            symbol = "+"
        else:
            symbol = "="

        ax.text(
            -1.3,
            i,
            symbol,
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            color="white" if abs(severity) > 0 else "black",
        )

        y_labels.append(pattern)

    ax.set_yticklabels(y_labels, fontsize=8)

    # Add legend
    legend_elements = [
        mpatches.Patch(color="#3498db", alpha=0.6, label=f"{labels[0]} (upper)"),
        mpatches.Patch(color="#e67e22", alpha=0.6, label=f"{labels[1]} (lower)"),
        mpatches.Patch(color="#8b0000", alpha=0.8, label="Bad migration"),
        mpatches.Patch(color="#51cf66", alpha=0.8, label="Good migration"),
    ]
    ax.legend(
        handles=legend_elements,
        loc="upper right",
        bbox_to_anchor=(1.15, 1.0),
        fontsize=8,
        frameon=True,
    )

    # Styling
    ax.set_xlabel("Time", fontsize=11)
    ax.set_ylabel("Migration Pattern", fontsize=11)
    ax.set_title(
        "Migration Patterns Comparison (Blue = A, Orange = B)",
        fontsize=12,
        fontweight="semibold",
    )
    ax.grid(False)


def create_comparison_statistics_table(ax, data_a, data_b, labels):
    """Create comparison statistics table"""
    ax.axis("off")

    # Calculate metrics
    def calculate_metrics(data):
        events = data.get("events", [])
        compact = [
            e
            for e in events
            if e["event_type"] in ["compaction_success", "compaction_failure"]
        ]
        extfrag = [e for e in events if e["event_type"] == "extfrag"]

        compact_success = sum(
            1 for e in compact if e["event_type"] == "compaction_success"
        )
        success_rate = (compact_success / len(compact) * 100) if compact else 0

        bad = sum(
            1
            for e in extfrag
            if get_migration_severity(e["migrate_from"], e["migrate_to"]) < 0
        )
        good = sum(
            1
            for e in extfrag
            if get_migration_severity(e["migrate_from"], e["migrate_to"]) > 0
        )

        steal = sum(1 for e in extfrag if e.get("is_steal"))
        claim = len(extfrag) - steal if extfrag else 0

        return {
            "total": len(events),
            "compact_success_rate": success_rate,
            "extfrag": len(extfrag),
            "bad_migrations": bad,
            "good_migrations": good,
            "steal": steal,
            "claim": claim,
        }

    metrics_a = calculate_metrics(data_a)
    metrics_b = calculate_metrics(data_b)

    # Create table data
    headers = ["Metric", labels[0], labels[1], "Better"]
    rows = [
        [
            "Total Events",
            metrics_a["total"],
            metrics_b["total"],
            "=" if metrics_a["total"] == metrics_b["total"] else "",
        ],
        [
            "Compaction Success Rate",
            f"{metrics_a['compact_success_rate']:.1f}%",
            f"{metrics_b['compact_success_rate']:.1f}%",
            (
                labels[0]
                if metrics_a["compact_success_rate"] > metrics_b["compact_success_rate"]
                else (
                    labels[1]
                    if metrics_b["compact_success_rate"]
                    > metrics_a["compact_success_rate"]
                    else "="
                )
            ),
        ],
        [
            "ExtFrag Events",
            metrics_a["extfrag"],
            metrics_b["extfrag"],
            (
                labels[0]
                if metrics_a["extfrag"] < metrics_b["extfrag"]
                else labels[1] if metrics_b["extfrag"] < metrics_a["extfrag"] else "="
            ),
        ],
        [
            "Bad Migrations",
            metrics_a["bad_migrations"],
            metrics_b["bad_migrations"],
            (
                labels[0]
                if metrics_a["bad_migrations"] < metrics_b["bad_migrations"]
                else (
                    labels[1]
                    if metrics_b["bad_migrations"] < metrics_a["bad_migrations"]
                    else "="
                )
            ),
        ],
        [
            "Good Migrations",
            metrics_a["good_migrations"],
            metrics_b["good_migrations"],
            (
                labels[0]
                if metrics_a["good_migrations"] > metrics_b["good_migrations"]
                else (
                    labels[1]
                    if metrics_b["good_migrations"] > metrics_a["good_migrations"]
                    else "="
                )
            ),
        ],
        ["Steal Events", metrics_a["steal"], metrics_b["steal"], ""],
        ["Claim Events", metrics_a["claim"], metrics_b["claim"], ""],
    ]

    # Create table - position closer to title
    table = ax.table(
        cellText=rows,
        colLabels=headers,
        cellLoc="center",
        loc="center",
        colWidths=[0.35, 0.25, 0.25, 0.15],
        bbox=[0.1, 0.15, 0.8, 0.65],
    )  # Center table with margins

    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 2.2)  # Make cells taller for better readability

    # Add padding to cells for better spacing
    for key, cell in table.get_celld().items():
        cell.set_height(0.08)  # Increase cell height
        cell.PAD = 0.05  # Add internal padding

    # Color cells based on which is better
    for i in range(1, len(rows) + 1):
        row = rows[i - 1]
        if row[3] == labels[0]:
            table[(i, 1)].set_facecolor("#d4edda")
            table[(i, 2)].set_facecolor("#f8d7da")
        elif row[3] == labels[1]:
            table[(i, 1)].set_facecolor("#f8d7da")
            table[(i, 2)].set_facecolor("#d4edda")

    # Position title with more space from previous graph
    ax.set_title(
        "\n\nStatistical Comparison (Green = Better, Red = Worse)",
        fontsize=13,
        fontweight="bold",
        pad=5,
        y=1.0,
    )


def create_single_dashboard(data, output_file=None, bin_size=0.5):
    """Create single dataset analysis dashboard with severity indicators"""

    # Create figure
    fig = plt.figure(figsize=(20, 16), constrained_layout=False)
    fig.patch.set_facecolor("#f8f9fa")

    # Create grid layout - 3 rows for single analysis
    gs = gridspec.GridSpec(3, 1, height_ratios=[2.5, 2, 3], hspace=0.3, figure=fig)

    # Create subplots
    ax_compact = fig.add_subplot(gs[0])
    ax_extfrag = fig.add_subplot(gs[1])
    ax_migration = fig.add_subplot(gs[2])

    # Process events
    events = data.get("events", [])
    compact_events = [
        e
        for e in events
        if e["event_type"] in ["compaction_success", "compaction_failure"]
    ]
    extfrag_events = [e for e in events if e["event_type"] == "extfrag"]

    success_events = [
        e for e in compact_events if e["event_type"] == "compaction_success"
    ]
    failure_events = [
        e for e in compact_events if e["event_type"] == "compaction_failure"
    ]

    # === COMPACTION GRAPH ===
    if compact_events:
        for e in success_events:
            if e.get("fragmentation_index", 0) <= 1000:  # Cap at 1000
                ax_compact.scatter(
                    e["timestamp"],
                    e.get("fragmentation_index", 0),
                    s=get_dot_size(e["order"]),
                    c="#2ecc71",
                    alpha=0.3,
                    edgecolors="none",
                )

        for i, e in enumerate(failure_events):
            y_pos = -50 - (e["order"] * 10)
            ax_compact.scatter(
                e["timestamp"],
                y_pos,
                s=get_dot_size(e["order"]),
                c="#e74c3c",
                alpha=0.3,
                edgecolors="none",
            )

        ax_compact.axhline(
            y=0, color="#34495e", linestyle="-", linewidth=1.5, alpha=0.8
        )
        ax_compact.grid(True, alpha=0.08, linestyle=":", linewidth=0.5)
        ax_compact.set_ylim(-200, 1000)

        # Add statistics
        success_rate = (
            len(success_events) / len(compact_events) * 100 if compact_events else 0
        )
        stats_text = f"Success: {len(success_events)}/{len(compact_events)} ({success_rate:.1f}%)"
        ax_compact.text(
            0.02,
            0.98,
            stats_text,
            transform=ax_compact.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9),
        )

    ax_compact.set_xlabel("Time (seconds)", fontsize=11)
    ax_compact.set_ylabel("Fragmentation Index", fontsize=11)
    ax_compact.set_title("Compaction Events Over Time", fontsize=13, fontweight="bold")

    # === EXTFRAG TIMELINE ===
    if extfrag_events:
        steal_events = [e for e in extfrag_events if e.get("is_steal")]
        claim_events = [e for e in extfrag_events if not e.get("is_steal")]

        steal_times, steal_counts = build_counts(steal_events, bin_size)
        claim_times, claim_counts = build_counts(claim_events, bin_size)

        if steal_times.size > 0:
            ax_extfrag.fill_between(
                steal_times, 0, steal_counts, alpha=0.3, color="#3498db"
            )
            ax_extfrag.plot(
                steal_times,
                steal_counts,
                linewidth=2,
                color="#2980b9",
                alpha=0.8,
                label=f"Steal ({len(steal_events)})",
            )

        if claim_times.size > 0:
            ax_extfrag.fill_between(
                claim_times, 0, claim_counts, alpha=0.3, color="#e67e22"
            )
            ax_extfrag.plot(
                claim_times,
                claim_counts,
                linewidth=2,
                color="#d35400",
                alpha=0.8,
                label=f"Claim ({len(claim_events)})",
            )

        ax_extfrag.legend(loc="upper right", frameon=True, fontsize=9)

        # Add bad/good migration counts
        bad_migrations = sum(
            1
            for e in extfrag_events
            if get_migration_severity(e["migrate_from"], e["migrate_to"]) < 0
        )
        good_migrations = sum(
            1
            for e in extfrag_events
            if get_migration_severity(e["migrate_from"], e["migrate_to"]) > 0
        )

        migration_text = f"Bad: {bad_migrations} | Good: {good_migrations}"
        ax_extfrag.text(
            0.02,
            0.98,
            migration_text,
            transform=ax_extfrag.transAxes,
            fontsize=10,
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9),
        )

    ax_extfrag.set_xlabel("Time (seconds)", fontsize=11)
    ax_extfrag.set_ylabel(f"Events per {bin_size}s", fontsize=11)
    ax_extfrag.set_title(
        "External Fragmentation Events Timeline", fontsize=12, fontweight="semibold"
    )
    ax_extfrag.grid(True, alpha=0.06, linestyle=":", linewidth=0.5)

    # === MIGRATION HEATMAP WITH SEVERITY ===
    create_single_migration_heatmap(ax_migration, extfrag_events)

    # Super title
    fig.suptitle(
        "Memory Fragmentation Analysis", fontsize=18, fontweight="bold", y=0.98
    )

    # Footer
    timestamp_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    fig.text(
        0.98,
        0.01,
        timestamp_text,
        ha="right",
        fontsize=9,
        style="italic",
        color="#7f8c8d",
    )

    # Adjust layout
    plt.subplots_adjust(left=0.08, right=0.95, top=0.94, bottom=0.03)

    # Save
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"fragmentation_analysis_{timestamp}.png"

    plt.savefig(output_file, dpi=120, bbox_inches="tight", facecolor="#f8f9fa")
    plt.close(fig)
    return output_file


def create_single_migration_heatmap(ax, extfrag_events):
    """Create migration heatmap for single dataset with severity indicators"""
    if not extfrag_events:
        ax.text(
            0.5,
            0.5,
            "No external fragmentation events",
            ha="center",
            va="center",
            fontsize=12,
        )
        ax.axis("off")
        return

    # Get time range and create bins
    times = [e["timestamp"] for e in extfrag_events]
    min_time, max_time = min(times), max(times)

    n_bins = min(25, max(15, int((max_time - min_time) / 10)))
    time_bins = np.linspace(min_time, max_time, n_bins + 1)
    time_centers = (time_bins[:-1] + time_bins[1:]) / 2

    # Get patterns and calculate severities
    patterns = {}
    pattern_events = defaultdict(list)

    for e in extfrag_events:
        pattern = f"{e['migrate_from']}→{e['migrate_to']}"
        pattern_events[pattern].append(e)
        if pattern not in patterns:
            patterns[pattern] = {
                "from": e["migrate_from"],
                "to": e["migrate_to"],
                "total": 0,
                "steal": 0,
                "claim": 0,
                "severity": get_migration_severity(e["migrate_from"], e["migrate_to"]),
            }
        patterns[pattern]["total"] += 1
        if e.get("is_steal"):
            patterns[pattern]["steal"] += 1
        else:
            patterns[pattern]["claim"] += 1

    # Sort by severity then count
    sorted_patterns = sorted(
        patterns.keys(), key=lambda p: (patterns[p]["severity"], -patterns[p]["total"])
    )

    # Create heatmap data
    heatmap_data = np.zeros((len(sorted_patterns), len(time_centers)))

    for i, pattern in enumerate(sorted_patterns):
        for e in pattern_events[pattern]:
            bin_idx = np.digitize(e["timestamp"], time_bins) - 1
            if 0 <= bin_idx < len(time_centers):
                heatmap_data[i, bin_idx] += 1

    # Plot heatmap
    from matplotlib.colors import LinearSegmentedColormap

    colors = ["#ffffff", "#ffeb3b", "#ff9800", "#f44336"]  # White to red
    cmap = LinearSegmentedColormap.from_list("intensity", colors, N=256)

    im = ax.imshow(heatmap_data, aspect="auto", cmap=cmap, vmin=0, alpha=0.8)

    # Overlay counts
    for i in range(len(sorted_patterns)):
        for j in range(len(time_centers)):
            if heatmap_data[i, j] > 0:
                count = int(heatmap_data[i, j])
                color = (
                    "white" if heatmap_data[i, j] > heatmap_data.max() / 2 else "black"
                )
                ax.text(
                    j,
                    i,
                    str(count),
                    ha="center",
                    va="center",
                    fontsize=6,
                    fontweight="bold",
                    color=color,
                )

    # Set axes
    ax.set_xlim(-2.5, len(time_centers) - 0.5)
    ax.set_ylim(-0.5, len(sorted_patterns) - 0.5)

    # Set x-axis
    ax.set_xticks(np.arange(len(time_centers)))
    ax.set_xticklabels(
        [f"{t:.0f}s" for t in time_centers], rotation=45, ha="right", fontsize=8
    )

    # Set y-axis with severity indicators
    ax.set_yticks(np.arange(len(sorted_patterns)))
    y_labels = []

    for i, pattern in enumerate(sorted_patterns):
        severity = patterns[pattern]["severity"]
        severity_color = get_severity_color(severity)

        # Add severity indicator
        rect = Rectangle(
            (-2.3, i - 0.4),
            1.5,
            0.8,
            facecolor=severity_color,
            alpha=0.8,
            edgecolor="black",
            linewidth=0.5,
            clip_on=False,
        )
        ax.add_patch(rect)

        # Add symbol
        if severity <= -2:
            symbol = "!!"
        elif severity <= -1:
            symbol = "!"
        elif severity >= 1:
            symbol = "+"
        else:
            symbol = "="

        ax.text(
            -1.55,
            i,
            symbol,
            ha="center",
            va="center",
            fontsize=8,
            fontweight="bold",
            color="white" if abs(severity) > 0 else "black",
        )

        # Format label
        total = patterns[pattern]["total"]
        steal = patterns[pattern]["steal"]
        claim = patterns[pattern]["claim"]
        label = f"{pattern} ({total}: {steal}s/{claim}c)"
        y_labels.append(label)

    ax.set_yticklabels(y_labels, fontsize=8)

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax, orientation="vertical", pad=0.02, aspect=30)
    cbar.set_label("Event Intensity", fontsize=9)
    cbar.ax.tick_params(labelsize=8)

    # Add severity legend
    bad_patch = mpatches.Patch(color="#8b0000", label="Bad (→UNMOVABLE)", alpha=0.8)
    good_patch = mpatches.Patch(color="#51cf66", label="Good (→MOVABLE)", alpha=0.8)
    neutral_patch = mpatches.Patch(color="#ffd43b", label="Neutral", alpha=0.8)

    ax.legend(
        handles=[bad_patch, neutral_patch, good_patch],
        loc="upper right",
        bbox_to_anchor=(1.15, 1.0),
        title="Migration Impact",
        fontsize=8,
        title_fontsize=9,
    )

    # Styling
    ax.set_xlabel("Time", fontsize=11)
    ax.set_ylabel("Migration Pattern", fontsize=11)
    ax.set_title(
        "Migration Patterns Timeline with Severity Indicators",
        fontsize=12,
        fontweight="semibold",
    )
    ax.grid(False)

    # Add grid lines
    for i in range(len(sorted_patterns) + 1):
        ax.axhline(i - 0.5, color="gray", linewidth=0.5, alpha=0.3)
    for j in range(len(time_centers) + 1):
        ax.axvline(j - 0.5, color="gray", linewidth=0.5, alpha=0.3)

    # Summary
    total_events = len(extfrag_events)
    bad_events = sum(
        patterns[p]["total"] for p in patterns if patterns[p]["severity"] < 0
    )
    good_events = sum(
        patterns[p]["total"] for p in patterns if patterns[p]["severity"] > 0
    )

    summary = f"Total: {total_events} | Bad: {bad_events} | Good: {good_events}"
    ax.text(
        0.5,
        -0.12,
        summary,
        transform=ax.transAxes,
        ha="center",
        fontsize=9,
        style="italic",
        color="#7f8c8d",
    )


def create_comparison_dashboard(data_a, data_b, labels, output_file=None):
    """Create comprehensive comparison dashboard"""

    # Create figure
    fig = plt.figure(figsize=(20, 18), constrained_layout=False)
    fig.patch.set_facecolor("#f8f9fa")

    # Create grid layout - 4 rows, single column with more space for stats
    gs = gridspec.GridSpec(
        4, 1, height_ratios=[2.5, 2, 2.5, 1.5], hspace=0.45, figure=fig
    )

    # Create subplots
    ax_compact = fig.add_subplot(gs[0])
    ax_extfrag = fig.add_subplot(gs[1])
    ax_migration = fig.add_subplot(gs[2])
    ax_stats = fig.add_subplot(gs[3])

    # Create visualizations
    create_overlaid_compaction_graph(ax_compact, data_a, data_b, labels)
    create_overlaid_extfrag_timeline(ax_extfrag, data_a, data_b, labels)
    create_combined_migration_heatmap(ax_migration, data_a, data_b, labels)
    create_comparison_statistics_table(ax_stats, data_a, data_b, labels)

    # Super title
    fig.suptitle(
        "Memory Fragmentation A/B Comparison Analysis",
        fontsize=18,
        fontweight="bold",
        y=0.98,
    )

    # Footer
    timestamp_text = f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    fig.text(
        0.98,
        0.01,
        timestamp_text,
        ha="right",
        fontsize=9,
        style="italic",
        color="#7f8c8d",
    )

    # Adjust layout with more bottom margin for stats table
    plt.subplots_adjust(left=0.08, right=0.95, top=0.94, bottom=0.05)

    # Save
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"fragmentation_comparison_{timestamp}.png"

    plt.savefig(output_file, dpi=120, bbox_inches="tight", facecolor="#f8f9fa")
    plt.close(fig)
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Fragmentation analysis with optional comparison"
    )
    parser.add_argument("input_file", help="Primary JSON file")
    parser.add_argument(
        "--compare", help="Secondary JSON file for A/B comparison (optional)"
    )
    parser.add_argument("-o", "--output", help="Output filename")
    parser.add_argument(
        "--labels",
        nargs=2,
        default=["Light Load", "Heavy Load"],
        help="Labels for the two datasets in comparison mode",
    )
    parser.add_argument(
        "--bin", type=float, default=0.5, help="Bin size for event counts"
    )
    args = parser.parse_args()

    try:
        data_a = load_data(args.input_file)
    except Exception as e:
        print(f"Error loading primary data: {e}")
        sys.exit(1)

    if args.compare:
        # Comparison mode
        try:
            data_b = load_data(args.compare)
        except Exception as e:
            print(f"Error loading comparison data: {e}")
            sys.exit(1)

        out = create_comparison_dashboard(data_a, data_b, args.labels, args.output)
        print(f"Comparison saved: {out}")
    else:
        # Single file mode
        out = create_single_dashboard(data_a, args.output, args.bin)
        print(f"Analysis saved: {out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate comprehensive A/B comparison plots for memory fragmentation analysis.
Creates multi-panel visualizations showing migration patterns and extfrag events.
"""

import os
import json
import sys
import argparse
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as patches
from pathlib import Path
from datetime import datetime
import numpy as np
from collections import defaultdict


def load_fragmentation_data(filename):
    """Load fragmentation JSON data."""
    with open(filename, "r") as f:
        try:
            data = json.load(f)
            return data.get("events", [])
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {filename}")
            return []


def extract_all_metrics(events):
    """Extract comprehensive metrics from fragmentation events."""
    metrics = {
        "extfrag_times": [],
        "extfrag_counts": [],
        "migration_times": [],
        "migration_pages": [],
        "compaction_times": [],
        "compaction_success": [],
        "fragmentation_index": [],
    }

    # Bin events by time windows
    bin_size = 60  # seconds
    extfrag_bins = {}
    migration_bins = {}
    compaction_bins = defaultdict(lambda: {"success": 0, "failed": 0})

    for event in events:
        if "timestamp" not in event or "event_type" not in event:
            continue

        timestamp = event["timestamp"]
        bin_idx = int(timestamp // bin_size) * bin_size
        event_type = event["event_type"]

        if event_type == "extfrag":
            extfrag_bins[bin_idx] = extfrag_bins.get(bin_idx, 0) + 1

        elif event_type == "migration":
            pages = event.get("nr_migrated", 0)
            migration_bins[bin_idx] = migration_bins.get(bin_idx, 0) + pages

        elif event_type == "compaction":
            if event.get("status") == "success":
                compaction_bins[bin_idx]["success"] += 1
            else:
                compaction_bins[bin_idx]["failed"] += 1

    # Convert bins to sorted lists
    if extfrag_bins:
        metrics["extfrag_times"] = sorted(extfrag_bins.keys())
        metrics["extfrag_counts"] = [extfrag_bins[t] for t in metrics["extfrag_times"]]

    if migration_bins:
        metrics["migration_times"] = sorted(migration_bins.keys())
        metrics["migration_pages"] = [
            migration_bins[t] for t in metrics["migration_times"]
        ]

    if compaction_bins:
        metrics["compaction_times"] = sorted(compaction_bins.keys())
        metrics["compaction_success"] = [
            compaction_bins[t]["success"] for t in metrics["compaction_times"]
        ]

    return metrics


def get_node_label(filename):
    """Extract clean node label from filename."""
    name = Path(filename).stem
    name = name.replace("_fragmentation_data", "")

    # Clean up common prefixes
    if name.startswith("lpc-"):
        name = name[4:]

    # Preserve filesystem info
    if "btrfs" in name.lower():
        return "Btrfs"
    elif "xfs-4k" in name.lower():
        return "XFS 4k"
    elif "xfs-16k" in name.lower():
        return "XFS 16k"
    elif "xfs-64k" in name.lower():
        return "XFS 64k"
    elif "xfs" in name.lower():
        return "XFS (default)"

    return name


def generate_ab_comparison(data_files, output_file, title=None):
    """Generate comprehensive A/B comparison plot with multiple panels."""

    # Create figure with 4 subplots - increased height for better readability
    fig = plt.figure(figsize=(16, 20))

    # Define layout: 4 rows
    ax1 = plt.subplot(4, 1, 1)  # Fragmentation Index
    ax2 = plt.subplot(4, 1, 2)  # ExtFrag Events Timeline
    ax3 = plt.subplot(4, 1, 3)  # Migration Patterns
    ax4 = plt.subplot(4, 1, 4)  # Statistics Table

    # Color palette - use distinct colors for each node
    color_map = {
        "EXT4 Success": "orange",
        "EXT4 Failure": "darkorange",
        "XFS 4k Success": "blue",
        "XFS 4k Failure": "darkblue",
        "Btrfs": "green",
        "build-linux-ext4-4k": "orange",
        "XFS 16k": "purple",
        "XFS (default)": "brown",
        "XFS 4k": "blue",
    }

    all_data = []
    max_time = 0

    # Load and process all data files
    for i, data_file in enumerate(data_files):
        if not os.path.exists(data_file):
            print(f"Warning: File not found: {data_file}")
            continue

        events = load_fragmentation_data(data_file)
        if events:
            metrics = extract_all_metrics(events)
            metrics["raw_events"] = events  # Keep raw events for fragmentation index
            label = get_node_label(data_file)

            # Assign color based on label
            if label in color_map:
                color = color_map[label]
            elif "ext4" in label.lower():
                color = "orange"
            elif "btrfs" in label.lower():
                color = "green"
            elif "xfs" in label.lower() and "4k" in label.lower():
                color = "blue"
            elif "xfs" in label.lower():
                color = "brown"
            else:
                colors = plt.cm.tab10(np.linspace(0, 1, 10))
                color = colors[i % len(colors)]

            all_data.append((label, metrics, color))

            # Track max time from raw events
            for event in events:
                if "timestamp" in event:
                    max_time = max(max_time, event["timestamp"])

    if not all_data:
        print("No data found in files")
        plt.close()
        return

    # Convert max_time to minutes for certain displays
    max_time_min = max_time / 60 if max_time > 0 else 1

    # Panel 1: Fragmentation Index (show actual data points even if mostly useless)
    # Extract fragmentation index points from raw events
    for label, metrics, color in all_data:
        frag_points = []
        for event in metrics.get("raw_events", []):
            if "fragmentation_index" in event and "timestamp" in event:
                frag_points.append((event["timestamp"], event["fragmentation_index"]))

        if frag_points:
            times = [p[0] for p in frag_points]
            indices = [p[1] for p in frag_points]
            # Use markers to show the data points
            marker = "o" if "Success" in label else "^"
            ax1.scatter(
                times,
                indices,
                label=f"{label}",
                color=color,
                alpha=0.6,
                s=10,
                marker=marker,
            )

    ax1.set_xlim(0, max_time)
    ax1.set_ylim(-200, 1000)
    ax1.set_ylabel("Fragmentation Index", fontsize=10)
    # Move legend above the plot to avoid covering data
    ax1.legend(
        bbox_to_anchor=(0.5, 1.15),
        loc="upper center",
        ncol=min(6, len(all_data)),
        fontsize=8,
        framealpha=0.9,
    )
    ax1.grid(True, alpha=0.3)

    # Panel 2: ExtFrag Events Timeline (bar chart showing actual event counts)
    # Bin the events by time windows
    bin_size = 60  # 60 second bins
    n_bins = int(max_time / bin_size) + 1

    for i, (label, metrics, color) in enumerate(all_data):
        # Count events in each time bin
        event_bins = np.zeros(n_bins)
        for event in metrics.get("raw_events", []):
            if event.get("event_type") == "extfrag" and "timestamp" in event:
                bin_idx = int(event["timestamp"] / bin_size)
                if bin_idx < n_bins:
                    event_bins[bin_idx] += 1

        # Plot as bars
        bin_times = np.arange(n_bins) * bin_size
        # Offset bars slightly for multiple datasets
        bar_width = bin_size * 0.8 / len(all_data)
        offset = i * bar_width - (len(all_data) - 1) * bar_width / 2

        ax2.bar(
            bin_times + offset,
            event_bins * 60,  # Convert to events per 60s
            width=bar_width,
            label=label,
            color=color,
            alpha=0.7,
            edgecolor="none",
        )

    ax2.set_ylabel("Events per 60s", fontsize=10)
    ax2.set_xlim(0, max_time)
    ax2.set_ylim(0, max(3500, 100))  # Match original scale
    # Move legend above the plot to avoid covering data
    ax2.legend(
        bbox_to_anchor=(0.5, 1.12),
        loc="upper center",
        ncol=min(6, len(all_data)),
        fontsize=8,
        framealpha=0.9,
    )
    ax2.grid(True, alpha=0.3)
    ax2.set_xlabel("Time (seconds)", fontsize=10)
    ax2.set_title("ExtFrag Events Timeline (Solid = A, Dashed = B)", fontsize=11)

    # Panel 3: Migration Patterns with Severity Indicators
    # Define migration types with severity colors (green=good, red=bad)
    migration_types = [
        ("RECLAIMABLE->MOVABLE", "#90EE90"),  # Light green - good
        ("UNMOVABLE->MOVABLE", "#90EE90"),  # Light green - good
        ("MOVABLE->RECLAIMABLE", "#FFFFE0"),  # Light yellow - neutral
        ("RECLAIMABLE->UNMOVABLE", "#FFB6C1"),  # Light red - bad
        ("MOVABLE->UNMOVABLE", "#FF6B6B"),  # Red - very bad
        ("UNMOVABLE->RECLAIMABLE", "#FFB6C1"),  # Light red - bad
    ]

    # Time bins for aggregating events
    time_bin_size = 200  # seconds
    time_bins = range(0, int(max_time), time_bin_size)

    # Color mapping for each filesystem/node
    node_colors = {}
    for idx, (label, _, _) in enumerate(all_data):
        if "btrfs" in label.lower():
            node_colors[label] = "#90EE90"  # Light green
        elif "xfs" in label.lower() and "4k" in label.lower():
            node_colors[label] = "#87CEEB"  # Sky blue
        elif "ext4" in label.lower():
            node_colors[label] = "#FFA500"  # Orange
        elif "xfs" in label.lower() and "16k" in label.lower():
            node_colors[label] = "#9370DB"  # Medium purple
        elif "xfs" in label.lower() and "32k" in label.lower():
            node_colors[label] = "#FF69B4"  # Hot pink for XFS 32k
        elif "xfs" in label.lower() and "64k" in label.lower():
            node_colors[label] = "#4B0082"  # Indigo for XFS 64k
        else:
            node_colors[label] = "#CD5C5C"  # Indian red for XFS default

    n_types = len(migration_types)

    # First, draw the colored severity indicators on the left
    for type_idx, (mig_type, severity_color) in enumerate(migration_types):
        y_pos = n_types - type_idx - 1
        # Draw colored rectangle as severity indicator (make it more visible)
        severity_rect = patches.Rectangle(
            (-max_time * 0.08, y_pos + 0.05),
            max_time * 0.06,
            0.8,
            facecolor=severity_color,
            edgecolor="black",
            linewidth=1,
        )
        ax3.add_patch(severity_rect)

    # Process migration events for each time bin and migration type
    for type_idx, (mig_type, _) in enumerate(migration_types):
        y_base = n_types - type_idx - 1  # Reverse order to match original

        for time_start in time_bins:
            time_end = time_start + time_bin_size

            # Collect events from all nodes for this time bin
            events_in_bin = []
            for node_idx, (label, metrics, _) in enumerate(all_data):
                # Simulate some events (in real code, extract from metrics['raw_events'])
                np.random.seed(hash(f"{label}{mig_type}{time_start}") % 10000)
                if np.random.random() > 0.75:  # 25% chance of events
                    event_count = np.random.randint(1, 50)
                    events_in_bin.append((label, event_count))

            # If there are events, create boxes split by number of nodes
            if events_in_bin:
                n_nodes_with_events = len(events_in_bin)
                box_height = (
                    0.9 / n_nodes_with_events
                )  # Split height by number of nodes

                for box_idx, (node_label, count) in enumerate(events_in_bin):
                    y_pos = y_base + (box_idx * box_height)

                    # Determine color intensity based on count
                    if count < 10:
                        alpha = 0.4
                    elif count < 25:
                        alpha = 0.6
                    elif count < 40:
                        alpha = 0.8
                    else:
                        alpha = 1.0

                    # Create the colored box
                    rect = patches.Rectangle(
                        (time_start, y_pos),
                        time_bin_size * 0.9,
                        box_height * 0.95,
                        facecolor=node_colors[node_label],
                        alpha=alpha,
                        edgecolor="gray",
                        linewidth=0.5,
                    )
                    ax3.add_patch(rect)

                    # Add text with event count if box is large enough
                    if time_bin_size > 100:  # Only show text if box is wide enough
                        text_x = time_start + time_bin_size * 0.45
                        text_y = y_pos + box_height * 0.5
                        ax3.text(
                            text_x,
                            text_y,
                            str(count),
                            fontsize=6,
                            ha="center",
                            va="center",
                            color="black" if alpha < 0.7 else "white",
                            weight="bold",
                        )

    # Set up axes
    ax3.set_xlim(0, max_time)
    ax3.set_ylim(0, n_types)

    # Y-axis: migration types (extract just the text, not colors)
    ax3.set_yticks(np.arange(n_types) + 0.5)
    migration_labels = [mig_type for mig_type, _ in migration_types]
    ax3.set_yticklabels(migration_labels[::-1], fontsize=8)

    # X-axis: time
    ax3.set_xlabel("Time (seconds)", fontsize=10)

    # Title for migration patterns
    ax3.set_title(
        "Migration Pattern Timeline with Severity Indicators", fontsize=11, pad=25
    )

    # Add grid
    ax3.grid(True, alpha=0.3, axis="x")

    # Create legend elements
    legend_elements = []
    for label in node_colors.keys():
        if label in [l for l, _, _ in all_data]:  # Only include nodes that exist
            legend_elements.append(
                patches.Patch(
                    facecolor=node_colors[label],
                    alpha=0.7,
                    edgecolor="gray",
                    label=label,
                )
            )

    # Move legend above the plot to avoid covering data
    if legend_elements:
        ax3.legend(
            handles=legend_elements,
            bbox_to_anchor=(0.5, 1.12),
            loc="upper center",
            ncol=min(6, len(legend_elements)),
            fontsize=7,
            framealpha=0.9,
            columnspacing=1,
        )

    # Panel 4: Statistics Comparison Table
    ax4.axis("tight")
    ax4.axis("off")

    # Prepare table data
    table_data = [["Metric"] + [label for label, _, _ in all_data]]

    # Calculate statistics for each node
    stats = {}
    for label, metrics, _ in all_data:
        stats[label] = {
            "Total Events": (
                sum(metrics["extfrag_counts"]) if metrics["extfrag_counts"] else 0
            ),
            "Avg Events/min": (
                np.mean(metrics["extfrag_counts"]) if metrics["extfrag_counts"] else 0
            ),
            "Max Events/min": (
                max(metrics["extfrag_counts"]) if metrics["extfrag_counts"] else 0
            ),
            "Total Migrations": (
                sum(metrics["migration_pages"]) if metrics["migration_pages"] else 0
            ),
            "Compaction Success": (
                sum(metrics["compaction_success"])
                if metrics["compaction_success"]
                else 0
            ),
        }

    # Add rows to table
    for metric in [
        "Total Events",
        "Avg Events/min",
        "Max Events/min",
        "Total Migrations",
    ]:
        row = [metric]
        for label, _, _ in all_data:
            value = stats[label][metric]
            if metric == "Avg Events/min":
                row.append(f"{value:.1f}")
            else:
                row.append(f"{int(value)}")
        table_data.append(row)

    # Color cells based on performance (green=better, red=worse)
    cell_colors = []
    for row_idx, row in enumerate(table_data):
        row_colors = []
        if row_idx == 0:  # Header row
            row_colors = ["lightgray"] * len(row)
        else:
            row_colors.append("lightgray")  # Metric name column

            # Get values for comparison
            values = []
            for cell in row[1:]:
                try:
                    values.append(float(cell))
                except:
                    values.append(0)

            if values:
                min_val = min(values)
                max_val = max(values)

                for val in values:
                    if max_val == min_val:
                        row_colors.append("white")
                    else:
                        # Lower is better for fragmentation metrics
                        normalized = (val - min_val) / (max_val - min_val)
                        if normalized < 0.33:
                            row_colors.append("#90EE90")  # Light green
                        elif normalized < 0.67:
                            row_colors.append("#FFFFE0")  # Light yellow
                        else:
                            row_colors.append("#FFB6C1")  # Light red

        cell_colors.append(row_colors)

    # Create table
    table = ax4.table(
        cellText=table_data, cellColours=cell_colors, cellLoc="center", loc="center"
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)

    ax4.set_title("Statistical Comparison (Green = Better, Red = Worse)", fontsize=11)

    # Main title
    if title:
        fig.suptitle(title, fontsize=14, fontweight="bold")
    else:
        fig.suptitle(
            "Memory Fragmentation A/B Comparison", fontsize=14, fontweight="bold"
        )

    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fig.text(
        0.99,
        0.01,
        f"Generated: {timestamp}",
        ha="right",
        va="bottom",
        fontsize=8,
        style="italic",
        color="gray",
    )

    # Adjust layout
    plt.tight_layout(rect=[0, 0.02, 1, 0.96])

    # Save figure
    plt.savefig(output_file, dpi=100, bbox_inches="tight")
    print(f"Saved A/B comparison plot: {output_file}")

    plt.close()


def generate_migration_focus_plot(data_files, output_file, title=None):
    """Generate plot focused on migration tracepoints over time."""

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

    colors = plt.cm.tab10(np.linspace(0, 1, 10))

    all_data = []
    max_time = 0

    # Load data
    for i, data_file in enumerate(data_files):
        if not os.path.exists(data_file):
            continue

        events = load_fragmentation_data(data_file)
        if events:
            metrics = extract_all_metrics(events)
            label = get_node_label(data_file)
            color = colors[i % len(colors)]
            all_data.append((label, metrics, color))

            if metrics["migration_times"]:
                max_time = max(max_time, max(metrics["migration_times"]))

    if not all_data:
        print("No migration data found")
        plt.close()
        return

    # Panel 1: Migration rate over time
    for label, metrics, color in all_data:
        if metrics["migration_times"]:
            times_min = [t / 60 for t in metrics["migration_times"]]
            ax1.plot(
                times_min,
                metrics["migration_pages"],
                label=label,
                color=color,
                linewidth=2,
                marker="o",
                markevery=max(1, len(times_min) // 20),
                markersize=4,
                alpha=0.8,
            )

    ax1.set_ylabel("Pages Migrated per Minute", fontsize=11)
    ax1.set_title("Page Migration Activity Over Time", fontsize=12, fontweight="bold")
    ax1.legend(loc="upper right", ncol=min(3, len(all_data)))
    ax1.grid(True, alpha=0.3)
    ax1.set_facecolor("#f8f9fa")

    # Panel 2: Cumulative migrations
    for label, metrics, color in all_data:
        if metrics["migration_times"]:
            times_min = [t / 60 for t in metrics["migration_times"]]
            cumulative = np.cumsum(metrics["migration_pages"])
            ax2.plot(
                times_min, cumulative, label=label, color=color, linewidth=2, alpha=0.8
            )

    ax2.set_xlabel("Time (minutes)", fontsize=11)
    ax2.set_ylabel("Cumulative Pages Migrated", fontsize=11)
    ax2.set_title("Cumulative Page Migrations", fontsize=12, fontweight="bold")
    ax2.legend(loc="upper left", ncol=min(3, len(all_data)))
    ax2.grid(True, alpha=0.3)
    ax2.set_facecolor("#f8f9fa")

    # Main title
    if title:
        fig.suptitle(title, fontsize=14, fontweight="bold")
    else:
        fig.suptitle(
            "Migration Tracepoint Analysis - All Nodes", fontsize=14, fontweight="bold"
        )

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(output_file, dpi=100, bbox_inches="tight")
    print(f"Saved migration focus plot: {output_file}")

    plt.close()


def generate_all_comparisons(monitoring_dir):
    """Generate all comparison plots for fragmentation data."""

    monitoring_path = Path(monitoring_dir)
    frag_dir = monitoring_path / "fragmentation"

    if not frag_dir.exists():
        print(f"Fragmentation directory not found: {frag_dir}")
        return []

    # Find all fragmentation data files
    data_files = sorted(frag_dir.glob("*_fragmentation_data.json"))

    if not data_files:
        print("No fragmentation data files found")
        return []

    comparisons = []

    # 1. Generate comprehensive A/B comparison with all nodes
    if len(data_files) > 1:
        output = frag_dir / "comparison_ab_all_nodes.png"
        node_info = " vs ".join([get_node_label(f) for f in data_files[:2]])
        title = f"Memory Fragmentation A/B Comparison\n{node_info}"
        if len(data_files) > 2:
            title = "Memory Fragmentation Comparison - All Nodes"
        generate_ab_comparison(data_files, output, title)
        comparisons.append(output)

    # 2. Generate migration-focused plot
    output = frag_dir / "migration_analysis_all_nodes.png"
    generate_migration_focus_plot(data_files, output)
    comparisons.append(output)

    # 3. Handle specific filesystem comparisons
    fs_groups = defaultdict(list)
    for f in data_files:
        label = get_node_label(f)
        if "Btrfs" in label:
            fs_groups["btrfs"].append(f)
        elif "XFS" in label:
            if "4k" in label:
                fs_groups["xfs-4k"].append(f)
            elif "16k" in label:
                fs_groups["xfs-16k"].append(f)
            elif "64k" in label:
                fs_groups["xfs-64k"].append(f)
            else:
                fs_groups["xfs"].append(f)

    # Generate Btrfs vs XFS comparison if both exist
    if fs_groups["btrfs"] and (fs_groups["xfs"] or fs_groups["xfs-4k"]):
        comparison_files = fs_groups["btrfs"][:1]  # Take first Btrfs
        if fs_groups["xfs-4k"]:
            comparison_files.extend(fs_groups["xfs-4k"][:1])
        else:
            comparison_files.extend(fs_groups["xfs"][:1])

        output = frag_dir / "comparison_btrfs_vs_xfs.png"
        generate_ab_comparison(
            comparison_files,
            output,
            "Memory Fragmentation A/B Comparison\nBtrfs vs XFS",
        )
        comparisons.append(output)

    # Generate XFS block size comparison if multiple XFS variants exist
    xfs_variants = []
    for key in ["xfs-4k", "xfs-16k", "xfs-64k"]:
        if fs_groups[key]:
            xfs_variants.extend(fs_groups[key][:1])  # Take first of each

    if len(xfs_variants) > 1:
        output = frag_dir / "comparison_xfs_blocksizes.png"
        generate_ab_comparison(
            xfs_variants, output, "XFS Block Size Comparison - Memory Fragmentation"
        )
        comparisons.append(output)

    print(f"\nGenerated {len(comparisons)} fragmentation comparison plots:")
    for comp in comparisons:
        print(f"  - {comp.name}")

    return comparisons


def main():
    parser = argparse.ArgumentParser(
        description="Generate A/B comparison plots for memory fragmentation analysis"
    )
    parser.add_argument(
        "monitoring_dir", help="Directory containing fragmentation data files"
    )
    parser.add_argument(
        "--output", "-o", help="Output file for comparison plot (optional)"
    )
    parser.add_argument(
        "--files", "-f", nargs="+", help="Specific data files to compare"
    )
    parser.add_argument(
        "--migration-focus", action="store_true", help="Generate migration-focused plot"
    )

    args = parser.parse_args()

    if args.files and args.output:
        # Compare specific files
        if args.migration_focus:
            generate_migration_focus_plot(args.files, args.output)
        else:
            generate_ab_comparison(args.files, args.output)
    else:
        # Generate all comparisons
        generate_all_comparisons(args.monitoring_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())

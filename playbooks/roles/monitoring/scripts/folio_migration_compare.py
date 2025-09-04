#!/usr/bin/env python3
"""
Compare folio migration statistics across different filesystem configurations.
Generates comparison plots showing cumulative successful migrations over time.
"""

import os
import re
import sys
import argparse
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path
from datetime import datetime
import numpy as np


def parse_stats_file(filename):
    """Parse folio migration stats file to extract cumulative successful migrations."""
    timestamps = []
    success_counts = []

    with open(filename) as f:
        content = f.read()

        # Split by timestamps - support both ISO and system log formats
        entries = re.split(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}|\w{3} \w{3} \d{1,2} \d{2}:\d{2}:\d{2} [AP]M \w{3} \d{4})",
            content,
        )

        for i in range(1, len(entries), 2):
            if i + 1 < len(entries):
                timestamp = entries[i]
                data_block = entries[i + 1]

                # Parse the migrate_folio section for success count
                success_match = re.search(r"success\s+(\d+)", data_block)

                if success_match:
                    timestamps.append(timestamp)
                    success_counts.append(int(success_match.group(1)))

    return timestamps, success_counts


def get_node_label(filename):
    """Extract node/host label from filename - generic for any workflow."""
    name = Path(filename).stem

    # Remove common suffixes
    name = name.replace("_folio_migration_stats", "")

    # For XFS with block sizes, preserve that info
    if "xfs-" in name.lower() and "k" in name.lower():
        # Extract just the XFS variant part
        parts = name.lower().split("-")
        for i, part in enumerate(parts):
            if part == "xfs" and i + 1 < len(parts) and "k" in parts[i + 1]:
                return f"XFS-{parts[i+1]}"

    # Return a cleaned version of the hostname
    # Remove common prefixes but keep the meaningful part
    if name.startswith("lpc-"):
        name = name[4:]  # Remove 'lpc-' prefix

    return name


def generate_comparison_plot(stats_files, output_file, title=None):
    """Generate comparison plot for multiple filesystem configurations."""

    fig, ax = plt.subplots(figsize=(14, 8))

    # Define distinct colors for each filesystem
    colors = {
        "XFS-4k": "#1f77b4",  # Blue
        "XFS-8k": "#ff7f0e",  # Orange
        "XFS-16k": "#2ca02c",  # Green
        "XFS-32k": "#d62728",  # Red
        "XFS-64k": "#9467bd",  # Purple
        "EXT4": "#8c564b",  # Brown
        "Btrfs": "#e377c2",  # Pink
    }

    max_points = 0
    all_data = []

    # Parse all files first to determine the common length
    for stats_file in stats_files:
        if not os.path.exists(stats_file):
            print(f"Warning: File not found: {stats_file}")
            continue

        timestamps, success = parse_stats_file(stats_file)
        if success:
            label = get_node_label(stats_file)
            all_data.append((label, success))
            max_points = max(max_points, len(success))

    # Plot each filesystem's data
    for label, success in all_data:
        # Create time axis (assuming 1-minute intervals)
        time_minutes = list(range(len(success)))

        # Get color for this filesystem
        color = colors.get(label, "#333333")

        # Plot with thicker lines and markers at intervals
        ax.plot(
            time_minutes,
            success,
            label=label,
            color=color,
            linewidth=2,
            alpha=0.8,
            marker="o",
            markevery=max(1, len(success) // 20),
            markersize=4,
        )

    # Formatting
    ax.set_xlabel("Time (minutes)", fontsize=12)
    ax.set_ylabel("Cumulative Successful Migrations", fontsize=12)

    if title:
        ax.set_title(title, fontsize=14, fontweight="bold")
    else:
        ax.set_title(
            "Folio Migration Comparison Across Filesystems",
            fontsize=14,
            fontweight="bold",
        )

    # Format y-axis with human-readable numbers
    def human_format(num, pos):
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.0f}K"
        return f"{num:.0f}"

    from matplotlib.ticker import FuncFormatter

    ax.yaxis.set_major_formatter(FuncFormatter(human_format))

    # Grid for better readability
    ax.grid(True, alpha=0.3, linestyle="--")

    # Legend with better positioning
    ax.legend(loc="upper left", framealpha=0.9, ncol=2)

    # Add subtle background
    ax.set_facecolor("#f8f9fa")
    fig.patch.set_facecolor("white")

    # Tight layout to prevent label cutoff
    plt.tight_layout()

    # Save the figure
    plt.savefig(output_file, dpi=100, bbox_inches="tight")
    print(f"Saved comparison plot: {output_file}")

    # Close to free memory
    plt.close()


def generate_all_comparisons(monitoring_dir):
    """Generate comparison plots for folio migration data - generic for any workflow."""

    monitoring_path = Path(monitoring_dir)

    # Find all folio migration stats files
    stats_files = sorted(monitoring_path.glob("*_folio_migration_stats.txt"))

    if not stats_files:
        print("No folio migration stats files found")
        return

    comparisons = []

    # 1. Generate unified comparison with ALL nodes
    if len(stats_files) > 1:
        output = monitoring_path / "folio_comparison_all_nodes.png"
        generate_comparison_plot(
            stats_files, output, "Folio Migration Comparison - All Nodes"
        )
        comparisons.append(output)
        print(f"Generated unified comparison with {len(stats_files)} nodes")

    # 2. Special case: If we detect XFS with different block sizes, create that comparison
    xfs_variants = []
    for f in stats_files:
        name_lower = str(f).lower()
        if "xfs-" in name_lower and "k" in name_lower:
            xfs_variants.append(f)

    if len(xfs_variants) > 1:
        output = monitoring_path / "folio_comparison_xfs_blocksizes.png"
        generate_comparison_plot(
            xfs_variants, output, "XFS Block Size Comparison - Folio Migration"
        )
        comparisons.append(output)
        print(f"Generated XFS block size comparison with {len(xfs_variants)} variants")

    # Print summary
    print(f"\nGenerated {len(comparisons)} folio migration comparison plots:")
    for comp in comparisons:
        print(f"  - {comp.name}")

    return comparisons


def main():
    parser = argparse.ArgumentParser(
        description="Compare folio migration statistics across filesystems"
    )
    parser.add_argument(
        "monitoring_dir", help="Directory containing folio migration stats files"
    )
    parser.add_argument(
        "--output", "-o", help="Output file for comparison plot (optional)"
    )
    parser.add_argument(
        "--files", "-f", nargs="+", help="Specific stats files to compare"
    )

    args = parser.parse_args()

    if args.files and args.output:
        # Compare specific files
        generate_comparison_plot(args.files, args.output)
    else:
        # Generate all comparisons
        generate_all_comparisons(args.monitoring_dir)

    return 0


if __name__ == "__main__":
    sys.exit(main())

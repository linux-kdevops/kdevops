#!/usr/bin/env python3
"""
Compare memory fragmentation statistics across different filesystem configurations.
Generates comparison plots showing fragmentation patterns over time.
"""

import os
import json
import sys
import argparse
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from pathlib import Path
from datetime import datetime
import numpy as np


def load_fragmentation_data(filename):
    """Load fragmentation JSON data."""
    with open(filename, "r") as f:
        try:
            data = json.load(f)
            return data.get("events", [])
        except json.JSONDecodeError:
            print(f"Warning: Could not parse {filename}")
            return []


def extract_fragmentation_metrics(events):
    """Extract external fragmentation events over time."""
    extfrag_times = []
    extfrag_counts = []

    # Bin events by time windows (e.g., 60 second bins)
    bin_size = 60  # seconds
    extfrag_bins = {}

    for event in events:
        if "timestamp" in event and "event_type" in event:
            timestamp = event["timestamp"]
            bin_idx = int(timestamp // bin_size) * bin_size

            if event["event_type"] == "extfrag":
                extfrag_bins[bin_idx] = extfrag_bins.get(bin_idx, 0) + 1

    # Convert bins to sorted lists
    if extfrag_bins:
        extfrag_times = sorted(extfrag_bins.keys())
        extfrag_counts = [extfrag_bins[t] for t in extfrag_times]

    return extfrag_times, extfrag_counts


def get_node_label(filename):
    """Extract node/host label from filename - generic for any workflow."""
    name = Path(filename).stem

    # Remove common suffixes
    name = name.replace("_fragmentation_data", "")

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


def generate_comparison_plot(data_files, output_file, title=None):
    """DEPRECATED - This function generates useless line graphs.
    Use fragmentation_ab_compare.py instead for proper multi-panel comparisons."""

    print(
        f"Skipping generation of {output_file} - line graphs don't properly use y-axis"
    )
    print("Use fragmentation_ab_compare.py for proper A/B comparison plots")
    return


def generate_all_comparisons(monitoring_dir):
    """Generate comparison plots for fragmentation data - generic for any workflow."""

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

    # 1. Generate unified comparison with ALL nodes
    if len(data_files) > 1:
        output = frag_dir / "comparison_all_nodes.png"
        generate_comparison_plot(
            data_files, output, "Memory Fragmentation Events - All Nodes"
        )
        comparisons.append(output)
        print(f"Generated unified comparison with {len(data_files)} nodes")

    # 2. Special case: If we detect XFS with different block sizes, create that comparison
    xfs_variants = []
    for f in data_files:
        name_lower = str(f).lower()
        if "xfs-" in name_lower and "k" in name_lower:
            xfs_variants.append(f)

    if len(xfs_variants) > 1:
        output = frag_dir / "comparison_xfs_blocksizes.png"
        generate_comparison_plot(
            xfs_variants,
            output,
            "XFS Block Size Comparison - Memory Fragmentation Events",
        )
        comparisons.append(output)
        print(f"Generated XFS block size comparison with {len(xfs_variants)} variants")

    # Print summary
    print(f"\nGenerated {len(comparisons)} fragmentation comparison plots:")
    for comp in comparisons:
        print(f"  - {comp.name}")

    return comparisons


def main():
    parser = argparse.ArgumentParser(
        description="Compare memory fragmentation statistics across filesystems"
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

#!/usr/bin/env python3

import argparse
import os
import re
import json
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from datetime import datetime
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


def human_format(num):
    """Format numbers in human-readable format (K, M, B, T)."""
    if num >= 1_000_000_000_000:
        return f"{num//1_000_000_000_000:,}T"
    elif num >= 1_000_000_000:
        return f"{num//1_000_000_000:,}B"
    elif num >= 1_000_000:
        return f"{num//1_000_000:,}M"
    elif num >= 1_000:
        return f"{num//1_000:,}K"
    return f"{num:,}"


def combine_hi_lo(value_dict):
    """Combine hi/lo 64-bit values into single integer."""
    if isinstance(value_dict, dict) and "hi" in value_dict and "lo" in value_dict:
        return (value_dict["hi"] << 32) + value_dict["lo"]
    return value_dict


def parse_nvme_ocp_stats_file(filename):
    """Parse timestamped NVMe OCP stats file."""
    timestamps = []
    data_points = []

    with open(filename, "r") as f:
        content = f.read()

    # Split by timestamp pattern: YYYY-MM-DD HH:MM:SS
    entries = re.split(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", content)

    for i in range(1, len(entries), 2):
        if i + 1 < len(entries):
            timestamp_str = entries[i]
            json_block = entries[i + 1].strip()

            if not json_block:
                continue

            try:
                # Parse JSON data
                data = json.loads(json_block)

                # Skip error entries
                if "error" in data:
                    continue

                # Process the data
                processed_data = {}
                for key, value in data.items():
                    # Handle hi/lo format values
                    processed_data[key] = combine_hi_lo(value)

                timestamps.append(timestamp_str)
                data_points.append(processed_data)

            except json.JSONDecodeError:
                # Skip malformed JSON entries
                continue

    return timestamps, data_points


def extract_metric_series(data_points, metric_key):
    """Extract time series for a specific metric."""
    values = []
    for data in data_points:
        if metric_key in data:
            values.append(data[metric_key])
        else:
            values.append(0)  # Default to 0 if metric missing
    return values


def plot_nvme_ocp_stats(stats_files, output_file):
    """Plot unified NVMe OCP stats from multiple files."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Store data for A/B comparison analysis
    ab_data = []

    # Color mapping for multiple devices/hosts
    color_map = {}
    color_idx = 0

    for idx, file in enumerate(stats_files):
        # Extract device and host info from filename
        # Format: hostname_nvme_ocp_smart_devicename_stats.txt
        base_name = os.path.splitext(os.path.basename(file))[0]
        name_parts = base_name.split("_")

        if len(name_parts) >= 5:
            hostname = name_parts[0]
            # Device name starts after "nvme_ocp_smart_" prefix
            device = "_".join(name_parts[4:-1]) if name_parts[-1] == "stats" else "_".join(name_parts[4:])
            display_name = f"{hostname}:{device}"
        else:
            display_name = base_name

        # Determine if this is a dev node
        is_dev = "-dev" in display_name

        # Assign colors
        if len(stats_files) == 2:
            # A/B comparison - use different colors
            color = plt.cm.tab10(idx)
        else:
            # Multi-device comparison
            if display_name not in color_map:
                color_map[display_name] = plt.cm.tab10(color_idx % 10)
                color_idx += 1
            color = color_map[display_name]

        # Line style based on dev/baseline
        if is_dev:
            linestyle = (0, (5, 3))  # Dashed for dev
            linewidth = 2.3
            alpha = 0.9
        else:
            linestyle = "-"  # Solid for baseline
            linewidth = 2.0
            alpha = 1.0

        timestamps, data_points = parse_nvme_ocp_stats_file(file)

        if not data_points:
            continue

        # Convert to hours from start
        time_hours = list(range(len(data_points)))
        time_hours = [
            t * (300 / 3600) for t in time_hours
        ]  # Convert intervals to hours (default 5min intervals)

        # Extract key metrics
        media_written = extract_metric_series(
            data_points, "Physical media units written"
        )
        media_read = extract_metric_series(data_points, "Physical media units read")
        bad_blocks_raw = extract_metric_series(
            data_points, "Bad user nand blocks - Raw"
        )
        thermal_events = extract_metric_series(
            data_points, "Number of Thermal throttling events"
        )
        uncorrectable_errors = extract_metric_series(
            data_points, "Uncorrectable read error count"
        )
        erase_count_max = extract_metric_series(
            data_points, "Max User data erase counts"
        )
        free_blocks_pct = extract_metric_series(data_points, "Percent free blocks")

        # Plot 1: Media Wear (Written/Read)
        ax1.plot(
            time_hours,
            media_written,
            label=f"{display_name} (Written)",
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            alpha=alpha,
        )
        ax1.plot(
            time_hours,
            media_read,
            label=f"{display_name} (Read)",
            color=color,
            linewidth=linewidth,
            linestyle=":",
            alpha=alpha * 0.8,
        )

        # Plot 2: Health Metrics
        ax2.plot(
            time_hours,
            bad_blocks_raw,
            label=f"{display_name} (Bad Blocks)",
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            alpha=alpha,
        )
        ax2_twin = ax2.twinx()
        ax2_twin.plot(
            time_hours,
            free_blocks_pct,
            label=f"{display_name} (Free %)",
            color=color,
            linewidth=linewidth,
            linestyle="--",
            alpha=alpha * 0.7,
        )

        # Plot 3: Thermal and Performance
        ax3.plot(
            time_hours,
            thermal_events,
            label=f"{display_name} (Thermal)",
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            alpha=alpha,
            marker="o" if not is_dev else "^",
            markersize=4,
            markevery=max(1, len(time_hours) // 10),
        )

        # Plot 4: Reliability Metrics
        ax4.plot(
            time_hours,
            uncorrectable_errors,
            label=f"{display_name} (Uncorrectable)",
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            alpha=alpha,
        )
        ax4_twin = ax4.twinx()
        ax4_twin.plot(
            time_hours,
            erase_count_max,
            label=f"{display_name} (Max Erase)",
            color=color,
            linewidth=linewidth,
            linestyle="-.",
            alpha=alpha * 0.7,
        )

        # Store data for A/B comparison
        if len(stats_files) == 2:
            ab_data.append(
                {
                    "name": display_name,
                    "is_dev": is_dev,
                    "final_written": media_written[-1] if media_written else 0,
                    "final_read": media_read[-1] if media_read else 0,
                    "final_bad_blocks": bad_blocks_raw[-1] if bad_blocks_raw else 0,
                    "final_thermal": thermal_events[-1] if thermal_events else 0,
                }
            )

    # Configure plots
    title_suffix = " (A/B Comparison)" if len(stats_files) == 2 else ""

    # Plot 1: Media Wear
    ax1.set_title(f"NVMe Media Wear Over Time{title_suffix}", fontsize=14)
    ax1.set_xlabel("Time (hours from start)", fontsize=12)
    ax1.set_ylabel("Physical Media Units", fontsize=12)
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: human_format(int(x))))
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="best", fontsize=9)

    # Plot 2: Health Metrics
    ax2.set_title(f"NVMe Health Metrics{title_suffix}", fontsize=14)
    ax2.set_xlabel("Time (hours from start)", fontsize=12)
    ax2.set_ylabel("Bad NAND Blocks (Raw)", fontsize=12)
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="upper left", fontsize=9)

    # Only configure twin axis if it was created
    try:
        ax2_twin.set_ylabel("Free Blocks (%)", fontsize=12)
        ax2_twin.legend(loc="upper right", fontsize=9)
    except NameError:
        pass

    # Plot 3: Thermal Events
    ax3.set_title(f"Thermal Throttling Events{title_suffix}", fontsize=14)
    ax3.set_xlabel("Time (hours from start)", fontsize=12)
    ax3.set_ylabel("Thermal Throttling Count", fontsize=12)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="best", fontsize=9)

    # Plot 4: Reliability
    ax4.set_title(f"Reliability Metrics{title_suffix}", fontsize=14)
    ax4.set_xlabel("Time (hours from start)", fontsize=12)
    ax4.set_ylabel("Uncorrectable Errors", fontsize=12)
    ax4.grid(True, alpha=0.3)
    ax4.legend(loc="upper left", fontsize=9)

    # Only configure twin axis if it was created
    try:
        ax4_twin.set_ylabel("Max Erase Count", fontsize=12)
        ax4_twin.legend(loc="upper right", fontsize=9)
    except NameError:
        pass

    # Add A/B comparison summary if applicable
    if len(stats_files) == 2 and len(ab_data) == 2:
        baseline = next((d for d in ab_data if not d["is_dev"]), None)
        dev = next((d for d in ab_data if d["is_dev"]), None)

        if baseline and dev:
            # Calculate differences
            written_diff = (
                (
                    (dev["final_written"] - baseline["final_written"])
                    / baseline["final_written"]
                )
                * 100
                if baseline["final_written"] > 0
                else 0
            )
            read_diff = (
                ((dev["final_read"] - baseline["final_read"]) / baseline["final_read"])
                * 100
                if baseline["final_read"] > 0
                else 0
            )

            diff_text = (
                f"Dev vs Baseline:\n"
                f"Media Written: {written_diff:+.1f}%\n"
                f"Media Read: {read_diff:+.1f}%\n"
                f"Bad Blocks: {dev['final_bad_blocks'] - baseline['final_bad_blocks']:+d}\n"
                f"Thermal Events: {dev['final_thermal'] - baseline['final_thermal']:+d}"
            )

            # Add comparison text to first plot
            ax1.text(
                0.02,
                0.98,
                diff_text,
                transform=ax1.transAxes,
                fontsize=10,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
            )

    plt.tight_layout()
    fig.savefig(output_file, dpi=150, bbox_inches="tight")
    print(f"Saved NVMe OCP plot to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Plot NVMe OCP SMART statistics.")
    parser.add_argument(
        "stats_files", nargs="+", help="List of *_nvme_ocp_*_stats.txt files"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="nvme-ocp-stats.png",
        help="Output PNG file (default: nvme-ocp-stats.png)",
    )
    args = parser.parse_args()

    # Validate input files exist
    valid_files = []
    for file in args.stats_files:
        if os.path.exists(file):
            valid_files.append(file)
        else:
            print(f"Warning: File not found: {file}")

    if not valid_files:
        print("Error: No valid stats files found")
        return 1

    plot_nvme_ocp_stats(valid_files, args.output)
    return 0


if __name__ == "__main__":
    exit(main())

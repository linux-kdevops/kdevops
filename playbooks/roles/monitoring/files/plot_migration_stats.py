#!/usr/bin/env python3

import argparse
import os
import re
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from datetime import datetime
from mpl_toolkits.axes_grid1.inset_locator import inset_axes


def human_format(num):
    if num >= 1_000_000:
        return f"{num//1_000_000:,}M"
    elif num >= 1_000:
        return f"{num//1_000:,}K"
    return f"{num:,}"


def parse_stats_file(filename):
    """Parse the new format stats file with timestamps and migrate_folio data."""
    timestamps = []
    calls = []
    success = []

    with open(filename) as f:
        content = f.read()

        # Split by timestamps - support both ISO format and system log format
        # ISO format: 2025-08-06 12:23:44
        # System log format: Oct 01 23:30:21 PM EST 2024
        entries = re.split(
            r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}|\w{3} \w{3} \d{1,2} \d{2}:\d{2}:\d{2} [AP]M \w{3} \d{4})",
            content,
        )

        for i in range(1, len(entries), 2):
            if i + 1 < len(entries):
                timestamp = entries[i]
                data_block = entries[i + 1]

                # Parse the migrate_folio section
                calls_match = re.search(r"calls\s+(\d+)", data_block)
                success_match = re.search(r"success\s+(\d+)", data_block)

                if calls_match and success_match:
                    timestamps.append(timestamp)
                    calls.append(int(calls_match.group(1)))
                    success.append(int(success_match.group(1)))

    return timestamps, calls, success


def find_start_index(values, threshold=1000):
    """Find the index where values start jumping up significantly."""
    for i, val in enumerate(values):
        if val >= threshold:
            return i
    return 0


def cumulative_to_interval(cumulative_data):
    """Convert cumulative data to per-interval data."""
    interval_data = []
    for i in range(len(cumulative_data)):
        if i == 0:
            interval_data.append(cumulative_data[0])
        else:
            interval_data.append(cumulative_data[i] - cumulative_data[i - 1])
    return interval_data


def find_end_of_activity(interval_data, zero_threshold_hours=1):
    """
    Find where activity ends by detecting consistent zero values.

    The heuristic stops data when there's been no activity (0 migrations per minute)
    for a continuous period of 1 hour (60 consecutive zero values). This handles
    cases where stats collection continues long after the workload has completed.

    Args:
        interval_data: List of per-interval values
        zero_threshold_hours: Hours of continuous zero activity to detect end (default: 1)

    Returns:
        Index where to truncate the data, or len(interval_data) if activity continues
    """
    zero_threshold_minutes = int(zero_threshold_hours * 60)
    consecutive_zeros = 0

    for i, value in enumerate(interval_data):
        if value == 0:
            consecutive_zeros += 1
            if consecutive_zeros >= zero_threshold_minutes:
                # Return the index where zeros started
                return i - zero_threshold_minutes + 1
        else:
            consecutive_zeros = 0

    return len(interval_data)


def plot_folio_migration(stats_files, output_file):
    """Plot unified folio migration stats from multiple files."""
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 14))

    # Store data for A/B comparison analysis
    ab_data = []

    # Build mapping of baseline to dev hosts for comprehensive plots
    baseline_hosts = {}
    dev_hosts = {}
    for file in stats_files:
        name = os.path.splitext(os.path.basename(file))[0]
        if "-dev" in name:
            # This is a dev host
            baseline_name = name.replace("-dev", "")
            dev_hosts[baseline_name] = name
        else:
            # This might be a baseline host
            baseline_hosts[name] = name

    # Assign colors to baseline/dev pairs
    color_map = {}
    color_idx = 0

    # For comprehensive plots, assign paired colors
    if len(stats_files) > 2:
        for baseline_name in sorted(baseline_hosts.keys()):
            base_color = plt.cm.tab10(color_idx % 10)
            color_map[baseline_name] = base_color

            # If there's a corresponding dev host, give it a modified version of the same color
            if baseline_name in dev_hosts:
                dev_name = dev_hosts[baseline_name]
                # Make dev color slightly darker
                dev_color = tuple([c * 0.7 for c in base_color[:3]] + [1.0])
                color_map[dev_name] = dev_color

            color_idx += 1

    for idx, file in enumerate(stats_files):
        name = os.path.splitext(os.path.basename(file))[0]

        # Determine if this is a dev node
        is_dev = "-dev" in name

        # For A/B comparison plots (2 files), use completely different colors
        if len(stats_files) == 2:
            # A/B comparison - use completely different colors for each host
            if idx == 0:
                color = plt.cm.tab10(0)  # Blue for first host
            else:
                color = plt.cm.tab10(1)  # Orange for second host

            # Different line styles for baseline vs dev
            if is_dev:
                linestyle = (
                    0,
                    (5, 3),
                )  # Custom dash pattern: 5 points on, 3 points off
                linewidth = 2.3
                alpha = 0.9
            else:
                linestyle = "-"
                linewidth = 2.0
                alpha = 1.0
        else:
            # Comprehensive plot - use paired colors from color_map
            color = color_map.get(name, plt.cm.tab10(idx % 10))

            if is_dev:
                linestyle = (
                    0,
                    (5, 3),
                )  # Custom dash pattern: 5 points on, 3 points off
                linewidth = 2.3
                alpha = 0.9
            else:
                linestyle = "-"
                linewidth = 2.0
                alpha = 1.0
        timestamps, calls_cumulative, success_cumulative = parse_stats_file(file)

        if not calls_cumulative:
            continue

        # Find where the workload starts (when calls jump up)
        start_idx = find_start_index(calls_cumulative)

        # Trim data to start from when workload begins
        calls_cumulative = calls_cumulative[start_idx:]
        success_cumulative = success_cumulative[start_idx:]

        # Convert cumulative to per-interval
        calls_interval = cumulative_to_interval(calls_cumulative)
        success_interval = cumulative_to_interval(success_cumulative)

        # Find where activity ends (1 hour of zero activity)
        end_idx = find_end_of_activity(calls_interval)

        # Truncate all data at the end of activity
        calls_interval = calls_interval[:end_idx]
        success_interval = success_interval[:end_idx]
        calls_cumulative = calls_cumulative[:end_idx]
        success_cumulative = success_cumulative[:end_idx]

        # Convert to hours from start
        time_hours = list(range(len(calls_interval)))  # Each entry is 1 minute apart
        time_hours = [t / 60.0 for t in time_hours]  # Convert to hours

        # Calculate success rate per interval
        success_rate = []
        for c, s in zip(calls_interval, success_interval):
            if c > 0:
                success_rate.append((s / c) * 100)
            else:
                success_rate.append(0)

        # Plot 1: Cumulative success count over time
        ax1.plot(
            time_hours,
            success_cumulative,
            label=f"{name}",
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            alpha=alpha,
        )

        # Plot 2: Migration rate over time (calls per minute)
        ax2.plot(
            time_hours,
            calls_interval,
            label=f"{name}",
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            alpha=alpha,
        )

        # Plot 3: Success rate per interval
        ax3.plot(
            time_hours,
            success_rate,
            label=f"{name}",
            color=color,
            linewidth=linewidth,
            linestyle=linestyle,
            marker="o" if not is_dev else "^",
            markersize=3,
            markevery=max(1, len(time_hours) // 20),
            alpha=alpha,
        )

        # Store data for A/B comparison
        if len(stats_files) == 2:
            ab_data.append(
                {
                    "name": name,
                    "is_dev": is_dev,
                    "final_calls": calls_cumulative[-1] if calls_cumulative else 0,
                    "final_success": (
                        success_cumulative[-1] if success_cumulative else 0
                    ),
                }
            )

    # Configure first plot (cumulative success)
    title_suffix = " (A/B Comparison)" if len(stats_files) == 2 else ""
    ax1.set_title(f"Cumulative Successful Migrations{title_suffix}", fontsize=16)
    ax1.set_xlabel("Time (hours from workload start)", fontsize=12)
    ax1.set_ylabel("Total Successful Migrations", fontsize=12)
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: human_format(int(x))))
    ax1.grid(True, alpha=0.3)
    legend1 = ax1.legend(loc="best", fontsize=10)
    # Make legend more visible for A/B comparisons
    if len(stats_files) == 2:
        legend1.get_frame().set_alpha(0.9)
        legend1.get_frame().set_facecolor("white")

    # Configure second plot (migration rate)
    ax2.set_title(f"Folio Migration Rate (calls per minute){title_suffix}", fontsize=16)
    ax2.set_xlabel("Time (hours from workload start)", fontsize=12)
    ax2.set_ylabel("Migrations per minute", fontsize=12)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: human_format(int(x))))
    ax2.grid(True, alpha=0.3)
    legend2 = ax2.legend(loc="best", fontsize=10)
    if len(stats_files) == 2:
        legend2.get_frame().set_alpha(0.9)
        legend2.get_frame().set_facecolor("white")

    # Configure third plot (success rate)
    ax3.set_title(
        f"Folio Migration Success Rate (per interval){title_suffix}", fontsize=16
    )
    ax3.set_xlabel("Time (hours from workload start)", fontsize=12)
    ax3.set_ylabel("Success Rate (%)", fontsize=12)
    ax3.set_ylim(0, 105)
    ax3.grid(True, alpha=0.3)
    legend3 = ax3.legend(loc="best", fontsize=10)
    if len(stats_files) == 2:
        legend3.get_frame().set_alpha(0.9)
        legend3.get_frame().set_facecolor("white")

        # Add text showing percentage difference for A/B comparison
        if len(ab_data) == 2:
            baseline = next((d for d in ab_data if not d["is_dev"]), None)
            dev = next((d for d in ab_data if d["is_dev"]), None)

            if baseline and dev and baseline["final_calls"] > 0:
                pct_diff_calls = (
                    (dev["final_calls"] - baseline["final_calls"])
                    / baseline["final_calls"]
                ) * 100
                pct_diff_success = (
                    (dev["final_success"] - baseline["final_success"])
                    / baseline["final_success"]
                ) * 100

                diff_text = (
                    f"Dev vs Baseline Difference:\n"
                    f"Total Calls: {pct_diff_calls:+.2f}%\n"
                    f"Total Success: {pct_diff_success:+.2f}%"
                )

                # Add text box in top left of first plot
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
    fig.savefig(output_file, dpi=150)
    print(f"Saved folio migration plot to: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="Plot folio migration stats.")
    parser.add_argument("stats_files", nargs="+", help="List of *.stats.txt files")
    parser.add_argument(
        "-o",
        "--output",
        default="folio-migration.png",
        help="Output PNG file (default: folio-migration.png)",
    )
    args = parser.parse_args()

    plot_folio_migration(args.stats_files, args.output)


if __name__ == "__main__":
    main()

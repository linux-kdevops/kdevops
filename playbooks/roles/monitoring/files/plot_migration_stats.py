#!/usr/bin/env python3

import argparse
import os
import re
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
from datetime import datetime


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

        # Split by timestamps
        entries = re.split(
            r"(\w{3} \w{3} \d{1,2} \d{2}:\d{2}:\d{2} [AP]M \w{3} \d{4})", content
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

    colors = plt.cm.tab10(range(len(stats_files)))

    for idx, file in enumerate(stats_files):
        name = os.path.splitext(os.path.basename(file))[0]
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
            color=colors[idx],
            linewidth=2,
            alpha=0.8,
        )

        # Plot 2: Migration rate over time (calls per minute)
        ax2.plot(
            time_hours,
            calls_interval,
            label=f"{name}",
            color=colors[idx],
            linewidth=2,
            alpha=0.8,
        )

        # Plot 3: Success rate per interval
        ax3.plot(
            time_hours,
            success_rate,
            label=f"{name}",
            color=colors[idx],
            linewidth=2,
            marker="o",
            markersize=3,
            markevery=max(1, len(time_hours) // 20),
        )

    # Configure first plot (cumulative success)
    ax1.set_title("Cumulative Successful Migrations", fontsize=16)
    ax1.set_xlabel("Time (hours from workload start)", fontsize=12)
    ax1.set_ylabel("Total Successful Migrations", fontsize=12)
    ax1.yaxis.set_major_formatter(FuncFormatter(lambda x, _: human_format(int(x))))
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc="best", fontsize=10)

    # Configure second plot (migration rate)
    ax2.set_title("Folio Migration Rate (calls per minute)", fontsize=16)
    ax2.set_xlabel("Time (hours from workload start)", fontsize=12)
    ax2.set_ylabel("Migrations per minute", fontsize=12)
    ax2.yaxis.set_major_formatter(FuncFormatter(lambda x, _: human_format(int(x))))
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc="best", fontsize=10)

    # Configure third plot (success rate)
    ax3.set_title("Folio Migration Success Rate (per interval)", fontsize=16)
    ax3.set_xlabel("Time (hours from workload start)", fontsize=12)
    ax3.set_ylabel("Success Rate (%)", fontsize=12)
    ax3.set_ylim(0, 105)
    ax3.grid(True, alpha=0.3)
    ax3.legend(loc="best", fontsize=10)

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

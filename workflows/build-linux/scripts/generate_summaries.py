#!/usr/bin/env python3
"""
Generate summary files from build_times JSON files.
"""

import json
import sys
import argparse
from pathlib import Path
import statistics
import socket
import os


def generate_summary_from_timing(timing_file):
    """Generate a summary from a build_times JSON file."""
    with open(timing_file, "r") as f:
        timing_data = json.load(f)

    # Extract hostname from filename
    # Format: hostname_build_times_hostname.json
    filename = timing_file.stem
    hostname = filename.split("_build_times_")[-1]

    # Count successful and failed builds
    successful = [entry for entry in timing_data if entry.get("success", False)]
    failed = [entry for entry in timing_data if not entry.get("success", False)]

    summary = {
        "hostname": hostname,
        "total_builds": len(timing_data),
        "successful_builds": len(successful),
        "failed_builds": len(failed),
        "build_target": "vmlinux",  # Default target
        "make_jobs": os.cpu_count(),
        "statistics": {},
    }

    # Calculate statistics for successful builds
    if successful:
        durations = [entry["duration"] for entry in successful]
        summary["statistics"] = {
            "average": statistics.mean(durations),
            "median": statistics.median(durations),
            "min": min(durations),
            "max": max(durations),
            "total_time": sum(durations),
            "total_hours": sum(durations) / 3600,
        }

        if len(durations) > 1:
            summary["statistics"]["stddev"] = statistics.stdev(durations)
    else:
        # If no successful builds, use all builds for stats
        durations = [entry["duration"] for entry in timing_data]
        summary["statistics"] = {
            "average": statistics.mean(durations) if durations else 0,
            "median": statistics.median(durations) if durations else 0,
            "min": min(durations) if durations else 0,
            "max": max(durations) if durations else 0,
            "total_time": sum(durations) if durations else 0,
            "total_hours": sum(durations) / 3600 if durations else 0,
        }

    return summary


def generate_all_summaries(results_dir):
    """Generate summary files for all build_times JSON files."""
    results_path = Path(results_dir)
    timing_files = list(results_path.glob("*_build_times_*.json"))

    if not timing_files:
        print("No build_times JSON files found")
        return 1

    print(f"Found {len(timing_files)} build_times files")

    for timing_file in timing_files:
        summary = generate_summary_from_timing(timing_file)

        # Save summary file
        hostname = summary["hostname"]
        summary_file = results_path / f"{hostname}_summary_{hostname}.json"

        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        print(f"Generated summary for {hostname}: {summary_file.name}")
        print(f"  Total builds: {summary['total_builds']}")
        print(f"  Successful: {summary['successful_builds']}")
        print(f"  Failed: {summary['failed_builds']}")
        if summary["statistics"]:
            print(f"  Average time: {summary['statistics']['average']:.2f}s")
        print()

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Generate summary files from build_times JSON files"
    )
    parser.add_argument(
        "results_dir", help="Directory containing build_times JSON files"
    )
    args = parser.parse_args()

    return generate_all_summaries(args.results_dir)


if __name__ == "__main__":
    sys.exit(main())

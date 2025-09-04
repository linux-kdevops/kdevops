#!/usr/bin/env python3
"""
Combine build results from multiple hosts into a single report.
"""

import json
import glob
import sys
import argparse
from pathlib import Path


def combine_results(results_dir):
    """Combine summary files from multiple hosts."""
    results_path = Path(results_dir)
    summary_files = list(results_path.glob("*_summary_*.json"))

    if not summary_files:
        print("No summary files found")
        return 1

    combined = {
        "hosts": {},
        "totals": {
            "total_builds": 0,
            "successful_builds": 0,
            "failed_builds": 0,
            "total_time_hours": 0,
        },
    }

    for summary_file in summary_files:
        with open(summary_file, "r") as f:
            data = json.load(f)
            hostname = data["hostname"]
            combined["hosts"][hostname] = data
            combined["totals"]["total_builds"] += data["total_builds"]
            combined["totals"]["successful_builds"] += data["successful_builds"]
            combined["totals"]["failed_builds"] += data["failed_builds"]
            combined["totals"]["total_time_hours"] += data["statistics"]["total_hours"]

    # Calculate aggregate statistics
    all_durations = []
    for host_data in combined["hosts"].values():
        if "statistics" in host_data and "average" in host_data["statistics"]:
            # Approximate durations based on average and count
            count = host_data["successful_builds"]
            avg = host_data["statistics"]["average"]
            all_durations.extend([avg] * count)

    if all_durations:
        combined["aggregate_stats"] = {
            "average": sum(all_durations) / len(all_durations),
            "min": min(all_durations),
            "max": max(all_durations),
            "total_builds": len(all_durations),
        }

    # Save combined report
    report_file = results_path / "combined_report.json"
    with open(report_file, "w") as f:
        json.dump(combined, f, indent=2)

    # Print summary
    print("Build Linux Combined Results Report")
    print("====================================")
    print(f"Total hosts: {len(combined['hosts'])}")
    print(f"Total builds: {combined['totals']['total_builds']}")
    print(f"Successful builds: {combined['totals']['successful_builds']}")
    print(f"Failed builds: {combined['totals']['failed_builds']}")
    print(f"Total time: {combined['totals']['total_time_hours']:.2f} hours")
    print()

    for hostname, data in combined["hosts"].items():
        print(f"Host: {hostname}")
        print(f"  Builds: {data['successful_builds']}/{data['total_builds']}")
        print(f"  Average: {data['statistics']['average']:.2f} seconds")
        print(
            f"  Min/Max: {data['statistics']['min']:.2f}/{data['statistics']['max']:.2f} seconds"
        )
        print()

    print(f"Report saved to: {report_file}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Combine build results from multiple hosts"
    )
    parser.add_argument("results_dir", help="Directory containing result files")
    args = parser.parse_args()

    return combine_results(args.results_dir)


if __name__ == "__main__":
    sys.exit(main())

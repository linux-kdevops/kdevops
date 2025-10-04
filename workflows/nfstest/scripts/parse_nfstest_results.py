#!/usr/bin/env python3
"""
Parse NFS test results from log files and extract key metrics.
"""

import os
import re
import sys
import json
import glob
from datetime import datetime
from pathlib import Path
from collections import defaultdict


def parse_timestamp(timestamp_str):
    """Parse timestamp from log format"""
    try:
        # Handle format: 17:18:41.048703
        time_parts = timestamp_str.split(":")
        if len(time_parts) == 3:
            hours = int(time_parts[0])
            minutes = int(time_parts[1])
            seconds = float(time_parts[2])
            return hours * 3600 + minutes * 60 + seconds
    except:
        pass
    return 0


def parse_test_log(log_path):
    """Parse a single NFS test log file"""
    results = {
        "file": os.path.basename(log_path),
        "test_suite": "",
        "tests": [],
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "total_time": 0,
        },
        "configuration": {},
        "test_groups": defaultdict(list),
    }

    # Determine test suite from filename
    if "interop" in log_path:
        results["test_suite"] = "interop"
    elif "alloc" in log_path:
        results["test_suite"] = "alloc"
    elif "dio" in log_path:
        results["test_suite"] = "dio"
    elif "lock" in log_path:
        results["test_suite"] = "lock"
    elif "posix" in log_path:
        results["test_suite"] = "posix"
    elif "sparse" in log_path:
        results["test_suite"] = "sparse"
    elif "ssc" in log_path:
        results["test_suite"] = "ssc"

    current_test = None
    start_time = None

    with open(log_path, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        # Parse configuration options
        if line.strip().startswith("OPTS:") and "--" in line:
            opts_match = re.search(r"OPTS:.*?-\s*(.+?)(?:--|\s*$)", line)
            if opts_match:
                opt_str = opts_match.group(1).strip()
                if "=" in opt_str:
                    key = opt_str.split("=")[0].replace("-", "_")
                    value = opt_str.split("=", 1)[1] if "=" in opt_str else "true"
                    results["configuration"][key] = value

        # Parse individual OPTS lines for configuration
        if line.strip().startswith("OPTS:") and "=" in line and "--" not in line:
            opts_match = re.search(r"OPTS:.*?-\s*(\w+)\s*=\s*(.+)", line)
            if opts_match:
                key = opts_match.group(1).replace("-", "_")
                value = opts_match.group(2).strip()
                results["configuration"][key] = value

        # Parse test start
        if line.startswith("*** "):
            test_desc = line[4:].strip()
            current_test = {
                "name": "",
                "description": test_desc,
                "status": "unknown",
                "duration": 0,
                "errors": [],
            }

        # Parse test name
        if "TEST: Running test" in line:
            test_match = re.search(r"Running test '(\w+)'", line)
            if test_match and current_test:
                current_test["name"] = test_match.group(1)

        # Parse test results
        if line.strip().startswith("PASS:"):
            if current_test:
                current_test["status"] = "passed"
                pass_msg = line.split("PASS:", 1)[1].strip()
                if "assertions" not in current_test:
                    current_test["assertions"] = []
                current_test["assertions"].append(
                    {"status": "PASS", "message": pass_msg}
                )

        if line.strip().startswith("FAIL:"):
            if current_test:
                current_test["status"] = "failed"
                fail_msg = line.split("FAIL:", 1)[1].strip()
                current_test["errors"].append(fail_msg)
                if "assertions" not in current_test:
                    current_test["assertions"] = []
                current_test["assertions"].append(
                    {"status": "FAIL", "message": fail_msg}
                )

        # Parse test timing
        if line.strip().startswith("TIME:"):
            time_match = re.search(r"TIME:\s*([\d.]+)([ms]?)", line)
            if time_match and current_test:
                duration = float(time_match.group(1))
                unit = time_match.group(2) if time_match.group(2) else "s"
                if unit == "m":
                    duration *= 60
                elif unit == "ms":
                    duration /= 1000
                current_test["duration"] = duration
                results["tests"].append(current_test)

                # Group tests by category (first part of test name)
                if current_test["name"]:
                    # Group by NFS version tested
                    if "NFSv3" in current_test["description"]:
                        results["test_groups"]["NFSv3"].append(current_test)
                    if "NFSv4" in current_test["description"]:
                        if "NFSv4.1" in current_test["description"]:
                            results["test_groups"]["NFSv4.1"].append(current_test)
                        else:
                            results["test_groups"]["NFSv4.0"].append(current_test)

                current_test = None

        # Parse final summary
        if "tests (" in line and "passed," in line:
            summary_match = re.search(
                r"(\d+)\s+tests\s*\((\d+)\s+passed,\s*(\d+)\s+failed", line
            )
            if summary_match:
                results["summary"]["total"] = int(summary_match.group(1))
                results["summary"]["passed"] = int(summary_match.group(2))
                results["summary"]["failed"] = int(summary_match.group(3))

        # Parse total time
        if line.startswith("Total time:"):
            time_match = re.search(r"Total time:\s*(.+)", line)
            if time_match:
                time_str = time_match.group(1).strip()
                # Convert format like "2m22.099818s" to seconds
                total_seconds = 0
                if "m" in time_str:
                    parts = time_str.split("m")
                    total_seconds += int(parts[0]) * 60
                    if len(parts) > 1:
                        seconds_part = parts[1].replace("s", "").strip()
                        if seconds_part:
                            total_seconds += float(seconds_part)
                elif "s" in time_str:
                    total_seconds = float(time_str.replace("s", "").strip())
                results["summary"]["total_time"] = total_seconds

    return results


def parse_all_results(results_dir):
    """Parse all test results in a directory"""
    all_results = {
        "timestamp": datetime.now().isoformat(),
        "test_suites": {},
        "overall_summary": {
            "total_tests": 0,
            "total_passed": 0,
            "total_failed": 0,
            "total_time": 0,
            "test_suites_run": [],
        },
    }

    # Find all log files
    log_pattern = os.path.join(results_dir, "**/*.log")
    log_files = glob.glob(log_pattern, recursive=True)

    for log_file in sorted(log_files):
        # Parse the log file
        suite_results = parse_test_log(log_file)

        # Determine suite category from path
        if "/interop/" in log_file:
            suite_key = "interop"
        elif "/alloc/" in log_file:
            suite_key = "alloc"
        elif "/dio/" in log_file:
            suite_key = "dio"
        elif "/lock/" in log_file:
            suite_key = "lock"
        elif "/posix/" in log_file:
            suite_key = "posix"
        elif "/sparse/" in log_file:
            suite_key = "sparse"
        elif "/ssc/" in log_file:
            suite_key = "ssc"
        else:
            suite_key = suite_results["test_suite"] or "unknown"

        # Store results
        if suite_key not in all_results["test_suites"]:
            all_results["test_suites"][suite_key] = []
            all_results["overall_summary"]["test_suites_run"].append(suite_key)

        all_results["test_suites"][suite_key].append(suite_results)

        # Update overall summary
        all_results["overall_summary"]["total_tests"] += suite_results["summary"][
            "total"
        ]
        all_results["overall_summary"]["total_passed"] += suite_results["summary"][
            "passed"
        ]
        all_results["overall_summary"]["total_failed"] += suite_results["summary"][
            "failed"
        ]
        all_results["overall_summary"]["total_time"] += suite_results["summary"][
            "total_time"
        ]

    return all_results


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        results_dir = "workflows/nfstest/results/last-run"

    if not os.path.exists(results_dir):
        print(
            f"Error: Results directory '{results_dir}' does not exist", file=sys.stderr
        )
        sys.exit(1)

    # Parse all results
    results = parse_all_results(results_dir)

    # Output as JSON
    print(json.dumps(results, indent=2))

    # Save to file
    output_file = os.path.join(results_dir, "parsed_results.json")
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_file}", file=sys.stderr)


if __name__ == "__main__":
    main()

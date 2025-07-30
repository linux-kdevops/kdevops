#!/usr/bin/python3
# SPDX-License-Identifier: copyleft-next-0.3.1
# Accepts sysbench json output, lets you compare two separate runs

import pandas as pd
import matplotlib.pyplot as plt
import re
import argparse
from concurrent.futures import ThreadPoolExecutor


# Function to parse a line and extract time and TPS
def parse_line(line):
    match = re.search(r"\[\s*(\d+)s\s*\].*?tps:\s*([\d.]+)", line)
    if match:
        time_in_seconds = int(match.group(1))
        tps = float(match.group(2))
        return time_in_seconds, tps
    return None


# Function to read and parse sysbench output file
def read_sysbench_output(file_path):
    with open(file_path, "r") as file:
        lines = file.readlines()

    with ThreadPoolExecutor() as executor:
        results = list(executor.map(parse_line, lines))

    return [result for result in results if result is not None]


# Function to list available matplotlib themes
def list_themes():
    print("Available matplotlib themes:")
    for style in plt.style.available:
        print(style)


# Main function
def main():
    parser = argparse.ArgumentParser(description="Compare sysbench outputs.")
    parser.add_argument(
        "file1",
        type=str,
        nargs="?",
        default="sysbench_output_doublewrite.txt",
        help="First sysbench output file",
    )
    parser.add_argument(
        "file2",
        type=str,
        nargs="?",
        default="sysbench_output_nodoublewrite.txt",
        help="Second sysbench output file",
    )
    parser.add_argument(
        "--legend1",
        type=str,
        default="innodb_doublewrite=ON",
        help="Legend for the first file",
    )
    parser.add_argument(
        "--legend2",
        type=str,
        default="innodb_doublewrite=OFF",
        help="Legend for the second file",
    )
    parser.add_argument(
        "--theme", type=str, default="dark_background", help="Matplotlib theme to use"
    )
    parser.add_argument(
        "--list-themes", action="store_true", help="List available matplotlib themes"
    )
    parser.add_argument(
        "--output", type=str, default="a_vs_b.png", help="Path of file to save"
    )
    parser.add_argument(
        "--report-interval",
        type=int,
        default=1,
        help="Time interval in seconds for reporting",
    )

    args = parser.parse_args()

    if args.list_themes:
        list_themes()
        return

    plt.style.use(args.theme)

    # Read and parse both sysbench output files
    tps_data_1 = read_sysbench_output(args.file1)
    tps_data_2 = read_sysbench_output(args.file2)

    # Adjust time intervals based on the report interval
    tps_data_1 = [(time * args.report_interval, tps) for time, tps in tps_data_1]
    tps_data_2 = [(time * args.report_interval, tps) for time, tps in tps_data_2]

    # Determine the maximum time value to decide if we need to use hours or seconds
    max_time_in_seconds = max(
        max(tps_data_1, key=lambda x: x[0])[0], max(tps_data_2, key=lambda x: x[0])[0]
    )
    use_hours = max_time_in_seconds > 2 * 3600

    # Convert times if necessary
    if use_hours:
        tps_data_1 = [(time / 3600, tps) for time, tps in tps_data_1]
        tps_data_2 = [(time / 3600, tps) for time, tps in tps_data_2]
        time_label = "Time (hours)"
    else:
        time_label = "Time (seconds)"

    # Create pandas DataFrames
    df1 = pd.DataFrame(tps_data_1, columns=[time_label, "TPS"])
    df2 = pd.DataFrame(tps_data_2, columns=[time_label, "TPS"])

    # Plot the TPS values
    plt.figure(figsize=(30, 12))

    plt.plot(df1[time_label], df1["TPS"], "ro", markersize=2, label=args.legend1)
    plt.plot(df2[time_label], df2["TPS"], "go", markersize=2, label=args.legend2)

    plt.title("Transactions Per Second (TPS) Over Time")
    plt.xlabel(time_label)
    plt.ylabel("TPS")
    plt.grid(True)
    # Try plotting without this to zoom in
    plt.ylim(0)
    plt.legend()
    plt.tight_layout()
    plt.savefig(args.output)
    # plt.show()


if __name__ == "__main__":
    main()

#!/usr/bin/python3
# SPDX-License-Identifier: copyleft-next-0.3.1

# Accepts sysbench output and provides a plot

import pandas as pd
import matplotlib.pyplot as plt
import re
import argparse
from concurrent.futures import ThreadPoolExecutor


# Function to parse a line and extract time and TPS from text
def parse_line(line):
    match = re.search(r"\[\s*(\d+)s\s*\].*?tps:\s*([\d.]+)", line)
    if match:
        time_in_seconds = int(match.group(1))
        tps = float(match.group(2))
        return time_in_seconds, tps
    return None


def main():
    # Setup argument parser
    parser = argparse.ArgumentParser(
        description="Generate TPS plot from sysbench output"
    )
    parser.add_argument(
        "input_file", type=str, help="Path to the input file (text or JSON)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="tps_over_time.png",
        help="Output image file (default: tps_over_time.png)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Read the input file
    try:
        with open(args.input_file, "r") as file:
            # Read text lines and parse them concurrently
            lines = file.readlines()
            with ThreadPoolExecutor() as executor:
                results = list(executor.map(parse_line, lines))
            tps_data = [result for result in results if result is not None]
    except FileNotFoundError:
        print(f"Error: File '{args.input_file}' not found.")
        exit(1)

    # Check if we got any data
    if not tps_data:
        print("Error: No valid TPS data found in the input file.")
        exit(1)

    # Determine if we need to use hours or seconds based on the maximum time value
    max_time_in_seconds = max(tps_data, key=lambda x: x[0])[0]
    use_hours = max_time_in_seconds > 2 * 3600

    # Convert times if necessary
    if use_hours:
        tps_data = [(time / 3600, tps) for time, tps in tps_data]
        time_label = "Time (hours)"
    else:
        time_label = "Time (seconds)"

    # Create a pandas DataFrame
    df = pd.DataFrame(tps_data, columns=[time_label, "TPS"])

    # Plot the TPS values
    plt.figure(figsize=(30, 12))
    plt.plot(df[time_label], df["TPS"], "o", markersize=2)
    plt.title("Transactions Per Second (TPS) Over Time")
    plt.xlabel(time_label)
    plt.ylabel("TPS")
    plt.grid(True)
    plt.ylim(0)
    plt.tight_layout()

    # Save the plot to the output file
    plt.savefig(args.output)
    print(f"TPS plot saved to {args.output}")


if __name__ == "__main__":
    main()

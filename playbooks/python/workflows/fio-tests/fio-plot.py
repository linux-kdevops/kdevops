#!/usr/bin/python3
# SPDX-License-Identifier: copyleft-next-0.3.1

# Accepts fio output and provides comprehensive plots for performance analysis

import pandas as pd
import matplotlib.pyplot as plt
import json
import argparse
import os
import sys
from pathlib import Path


def parse_fio_json(file_path):
    """Parse fio JSON output and extract key metrics"""
    try:
        with open(file_path, "r") as f:
            data = json.load(f)

        if "jobs" not in data:
            return None

        job = data["jobs"][0]  # Use first job

        # Extract read metrics
        read_stats = job.get("read", {})
        read_bw = read_stats.get("bw", 0) / 1024  # Convert to MB/s
        read_iops = read_stats.get("iops", 0)
        read_lat_mean = (
            read_stats.get("lat_ns", {}).get("mean", 0) / 1000000
        )  # Convert to ms

        # Extract write metrics
        write_stats = job.get("write", {})
        write_bw = write_stats.get("bw", 0) / 1024  # Convert to MB/s
        write_iops = write_stats.get("iops", 0)
        write_lat_mean = (
            write_stats.get("lat_ns", {}).get("mean", 0) / 1000000
        )  # Convert to ms

        return {
            "read_bw": read_bw,
            "read_iops": read_iops,
            "read_lat": read_lat_mean,
            "write_bw": write_bw,
            "write_iops": write_iops,
            "write_lat": write_lat_mean,
            "total_bw": read_bw + write_bw,
            "total_iops": read_iops + write_iops,
        }
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Error parsing {file_path}: {e}")
        return None


def extract_test_params(filename):
    """Extract test parameters from filename"""
    # Expected format: pattern_bs4k_iodepth1_jobs1.json
    parts = filename.replace(".json", "").replace("results_", "").split("_")

    params = {}
    for part in parts:
        if part.startswith("bs"):
            params["block_size"] = part[2:]
        elif part.startswith("iodepth"):
            params["io_depth"] = int(part[7:])
        elif part.startswith("jobs"):
            params["num_jobs"] = int(part[4:])
        elif part in [
            "randread",
            "randwrite",
            "seqread",
            "seqwrite",
            "mixed_75_25",
            "mixed_50_50",
        ]:
            params["pattern"] = part

    return params


def create_performance_matrix(results_dir):
    """Create performance matrix from all test results"""
    results = []

    # Look for JSON result files
    json_files = list(Path(results_dir).glob("results_*.json"))
    if not json_files:
        # Fallback to text files if JSON not available
        json_files = list(Path(results_dir).glob("results_*.txt"))

    for file_path in json_files:
        if file_path.name.endswith(".json"):
            metrics = parse_fio_json(file_path)
        else:
            continue  # Skip text files for now, could add text parsing later

        if metrics:
            params = extract_test_params(file_path.name)
            result = {**params, **metrics}
            results.append(result)

    return pd.DataFrame(results) if results else None


def plot_bandwidth_heatmap(df, output_file):
    """Create bandwidth heatmap across block sizes and IO depths"""
    if df.empty or "block_size" not in df.columns or "io_depth" not in df.columns:
        return

    # Create pivot table for heatmap
    pivot_data = df.pivot_table(
        values="total_bw", index="io_depth", columns="block_size", aggfunc="mean"
    )

    plt.figure(figsize=(12, 8))
    im = plt.imshow(pivot_data.values, cmap="viridis", aspect="auto")

    # Add colorbar
    plt.colorbar(im, label="Bandwidth (MB/s)")

    # Set ticks and labels
    plt.xticks(range(len(pivot_data.columns)), pivot_data.columns)
    plt.yticks(range(len(pivot_data.index)), pivot_data.index)

    plt.xlabel("Block Size")
    plt.ylabel("IO Depth")
    plt.title("Bandwidth Performance Matrix")

    # Add text annotations
    for i in range(len(pivot_data.index)):
        for j in range(len(pivot_data.columns)):
            if not pd.isna(pivot_data.iloc[i, j]):
                plt.text(
                    j,
                    i,
                    f"{pivot_data.iloc[i, j]:.0f}",
                    ha="center",
                    va="center",
                    color="white",
                    fontweight="bold",
                )

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()


def plot_iops_scaling(df, output_file):
    """Plot IOPS scaling with IO depth"""
    if df.empty or "io_depth" not in df.columns:
        return

    plt.figure(figsize=(12, 8))

    # Group by pattern and plot separately
    patterns = df["pattern"].unique() if "pattern" in df.columns else ["all"]

    for pattern in patterns:
        if pattern != "all":
            pattern_df = df[df["pattern"] == pattern]
        else:
            pattern_df = df

        # Group by IO depth and calculate mean IOPS
        iops_by_depth = pattern_df.groupby("io_depth")["total_iops"].mean()

        plt.plot(
            iops_by_depth.index,
            iops_by_depth.values,
            marker="o",
            linewidth=2,
            markersize=6,
            label=pattern,
        )

    plt.xlabel("IO Depth")
    plt.ylabel("IOPS")
    plt.title("IOPS Scaling with IO Depth")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()


def plot_latency_distribution(df, output_file):
    """Plot latency distribution across different configurations"""
    if df.empty:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Read latency
    if "read_lat" in df.columns:
        read_lat_data = df[df["read_lat"] > 0]["read_lat"]
        if not read_lat_data.empty:
            ax1.hist(read_lat_data, bins=20, alpha=0.7, color="blue", edgecolor="black")
            ax1.set_xlabel("Read Latency (ms)")
            ax1.set_ylabel("Frequency")
            ax1.set_title("Read Latency Distribution")
            ax1.grid(True, alpha=0.3)

    # Write latency
    if "write_lat" in df.columns:
        write_lat_data = df[df["write_lat"] > 0]["write_lat"]
        if not write_lat_data.empty:
            ax2.hist(write_lat_data, bins=20, alpha=0.7, color="red", edgecolor="black")
            ax2.set_xlabel("Write Latency (ms)")
            ax2.set_ylabel("Frequency")
            ax2.set_title("Write Latency Distribution")
            ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()


def plot_pattern_comparison(df, output_file):
    """Compare performance across different workload patterns"""
    if df.empty or "pattern" not in df.columns:
        return

    patterns = df["pattern"].unique()
    if len(patterns) <= 1:
        return

    # Calculate mean metrics for each pattern
    pattern_stats = (
        df.groupby("pattern")
        .agg(
            {
                "total_bw": "mean",
                "total_iops": "mean",
                "read_lat": "mean",
                "write_lat": "mean",
            }
        )
        .reset_index()
    )

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Bandwidth comparison
    ax1.bar(
        pattern_stats["pattern"],
        pattern_stats["total_bw"],
        color="skyblue",
        edgecolor="navy",
    )
    ax1.set_ylabel("Bandwidth (MB/s)")
    ax1.set_title("Bandwidth by Workload Pattern")
    ax1.tick_params(axis="x", rotation=45)

    # IOPS comparison
    ax2.bar(
        pattern_stats["pattern"],
        pattern_stats["total_iops"],
        color="lightgreen",
        edgecolor="darkgreen",
    )
    ax2.set_ylabel("IOPS")
    ax2.set_title("IOPS by Workload Pattern")
    ax2.tick_params(axis="x", rotation=45)

    # Read latency comparison
    read_lat_data = pattern_stats[pattern_stats["read_lat"] > 0]
    if not read_lat_data.empty:
        ax3.bar(
            read_lat_data["pattern"],
            read_lat_data["read_lat"],
            color="orange",
            edgecolor="darkorange",
        )
    ax3.set_ylabel("Read Latency (ms)")
    ax3.set_title("Read Latency by Workload Pattern")
    ax3.tick_params(axis="x", rotation=45)

    # Write latency comparison
    write_lat_data = pattern_stats[pattern_stats["write_lat"] > 0]
    if not write_lat_data.empty:
        ax4.bar(
            write_lat_data["pattern"],
            write_lat_data["write_lat"],
            color="salmon",
            edgecolor="darkred",
        )
    ax4.set_ylabel("Write Latency (ms)")
    ax4.set_title("Write Latency by Workload Pattern")
    ax4.tick_params(axis="x", rotation=45)

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive performance graphs from fio test results"
    )
    parser.add_argument(
        "results_dir", type=str, help="Directory containing fio test results"
    )
    parser.add_argument(
        "--output-dir", type=str, default=".", help="Output directory for graphs"
    )
    parser.add_argument(
        "--prefix", type=str, default="fio_performance", help="Prefix for output files"
    )

    args = parser.parse_args()

    if not os.path.exists(args.results_dir):
        print(f"Error: Results directory '{args.results_dir}' not found.")
        sys.exit(1)

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Load and process results
    print("Loading fio test results...")
    df = create_performance_matrix(args.results_dir)

    if df is None or df.empty:
        print("No valid fio results found.")
        sys.exit(1)

    print(f"Found {len(df)} test results")
    print("Generating graphs...")

    # Generate different types of graphs
    plot_bandwidth_heatmap(
        df, os.path.join(args.output_dir, f"{args.prefix}_bandwidth_heatmap.png")
    )
    plot_iops_scaling(
        df, os.path.join(args.output_dir, f"{args.prefix}_iops_scaling.png")
    )
    plot_latency_distribution(
        df, os.path.join(args.output_dir, f"{args.prefix}_latency_distribution.png")
    )
    plot_pattern_comparison(
        df, os.path.join(args.output_dir, f"{args.prefix}_pattern_comparison.png")
    )

    print(f"Graphs saved to {args.output_dir}")


if __name__ == "__main__":
    main()

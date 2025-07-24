#!/usr/bin/python3
# SPDX-License-Identifier: copyleft-next-0.3.1

# Analyze fio performance trends across different test parameters

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import json
import argparse
import os
import sys
from pathlib import Path


def parse_fio_json(file_path):
    """Parse fio JSON output and extract detailed metrics"""
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
        read_lat = read_stats.get("lat_ns", {})
        read_lat_mean = read_lat.get("mean", 0) / 1000000  # Convert to ms
        read_lat_stddev = read_lat.get("stddev", 0) / 1000000
        read_lat_p95 = read_lat.get("percentile", {}).get("95.000000", 0) / 1000000
        read_lat_p99 = read_lat.get("percentile", {}).get("99.000000", 0) / 1000000

        # Extract write metrics
        write_stats = job.get("write", {})
        write_bw = write_stats.get("bw", 0) / 1024  # Convert to MB/s
        write_iops = write_stats.get("iops", 0)
        write_lat = write_stats.get("lat_ns", {})
        write_lat_mean = write_lat.get("mean", 0) / 1000000  # Convert to ms
        write_lat_stddev = write_lat.get("stddev", 0) / 1000000
        write_lat_p95 = write_lat.get("percentile", {}).get("95.000000", 0) / 1000000
        write_lat_p99 = write_lat.get("percentile", {}).get("99.000000", 0) / 1000000

        return {
            "read_bw": read_bw,
            "read_iops": read_iops,
            "read_lat_mean": read_lat_mean,
            "read_lat_stddev": read_lat_stddev,
            "read_lat_p95": read_lat_p95,
            "read_lat_p99": read_lat_p99,
            "write_bw": write_bw,
            "write_iops": write_iops,
            "write_lat_mean": write_lat_mean,
            "write_lat_stddev": write_lat_stddev,
            "write_lat_p95": write_lat_p95,
            "write_lat_p99": write_lat_p99,
            "total_bw": read_bw + write_bw,
            "total_iops": read_iops + write_iops,
        }
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Error parsing {file_path}: {e}")
        return None


def extract_test_params(filename):
    """Extract test parameters from filename"""
    parts = filename.replace(".json", "").replace("results_", "").split("_")

    params = {}
    for part in parts:
        if part.startswith("bs"):
            # Convert block size to numeric KB for sorting
            bs_str = part[2:]
            if bs_str.endswith("k"):
                params["block_size_kb"] = int(bs_str[:-1])
                params["block_size"] = bs_str
            else:
                params["block_size_kb"] = int(bs_str)
                params["block_size"] = bs_str
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


def load_all_results(results_dir):
    """Load all fio results from directory"""
    results = []

    json_files = list(Path(results_dir).glob("results_*.json"))
    if not json_files:
        json_files = list(Path(results_dir).glob("results_*.txt"))

    for file_path in json_files:
        if file_path.name.endswith(".json"):
            metrics = parse_fio_json(file_path)
        else:
            continue

        if metrics:
            params = extract_test_params(file_path.name)
            result = {**params, **metrics}
            results.append(result)

    return pd.DataFrame(results) if results else None


def plot_block_size_trends(df, output_dir):
    """Plot performance trends across block sizes"""
    if df.empty or "block_size_kb" not in df.columns:
        return

    # Group by block size and calculate means
    bs_trends = (
        df.groupby("block_size_kb")
        .agg(
            {
                "total_bw": "mean",
                "total_iops": "mean",
                "read_lat_mean": "mean",
                "write_lat_mean": "mean",
            }
        )
        .reset_index()
    )

    bs_trends = bs_trends.sort_values("block_size_kb")

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Bandwidth trend
    ax1.plot(
        bs_trends["block_size_kb"],
        bs_trends["total_bw"],
        marker="o",
        linewidth=2,
        markersize=8,
        color="blue",
    )
    ax1.set_xlabel("Block Size (KB)")
    ax1.set_ylabel("Bandwidth (MB/s)")
    ax1.set_title("Bandwidth vs Block Size")
    ax1.grid(True, alpha=0.3)

    # IOPS trend
    ax2.plot(
        bs_trends["block_size_kb"],
        bs_trends["total_iops"],
        marker="s",
        linewidth=2,
        markersize=8,
        color="green",
    )
    ax2.set_xlabel("Block Size (KB)")
    ax2.set_ylabel("IOPS")
    ax2.set_title("IOPS vs Block Size")
    ax2.grid(True, alpha=0.3)

    # Read latency trend
    read_lat_data = bs_trends[bs_trends["read_lat_mean"] > 0]
    if not read_lat_data.empty:
        ax3.plot(
            read_lat_data["block_size_kb"],
            read_lat_data["read_lat_mean"],
            marker="^",
            linewidth=2,
            markersize=8,
            color="orange",
        )
    ax3.set_xlabel("Block Size (KB)")
    ax3.set_ylabel("Read Latency (ms)")
    ax3.set_title("Read Latency vs Block Size")
    ax3.grid(True, alpha=0.3)

    # Write latency trend
    write_lat_data = bs_trends[bs_trends["write_lat_mean"] > 0]
    if not write_lat_data.empty:
        ax4.plot(
            write_lat_data["block_size_kb"],
            write_lat_data["write_lat_mean"],
            marker="v",
            linewidth=2,
            markersize=8,
            color="red",
        )
    ax4.set_xlabel("Block Size (KB)")
    ax4.set_ylabel("Write Latency (ms)")
    ax4.set_title("Write Latency vs Block Size")
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "block_size_trends.png"), dpi=300, bbox_inches="tight"
    )
    plt.close()


def plot_io_depth_scaling(df, output_dir):
    """Plot performance scaling with IO depth"""
    if df.empty or "io_depth" not in df.columns:
        return

    patterns = df["pattern"].unique() if "pattern" in df.columns else [None]

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    colors = plt.cm.tab10(np.linspace(0, 1, len(patterns)))

    for pattern, color in zip(patterns, colors):
        if pattern is not None:
            pattern_df = df[df["pattern"] == pattern]
            label = pattern
        else:
            pattern_df = df
            label = "All"

        if pattern_df.empty:
            continue

        depth_trends = (
            pattern_df.groupby("io_depth")
            .agg(
                {
                    "total_bw": "mean",
                    "total_iops": "mean",
                    "read_lat_mean": "mean",
                    "write_lat_mean": "mean",
                }
            )
            .reset_index()
        )

        depth_trends = depth_trends.sort_values("io_depth")

        # Bandwidth scaling
        ax1.plot(
            depth_trends["io_depth"],
            depth_trends["total_bw"],
            marker="o",
            linewidth=2,
            markersize=6,
            label=label,
            color=color,
        )

        # IOPS scaling
        ax2.plot(
            depth_trends["io_depth"],
            depth_trends["total_iops"],
            marker="s",
            linewidth=2,
            markersize=6,
            label=label,
            color=color,
        )

        # Read latency scaling
        read_lat_data = depth_trends[depth_trends["read_lat_mean"] > 0]
        if not read_lat_data.empty:
            ax3.plot(
                read_lat_data["io_depth"],
                read_lat_data["read_lat_mean"],
                marker="^",
                linewidth=2,
                markersize=6,
                label=label,
                color=color,
            )

        # Write latency scaling
        write_lat_data = depth_trends[depth_trends["write_lat_mean"] > 0]
        if not write_lat_data.empty:
            ax4.plot(
                write_lat_data["io_depth"],
                write_lat_data["write_lat_mean"],
                marker="v",
                linewidth=2,
                markersize=6,
                label=label,
                color=color,
            )

    ax1.set_xlabel("IO Depth")
    ax1.set_ylabel("Bandwidth (MB/s)")
    ax1.set_title("Bandwidth Scaling with IO Depth")
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    ax2.set_xlabel("IO Depth")
    ax2.set_ylabel("IOPS")
    ax2.set_title("IOPS Scaling with IO Depth")
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    ax3.set_xlabel("IO Depth")
    ax3.set_ylabel("Read Latency (ms)")
    ax3.set_title("Read Latency vs IO Depth")
    ax3.grid(True, alpha=0.3)
    ax3.legend()

    ax4.set_xlabel("IO Depth")
    ax4.set_ylabel("Write Latency (ms)")
    ax4.set_title("Write Latency vs IO Depth")
    ax4.grid(True, alpha=0.3)
    ax4.legend()

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "io_depth_scaling.png"), dpi=300, bbox_inches="tight"
    )
    plt.close()


def plot_latency_percentiles(df, output_dir):
    """Plot latency percentile analysis"""
    if df.empty:
        return

    latency_cols = [
        "read_lat_mean",
        "read_lat_p95",
        "read_lat_p99",
        "write_lat_mean",
        "write_lat_p95",
        "write_lat_p99",
    ]

    # Filter out zero latencies
    lat_df = df[latency_cols]
    lat_df = lat_df[(lat_df > 0).any(axis=1)]

    if lat_df.empty:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Read latency percentiles
    read_cols = [col for col in latency_cols if col.startswith("read_")]
    if any(col in lat_df.columns for col in read_cols):
        read_data = lat_df[read_cols].dropna()
        if not read_data.empty:
            bp1 = ax1.boxplot(
                [read_data[col] for col in read_cols],
                labels=["Mean", "P95", "P99"],
                patch_artist=True,
            )
            for patch in bp1["boxes"]:
                patch.set_facecolor("lightblue")
            ax1.set_ylabel("Latency (ms)")
            ax1.set_title("Read Latency Distribution")
            ax1.grid(True, alpha=0.3)

    # Write latency percentiles
    write_cols = [col for col in latency_cols if col.startswith("write_")]
    if any(col in lat_df.columns for col in write_cols):
        write_data = lat_df[write_cols].dropna()
        if not write_data.empty:
            bp2 = ax2.boxplot(
                [write_data[col] for col in write_cols],
                labels=["Mean", "P95", "P99"],
                patch_artist=True,
            )
            for patch in bp2["boxes"]:
                patch.set_facecolor("lightcoral")
            ax2.set_ylabel("Latency (ms)")
            ax2.set_title("Write Latency Distribution")
            ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "latency_percentiles.png"),
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()


def create_correlation_heatmap(df, output_dir):
    """Create correlation heatmap of performance metrics"""
    if df.empty:
        return

    # Select numeric columns for correlation
    numeric_cols = [
        "block_size_kb",
        "io_depth",
        "num_jobs",
        "total_bw",
        "total_iops",
        "read_lat_mean",
        "write_lat_mean",
    ]

    corr_df = df[numeric_cols].dropna()

    if corr_df.empty:
        return

    correlation_matrix = corr_df.corr()

    plt.figure(figsize=(10, 8))
    sns.heatmap(
        correlation_matrix,
        annot=True,
        cmap="coolwarm",
        center=0,
        square=True,
        linewidths=0.5,
        cbar_kws={"shrink": 0.8},
    )
    plt.title("Performance Metrics Correlation Matrix")
    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "correlation_heatmap.png"),
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()


def main():
    parser = argparse.ArgumentParser(
        description="Analyze fio performance trends and patterns"
    )
    parser.add_argument(
        "results_dir", type=str, help="Directory containing fio test results"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=".",
        help="Output directory for analysis graphs",
    )

    args = parser.parse_args()

    if not os.path.exists(args.results_dir):
        print(f"Error: Results directory '{args.results_dir}' not found.")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    print("Loading fio test results...")
    df = load_all_results(args.results_dir)

    if df is None or df.empty:
        print("No valid fio results found.")
        sys.exit(1)

    print(f"Analyzing {len(df)} test results...")

    # Generate trend analysis
    plot_block_size_trends(df, args.output_dir)
    plot_io_depth_scaling(df, args.output_dir)
    plot_latency_percentiles(df, args.output_dir)
    create_correlation_heatmap(df, args.output_dir)

    print(f"Trend analysis saved to {args.output_dir}")


if __name__ == "__main__":
    main()

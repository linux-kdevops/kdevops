#!/usr/bin/python3
# SPDX-License-Identifier: copyleft-next-0.3.1

# Multi-filesystem comparison tool for fio-tests
# Aggregates results from multiple filesystem configurations and generates comparison plots

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import json
import argparse
import os
import sys
import glob
from pathlib import Path
import numpy as np


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
        read_lat_p99 = (
            read_stats.get("lat_ns", {}).get("percentile", {}).get("99.000000", 0)
            / 1000000
        )

        # Extract write metrics
        write_stats = job.get("write", {})
        write_bw = write_stats.get("bw", 0) / 1024  # Convert to MB/s
        write_iops = write_stats.get("iops", 0)
        write_lat_mean = (
            write_stats.get("lat_ns", {}).get("mean", 0) / 1000000
        )  # Convert to ms
        write_lat_p99 = (
            write_stats.get("lat_ns", {}).get("percentile", {}).get("99.000000", 0)
            / 1000000
        )

        # Extract job parameters
        job_options = job.get("job options", {})
        block_size = job_options.get("bs", "unknown")
        iodepth = job_options.get("iodepth", "unknown")
        numjobs = job_options.get("numjobs", "unknown")
        rw_pattern = job_options.get("rw", "unknown")

        return {
            "read_bw": read_bw,
            "read_iops": read_iops,
            "read_lat_mean": read_lat_mean,
            "read_lat_p99": read_lat_p99,
            "write_bw": write_bw,
            "write_iops": write_iops,
            "write_lat_mean": write_lat_mean,
            "write_lat_p99": write_lat_p99,
            "total_bw": read_bw + write_bw,
            "total_iops": read_iops + write_iops,
            "block_size": block_size,
            "iodepth": str(iodepth),
            "numjobs": str(numjobs),
            "rw_pattern": rw_pattern,
        }
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Error parsing {file_path}: {e}")
        return None


def extract_filesystem_from_hostname(hostname):
    """Extract filesystem configuration from hostname"""
    # Expected format: hostname-fio-tests-section-name
    # Examples: demo-fio-tests-xfs-4k, demo-fio-tests-ext4-bigalloc
    parts = hostname.split("-")
    if len(parts) >= 4 and "fio-tests" in parts:
        fio_tests_idx = parts.index("fio-tests")
        if fio_tests_idx + 1 < len(parts):
            # Join remaining parts as filesystem section
            return "-".join(parts[fio_tests_idx + 1 :])

    # Fallback: try to extract filesystem type
    if "xfs" in hostname:
        return "xfs"
    elif "ext4" in hostname:
        return "ext4"
    elif "btrfs" in hostname:
        return "btrfs"
    else:
        return "unknown"


def collect_results(results_dir):
    """Collect all fio results from multiple filesystem configurations"""
    results = []

    # Find all JSON result files
    json_files = glob.glob(os.path.join(results_dir, "**/*.json"), recursive=True)

    for json_file in json_files:
        # Extract filesystem config from path
        path_parts = Path(json_file).parts
        filesystem = "unknown"

        # Look for filesystem indicator in path
        for part in path_parts:
            if "fio-tests-" in part:
                filesystem = part.replace("fio-tests-", "")
                break
            elif any(fs in part.lower() for fs in ["xfs", "ext4", "btrfs"]):
                filesystem = extract_filesystem_from_hostname(part)
                break

        # Parse the fio results
        metrics = parse_fio_json(json_file)
        if metrics:
            metrics["filesystem"] = filesystem
            metrics["json_file"] = json_file
            results.append(metrics)

    return pd.DataFrame(results)


def create_filesystem_comparison_plots(df, output_dir):
    """Create comprehensive comparison plots across filesystems"""

    # Set style for better looking plots
    plt.style.use("default")
    sns.set_palette("husl")

    # Group by filesystem for easier analysis
    fs_groups = df.groupby("filesystem")

    # 1. Overall Performance Comparison by Filesystem
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle("Filesystem Performance Comparison", fontsize=16, fontweight="bold")

    # Average throughput by filesystem
    avg_metrics = (
        df.groupby("filesystem")
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

    # Throughput comparison
    axes[0, 0].bar(avg_metrics["filesystem"], avg_metrics["total_bw"])
    axes[0, 0].set_title("Average Total Bandwidth (MB/s)")
    axes[0, 0].set_ylabel("Bandwidth (MB/s)")
    axes[0, 0].tick_params(axis="x", rotation=45)

    # IOPS comparison
    axes[0, 1].bar(avg_metrics["filesystem"], avg_metrics["total_iops"])
    axes[0, 1].set_title("Average Total IOPS")
    axes[0, 1].set_ylabel("IOPS")
    axes[0, 1].tick_params(axis="x", rotation=45)

    # Read latency comparison
    axes[1, 0].bar(avg_metrics["filesystem"], avg_metrics["read_lat_mean"])
    axes[1, 0].set_title("Average Read Latency (ms)")
    axes[1, 0].set_ylabel("Latency (ms)")
    axes[1, 0].tick_params(axis="x", rotation=45)

    # Write latency comparison
    axes[1, 1].bar(avg_metrics["filesystem"], avg_metrics["write_lat_mean"])
    axes[1, 1].set_title("Average Write Latency (ms)")
    axes[1, 1].set_ylabel("Latency (ms)")
    axes[1, 1].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "filesystem_performance_overview.png"),
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()

    # 2. Performance by Block Size (if available)
    if "block_size" in df.columns and len(df["block_size"].unique()) > 1:
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(
            "Performance by Block Size Across Filesystems",
            fontsize=16,
            fontweight="bold",
        )

        # Create pivot tables for heatmaps
        bw_pivot = df.pivot_table(
            values="total_bw", index="filesystem", columns="block_size", aggfunc="mean"
        )
        iops_pivot = df.pivot_table(
            values="total_iops",
            index="filesystem",
            columns="block_size",
            aggfunc="mean",
        )
        read_lat_pivot = df.pivot_table(
            values="read_lat_mean",
            index="filesystem",
            columns="block_size",
            aggfunc="mean",
        )
        write_lat_pivot = df.pivot_table(
            values="write_lat_mean",
            index="filesystem",
            columns="block_size",
            aggfunc="mean",
        )

        # Bandwidth heatmap
        sns.heatmap(
            bw_pivot,
            annot=True,
            fmt=".1f",
            cmap="YlOrRd",
            ax=axes[0, 0],
            cbar_kws={"label": "MB/s"},
        )
        axes[0, 0].set_title("Total Bandwidth by Block Size")

        # IOPS heatmap
        sns.heatmap(
            iops_pivot,
            annot=True,
            fmt=".0f",
            cmap="YlOrRd",
            ax=axes[0, 1],
            cbar_kws={"label": "IOPS"},
        )
        axes[0, 1].set_title("Total IOPS by Block Size")

        # Read latency heatmap
        sns.heatmap(
            read_lat_pivot,
            annot=True,
            fmt=".2f",
            cmap="YlOrRd_r",
            ax=axes[1, 0],
            cbar_kws={"label": "ms"},
        )
        axes[1, 0].set_title("Read Latency by Block Size")

        # Write latency heatmap
        sns.heatmap(
            write_lat_pivot,
            annot=True,
            fmt=".2f",
            cmap="YlOrRd_r",
            ax=axes[1, 1],
            cbar_kws={"label": "ms"},
        )
        axes[1, 1].set_title("Write Latency by Block Size")

        plt.tight_layout()
        plt.savefig(
            os.path.join(output_dir, "filesystem_blocksize_heatmaps.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

    # 3. Detailed Performance Scaling Analysis
    if "iodepth" in df.columns and len(df["iodepth"].unique()) > 1:
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle("Performance Scaling by IO Depth", fontsize=16, fontweight="bold")

        for fs in df["filesystem"].unique():
            fs_data = df[df["filesystem"] == fs]
            if len(fs_data) == 0:
                continue

            iodepth_data = (
                fs_data.groupby("iodepth")
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

            iodepth_data["iodepth"] = pd.to_numeric(
                iodepth_data["iodepth"], errors="coerce"
            )
            iodepth_data = iodepth_data.sort_values("iodepth")

            axes[0, 0].plot(
                iodepth_data["iodepth"], iodepth_data["total_bw"], marker="o", label=fs
            )
            axes[0, 1].plot(
                iodepth_data["iodepth"],
                iodepth_data["total_iops"],
                marker="o",
                label=fs,
            )
            axes[1, 0].plot(
                iodepth_data["iodepth"],
                iodepth_data["read_lat_mean"],
                marker="o",
                label=fs,
            )
            axes[1, 1].plot(
                iodepth_data["iodepth"],
                iodepth_data["write_lat_mean"],
                marker="o",
                label=fs,
            )

        axes[0, 0].set_title("Bandwidth Scaling")
        axes[0, 0].set_xlabel("IO Depth")
        axes[0, 0].set_ylabel("Bandwidth (MB/s)")
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        axes[0, 1].set_title("IOPS Scaling")
        axes[0, 1].set_xlabel("IO Depth")
        axes[0, 1].set_ylabel("IOPS")
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        axes[1, 0].set_title("Read Latency vs IO Depth")
        axes[1, 0].set_xlabel("IO Depth")
        axes[1, 0].set_ylabel("Read Latency (ms)")
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        axes[1, 1].set_title("Write Latency vs IO Depth")
        axes[1, 1].set_xlabel("IO Depth")
        axes[1, 1].set_ylabel("Write Latency (ms)")
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(
            os.path.join(output_dir, "filesystem_iodepth_scaling.png"),
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

    # 4. Summary Statistics Table
    summary_stats = (
        df.groupby("filesystem")
        .agg(
            {
                "total_bw": ["mean", "std", "min", "max"],
                "total_iops": ["mean", "std", "min", "max"],
                "read_lat_mean": ["mean", "std", "min", "max"],
                "write_lat_mean": ["mean", "std", "min", "max"],
            }
        )
        .round(2)
    )

    # Save summary to CSV
    summary_stats.to_csv(os.path.join(output_dir, "filesystem_performance_summary.csv"))

    print(f"Generated multi-filesystem comparison plots in {output_dir}")
    print("\nGenerated files:")
    print("- filesystem_performance_overview.png")
    if "block_size" in df.columns and len(df["block_size"].unique()) > 1:
        print("- filesystem_blocksize_heatmaps.png")
    if "iodepth" in df.columns and len(df["iodepth"].unique()) > 1:
        print("- filesystem_iodepth_scaling.png")
    print("- filesystem_performance_summary.csv")


def main():
    parser = argparse.ArgumentParser(
        description="Generate multi-filesystem comparison plots from fio results"
    )
    parser.add_argument(
        "results_dir", help="Directory containing fio results from multiple filesystems"
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=".",
        help="Output directory for generated plots (default: current directory)",
    )
    parser.add_argument(
        "--title",
        default="Multi-Filesystem Performance Comparison",
        help="Title for the generated plots",
    )

    args = parser.parse_args()

    if not os.path.exists(args.results_dir):
        print(f"Error: Results directory {args.results_dir} does not exist")
        sys.exit(1)

    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Collect results from all filesystems
    print(f"Collecting results from {args.results_dir}...")
    df = collect_results(args.results_dir)

    if df.empty:
        print("No valid fio results found in the specified directory")
        sys.exit(1)

    print(
        f"Found {len(df)} fio test results across {len(df['filesystem'].unique())} filesystem configurations"
    )
    print(f"Filesystem configurations: {', '.join(df['filesystem'].unique())}")

    # Generate comparison plots
    create_filesystem_comparison_plots(df, args.output_dir)


if __name__ == "__main__":
    main()

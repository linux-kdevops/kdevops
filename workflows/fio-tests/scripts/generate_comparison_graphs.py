#!/usr/bin/env python3
"""
Multi-filesystem performance comparison graph generator for fio-tests
Generates comparative visualizations across XFS, ext4, and btrfs filesystems
"""

import json
import os
import glob
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path
import sys


def load_fio_results(results_dir):
    """Load and parse fio JSON results from all filesystem directories"""

    filesystems = {
        "XFS (16K blocks)": "debian13-fio-tests-xfs-16k",
        "ext4 (bigalloc, 32K)": "debian13-fio-tests-ext4-bigalloc",
        "btrfs (zstd compression)": "debian13-fio-tests-btrfs-zstd",
    }

    results = {}

    for fs_name, dir_name in filesystems.items():
        fs_dir = os.path.join(results_dir, dir_name)
        if not os.path.exists(fs_dir):
            print(f"Warning: Directory {fs_dir} not found")
            continue

        results[fs_name] = {}

        # Find all JSON result files
        json_files = glob.glob(os.path.join(fs_dir, "results_*.json"))
        json_files = [
            f for f in json_files if not f.endswith("results_*.json")
        ]  # Skip literal wildcards

        for json_file in json_files:
            try:
                with open(json_file, "r") as f:
                    data = json.load(f)

                # Extract test parameters from filename
                basename = os.path.basename(json_file)
                test_name = basename.replace("results_", "").replace(".json", "")

                # Parse test parameters
                parts = test_name.split("_")
                if len(parts) >= 4:
                    pattern = parts[0]
                    block_size = parts[1].replace("bs", "")
                    io_depth = parts[2].replace("iodepth", "")
                    num_jobs = parts[3].replace("jobs", "")

                    # Extract performance metrics
                    if "jobs" in data and len(data["jobs"]) > 0:
                        job = data["jobs"][0]

                        # Get read/write metrics based on pattern
                        if "read" in pattern:
                            metrics = job.get("read", {})
                        elif "write" in pattern:
                            metrics = job.get("write", {})
                        else:
                            metrics = job.get("read", {})  # Default to read

                        test_key = f"{pattern}_{block_size}_{io_depth}_{num_jobs}"
                        results[fs_name][test_key] = {
                            "pattern": pattern,
                            "block_size": block_size,
                            "io_depth": int(io_depth),
                            "num_jobs": int(num_jobs),
                            "iops": metrics.get("iops", 0),
                            "bandwidth_kbs": metrics.get("bw", 0),
                            "bandwidth_mbs": metrics.get("bw", 0) / 1024.0,
                            "latency_us": (
                                job.get("lat_ns", {}).get("mean", 0) / 1000.0
                                if job.get("lat_ns")
                                else 0
                            ),
                        }

            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue

    return results


def create_comparison_bar_chart(results, output_dir):
    """Create a bar chart comparing IOPS across filesystems for key tests"""

    # Select key test scenarios for comparison
    key_tests = [
        "randread_16k_1_1",
        "randwrite_16k_1_1",
        "seqread_16k_1_1",
        "seqwrite_16k_1_1",
        "randread_16k_32_1",
        "randwrite_16k_32_1",
    ]

    test_labels = [
        "Random Read\n16K, iodepth=1",
        "Random Write\n16K, iodepth=1",
        "Sequential Read\n16K, iodepth=1",
        "Sequential Write\n16K, iodepth=1",
        "Random Read\n16K, iodepth=32",
        "Random Write\n16K, iodepth=32",
    ]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 12))

    # IOPS Comparison
    filesystems = list(results.keys())
    x = np.arange(len(key_tests))
    width = 0.25

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]  # Blue, Orange, Green

    for i, fs in enumerate(filesystems):
        iops_values = []
        for test in key_tests:
            if test in results[fs]:
                iops_values.append(results[fs][test]["iops"])
            else:
                iops_values.append(0)

        bars = ax1.bar(
            x + i * width, iops_values, width, label=fs, color=colors[i], alpha=0.8
        )

        # Add value labels on bars
        for bar, value in zip(bars, iops_values):
            if value > 0:
                ax1.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(iops_values) * 0.01,
                    f"{value:.0f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    rotation=0,
                )

    ax1.set_xlabel("Test Scenarios")
    ax1.set_ylabel("IOPS")
    ax1.set_title(
        "Multi-Filesystem Performance Comparison - IOPS", fontsize=14, fontweight="bold"
    )
    ax1.set_xticks(x + width)
    ax1.set_xticklabels(test_labels, rotation=45, ha="right")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Bandwidth Comparison
    for i, fs in enumerate(filesystems):
        bw_values = []
        for test in key_tests:
            if test in results[fs]:
                bw_values.append(results[fs][test]["bandwidth_mbs"])
            else:
                bw_values.append(0)

        bars = ax2.bar(
            x + i * width, bw_values, width, label=fs, color=colors[i], alpha=0.8
        )

        # Add value labels on bars
        for bar, value in zip(bars, bw_values):
            if value > 0:
                ax2.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(bw_values) * 0.01,
                    f"{value:.1f}",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    rotation=0,
                )

    ax2.set_xlabel("Test Scenarios")
    ax2.set_ylabel("Bandwidth (MB/s)")
    ax2.set_title(
        "Multi-Filesystem Performance Comparison - Bandwidth",
        fontsize=14,
        fontweight="bold",
    )
    ax2.set_xticks(x + width)
    ax2.set_xticklabels(test_labels, rotation=45, ha="right")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = os.path.join(output_dir, "multi_filesystem_comparison.png")
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Generated: {output_file}")
    plt.close()


def create_block_size_comparison(results, output_dir):
    """Create comparison across different block sizes"""

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Block sizes to compare
    block_sizes = ["4k", "16k", "64k"]
    patterns = ["randread", "randwrite", "seqread", "seqwrite"]
    pattern_titles = [
        "Random Read",
        "Random Write",
        "Sequential Read",
        "Sequential Write",
    ]
    axes = [ax1, ax2, ax3, ax4]

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    filesystems = list(results.keys())

    for ax, pattern, title in zip(axes, patterns, pattern_titles):
        x = np.arange(len(block_sizes))
        width = 0.25

        for i, fs in enumerate(filesystems):
            iops_values = []
            for bs in block_sizes:
                test_key = f"{pattern}_{bs}_1_1"  # iodepth=1, jobs=1
                if test_key in results[fs]:
                    iops_values.append(results[fs][test_key]["iops"])
                else:
                    iops_values.append(0)

            bars = ax.bar(
                x + i * width, iops_values, width, label=fs, color=colors[i], alpha=0.8
            )

            # Add value labels
            for bar, value in zip(bars, iops_values):
                if value > 0:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + max(iops_values) * 0.01,
                        f"{value:.0f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )

        ax.set_xlabel("Block Size")
        ax.set_ylabel("IOPS")
        ax.set_title(f"{title} - Block Size Impact", fontweight="bold")
        ax.set_xticks(x + width)
        ax.set_xticklabels(block_sizes)
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.suptitle(
        "Block Size Performance Impact Across Filesystems",
        fontsize=16,
        fontweight="bold",
    )
    plt.tight_layout()

    output_file = os.path.join(output_dir, "block_size_comparison.png")
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Generated: {output_file}")
    plt.close()


def create_iodepth_scaling(results, output_dir):
    """Create IO depth scaling comparison"""

    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    io_depths = [1, 8, 32]
    patterns = ["randread", "randwrite", "seqread", "seqwrite"]
    pattern_titles = [
        "Random Read",
        "Random Write",
        "Sequential Read",
        "Sequential Write",
    ]
    axes = [ax1, ax2, ax3, ax4]

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]
    filesystems = list(results.keys())

    for ax, pattern, title in zip(axes, patterns, pattern_titles):
        for i, fs in enumerate(filesystems):
            iops_values = []
            for depth in io_depths:
                test_key = f"{pattern}_16k_{depth}_1"  # 16k blocks, 1 job
                if test_key in results[fs]:
                    iops_values.append(results[fs][test_key]["iops"])
                else:
                    iops_values.append(0)

            ax.plot(
                io_depths,
                iops_values,
                marker="o",
                linewidth=2,
                markersize=8,
                label=fs,
                color=colors[i],
            )

            # Add value labels
            for x, y in zip(io_depths, iops_values):
                if y > 0:
                    ax.annotate(
                        f"{y:.0f}",
                        (x, y),
                        textcoords="offset points",
                        xytext=(0, 10),
                        ha="center",
                        fontsize=8,
                    )

        ax.set_xlabel("IO Depth")
        ax.set_ylabel("IOPS")
        ax.set_title(f"{title} - IO Depth Scaling", fontweight="bold")
        ax.set_xscale("log", base=2)
        ax.set_xticks(io_depths)
        ax.set_xticklabels(io_depths)
        ax.legend()
        ax.grid(True, alpha=0.3)

    plt.suptitle("IO Depth Scaling Across Filesystems", fontsize=16, fontweight="bold")
    plt.tight_layout()

    output_file = os.path.join(output_dir, "iodepth_scaling.png")
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Generated: {output_file}")
    plt.close()


def create_summary_dashboard(results, output_dir):
    """Create a comprehensive dashboard with key metrics"""

    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 4, hspace=0.3, wspace=0.3)

    # Main comparison (top row, spans 2 columns)
    ax_main = fig.add_subplot(gs[0, :2])

    # Performance ranking for random read 16k
    filesystems = list(results.keys())
    test_key = "randread_16k_1_1"

    iops_values = []
    bw_values = []
    for fs in filesystems:
        if test_key in results[fs]:
            iops_values.append(results[fs][test_key]["iops"])
            bw_values.append(results[fs][test_key]["bandwidth_mbs"])
        else:
            iops_values.append(0)
            bw_values.append(0)

    # Create ranking bar chart
    y_pos = np.arange(len(filesystems))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]

    bars = ax_main.barh(y_pos, iops_values, color=colors, alpha=0.8)
    ax_main.set_yticks(y_pos)
    ax_main.set_yticklabels([fs.split(" (")[0] for fs in filesystems])
    ax_main.set_xlabel("IOPS")
    ax_main.set_title(
        "Random Read Performance (16K blocks, iodepth=1)",
        fontweight="bold",
        fontsize=14,
    )

    # Add value labels
    for bar, value in zip(bars, iops_values):
        ax_main.text(
            bar.get_width() + max(iops_values) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.0f}",
            ha="left",
            va="center",
            fontweight="bold",
        )

    ax_main.grid(True, alpha=0.3)

    # Performance matrix (top right)
    ax_matrix = fig.add_subplot(gs[0, 2:])

    # Create performance matrix
    patterns = ["randread", "randwrite", "seqread", "seqwrite"]
    matrix_data = []

    for fs in filesystems:
        fs_row = []
        for pattern in patterns:
            test_key = f"{pattern}_16k_1_1"
            if test_key in results[fs]:
                fs_row.append(results[fs][test_key]["iops"])
            else:
                fs_row.append(0)
        matrix_data.append(fs_row)

    im = ax_matrix.imshow(matrix_data, cmap="YlOrRd", aspect="auto")
    ax_matrix.set_xticks(range(len(patterns)))
    ax_matrix.set_xticklabels(
        ["Rand Read", "Rand Write", "Seq Read", "Seq Write"], rotation=45
    )
    ax_matrix.set_yticks(range(len(filesystems)))
    ax_matrix.set_yticklabels([fs.split(" (")[0] for fs in filesystems])
    ax_matrix.set_title("Performance Heatmap (IOPS)", fontweight="bold")

    # Add text annotations
    for i in range(len(filesystems)):
        for j in range(len(patterns)):
            text = ax_matrix.text(
                j,
                i,
                f"{matrix_data[i][j]:.0f}",
                ha="center",
                va="center",
                color="black",
                fontweight="bold",
            )

    # Block size comparison (bottom left)
    ax_bs = fig.add_subplot(gs[1, :2])

    block_sizes = ["4k", "16k", "64k"]
    x = np.arange(len(block_sizes))
    width = 0.25

    for i, fs in enumerate(filesystems):
        iops_values = []
        for bs in block_sizes:
            test_key = f"randread_{bs}_1_1"
            if test_key in results[fs]:
                iops_values.append(results[fs][test_key]["iops"])
            else:
                iops_values.append(0)

        ax_bs.bar(
            x + i * width,
            iops_values,
            width,
            label=fs.split(" (")[0],
            color=colors[i],
            alpha=0.8,
        )

    ax_bs.set_xlabel("Block Size")
    ax_bs.set_ylabel("IOPS")
    ax_bs.set_title("Random Read - Block Size Impact", fontweight="bold")
    ax_bs.set_xticks(x + width)
    ax_bs.set_xticklabels(block_sizes)
    ax_bs.legend()
    ax_bs.grid(True, alpha=0.3)

    # IO depth scaling (bottom right)
    ax_depth = fig.add_subplot(gs[1, 2:])

    io_depths = [1, 8, 32]
    for i, fs in enumerate(filesystems):
        iops_values = []
        for depth in io_depths:
            test_key = f"randread_16k_{depth}_1"
            if test_key in results[fs]:
                iops_values.append(results[fs][test_key]["iops"])
            else:
                iops_values.append(0)

        ax_depth.plot(
            io_depths,
            iops_values,
            marker="o",
            linewidth=3,
            markersize=8,
            label=fs.split(" (")[0],
            color=colors[i],
        )

    ax_depth.set_xlabel("IO Depth")
    ax_depth.set_ylabel("IOPS")
    ax_depth.set_title("Random Read - IO Depth Scaling", fontweight="bold")
    ax_depth.set_xscale("log", base=2)
    ax_depth.set_xticks(io_depths)
    ax_depth.set_xticklabels(io_depths)
    ax_depth.legend()
    ax_depth.grid(True, alpha=0.3)

    # Summary statistics (bottom row)
    ax_summary = fig.add_subplot(gs[2, :])
    ax_summary.axis("off")

    # Create summary table
    summary_text = "=== Performance Summary ===\n\n"

    # Random read comparison
    test_key = "randread_16k_1_1"
    performances = []
    for fs in filesystems:
        if test_key in results[fs]:
            performances.append(
                (
                    fs,
                    results[fs][test_key]["iops"],
                    results[fs][test_key]["bandwidth_mbs"],
                )
            )

    # Sort by IOPS
    performances.sort(key=lambda x: x[1], reverse=True)

    summary_text += "Random Read Performance Ranking (16K blocks):\n"
    for i, (fs, iops, bw) in enumerate(performances):
        fs_short = fs.split(" (")[0]
        if i == 0:
            summary_text += f"🥇 {fs_short}: {iops:.0f} IOPS, {bw:.1f} MB/s\n"
        elif i == 1:
            pct_diff = ((performances[0][1] - iops) / performances[0][1]) * 100
            summary_text += (
                f"🥈 {fs_short}: {iops:.0f} IOPS, {bw:.1f} MB/s (-{pct_diff:.1f}%)\n"
            )
        else:
            pct_diff = ((performances[0][1] - iops) / performances[0][1]) * 100
            summary_text += (
                f"🥉 {fs_short}: {iops:.0f} IOPS, {bw:.1f} MB/s (-{pct_diff:.1f}%)\n"
            )

    summary_text += (
        f"\nTest Infrastructure: 6 VMs (3 baseline + 3 dev for A/B testing)\n"
    )
    summary_text += f"Total Tests Executed: {sum(len(fs_results) for fs_results in results.values())} across all filesystems"

    ax_summary.text(
        0.05,
        0.5,
        summary_text,
        transform=ax_summary.transAxes,
        fontsize=12,
        verticalalignment="center",
        fontfamily="monospace",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="lightgray", alpha=0.8),
    )

    plt.suptitle(
        "kdevops Multi-Filesystem Performance Dashboard",
        fontsize=18,
        fontweight="bold",
        y=0.98,
    )

    output_file = os.path.join(output_dir, "performance_dashboard.png")
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"Generated: {output_file}")
    plt.close()


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 generate_comparison_graphs.py <results_directory>")
        sys.exit(1)

    results_dir = sys.argv[1]

    if not os.path.exists(results_dir):
        print(f"Error: Results directory {results_dir} not found")
        sys.exit(1)

    print("Loading fio results...")
    results = load_fio_results(results_dir)

    if not results:
        print("No results found!")
        sys.exit(1)

    print(f"Loaded results for {len(results)} filesystems:")
    for fs, tests in results.items():
        print(f"  {fs}: {len(tests)} tests")

    # Create output directory for graphs
    graphs_dir = os.path.join(results_dir, "graphs")
    os.makedirs(graphs_dir, exist_ok=True)

    print("Generating graphs...")

    # Generate all comparison graphs
    create_comparison_bar_chart(results, graphs_dir)
    create_block_size_comparison(results, graphs_dir)
    create_iodepth_scaling(results, graphs_dir)
    create_summary_dashboard(results, graphs_dir)

    print(f"\nAll graphs generated in: {graphs_dir}")
    print("\nGenerated files:")
    for graph_file in glob.glob(os.path.join(graphs_dir, "*.png")):
        print(f"  - {os.path.basename(graph_file)}")


if __name__ == "__main__":
    main()

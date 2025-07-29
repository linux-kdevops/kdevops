#!/usr/bin/env python3
"""
Generate graphs and analysis for AI benchmark results
"""

import json
import os
import sys
import glob
import numpy as np
import matplotlib

matplotlib.use("Agg")  # Use non-interactive backend
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from collections import defaultdict


def load_results(results_dir):
    """Load all JSON result files from the directory"""
    results = []
    json_files = glob.glob(os.path.join(results_dir, "*.json"))

    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                # Extract filesystem info from filename
                filename = os.path.basename(json_file)
                parts = filename.replace("results_", "").replace(".json", "").split("-")

                # Parse host info
                if "debian13-ai-" in filename:
                    host_parts = (
                        filename.replace("results_debian13-ai-", "")
                        .replace("_1.json", "")
                        .split("-")
                    )
                    if "xfs" in host_parts[0]:
                        fs_type = "xfs"
                        # Extract block size (e.g., "4k", "16k", etc.)
                        block_size = host_parts[1] if len(host_parts) > 1 else "unknown"
                    elif "ext4" in host_parts[0]:
                        fs_type = "ext4"
                        block_size = host_parts[1] if len(host_parts) > 1 else "4k"
                    elif "btrfs" in host_parts[0]:
                        fs_type = "btrfs"
                        block_size = "default"
                    else:
                        fs_type = "unknown"
                        block_size = "unknown"

                    is_dev = "dev" in filename

                    data["filesystem"] = fs_type
                    data["block_size"] = block_size
                    data["is_dev"] = is_dev
                    data["filename"] = filename

                results.append(data)
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    return results


def create_filesystem_comparison_chart(results, output_dir):
    """Create a bar chart comparing performance across filesystems"""
    # Group by filesystem and baseline/dev
    fs_data = defaultdict(lambda: {"baseline": [], "dev": []})

    for result in results:
        fs = result.get("filesystem", "unknown")
        category = "dev" if result.get("is_dev", False) else "baseline"

        # Use dummy performance data for now
        insert_qps = result.get("performance", {}).get("insert_qps", 1000)
        fs_data[fs][category].append(insert_qps)

    # Prepare data for plotting
    filesystems = list(fs_data.keys())
    baseline_means = [
        np.mean(fs_data[fs]["baseline"]) if fs_data[fs]["baseline"] else 0
        for fs in filesystems
    ]
    dev_means = [
        np.mean(fs_data[fs]["dev"]) if fs_data[fs]["dev"] else 0 for fs in filesystems
    ]

    x = np.arange(len(filesystems))
    width = 0.35

    fig, ax = plt.subplots(figsize=(10, 6))
    baseline_bars = ax.bar(
        x - width / 2, baseline_means, width, label="Baseline", color="#1f77b4"
    )
    dev_bars = ax.bar(
        x + width / 2, dev_means, width, label="Development", color="#ff7f0e"
    )

    ax.set_xlabel("Filesystem")
    ax.set_ylabel("Insert QPS")
    ax.set_title("Vector Database Performance by Filesystem")
    ax.set_xticks(x)
    ax.set_xticklabels(filesystems)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add value labels on bars
    for bars in [baseline_bars, dev_bars]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(
                    f"{height:.0f}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                )

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "filesystem_comparison.png"), dpi=150)
    plt.close()


def create_block_size_analysis(results, output_dir):
    """Create analysis for different block sizes (XFS specific)"""
    # Filter XFS results
    xfs_results = [r for r in results if r.get("filesystem") == "xfs"]

    if not xfs_results:
        return

    # Group by block size
    block_size_data = defaultdict(lambda: {"baseline": [], "dev": []})

    for result in xfs_results:
        block_size = result.get("block_size", "unknown")
        category = "dev" if result.get("is_dev", False) else "baseline"
        insert_qps = result.get("performance", {}).get("insert_qps", 1000)
        block_size_data[block_size][category].append(insert_qps)

    # Sort block sizes
    block_sizes = sorted(
        block_size_data.keys(),
        key=lambda x: (
            int(x.replace("k", "").replace("s", ""))
            if x not in ["unknown", "default"]
            else 0
        ),
    )

    # Create grouped bar chart
    baseline_means = [
        (
            np.mean(block_size_data[bs]["baseline"])
            if block_size_data[bs]["baseline"]
            else 0
        )
        for bs in block_sizes
    ]
    dev_means = [
        np.mean(block_size_data[bs]["dev"]) if block_size_data[bs]["dev"] else 0
        for bs in block_sizes
    ]

    x = np.arange(len(block_sizes))
    width = 0.35

    fig, ax = plt.subplots(figsize=(12, 6))
    baseline_bars = ax.bar(
        x - width / 2, baseline_means, width, label="Baseline", color="#2ca02c"
    )
    dev_bars = ax.bar(
        x + width / 2, dev_means, width, label="Development", color="#d62728"
    )

    ax.set_xlabel("Block Size")
    ax.set_ylabel("Insert QPS")
    ax.set_title("XFS Performance by Block Size")
    ax.set_xticks(x)
    ax.set_xticklabels(block_sizes)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add value labels
    for bars in [baseline_bars, dev_bars]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(
                    f"{height:.0f}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                )

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "xfs_block_size_analysis.png"), dpi=150)
    plt.close()


def create_heatmap_analysis(results, output_dir):
    """Create a heatmap showing performance across all configurations"""
    # Group data by configuration and version
    config_data = defaultdict(
        lambda: {
            "baseline": {"insert": 0, "query": 0},
            "dev": {"insert": 0, "query": 0},
        }
    )

    for result in results:
        fs = result.get("filesystem", "unknown")
        block_size = result.get("block_size", "default")
        config = f"{fs}-{block_size}"
        version = "dev" if result.get("is_dev", False) else "baseline"

        insert_qps = result.get("performance", {}).get("insert_qps", 1000)
        query_qps = result.get("performance", {}).get("query_qps", 5000)

        config_data[config][version]["insert"] = insert_qps
        config_data[config][version]["query"] = query_qps

    # Sort configurations
    configs = sorted(config_data.keys())

    # Prepare data for heatmap
    insert_baseline = [config_data[c]["baseline"]["insert"] for c in configs]
    insert_dev = [config_data[c]["dev"]["insert"] for c in configs]
    query_baseline = [config_data[c]["baseline"]["query"] for c in configs]
    query_dev = [config_data[c]["dev"]["query"] for c in configs]

    # Create figure with custom heatmap
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Create data matrices
    insert_data = np.array([insert_baseline, insert_dev]).T
    query_data = np.array([query_baseline, query_dev]).T

    # Insert QPS heatmap
    im1 = ax1.imshow(insert_data, cmap="YlOrRd", aspect="auto")
    ax1.set_xticks([0, 1])
    ax1.set_xticklabels(["Baseline", "Development"])
    ax1.set_yticks(range(len(configs)))
    ax1.set_yticklabels(configs)
    ax1.set_title("Insert Performance Heatmap")
    ax1.set_ylabel("Configuration")

    # Add text annotations
    for i in range(len(configs)):
        for j in range(2):
            text = ax1.text(
                j,
                i,
                f"{int(insert_data[i, j])}",
                ha="center",
                va="center",
                color="black",
            )

    # Add colorbar
    cbar1 = plt.colorbar(im1, ax=ax1)
    cbar1.set_label("Insert QPS")

    # Query QPS heatmap
    im2 = ax2.imshow(query_data, cmap="YlGnBu", aspect="auto")
    ax2.set_xticks([0, 1])
    ax2.set_xticklabels(["Baseline", "Development"])
    ax2.set_yticks(range(len(configs)))
    ax2.set_yticklabels(configs)
    ax2.set_title("Query Performance Heatmap")

    # Add text annotations
    for i in range(len(configs)):
        for j in range(2):
            text = ax2.text(
                j,
                i,
                f"{int(query_data[i, j])}",
                ha="center",
                va="center",
                color="black",
            )

    # Add colorbar
    cbar2 = plt.colorbar(im2, ax=ax2)
    cbar2.set_label("Query QPS")

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "performance_heatmap.png"), dpi=150)
    plt.close()


def create_performance_trends(results, output_dir):
    """Create line charts showing performance trends"""
    # Group by filesystem type
    fs_types = defaultdict(
        lambda: {
            "configs": [],
            "baseline_insert": [],
            "dev_insert": [],
            "baseline_query": [],
            "dev_query": [],
        }
    )

    for result in results:
        fs = result.get("filesystem", "unknown")
        block_size = result.get("block_size", "default")
        config = f"{block_size}"

        if config not in fs_types[fs]["configs"]:
            fs_types[fs]["configs"].append(config)
            fs_types[fs]["baseline_insert"].append(0)
            fs_types[fs]["dev_insert"].append(0)
            fs_types[fs]["baseline_query"].append(0)
            fs_types[fs]["dev_query"].append(0)

        idx = fs_types[fs]["configs"].index(config)

        if result.get("is_dev", False):
            fs_types[fs]["dev_insert"][idx] = result.get("performance", {}).get(
                "insert_qps", 0
            )
            fs_types[fs]["dev_query"][idx] = result.get("performance", {}).get(
                "query_qps", 0
            )
        else:
            fs_types[fs]["baseline_insert"][idx] = result.get("performance", {}).get(
                "insert_qps", 0
            )
            fs_types[fs]["baseline_query"][idx] = result.get("performance", {}).get(
                "query_qps", 0
            )

    # Create separate plots for each filesystem
    for fs, data in fs_types.items():
        if not data["configs"]:
            continue

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))

        x = range(len(data["configs"]))

        # Insert performance
        ax1.plot(
            x,
            data["baseline_insert"],
            "o-",
            label="Baseline",
            linewidth=2,
            markersize=8,
        )
        ax1.plot(
            x, data["dev_insert"], "s-", label="Development", linewidth=2, markersize=8
        )
        ax1.set_xlabel("Configuration")
        ax1.set_ylabel("Insert QPS")
        ax1.set_title(f"{fs.upper()} Insert Performance")
        ax1.set_xticks(x)
        ax1.set_xticklabels(data["configs"])
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # Query performance
        ax2.plot(
            x, data["baseline_query"], "o-", label="Baseline", linewidth=2, markersize=8
        )
        ax2.plot(
            x, data["dev_query"], "s-", label="Development", linewidth=2, markersize=8
        )
        ax2.set_xlabel("Configuration")
        ax2.set_ylabel("Query QPS")
        ax2.set_title(f"{fs.upper()} Query Performance")
        ax2.set_xticks(x)
        ax2.set_xticklabels(data["configs"])
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, f"{fs}_performance_trends.png"), dpi=150)
        plt.close()


def generate_summary_statistics(results, output_dir):
    """Generate summary statistics and save to JSON"""
    summary = {
        "total_tests": len(results),
        "filesystems_tested": list(
            set(r.get("filesystem", "unknown") for r in results)
        ),
        "configurations": {},
        "performance_summary": {
            "best_insert_qps": {"value": 0, "config": ""},
            "best_query_qps": {"value": 0, "config": ""},
            "average_insert_qps": 0,
            "average_query_qps": 0,
        },
    }

    # Calculate statistics
    all_insert_qps = []
    all_query_qps = []

    for result in results:
        fs = result.get("filesystem", "unknown")
        block_size = result.get("block_size", "default")
        is_dev = "dev" if result.get("is_dev", False) else "baseline"
        config_name = f"{fs}-{block_size}-{is_dev}"

        insert_qps = result.get("performance", {}).get("insert_qps", 0)
        query_qps = result.get("performance", {}).get("query_qps", 0)

        all_insert_qps.append(insert_qps)
        all_query_qps.append(query_qps)

        summary["configurations"][config_name] = {
            "insert_qps": insert_qps,
            "query_qps": query_qps,
            "host": result.get("host", "unknown"),
        }

        if insert_qps > summary["performance_summary"]["best_insert_qps"]["value"]:
            summary["performance_summary"]["best_insert_qps"] = {
                "value": insert_qps,
                "config": config_name,
            }

        if query_qps > summary["performance_summary"]["best_query_qps"]["value"]:
            summary["performance_summary"]["best_query_qps"] = {
                "value": query_qps,
                "config": config_name,
            }

    summary["performance_summary"]["average_insert_qps"] = (
        np.mean(all_insert_qps) if all_insert_qps else 0
    )
    summary["performance_summary"]["average_query_qps"] = (
        np.mean(all_query_qps) if all_query_qps else 0
    )

    # Save summary
    with open(os.path.join(output_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    return summary


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_graphs.py <results_dir> <output_dir>")
        sys.exit(1)

    results_dir = sys.argv[1]
    output_dir = sys.argv[2]

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load results
    results = load_results(results_dir)

    if not results:
        print("No results found to analyze")
        sys.exit(1)

    print(f"Loaded {len(results)} result files")

    # Generate graphs
    print("Generating filesystem comparison chart...")
    create_filesystem_comparison_chart(results, output_dir)

    print("Generating block size analysis...")
    create_block_size_analysis(results, output_dir)

    print("Generating performance heatmap...")
    create_heatmap_analysis(results, output_dir)

    print("Generating performance trends...")
    create_performance_trends(results, output_dir)

    print("Generating summary statistics...")
    summary = generate_summary_statistics(results, output_dir)

    print(f"\nAnalysis complete! Graphs saved to {output_dir}")
    print(f"Total configurations tested: {summary['total_tests']}")
    print(
        f"Best insert QPS: {summary['performance_summary']['best_insert_qps']['value']} ({summary['performance_summary']['best_insert_qps']['config']})"
    )
    print(
        f"Best query QPS: {summary['performance_summary']['best_query_qps']['value']} ({summary['performance_summary']['best_query_qps']['config']})"
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate meaningful graphs for AI benchmark results
Focus on QPS and Latency metrics that matter
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
import subprocess


def extract_filesystem_from_filename(filename):
    """Extract filesystem type from result filename"""
    # Expected format: results_debian13-ai-xfs-4k-4ks_1.json or results_debian13-ai-ext4-4k_1.json
    if "debian13-ai-" in filename:
        # Remove the "results_" prefix and ".json" suffix
        node_name = filename.replace("results_", "").replace(".json", "")
        # Remove the iteration number at the end
        if "_" in node_name:
            parts = node_name.split("_")
            node_name = "_".join(parts[:-1])  # Remove last part (iteration)

        # Extract filesystem type from node name
        if "-xfs-" in node_name:
            return "xfs"
        elif "-ext4-" in node_name:
            return "ext4"
        elif "-btrfs-" in node_name:
            return "btrfs"

    return "unknown"


def extract_node_config_from_filename(filename):
    """Extract detailed node configuration from filename"""
    # Expected format: results_debian13-ai-xfs-4k-4ks_1.json
    if "debian13-ai-" in filename:
        # Remove the "results_" prefix and ".json" suffix
        node_name = filename.replace("results_", "").replace(".json", "")
        # Remove the iteration number at the end
        if "_" in node_name:
            parts = node_name.split("_")
            node_name = "_".join(parts[:-1])  # Remove last part (iteration)

        # Remove -dev suffix if present
        node_name = node_name.replace("-dev", "")

        return node_name.replace("debian13-ai-", "")

    return "unknown"


def detect_filesystem():
    """Detect the filesystem type of /data on test nodes"""
    # This is now a fallback - we primarily use filename-based detection
    try:
        # Try to get filesystem info from a test node
        result = subprocess.run(
            ["ssh", "debian13-ai", "df -T /data | tail -1"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) >= 2:
                return parts[1]  # filesystem type is second column
    except:
        pass

    # Fallback to local filesystem check
    try:
        result = subprocess.run(["df", "-T", "."], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 2:
                    return parts[1]
    except:
        pass

    return "unknown"


def load_results(results_dir):
    """Load all JSON result files from the directory"""
    results = []
    json_files = glob.glob(os.path.join(results_dir, "results_*.json"))

    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                data = json.load(f)

                # Extract node type from filename
                filename = os.path.basename(json_file)
                data["filename"] = filename

                # Extract filesystem type and config from filename
                data["filesystem"] = extract_filesystem_from_filename(filename)
                data["node_config"] = extract_node_config_from_filename(filename)

                # Determine if it's baseline or dev
                if "-dev_" in filename or "-dev." in filename:
                    data["node_type"] = "dev"
                    data["is_dev"] = True
                else:
                    data["node_type"] = "baseline"
                    data["is_dev"] = False

                # Extract iteration number
                if "_" in filename:
                    parts = filename.split("_")
                    iteration = parts[-1].replace(".json", "")
                    data["iteration"] = int(iteration) if iteration.isdigit() else 1
                else:
                    data["iteration"] = 1

                results.append(data)
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    return results


def create_qps_comparison_chart(results, output_dir):
    """Create a clear QPS comparison chart between baseline and dev"""

    # Organize data by node type and test configuration
    baseline_data = defaultdict(list)
    dev_data = defaultdict(list)

    for result in results:
        if "query_performance" not in result:
            continue

        qp = result["query_performance"]
        node_type = result.get("node_type", "unknown")

        # Extract QPS for different configurations
        for topk in ["topk_1", "topk_10", "topk_100"]:
            if topk not in qp:
                continue
            for batch in ["batch_1", "batch_10", "batch_100"]:
                if batch not in qp[topk]:
                    continue

                config_name = f"{topk}_{batch}"
                qps = qp[topk][batch].get("queries_per_second", 0)

                if node_type == "dev":
                    dev_data[config_name].append(qps)
                else:
                    baseline_data[config_name].append(qps)

    # Calculate averages
    configs = sorted(set(baseline_data.keys()) | set(dev_data.keys()))
    baseline_avg = [
        np.mean(baseline_data[c]) if baseline_data[c] else 0 for c in configs
    ]
    dev_avg = [np.mean(dev_data[c]) if dev_data[c] else 0 for c in configs]

    # Create the plot
    fig, ax = plt.subplots(figsize=(14, 8))

    x = np.arange(len(configs))
    width = 0.35

    baseline_bars = ax.bar(
        x - width / 2, baseline_avg, width, label="Baseline", color="#2E86AB"
    )
    dev_bars = ax.bar(
        x + width / 2, dev_avg, width, label="Development", color="#A23B72"
    )

    # Customize the plot
    ax.set_xlabel("Query Configuration", fontsize=12)
    ax.set_ylabel("Queries Per Second (QPS)", fontsize=12)
    fs_type = results[0].get("filesystem", "unknown") if results else "unknown"
    ax.set_title(
        f"Milvus Query Performance Comparison\nFilesystem: {fs_type.upper()}",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_", "\n") for c in configs], rotation=45, ha="right")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis="y")

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
                    fontsize=9,
                )

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "qps_comparison.png"), dpi=150, bbox_inches="tight"
    )
    plt.close()

    print(f"Generated QPS comparison chart")


def create_latency_comparison_chart(results, output_dir):
    """Create latency comparison chart (lower is better)"""

    # Organize data by node type and test configuration
    baseline_latency = defaultdict(list)
    dev_latency = defaultdict(list)

    for result in results:
        if "query_performance" not in result:
            continue

        qp = result["query_performance"]
        node_type = result.get("node_type", "unknown")

        # Extract latency for different configurations
        for topk in ["topk_1", "topk_10", "topk_100"]:
            if topk not in qp:
                continue
            for batch in ["batch_1", "batch_10", "batch_100"]:
                if batch not in qp[topk]:
                    continue

                config_name = f"{topk}_{batch}"
                # Convert to milliseconds for readability
                latency_ms = qp[topk][batch].get("average_time_seconds", 0) * 1000

                if node_type == "dev":
                    dev_latency[config_name].append(latency_ms)
                else:
                    baseline_latency[config_name].append(latency_ms)

    # Calculate averages
    configs = sorted(set(baseline_latency.keys()) | set(dev_latency.keys()))
    baseline_avg = [
        np.mean(baseline_latency[c]) if baseline_latency[c] else 0 for c in configs
    ]
    dev_avg = [np.mean(dev_latency[c]) if dev_latency[c] else 0 for c in configs]

    # Create the plot
    fig, ax = plt.subplots(figsize=(14, 8))

    x = np.arange(len(configs))
    width = 0.35

    baseline_bars = ax.bar(
        x - width / 2, baseline_avg, width, label="Baseline", color="#2E86AB"
    )
    dev_bars = ax.bar(
        x + width / 2, dev_avg, width, label="Development", color="#A23B72"
    )

    # Customize the plot
    ax.set_xlabel("Query Configuration", fontsize=12)
    ax.set_ylabel("Average Latency (milliseconds)", fontsize=12)
    fs_type = results[0].get("filesystem", "unknown") if results else "unknown"
    ax.set_title(
        f"Milvus Query Latency Comparison (Lower is Better)\nFilesystem: {fs_type.upper()}",
        fontsize=14,
        fontweight="bold",
    )
    ax.set_xticks(x)
    ax.set_xticklabels([c.replace("_", "\n") for c in configs], rotation=45, ha="right")
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis="y")

    # Add value labels on bars
    for bars in [baseline_bars, dev_bars]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(
                    f"{height:.1f}ms",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "latency_comparison.png"), dpi=150, bbox_inches="tight"
    )
    plt.close()

    print(f"Generated latency comparison chart")


def create_insert_performance_chart(results, output_dir):
    """Create insert performance comparison"""

    baseline_insert = []
    dev_insert = []

    for result in results:
        if "insert_performance" not in result:
            continue

        vectors_per_sec = result["insert_performance"].get("vectors_per_second", 0)
        node_type = result.get("node_type", "unknown")

        if node_type == "dev":
            dev_insert.append(vectors_per_sec)
        else:
            baseline_insert.append(vectors_per_sec)

    if not baseline_insert and not dev_insert:
        return

    # Create box plot for insert performance
    fig, ax = plt.subplots(figsize=(10, 6))

    data_to_plot = []
    labels = []

    if baseline_insert:
        data_to_plot.append(baseline_insert)
        labels.append("Baseline")
    if dev_insert:
        data_to_plot.append(dev_insert)
        labels.append("Development")

    bp = ax.boxplot(data_to_plot, labels=labels, patch_artist=True)

    # Color the boxes
    colors = ["#2E86AB", "#A23B72"]
    for patch, color in zip(bp["boxes"], colors[: len(bp["boxes"])]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    # Add individual points
    for i, data in enumerate(data_to_plot, 1):
        x = np.random.normal(i, 0.04, size=len(data))
        ax.scatter(x, data, alpha=0.4, s=30, color="black")

    ax.set_ylabel("Vectors per Second", fontsize=12)
    fs_type = results[0].get("filesystem", "unknown") if results else "unknown"
    ax.set_title(
        f"Insert Performance Distribution\nFilesystem: {fs_type.upper()}",
        fontsize=14,
        fontweight="bold",
    )
    ax.grid(True, alpha=0.3, axis="y")

    # Add mean values
    for i, data in enumerate(data_to_plot, 1):
        mean_val = np.mean(data)
        ax.text(
            i,
            mean_val,
            f"μ={mean_val:.0f}",
            ha="center",
            va="bottom",
            fontweight="bold",
        )

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "insert_performance.png"), dpi=150, bbox_inches="tight"
    )
    plt.close()

    print(f"Generated insert performance chart")


def create_performance_summary_table(results, output_dir):
    """Create a performance summary table as an image"""

    # Calculate summary statistics
    summary_data = {"Metric": [], "Baseline": [], "Development": [], "Improvement": []}

    # Insert performance
    baseline_insert = []
    dev_insert = []

    for result in results:
        if "insert_performance" in result:
            vectors_per_sec = result["insert_performance"].get("vectors_per_second", 0)
            if result.get("node_type") == "dev":
                dev_insert.append(vectors_per_sec)
            else:
                baseline_insert.append(vectors_per_sec)

    if baseline_insert and dev_insert:
        baseline_avg = np.mean(baseline_insert)
        dev_avg = np.mean(dev_insert)
        improvement = ((dev_avg - baseline_avg) / baseline_avg) * 100

        summary_data["Metric"].append("Insert Rate (vec/s)")
        summary_data["Baseline"].append(f"{baseline_avg:.0f}")
        summary_data["Development"].append(f"{dev_avg:.0f}")
        summary_data["Improvement"].append(f"{improvement:+.1f}%")

    # Query performance (best case)
    baseline_best_qps = 0
    dev_best_qps = 0

    for result in results:
        if "query_performance" in result:
            qp = result["query_performance"]
            for topk in qp.values():
                for batch in topk.values():
                    qps = batch.get("queries_per_second", 0)
                    if result.get("node_type") == "dev":
                        dev_best_qps = max(dev_best_qps, qps)
                    else:
                        baseline_best_qps = max(baseline_best_qps, qps)

    if baseline_best_qps and dev_best_qps:
        improvement = ((dev_best_qps - baseline_best_qps) / baseline_best_qps) * 100
        summary_data["Metric"].append("Best Query QPS")
        summary_data["Baseline"].append(f"{baseline_best_qps:.0f}")
        summary_data["Development"].append(f"{dev_best_qps:.0f}")
        summary_data["Improvement"].append(f"{improvement:+.1f}%")

    # Create table plot
    # Check if we have data to create a table
    if not summary_data["Metric"]:
        print("No comparison data available for performance summary table")
        return

    fig, ax = plt.subplots(figsize=(10, 3))
    ax.axis("tight")
    ax.axis("off")

    table_data = []
    for i in range(len(summary_data["Metric"])):
        table_data.append(
            [
                summary_data["Metric"][i],
                summary_data["Baseline"][i],
                summary_data["Development"][i],
                summary_data["Improvement"][i],
            ]
        )

    table = ax.table(
        cellText=table_data,
        colLabels=["Metric", "Baseline", "Development", "Change"],
        cellLoc="center",
        loc="center",
        colWidths=[0.3, 0.2, 0.2, 0.2],
    )

    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1.2, 1.5)

    # Style the header
    for i in range(4):
        table[(0, i)].set_facecolor("#2E86AB")
        table[(0, i)].set_text_props(weight="bold", color="white")

    # Color improvement cells
    for i in range(1, len(table_data) + 1):
        if "+" in table_data[i - 1][3]:
            table[(i, 3)].set_facecolor("#90EE90")
        elif "-" in table_data[i - 1][3]:
            table[(i, 3)].set_facecolor("#FFB6C1")

    fs_type = results[0].get("filesystem", "unknown") if results else "unknown"
    plt.title(
        f"Performance Summary - Filesystem: {fs_type.upper()}",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    plt.savefig(
        os.path.join(output_dir, "performance_summary.png"),
        dpi=150,
        bbox_inches="tight",
    )
    plt.close()

    print(f"Generated performance summary table")


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_better_graphs.py <results_dir> <output_dir>")
        sys.exit(1)

    results_dir = sys.argv[1]
    output_dir = sys.argv[2]

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Load results
    results = load_results(results_dir)
    print(f"Loaded {len(results)} result files")

    if not results:
        print("No results found!")
        sys.exit(1)

    # Generate graphs
    print("Generating QPS comparison chart...")
    create_qps_comparison_chart(results, output_dir)

    print("Generating latency comparison chart...")
    create_latency_comparison_chart(results, output_dir)

    print("Generating insert performance chart...")
    create_insert_performance_chart(results, output_dir)

    print("Generating performance summary table...")
    create_performance_summary_table(results, output_dir)

    print(f"\nAnalysis complete! Graphs saved to {output_dir}")

    # Print summary
    fs_type = results[0].get("filesystem", "unknown")
    print(f"Filesystem detected: {fs_type}")
    print(f"Total tests analyzed: {len(results)}")

    baseline_count = sum(1 for r in results if r.get("node_type") == "baseline")
    dev_count = sum(1 for r in results if r.get("node_type") == "dev")
    print(f"Baseline tests: {baseline_count}")
    print(f"Development tests: {dev_count}")


if __name__ == "__main__":
    main()

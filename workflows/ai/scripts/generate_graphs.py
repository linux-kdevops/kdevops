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
    # Only load results_*.json files, not consolidated or other JSON files
    json_files = glob.glob(os.path.join(results_dir, "results_*.json"))

    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                # Extract filesystem info - prefer from JSON data over filename
                filename = os.path.basename(json_file)

                # First, try to get filesystem from the JSON data itself
                fs_type = data.get("filesystem", None)

                # If not in JSON, try to parse from filename (backwards compatibility)
                if not fs_type:
                    parts = (
                        filename.replace("results_", "").replace(".json", "").split("-")
                    )

                    # Parse host info
                    if "debian13-ai-" in filename:
                        host_parts = (
                            filename.replace("results_debian13-ai-", "")
                            .replace("_1.json", "")
                            .replace("_2.json", "")
                            .replace("_3.json", "")
                            .split("-")
                        )
                        if "xfs" in host_parts[0]:
                            fs_type = "xfs"
                            # Extract block size (e.g., "4k", "16k", etc.)
                            block_size = (
                                host_parts[1] if len(host_parts) > 1 else "unknown"
                            )
                        elif "ext4" in host_parts[0]:
                            fs_type = "ext4"
                            block_size = host_parts[1] if len(host_parts) > 1 else "4k"
                        elif "btrfs" in host_parts[0]:
                            fs_type = "btrfs"
                            block_size = "default"
                        else:
                            fs_type = "unknown"
                            block_size = "unknown"
                    else:
                        fs_type = "unknown"
                        block_size = "unknown"
                else:
                    # If filesystem came from JSON, set appropriate block size
                    if fs_type == "btrfs":
                        block_size = "default"
                    elif fs_type in ["ext4", "xfs"]:
                        block_size = data.get("block_size", "4k")
                    else:
                        block_size = data.get("block_size", "default")

                is_dev = "dev" in filename

                # Use filesystem from JSON if available, otherwise use parsed value
                if "filesystem" not in data:
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

        # Extract actual performance data from results
        if "insert_performance" in result:
            insert_qps = result["insert_performance"].get("vectors_per_second", 0)
        else:
            insert_qps = 0
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
        if "insert_performance" in result:
            insert_qps = result["insert_performance"].get("vectors_per_second", 0)
        else:
            insert_qps = 0
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
    """Create a heatmap showing AVERAGE performance across all test iterations"""
    # Group data by configuration and version, collecting ALL values for averaging
    config_data = defaultdict(
        lambda: {
            "baseline": {"insert": [], "query": [], "count": 0},
            "dev": {"insert": [], "query": [], "count": 0},
        }
    )

    for result in results:
        fs = result.get("filesystem", "unknown")
        block_size = result.get("block_size", "default")
        config = f"{fs}-{block_size}"
        version = "dev" if result.get("is_dev", False) else "baseline"

        # Get actual insert performance
        if "insert_performance" in result:
            insert_qps = result["insert_performance"].get("vectors_per_second", 0)
        else:
            insert_qps = 0

        # Calculate average query QPS
        query_qps = 0
        if "query_performance" in result:
            qp = result["query_performance"]
            total_qps = 0
            count = 0
            for topk_key in ["topk_1", "topk_10", "topk_100"]:
                if topk_key in qp:
                    for batch_key in ["batch_1", "batch_10", "batch_100"]:
                        if batch_key in qp[topk_key]:
                            total_qps += qp[topk_key][batch_key].get(
                                "queries_per_second", 0
                            )
                            count += 1
            if count > 0:
                query_qps = total_qps / count

        # Collect all values for averaging
        config_data[config][version]["insert"].append(insert_qps)
        config_data[config][version]["query"].append(query_qps)
        config_data[config][version]["count"] += 1

    # Sort configurations
    configs = sorted(config_data.keys())

    # Calculate averages for heatmap
    insert_baseline = []
    insert_dev = []
    query_baseline = []
    query_dev = []
    iteration_counts = {"baseline": 0, "dev": 0}

    for c in configs:
        # Calculate average insert QPS
        baseline_insert_vals = config_data[c]["baseline"]["insert"]
        insert_baseline.append(
            np.mean(baseline_insert_vals) if baseline_insert_vals else 0
        )

        dev_insert_vals = config_data[c]["dev"]["insert"]
        insert_dev.append(np.mean(dev_insert_vals) if dev_insert_vals else 0)

        # Calculate average query QPS
        baseline_query_vals = config_data[c]["baseline"]["query"]
        query_baseline.append(
            np.mean(baseline_query_vals) if baseline_query_vals else 0
        )

        dev_query_vals = config_data[c]["dev"]["query"]
        query_dev.append(np.mean(dev_query_vals) if dev_query_vals else 0)

        # Track iteration counts
        iteration_counts["baseline"] = max(
            iteration_counts["baseline"], len(baseline_insert_vals)
        )
        iteration_counts["dev"] = max(iteration_counts["dev"], len(dev_insert_vals))

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
    ax1.set_title(
        f"Insert Performance - AVERAGE across {iteration_counts['baseline']} iterations\n(1M vectors, 128 dims, HNSW index)"
    )
    ax1.set_ylabel("Configuration")

    # Add text annotations with dynamic color based on background
    # Get the colormap to determine actual colors
    cmap1 = plt.cm.YlOrRd
    norm1 = plt.Normalize(vmin=insert_data.min(), vmax=insert_data.max())

    for i in range(len(configs)):
        for j in range(2):
            # Get the actual color from the colormap
            val = insert_data[i, j]
            rgba = cmap1(norm1(val))
            # Calculate luminance using standard formula
            # Perceived luminance: 0.299*R + 0.587*G + 0.114*B
            luminance = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
            # Use white text on dark backgrounds (low luminance)
            text_color = "white" if luminance < 0.5 else "black"

            # Show average value with indicator
            text = ax1.text(
                j,
                i,
                f"{int(insert_data[i, j])}\n(avg)",
                ha="center",
                va="center",
                color=text_color,
                fontweight="bold",
                fontsize=9,
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
    ax2.set_title(
        f"Query Performance - AVERAGE across {iteration_counts['dev']} iterations\n(1M vectors, 128 dims, HNSW index)"
    )

    # Add text annotations with dynamic color based on background
    # Get the colormap to determine actual colors
    cmap2 = plt.cm.YlGnBu
    norm2 = plt.Normalize(vmin=query_data.min(), vmax=query_data.max())

    for i in range(len(configs)):
        for j in range(2):
            # Get the actual color from the colormap
            val = query_data[i, j]
            rgba = cmap2(norm2(val))
            # Calculate luminance using standard formula
            # Perceived luminance: 0.299*R + 0.587*G + 0.114*B
            luminance = 0.299 * rgba[0] + 0.587 * rgba[1] + 0.114 * rgba[2]
            # Use white text on dark backgrounds (low luminance)
            text_color = "white" if luminance < 0.5 else "black"

            # Show average value with indicator
            text = ax2.text(
                j,
                i,
                f"{int(query_data[i, j])}\n(avg)",
                ha="center",
                va="center",
                color=text_color,
                fontweight="bold",
                fontsize=9,
            )

    # Add colorbar
    cbar2 = plt.colorbar(im2, ax=ax2)
    cbar2.set_label("Query QPS")

    # Add overall figure title
    fig.suptitle(
        "Performance Heatmap - Showing AVERAGES across Multiple Test Iterations",
        fontsize=14,
        fontweight="bold",
        y=1.02,
    )

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "performance_heatmap.png"),
        dpi=150,
        bbox_inches="tight",
    )
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

        # Calculate average query QPS from all test configurations
        query_qps = 0
        if "query_performance" in result:
            qp = result["query_performance"]
            total_qps = 0
            count = 0
            for topk_key in ["topk_1", "topk_10", "topk_100"]:
                if topk_key in qp:
                    for batch_key in ["batch_1", "batch_10", "batch_100"]:
                        if batch_key in qp[topk_key]:
                            total_qps += qp[topk_key][batch_key].get(
                                "queries_per_second", 0
                            )
                            count += 1
            if count > 0:
                query_qps = total_qps / count

        if result.get("is_dev", False):
            if "insert_performance" in result:
                fs_types[fs]["dev_insert"][idx] = result["insert_performance"].get(
                    "vectors_per_second", 0
                )
            fs_types[fs]["dev_query"][idx] = query_qps
        else:
            if "insert_performance" in result:
                fs_types[fs]["baseline_insert"][idx] = result["insert_performance"].get(
                    "vectors_per_second", 0
                )
            fs_types[fs]["baseline_query"][idx] = query_qps

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


def create_simple_performance_trends(results, output_dir):
    """Create a simple performance trends chart for basic Milvus testing"""
    if not results:
        return

    # Extract configuration from first result for display
    config_text = ""
    if results:
        first_result = results[0]
        if "config" in first_result:
            cfg = first_result["config"]
            config_text = (
                f"Test Config:\n"
                f"• {cfg.get('vector_dataset_size', 'N/A'):,} vectors/iteration\n"
                f"• {cfg.get('vector_dimensions', 'N/A')} dimensions\n"
                f"• {cfg.get('index_type', 'N/A')} index"
            )

    # Separate baseline and dev results
    baseline_results = [r for r in results if not r.get("is_dev", False)]
    dev_results = [r for r in results if r.get("is_dev", False)]

    if not baseline_results and not dev_results:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))

    # Prepare data
    baseline_insert = []
    baseline_query = []
    dev_insert = []
    dev_query = []
    labels = []

    # Process baseline results
    for i, result in enumerate(baseline_results):
        if "insert_performance" in result:
            baseline_insert.append(
                result["insert_performance"].get("vectors_per_second", 0)
            )
        else:
            baseline_insert.append(0)

        # Calculate average query QPS
        query_qps = 0
        if "query_performance" in result:
            qp = result["query_performance"]
            total_qps = 0
            count = 0
            for topk_key in ["topk_1", "topk_10", "topk_100"]:
                if topk_key in qp:
                    for batch_key in ["batch_1", "batch_10", "batch_100"]:
                        if batch_key in qp[topk_key]:
                            total_qps += qp[topk_key][batch_key].get(
                                "queries_per_second", 0
                            )
                            count += 1
            if count > 0:
                query_qps = total_qps / count
        baseline_query.append(query_qps)
        labels.append(f"Iteration {i+1}")

    # Process dev results
    for result in dev_results:
        if "insert_performance" in result:
            dev_insert.append(result["insert_performance"].get("vectors_per_second", 0))
        else:
            dev_insert.append(0)

        query_qps = 0
        if "query_performance" in result:
            qp = result["query_performance"]
            total_qps = 0
            count = 0
            for topk_key in ["topk_1", "topk_10", "topk_100"]:
                if topk_key in qp:
                    for batch_key in ["batch_1", "batch_10", "batch_100"]:
                        if batch_key in qp[topk_key]:
                            total_qps += qp[topk_key][batch_key].get(
                                "queries_per_second", 0
                            )
                            count += 1
            if count > 0:
                query_qps = total_qps / count
        dev_query.append(query_qps)

    x = range(len(baseline_results) if baseline_results else len(dev_results))

    # Insert performance - with visible markers for all points
    if baseline_insert:
        # Line plot with smaller markers
        ax1.plot(
            x,
            baseline_insert,
            "-",
            label="Baseline",
            linewidth=1.5,
            color="blue",
            alpha=0.6,
        )
        # Add distinct markers for each point
        ax1.scatter(
            x,
            baseline_insert,
            s=30,
            color="blue",
            alpha=0.8,
            edgecolors="darkblue",
            linewidth=0.5,
            zorder=5,
        )
    if dev_insert:
        # Line plot with smaller markers
        ax1.plot(
            x[: len(dev_insert)],
            dev_insert,
            "-",
            label="Development",
            linewidth=1.5,
            color="red",
            alpha=0.6,
        )
        # Add distinct markers for each point
        ax1.scatter(
            x[: len(dev_insert)],
            dev_insert,
            s=30,
            color="red",
            alpha=0.8,
            edgecolors="darkred",
            linewidth=0.5,
            marker="s",
            zorder=5,
        )
    ax1.set_xlabel("Test Iteration (same configuration, repeated for reliability)")
    ax1.set_ylabel("Insert QPS (vectors/second)")
    ax1.set_title("Milvus Insert Performance")

    # Handle x-axis labels to prevent overlap
    num_points = len(x)
    if num_points > 20:
        # Show every 5th label for many iterations
        step = 5
        tick_positions = list(range(0, num_points, step))
        tick_labels = [
            labels[i] if labels else f"Iteration {i+1}" for i in tick_positions
        ]
        ax1.set_xticks(tick_positions)
        ax1.set_xticklabels(tick_labels, rotation=45, ha="right")
    elif num_points > 10:
        # Show every 2nd label for moderate iterations
        step = 2
        tick_positions = list(range(0, num_points, step))
        tick_labels = [
            labels[i] if labels else f"Iteration {i+1}" for i in tick_positions
        ]
        ax1.set_xticks(tick_positions)
        ax1.set_xticklabels(tick_labels, rotation=45, ha="right")
    else:
        # Show all labels for few iterations
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels if labels else [f"Iteration {i+1}" for i in x])

    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Add configuration text box - compact
    if config_text:
        ax1.text(
            0.02,
            0.98,
            config_text,
            transform=ax1.transAxes,
            fontsize=6,
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="wheat", alpha=0.85),
        )

    # Query performance - with visible markers for all points
    if baseline_query:
        # Line plot
        ax2.plot(
            x,
            baseline_query,
            "-",
            label="Baseline",
            linewidth=1.5,
            color="blue",
            alpha=0.6,
        )
        # Add distinct markers for each point
        ax2.scatter(
            x,
            baseline_query,
            s=30,
            color="blue",
            alpha=0.8,
            edgecolors="darkblue",
            linewidth=0.5,
            zorder=5,
        )
    if dev_query:
        # Line plot
        ax2.plot(
            x[: len(dev_query)],
            dev_query,
            "-",
            label="Development",
            linewidth=1.5,
            color="red",
            alpha=0.6,
        )
        # Add distinct markers for each point
        ax2.scatter(
            x[: len(dev_query)],
            dev_query,
            s=30,
            color="red",
            alpha=0.8,
            edgecolors="darkred",
            linewidth=0.5,
            marker="s",
            zorder=5,
        )
    ax2.set_xlabel("Test Iteration (same configuration, repeated for reliability)")
    ax2.set_ylabel("Query QPS (queries/second)")
    ax2.set_title("Milvus Query Performance")

    # Handle x-axis labels to prevent overlap
    num_points = len(x)
    if num_points > 20:
        # Show every 5th label for many iterations
        step = 5
        tick_positions = list(range(0, num_points, step))
        tick_labels = [
            labels[i] if labels else f"Iteration {i+1}" for i in tick_positions
        ]
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, rotation=45, ha="right")
    elif num_points > 10:
        # Show every 2nd label for moderate iterations
        step = 2
        tick_positions = list(range(0, num_points, step))
        tick_labels = [
            labels[i] if labels else f"Iteration {i+1}" for i in tick_positions
        ]
        ax2.set_xticks(tick_positions)
        ax2.set_xticklabels(tick_labels, rotation=45, ha="right")
    else:
        # Show all labels for few iterations
        ax2.set_xticks(x)
        ax2.set_xticklabels(labels if labels else [f"Iteration {i+1}" for i in x])

    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Add configuration text box - compact
    if config_text:
        ax2.text(
            0.02,
            0.98,
            config_text,
            transform=ax2.transAxes,
            fontsize=6,
            verticalalignment="top",
            bbox=dict(boxstyle="round,pad=0.3", facecolor="wheat", alpha=0.85),
        )

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "performance_trends.png"), dpi=150)
    plt.close()


def generate_summary_statistics(results, output_dir):
    """Generate summary statistics and save to JSON"""
    # Get unique filesystems, excluding "unknown"
    filesystems = set()
    for r in results:
        fs = r.get("filesystem", "unknown")
        if fs != "unknown":
            filesystems.add(fs)

    summary = {
        "total_tests": len(results),
        "filesystems_tested": sorted(list(filesystems)),
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

        # Get actual performance metrics
        if "insert_performance" in result:
            insert_qps = result["insert_performance"].get("vectors_per_second", 0)
        else:
            insert_qps = 0

        # Calculate average query QPS
        query_qps = 0
        if "query_performance" in result:
            qp = result["query_performance"]
            total_qps = 0
            count = 0
            for topk_key in ["topk_1", "topk_10", "topk_100"]:
                if topk_key in qp:
                    for batch_key in ["batch_1", "batch_10", "batch_100"]:
                        if batch_key in qp[topk_key]:
                            total_qps += qp[topk_key][batch_key].get(
                                "queries_per_second", 0
                            )
                            count += 1
            if count > 0:
                query_qps = total_qps / count

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


def create_comprehensive_fs_comparison(results, output_dir):
    """Create comprehensive filesystem performance comparison including all configurations"""
    import matplotlib.pyplot as plt
    import numpy as np
    from collections import defaultdict

    # Collect data for all filesystem configurations
    config_data = defaultdict(lambda: {"baseline": [], "dev": []})

    for result in results:
        fs = result.get("filesystem", "unknown")
        block_size = result.get("block_size", "")

        # Create configuration label
        if block_size and block_size != "default":
            config_label = f"{fs}-{block_size}"
        else:
            config_label = fs

        category = "dev" if result.get("is_dev", False) else "baseline"

        # Extract performance metrics
        if "insert_performance" in result:
            insert_qps = result["insert_performance"].get("vectors_per_second", 0)
        else:
            insert_qps = 0

        config_data[config_label][category].append(insert_qps)

    # Sort configurations for consistent display
    configs = sorted(config_data.keys())

    # Calculate means and standard deviations
    baseline_means = []
    baseline_stds = []
    dev_means = []
    dev_stds = []

    for config in configs:
        baseline_vals = config_data[config]["baseline"]
        dev_vals = config_data[config]["dev"]

        baseline_means.append(np.mean(baseline_vals) if baseline_vals else 0)
        baseline_stds.append(np.std(baseline_vals) if baseline_vals else 0)
        dev_means.append(np.mean(dev_vals) if dev_vals else 0)
        dev_stds.append(np.std(dev_vals) if dev_vals else 0)

    # Create the plot
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

    x = np.arange(len(configs))
    width = 0.35

    # Top plot: Absolute performance
    baseline_bars = ax1.bar(
        x - width / 2,
        baseline_means,
        width,
        yerr=baseline_stds,
        label="Baseline",
        color="#1f77b4",
        capsize=5,
    )
    dev_bars = ax1.bar(
        x + width / 2,
        dev_means,
        width,
        yerr=dev_stds,
        label="Development",
        color="#ff7f0e",
        capsize=5,
    )

    ax1.set_ylabel("Insert QPS")
    ax1.set_title("Vector Database Performance Across Filesystem Configurations")
    ax1.set_xticks(x)
    ax1.set_xticklabels(configs, rotation=45, ha="right")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Add value labels on bars
    for bars in [baseline_bars, dev_bars]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax1.annotate(
                    f"{height:.0f}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    # Bottom plot: Percentage improvement (dev vs baseline)
    improvements = []
    for i in range(len(configs)):
        if baseline_means[i] > 0:
            improvement = ((dev_means[i] - baseline_means[i]) / baseline_means[i]) * 100
        else:
            improvement = 0
        improvements.append(improvement)

    colors = ["green" if x > 0 else "red" for x in improvements]
    improvement_bars = ax2.bar(x, improvements, color=colors, alpha=0.7)

    ax2.set_ylabel("Performance Change (%)")
    ax2.set_title("Development vs Baseline Performance Change")
    ax2.set_xticks(x)
    ax2.set_xticklabels(configs, rotation=45, ha="right")
    ax2.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
    ax2.grid(True, alpha=0.3)

    # Add percentage labels
    for bar, val in zip(improvement_bars, improvements):
        ax2.annotate(
            f"{val:.1f}%",
            xy=(bar.get_x() + bar.get_width() / 2, val),
            xytext=(0, 3 if val > 0 else -15),
            textcoords="offset points",
            ha="center",
            va="bottom" if val > 0 else "top",
            fontsize=8,
        )

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "comprehensive_fs_comparison.png"), dpi=150)
    plt.close()


def create_fs_latency_comparison(results, output_dir):
    """Create latency comparison across filesystems"""
    import matplotlib.pyplot as plt
    import numpy as np
    from collections import defaultdict

    # Collect latency data
    config_latency = defaultdict(lambda: {"baseline": [], "dev": []})

    for result in results:
        fs = result.get("filesystem", "unknown")
        block_size = result.get("block_size", "")

        if block_size and block_size != "default":
            config_label = f"{fs}-{block_size}"
        else:
            config_label = fs

        category = "dev" if result.get("is_dev", False) else "baseline"

        # Extract latency metrics
        if "query_performance" in result:
            latency_p99 = result["query_performance"].get("latency_p99_ms", 0)
        else:
            latency_p99 = 0

        if latency_p99 > 0:
            config_latency[config_label][category].append(latency_p99)

    if not config_latency:
        return

    # Sort configurations
    configs = sorted(config_latency.keys())

    # Calculate statistics
    baseline_p99 = []
    dev_p99 = []

    for config in configs:
        baseline_vals = config_latency[config]["baseline"]
        dev_vals = config_latency[config]["dev"]

        baseline_p99.append(np.mean(baseline_vals) if baseline_vals else 0)
        dev_p99.append(np.mean(dev_vals) if dev_vals else 0)

    # Create plot
    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(configs))
    width = 0.35

    baseline_bars = ax.bar(
        x - width / 2, baseline_p99, width, label="Baseline P99", color="#9467bd"
    )
    dev_bars = ax.bar(
        x + width / 2, dev_p99, width, label="Development P99", color="#e377c2"
    )

    ax.set_xlabel("Filesystem Configuration")
    ax.set_ylabel("Latency P99 (ms)")
    ax.set_title("Query Latency (P99) Comparison Across Filesystems")
    ax.set_xticks(x)
    ax.set_xticklabels(configs, rotation=45, ha="right")
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add value labels
    for bars in [baseline_bars, dev_bars]:
        for bar in bars:
            height = bar.get_height()
            if height > 0:
                ax.annotate(
                    f"{height:.1f}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "filesystem_latency_comparison.png"), dpi=150)
    plt.close()


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
    print("Generating performance heatmap...")
    create_heatmap_analysis(results, output_dir)

    print("Generating performance trends...")
    create_simple_performance_trends(results, output_dir)

    print("Generating summary statistics...")
    summary = generate_summary_statistics(results, output_dir)

    # Check if we have multiple filesystems to compare
    filesystems = set(r.get("filesystem", "unknown") for r in results)
    if len(filesystems) > 1:
        print("Generating filesystem comparison chart...")
        create_filesystem_comparison_chart(results, output_dir)

        print("Generating comprehensive filesystem comparison...")
        create_comprehensive_fs_comparison(results, output_dir)

        print("Generating filesystem latency comparison...")
        create_fs_latency_comparison(results, output_dir)

        # Check if we have XFS results with different block sizes
        xfs_results = [r for r in results if r.get("filesystem") == "xfs"]
        block_sizes = set(r.get("block_size", "unknown") for r in xfs_results)
        if len(block_sizes) > 1:
            print("Generating XFS block size analysis...")
            create_block_size_analysis(results, output_dir)

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

#!/usr/bin/env python3
"""
Generate advanced graphs using matplotlib and seaborn if available
Falls back to simple visualizations if libraries are not installed
"""

import json
import os
import glob
from datetime import datetime

try:
    import matplotlib

    matplotlib.use("Agg")  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import seaborn as sns
    import pandas as pd
    import numpy as np

    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("Advanced plotting libraries not available.")
    print("Install with: pip install matplotlib seaborn pandas numpy")
    print("Falling back to simple visualizations...")


def generate_matplotlib_graphs(results_data):
    """Generate publication-quality graphs using matplotlib/seaborn"""

    if not PLOTTING_AVAILABLE:
        return

    # Set style
    plt.style.use("seaborn-v0_8-darkgrid")
    sns.set_palette("husl")

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 12))

    # Extract data from latest result
    latest_result = list(results_data.values())[0] if results_data else {}
    config = latest_result.get("config", {})
    insert_perf = latest_result.get("insert_performance", {})
    query_configs = latest_result.get("query_performance", {}).get("configurations", [])

    # Title
    fig.suptitle(
        f'AI Benchmark Results - {config.get("dataset_size", "N/A")} Vectors',
        fontsize=16,
    )

    # 1. Insert Performance Timeline
    ax1 = plt.subplot(2, 2, 1)
    if insert_perf.get("batches"):
        batch_times = [b["time"] for b in insert_perf["batches"]]
        batch_nums = [b["batch"] for b in insert_perf["batches"]]
        ax1.plot(batch_nums, batch_times, "o-", linewidth=2, markersize=8)
        ax1.set_xlabel("Batch Number")
        ax1.set_ylabel("Time (seconds)")
        ax1.set_title("Insert Performance by Batch")
        ax1.grid(True, alpha=0.3)

    # 2. Query Latency Comparison
    ax2 = plt.subplot(2, 2, 2)
    if query_configs:
        labels = [f"Batch {c['batch_size']}\nTop-{c['top_k']}" for c in query_configs]
        latencies = [c["avg_latency_ms"] for c in query_configs]
        colors = sns.color_palette("viridis", len(labels))
        bars = ax2.bar(labels, latencies, color=colors)
        ax2.set_ylabel("Latency (ms)")
        ax2.set_title("Average Query Latency by Configuration")

        # Add value labels on bars
        for bar, lat in zip(bars, latencies):
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{lat:.1f}",
                ha="center",
                va="bottom",
            )

    # 3. Throughput Analysis
    ax3 = plt.subplot(2, 2, 3)
    if query_configs:
        throughputs = [c["queries_per_second"] for c in query_configs]
        bars = ax3.bar(labels, throughputs, color=colors)
        ax3.set_ylabel("Queries per Second")
        ax3.set_title("Query Throughput by Configuration")

        # Add value labels
        for bar, qps in zip(bars, throughputs):
            height = bar.get_height()
            ax3.text(
                bar.get_x() + bar.get_width() / 2.0,
                height,
                f"{qps:.0f}",
                ha="center",
                va="bottom",
            )

    # 4. Latency Distribution Heatmap
    ax4 = plt.subplot(2, 2, 4)
    if query_configs:
        # Create heatmap data
        metrics = ["avg", "p50", "p95", "p99"]
        heatmap_data = []
        for cfg in query_configs:
            row = [
                cfg["avg_latency_ms"],
                cfg["p50_latency_ms"],
                cfg["p95_latency_ms"],
                cfg["p99_latency_ms"],
            ]
            heatmap_data.append(row)

        im = ax4.imshow(heatmap_data, cmap="YlOrRd", aspect="auto")
        ax4.set_xticks(range(len(metrics)))
        ax4.set_xticklabels(metrics)
        ax4.set_yticks(range(len(labels)))
        ax4.set_yticklabels(labels)
        ax4.set_title("Latency Percentiles Heatmap")

        # Add colorbar
        cbar = plt.colorbar(im, ax=ax4)
        cbar.set_label("Latency (ms)")

        # Add text annotations
        for i in range(len(labels)):
            for j in range(len(metrics)):
                text = ax4.text(
                    j,
                    i,
                    f"{heatmap_data[i][j]:.1f}",
                    ha="center",
                    va="center",
                    color="black",
                )

    plt.tight_layout()

    # Save the figure
    output_file = os.path.join("results", "benchmark_graphs.png")
    plt.savefig(output_file, dpi=300, bbox_inches="tight")
    print(f"📊 High-quality graphs saved to: {output_file}")
    plt.close()

    # Generate additional specialized plots
    generate_performance_trends(results_data)
    generate_comparison_radar(query_configs)


def generate_performance_trends(results_data):
    """Generate performance trend analysis"""

    if not PLOTTING_AVAILABLE:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Simulated multi-run data for demonstration
    runs = list(range(1, len(results_data) + 1))
    insert_rates = []
    avg_latencies = []

    for data in results_data.values():
        insert_perf = data.get("insert_performance", {})
        insert_rates.append(insert_perf.get("vectors_per_second", 0))

        query_configs = data.get("query_performance", {}).get("configurations", [])
        if query_configs:
            avg_latencies.append(query_configs[0].get("avg_latency_ms", 0))
        else:
            avg_latencies.append(0)

    # Insert rate trend
    ax1.plot(runs, insert_rates, "o-", linewidth=2, markersize=10, color="#2ecc71")
    ax1.fill_between(runs, insert_rates, alpha=0.3, color="#2ecc71")
    ax1.set_xlabel("Run Number")
    ax1.set_ylabel("Vectors per Second")
    ax1.set_title("Insert Performance Trend")
    ax1.grid(True, alpha=0.3)

    # Query latency trend
    ax2.plot(runs, avg_latencies, "o-", linewidth=2, markersize=10, color="#e74c3c")
    ax2.fill_between(runs, avg_latencies, alpha=0.3, color="#e74c3c")
    ax2.set_xlabel("Run Number")
    ax2.set_ylabel("Average Latency (ms)")
    ax2.set_title("Query Latency Trend")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(
        os.path.join("results", "performance_trends.png"), dpi=300, bbox_inches="tight"
    )
    print("📈 Performance trends saved to: results/performance_trends.png")
    plt.close()


def generate_comparison_radar(query_configs):
    """Generate radar chart for multi-dimensional comparison"""

    if not PLOTTING_AVAILABLE or not query_configs:
        return

    # Prepare data for radar chart
    categories = ["Avg Latency", "P50 Latency", "P95 Latency", "P99 Latency", "QPS/100"]

    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection="polar"))

    # Number of variables
    num_vars = len(categories)
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    categories += categories[:1]
    angles += angles[:1]

    # Plot data for each configuration
    colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12"]

    for i, cfg in enumerate(query_configs[:4]):  # Limit to 4 configs for clarity
        values = [
            10 - cfg["avg_latency_ms"],  # Invert so higher is better
            10 - cfg["p50_latency_ms"],
            10 - cfg["p95_latency_ms"],
            10 - cfg["p99_latency_ms"],
            cfg["queries_per_second"] / 100,
        ]
        values += values[:1]

        label = f"Batch {cfg['batch_size']}, Top-{cfg['top_k']}"
        ax.plot(
            angles,
            values,
            "o-",
            linewidth=2,
            label=label,
            color=colors[i % len(colors)],
        )
        ax.fill(angles, values, alpha=0.25, color=colors[i % len(colors)])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(categories[:-1])
    ax.set_ylim(0, 10)
    ax.set_title("Query Performance Comparison\n(Higher values are better)", y=1.08)
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    ax.grid(True)

    plt.tight_layout()
    plt.savefig(
        os.path.join("results", "performance_radar.png"), dpi=300, bbox_inches="tight"
    )
    print("🎯 Performance radar chart saved to: results/performance_radar.png")
    plt.close()


def main():
    """Generate graphs from benchmark results"""

    results_dir = "results"

    # Find all result files
    patterns = ["results_*.json", "benchmark_results_*.json"]
    result_files = []
    for pattern in patterns:
        result_files.extend(glob.glob(os.path.join(results_dir, pattern)))

    if not result_files:
        print("No result files found")
        return

    # Load results
    results_data = {}
    for result_file in sorted(result_files):
        with open(result_file, "r") as f:
            results_data[result_file] = json.load(f)

    # Generate graphs
    if PLOTTING_AVAILABLE:
        print("🎨 Generating advanced graphs with matplotlib/seaborn...")
        generate_matplotlib_graphs(results_data)
    else:
        print("\n💡 To generate advanced graphs, install required libraries:")
        print("   pip install matplotlib seaborn pandas numpy")
        print("\nFor now, use the HTML graphs by opening:")
        print("   workflows/ai/results/benchmark_graphs.html")

    print("\n✅ Graph generation complete!")


if __name__ == "__main__":
    main()

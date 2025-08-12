#!/usr/bin/env python3
"""
Generate visualization graphs for mmtests comparison results.

This script parses mmtests comparison output and creates informative graphs
that help understand performance differences between baseline and dev kernels.
"""

import sys
import re
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path

# Set matplotlib to use Agg backend for headless operation
import matplotlib

matplotlib.use("Agg")


def parse_comparison_file(filepath):
    """Parse mmtests comparison text file and extract data."""
    data = {
        "fault_base": {"threads": [], "baseline": [], "dev": [], "improvement": []},
        "fault_huge": {"threads": [], "baseline": [], "dev": [], "improvement": []},
        "fault_both": {"threads": [], "baseline": [], "dev": [], "improvement": []},
    }

    with open(filepath, "r") as f:
        for line in f:
            # Parse lines like: Min       fault-base-1       742.00 (   0.00%)     1228.00 ( -65.50%)
            match = re.match(
                r"(\w+)\s+fault-(\w+)-(\d+)\s+(\d+\.\d+)\s+\([^)]+\)\s+(\d+\.\d+)\s+\(\s*([+-]?\d+\.\d+)%\)",
                line.strip(),
            )
            if match:
                metric, fault_type, threads, baseline, dev, improvement = match.groups()

                # Focus on Amean (arithmetic mean) as it's most representative
                if metric == "Amean" and fault_type in ["base", "huge", "both"]:
                    key = f"fault_{fault_type}"
                    data[key]["threads"].append(int(threads))
                    data[key]["baseline"].append(float(baseline))
                    data[key]["dev"].append(float(dev))
                    data[key]["improvement"].append(float(improvement))

    return data


def create_performance_comparison_graph(data, output_dir):
    """Create a comprehensive performance comparison graph."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(
        "mmtests thpcompact: Baseline vs Dev Kernel Performance",
        fontsize=16,
        fontweight="bold",
    )

    colors = {"fault_base": "#1f77b4", "fault_huge": "#ff7f0e", "fault_both": "#2ca02c"}
    labels = {
        "fault_base": "Base Pages",
        "fault_huge": "Huge Pages",
        "fault_both": "Both Pages",
    }

    # Plot 1: Raw performance comparison
    for fault_type in ["fault_base", "fault_huge", "fault_both"]:
        if data[fault_type]["threads"]:
            threads = np.array(data[fault_type]["threads"])
            baseline = np.array(data[fault_type]["baseline"])
            dev = np.array(data[fault_type]["dev"])

            ax1.plot(
                threads,
                baseline,
                "o-",
                color=colors[fault_type],
                alpha=0.7,
                label=f"{labels[fault_type]} - Baseline",
                linewidth=2,
            )
            ax1.plot(
                threads,
                dev,
                "s--",
                color=colors[fault_type],
                alpha=0.9,
                label=f"{labels[fault_type]} - Dev",
                linewidth=2,
            )

    ax1.set_xlabel("Number of Threads")
    ax1.set_ylabel("Fault Time (microseconds)")
    ax1.set_title("Raw Performance: Lower is Better")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale("log")  # Log scale for better visibility of differences

    # Plot 2: Performance improvement percentage
    for fault_type in ["fault_base", "fault_huge", "fault_both"]:
        if data[fault_type]["threads"]:
            threads = np.array(data[fault_type]["threads"])
            improvement = np.array(data[fault_type]["improvement"])

            ax2.plot(
                threads,
                improvement,
                "o-",
                color=colors[fault_type],
                label=labels[fault_type],
                linewidth=2,
                markersize=6,
            )

    ax2.axhline(y=0, color="black", linestyle="-", alpha=0.5)
    ax2.fill_between(
        ax2.get_xlim(), 0, 100, alpha=0.1, color="green", label="Improvement"
    )
    ax2.fill_between(
        ax2.get_xlim(), -100, 0, alpha=0.1, color="red", label="Regression"
    )
    ax2.set_xlabel("Number of Threads")
    ax2.set_ylabel("Performance Change (%)")
    ax2.set_title("Performance Change: Positive = Better Dev Kernel")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: Scalability comparison (normalized to single thread)
    for fault_type in ["fault_base", "fault_huge"]:  # Skip 'both' to reduce clutter
        if data[fault_type]["threads"] and len(data[fault_type]["threads"]) > 1:
            threads = np.array(data[fault_type]["threads"])
            baseline = np.array(data[fault_type]["baseline"])
            dev = np.array(data[fault_type]["dev"])

            # Normalize to single thread performance
            baseline_norm = baseline / baseline[0] if baseline[0] > 0 else baseline
            dev_norm = dev / dev[0] if dev[0] > 0 else dev

            ax3.plot(
                threads,
                baseline_norm,
                "o-",
                color=colors[fault_type],
                alpha=0.7,
                label=f"{labels[fault_type]} - Baseline",
                linewidth=2,
            )
            ax3.plot(
                threads,
                dev_norm,
                "s--",
                color=colors[fault_type],
                alpha=0.9,
                label=f"{labels[fault_type]} - Dev",
                linewidth=2,
            )

    ax3.set_xlabel("Number of Threads")
    ax3.set_ylabel("Relative Performance (vs 1 thread)")
    ax3.set_title("Scalability: How Performance Changes with Thread Count")
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Plot 4: Summary statistics
    summary_data = []
    categories = []

    for fault_type in ["fault_base", "fault_huge", "fault_both"]:
        if data[fault_type]["improvement"]:
            improvements = np.array(data[fault_type]["improvement"])
            avg_improvement = np.mean(improvements)
            summary_data.append(avg_improvement)
            categories.append(labels[fault_type])

    bars = ax4.bar(
        categories,
        summary_data,
        color=[
            colors[f'fault_{k.lower().replace(" ", "_")}']
            for k in ["base", "huge", "both"]
        ][: len(categories)],
    )
    ax4.axhline(y=0, color="black", linestyle="-", alpha=0.5)
    ax4.set_ylabel("Average Performance Change (%)")
    ax4.set_title("Overall Performance Summary")
    ax4.grid(True, alpha=0.3, axis="y")

    # Add value labels on bars
    for bar, value in zip(bars, summary_data):
        height = bar.get_height()
        ax4.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + (1 if height >= 0 else -3),
            f"{value:.1f}%",
            ha="center",
            va="bottom" if height >= 0 else "top",
        )

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "performance_comparison.png"),
        dpi=150,
        bbox_inches="tight",
    )
    plt.close()


def create_detailed_thread_analysis(data, output_dir):
    """Create detailed analysis for different thread counts."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle("Thread Scaling Analysis", fontsize=14, fontweight="bold")

    colors = {"fault_base": "#1f77b4", "fault_huge": "#ff7f0e"}
    labels = {"fault_base": "Base Pages", "fault_huge": "Huge Pages"}

    # Plot thread efficiency (performance per thread)
    for fault_type in ["fault_base", "fault_huge"]:
        if data[fault_type]["threads"]:
            threads = np.array(data[fault_type]["threads"])
            baseline = np.array(data[fault_type]["baseline"])
            dev = np.array(data[fault_type]["dev"])

            # Calculate efficiency (lower time per operation = better efficiency)
            baseline_eff = baseline / threads  # Time per thread
            dev_eff = dev / threads

            ax1.plot(
                threads,
                baseline_eff,
                "o-",
                color=colors[fault_type],
                alpha=0.7,
                label=f"{labels[fault_type]} - Baseline",
                linewidth=2,
            )
            ax1.plot(
                threads,
                dev_eff,
                "s--",
                color=colors[fault_type],
                alpha=0.9,
                label=f"{labels[fault_type]} - Dev",
                linewidth=2,
            )

    ax1.set_xlabel("Number of Threads")
    ax1.set_ylabel("Time per Thread (microseconds)")
    ax1.set_title("Threading Efficiency: Lower is Better")
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_yscale("log")

    # Plot improvement by thread count
    thread_counts = set()
    for fault_type in ["fault_base", "fault_huge"]:
        thread_counts.update(data[fault_type]["threads"])

    thread_counts = sorted(list(thread_counts))

    base_improvements = []
    huge_improvements = []

    for tc in thread_counts:
        base_imp = None
        huge_imp = None

        for i, t in enumerate(data["fault_base"]["threads"]):
            if t == tc:
                base_imp = data["fault_base"]["improvement"][i]
                break

        for i, t in enumerate(data["fault_huge"]["threads"]):
            if t == tc:
                huge_imp = data["fault_huge"]["improvement"][i]
                break

        base_improvements.append(base_imp if base_imp is not None else 0)
        huge_improvements.append(huge_imp if huge_imp is not None else 0)

    x = np.arange(len(thread_counts))
    width = 0.35

    bars1 = ax2.bar(
        x - width / 2,
        base_improvements,
        width,
        label="Base Pages",
        color=colors["fault_base"],
        alpha=0.8,
    )
    bars2 = ax2.bar(
        x + width / 2,
        huge_improvements,
        width,
        label="Huge Pages",
        color=colors["fault_huge"],
        alpha=0.8,
    )

    ax2.set_xlabel("Thread Count")
    ax2.set_ylabel("Performance Improvement (%)")
    ax2.set_title("Improvement by Thread Count")
    ax2.set_xticks(x)
    ax2.set_xticklabels(thread_counts)
    ax2.legend()
    ax2.grid(True, alpha=0.3, axis="y")
    ax2.axhline(y=0, color="black", linestyle="-", alpha=0.5)

    # Add value labels on bars
    for bars in [bars1, bars2]:
        for bar in bars:
            height = bar.get_height()
            if abs(height) > 0.1:  # Only show labels for non-zero values
                ax2.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height + (1 if height >= 0 else -3),
                    f"{height:.1f}%",
                    ha="center",
                    va="bottom" if height >= 0 else "top",
                    fontsize=8,
                )

    plt.tight_layout()
    plt.savefig(
        os.path.join(output_dir, "thread_analysis.png"), dpi=150, bbox_inches="tight"
    )
    plt.close()


def generate_graphs_html(output_dir, baseline_kernel, dev_kernel):
    """Generate an HTML file with explanations and embedded graphs."""
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>mmtests Performance Analysis: {baseline_kernel} vs {dev_kernel}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }}
        .summary {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        .graph {{
            text-align: center;
            margin: 30px 0;
        }}
        .graph img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .explanation {{
            background: #fff;
            padding: 15px;
            border-left: 4px solid #2ecc71;
            margin: 15px 0;
        }}
        .warning {{
            background: #ffeaa7;
            border-left: 4px solid #fdcb6e;
            padding: 15px;
            margin: 15px 0;
        }}
        .good {{
            background: #d5f4e6;
            border-left: 4px solid #2ecc71;
        }}
        .bad {{
            background: #ffeaea;
            border-left: 4px solid #e74c3c;
        }}
        .metric {{
            font-family: monospace;
            background: #ecf0f1;
            padding: 2px 6px;
            border-radius: 3px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>mmtests thpcompact Performance Analysis</h1>
        <h2>Kernel Comparison: {baseline_kernel} vs {dev_kernel}</h2>

        <div class="summary">
            <h3>🎯 What is thpcompact testing?</h3>
            <p><strong>thpcompact</strong> is a memory management benchmark that tests how well the kernel handles:</p>
            <ul>
                <li><strong>Base Pages (4KB)</strong>: Standard memory pages</li>
                <li><strong>Huge Pages (2MB)</strong>: Large memory pages that reduce TLB misses</li>
                <li><strong>Memory Compaction</strong>: Kernel's ability to defragment memory</li>
                <li><strong>Thread Scaling</strong>: Performance under different levels of parallelism</li>
            </ul>
            <p><strong>Lower numbers are better</strong> - they represent faster memory allocation times.</p>
        </div>

        <h2>📊 Performance Overview</h2>
        <div class="graph">
            <img src="performance_comparison.png" alt="Performance Comparison">
        </div>

        <div class="explanation">
            <h3>Understanding the Performance Graphs:</h3>
            <ul>
                <li><strong>Top Left</strong>: Raw performance comparison. Lower lines = faster kernel.</li>
                <li><strong>Top Right</strong>: Performance changes. Green area = dev kernel improved, red = regressed.</li>
                <li><strong>Bottom Left</strong>: Scalability. Shows how performance changes with more threads.</li>
                <li><strong>Bottom Right</strong>: Overall summary of improvements/regressions.</li>
            </ul>
        </div>

        <h2>🧵 Thread Scaling Analysis</h2>
        <div class="graph">
            <img src="thread_analysis.png" alt="Thread Analysis">
        </div>

        <div class="explanation">
            <h3>Thread Scaling Insights:</h3>
            <ul>
                <li><strong>Left Graph</strong>: Threading efficiency - how well work is distributed across threads</li>
                <li><strong>Right Graph</strong>: Performance improvement at each thread count</li>
                <li>Good scaling means the kernel can efficiently use multiple CPUs for memory operations</li>
            </ul>
        </div>

        <h2>🔍 What These Results Mean</h2>

        <div class="explanation good">
            <h3>✅ Positive Performance Changes</h3>
            <p>When you see <strong>positive percentages</strong> in the comparison:</p>
            <ul>
                <li>The dev kernel is <em>faster</em> at memory allocation</li>
                <li>Applications will experience reduced memory latency</li>
                <li>Better overall system responsiveness</li>
            </ul>
        </div>

        <div class="explanation bad">
            <h3>❌ Negative Performance Changes</h3>
            <p>When you see <strong>negative percentages</strong>:</p>
            <ul>
                <li>The dev kernel is <em>slower</em> at memory allocation</li>
                <li>This might indicate a regression that needs investigation</li>
                <li>Consider the trade-offs - sometimes slower allocation enables other benefits</li>
            </ul>
        </div>

        <div class="warning">
            <h3>⚠️ Important Notes</h3>
            <ul>
                <li><strong>Variability is normal</strong>: Performance can vary significantly across different thread counts</li>
                <li><strong>Context matters</strong>: A regression in one area might be acceptable if it enables improvements elsewhere</li>
                <li><strong>Real-world impact</strong>: The significance depends on your workload's memory access patterns</li>
            </ul>
        </div>

        <h2>📈 Key Metrics Explained</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Description</th>
                <th>What it Means</th>
            </tr>
            <tr>
                <td><span class="metric">fault-base</span></td>
                <td>Standard 4KB page fault handling</td>
                <td>How quickly the kernel can allocate regular memory pages</td>
            </tr>
            <tr>
                <td><span class="metric">fault-huge</span></td>
                <td>2MB huge page fault handling</td>
                <td>Performance of large page allocations (important for databases, HPC)</td>
            </tr>
            <tr>
                <td><span class="metric">fault-both</span></td>
                <td>Mixed workload simulation</td>
                <td>Real-world scenario with both page sizes</td>
            </tr>
            <tr>
                <td><span class="metric">Thread Count</span></td>
                <td>Number of parallel threads</td>
                <td>Tests scalability across multiple CPU cores</td>
            </tr>
        </table>

        <h2>🎯 Bottom Line</h2>
        <div class="summary">
            <p>This analysis helps you understand:</p>
            <ul>
                <li>Whether your kernel changes improved or regressed memory performance</li>
                <li>How well your changes scale across multiple CPU cores</li>
                <li>Which types of memory allocations are affected</li>
                <li>The magnitude of performance changes in real-world scenarios</li>
            </ul>
            <p><strong>Use this data to make informed decisions about kernel optimizations and to identify areas needing further investigation.</strong></p>
        </div>

        <hr style="margin: 40px 0;">
        <p style="text-align: center; color: #7f8c8d; font-size: 0.9em;">
            Generated by kdevops mmtests analysis •
            Baseline: {baseline_kernel} • Dev: {dev_kernel}
        </p>
    </div>
</body>
</html>"""

    with open(os.path.join(output_dir, "graphs.html"), "w") as f:
        f.write(html_content)


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python3 generate_mmtests_graphs.py <comparison.txt> <output_dir> <baseline_kernel>-<dev_kernel>"
        )
        sys.exit(1)

    comparison_file = sys.argv[1]
    output_dir = sys.argv[2]
    kernel_names = sys.argv[3].split("-", 1)

    if len(kernel_names) != 2:
        print("Kernel names should be in format: baseline-dev")
        sys.exit(1)

    baseline_kernel, dev_kernel = kernel_names

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Parse the comparison data
    print(f"Parsing comparison data from {comparison_file}...")
    data = parse_comparison_file(comparison_file)

    # Generate graphs
    print("Generating performance comparison graphs...")
    create_performance_comparison_graph(data, output_dir)

    print("Generating thread analysis graphs...")
    create_detailed_thread_analysis(data, output_dir)

    # Generate HTML report
    print("Generating HTML report...")
    generate_graphs_html(output_dir, baseline_kernel, dev_kernel)

    print(
        f"✅ Analysis complete! Open {output_dir}/graphs.html in your browser to view results."
    )


if __name__ == "__main__":
    main()

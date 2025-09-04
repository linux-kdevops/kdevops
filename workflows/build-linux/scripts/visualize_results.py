#!/usr/bin/env python3
"""
Visualize build results with matplotlib graphs and generate HTML reports.
"""

import json
import sys
import argparse
from pathlib import Path
import statistics
from datetime import datetime
import base64
from io import BytesIO

# Try to import matplotlib, but make it optional
try:
    import matplotlib

    matplotlib.use("Agg")  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import numpy as np

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available. Install with your package manager:")
    print("  Debian/Ubuntu: sudo apt-get install python3-matplotlib python3-numpy")
    print("  RHEL/Fedora: sudo dnf install python3-matplotlib python3-numpy")
    print("  SUSE: sudo zypper install python3-matplotlib python3-numpy")


def load_all_results(results_dir):
    """Load all timing and summary data from the results directory."""
    results_path = Path(results_dir)

    # Load summary files
    summaries = {}
    for summary_file in results_path.glob("*_summary_*.json"):
        with open(summary_file, "r") as f:
            data = json.load(f)
            hostname = data["hostname"]
            summaries[hostname] = data

    # Load timing files
    timings = {}
    for timing_file in results_path.glob("*_build_times_*.json"):
        with open(timing_file, "r") as f:
            data = json.load(f)
            # Extract hostname from filename
            hostname = timing_file.stem.split("_build_times_")[-1]
            timings[hostname] = data

    return summaries, timings


def create_build_time_comparison_chart(summaries):
    """Create a bar chart comparing average build times across hosts."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    hosts = list(summaries.keys())
    avg_times = [summaries[h]["statistics"]["average"] for h in hosts]
    min_times = [summaries[h]["statistics"]["min"] for h in hosts]
    max_times = [summaries[h]["statistics"]["max"] for h in hosts]

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(hosts))
    width = 0.35

    # Create bars with error bars showing min/max
    bars = ax.bar(x, avg_times, width, label="Average", color="steelblue")

    # Add error bars for min/max with very low alpha for better visibility of numbers
    errors = [
        [avg_times[i] - min_times[i] for i in range(len(hosts))],
        [max_times[i] - avg_times[i] for i in range(len(hosts))],
    ]
    ax.errorbar(
        x,
        avg_times,
        yerr=errors,
        fmt="none",
        color="black",
        capsize=5,
        alpha=0.3,
        linewidth=1,
    )

    ax.set_xlabel("Host / Filesystem Configuration")
    ax.set_ylabel("Build Time (seconds)")
    ax.set_title("Linux Kernel Build Times Across Different Filesystem Configurations")
    ax.set_xticks(x)
    ax.set_xticklabels(
        [h.replace("lpc-build-linux-", "") for h in hosts], rotation=45, ha="right"
    )
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add value labels on bars with slight offset to avoid overlap with error bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height + 1,  # Added small offset
            f"{height:.1f}s",
            ha="center",
            va="bottom",
            fontweight="bold",
            fontsize=10,
        )

    plt.tight_layout()

    # Convert to base64 for embedding in HTML
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    return image_base64


def create_build_time_distribution(timings):
    """Create box plots showing distribution of build times."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    fig, ax = plt.subplots(figsize=(12, 6))

    hosts = list(timings.keys())
    data = []
    labels = []

    for host in hosts:
        durations = [entry["duration"] for entry in timings[host] if entry["success"]]
        if durations:
            data.append(durations)
            labels.append(host.replace("lpc-build-linux-", ""))

    if not data:
        return None

    bp = ax.boxplot(data, labels=labels, patch_artist=True)

    # Color the boxes
    colors = plt.cm.Set3(np.linspace(0, 1, len(data)))
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)

    ax.set_xlabel("Host / Filesystem Configuration")
    ax.set_ylabel("Build Time (seconds)")
    ax.set_title("Build Time Distribution (20 iterations per configuration)")
    ax.grid(True, alpha=0.3, axis="y")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()

    # Convert to base64
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    return image_base64


def create_build_timeline(timings):
    """Create a timeline showing build durations over iterations."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    fig, ax = plt.subplots(figsize=(14, 8))

    colors = plt.cm.tab10(np.linspace(0, 1, len(timings)))

    for idx, (host, timing_data) in enumerate(timings.items()):
        iterations = [entry["iteration"] for entry in timing_data]
        durations = [entry["duration"] for entry in timing_data]

        ax.plot(
            iterations,
            durations,
            marker="o",
            label=host.replace("lpc-build-linux-", ""),
            alpha=0.7,
            linewidth=2,
            markersize=6,
            color=colors[idx],
        )

    ax.set_xlabel("Build Iteration")
    ax.set_ylabel("Build Time (seconds)")
    ax.set_title("Build Time Progression Over Iterations")
    ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Convert to base64
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    return image_base64


def create_success_rate_chart(summaries):
    """Create a chart showing success rates."""
    if not MATPLOTLIB_AVAILABLE:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))

    hosts = list(summaries.keys())
    success_rates = []

    for host in hosts:
        total = summaries[host]["total_builds"]
        successful = summaries[host]["successful_builds"]
        success_rates.append((successful / total) * 100 if total > 0 else 0)

    colors = [
        "green" if rate == 100 else "orange" if rate >= 95 else "red"
        for rate in success_rates
    ]

    bars = ax.bar(range(len(hosts)), success_rates, color=colors, alpha=0.7)

    ax.set_xlabel("Host / Filesystem Configuration")
    ax.set_ylabel("Success Rate (%)")
    ax.set_title("Build Success Rates")
    ax.set_xticks(range(len(hosts)))
    ax.set_xticklabels(
        [h.replace("lpc-build-linux-", "") for h in hosts], rotation=45, ha="right"
    )
    ax.set_ylim(0, 105)
    ax.grid(True, alpha=0.3, axis="y")

    # Add value labels on bars
    for i, (bar, rate) in enumerate(zip(bars, success_rates)):
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            height,
            f"{rate:.1f}%",
            ha="center",
            va="bottom",
        )

    plt.tight_layout()

    # Convert to base64
    buffer = BytesIO()
    plt.savefig(buffer, format="png", dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    return image_base64


def generate_html_report(results_dir, summaries, timings):
    """Generate an HTML report with embedded graphs."""

    # Generate graphs
    comparison_chart = create_build_time_comparison_chart(summaries)
    distribution_chart = create_build_time_distribution(timings)
    timeline_chart = create_build_timeline(timings)
    success_chart = create_success_rate_chart(summaries)

    # Calculate overall statistics
    total_builds = sum(s["total_builds"] for s in summaries.values())
    successful_builds = sum(s["successful_builds"] for s in summaries.values())
    failed_builds = sum(s["failed_builds"] for s in summaries.values())
    total_time_hours = sum(s["statistics"]["total_hours"] for s in summaries.values())

    # Get all durations for overall statistics
    all_durations = []
    for timing_data in timings.values():
        all_durations.extend(
            [entry["duration"] for entry in timing_data if entry["success"]]
        )

    if all_durations:
        overall_avg = statistics.mean(all_durations)
        overall_median = statistics.median(all_durations)
        overall_stdev = statistics.stdev(all_durations) if len(all_durations) > 1 else 0
        overall_min = min(all_durations)
        overall_max = max(all_durations)
    else:
        overall_avg = overall_median = overall_stdev = overall_min = overall_max = 0

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Linux Kernel Build Performance Report</title>
    <meta charset="utf-8">
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            padding: 30px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #2d3748;
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }}
        .timestamp {{
            text-align: center;
            color: #718096;
            margin-bottom: 30px;
            font-size: 0.9em;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 12px rgba(0,0,0,0.2);
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }}
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .chart-container {{
            margin: 40px 0;
            padding: 20px;
            background: #f7fafc;
            border-radius: 10px;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.06);
        }}
        .chart-title {{
            font-size: 1.3em;
            color: #2d3748;
            margin-bottom: 20px;
            text-align: center;
            font-weight: 600;
        }}
        .chart {{
            text-align: center;
            margin: 20px 0;
        }}
        .chart img {{
            max-width: 100%;
            border-radius: 5px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #e2e8f0;
        }}
        tr:hover {{
            background: #f7fafc;
        }}
        tr:last-child td {{
            border-bottom: none;
        }}
        .success {{
            color: #48bb78;
            font-weight: bold;
        }}
        .failure {{
            color: #f56565;
            font-weight: bold;
        }}
        .section {{
            margin: 40px 0;
        }}
        .section-title {{
            font-size: 1.8em;
            color: #2d3748;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        .no-data {{
            text-align: center;
            padding: 40px;
            color: #718096;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Linux Kernel Build Performance Report</h1>
        <div class="timestamp">Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        
        <div class="summary-grid">
            <div class="stat-card">
                <div class="stat-label">Total Builds</div>
                <div class="stat-value">{total_builds}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Success Rate</div>
                <div class="stat-value">{(successful_builds/total_builds*100):.1f}%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Time</div>
                <div class="stat-value">{total_time_hours:.1f}h</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Average Build</div>
                <div class="stat-value">{overall_avg:.1f}s</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Configurations</div>
                <div class="stat-value">{len(summaries)}</div>
            </div>
        </div>
        
        <div class="section">
            <h2 class="section-title">📊 Build Time Comparison</h2>
            {"<div class='chart-container'><div class='chart'><img src='data:image/png;base64," + comparison_chart + "' /></div></div>" if comparison_chart else "<div class='no-data'>Graph generation requires matplotlib</div>"}
        </div>
        
        <div class="section">
            <h2 class="section-title">📈 Build Time Distribution</h2>
            {"<div class='chart-container'><div class='chart'><img src='data:image/png;base64," + distribution_chart + "' /></div></div>" if distribution_chart else "<div class='no-data'>Graph generation requires matplotlib</div>"}
        </div>
        
        <div class="section">
            <h2 class="section-title">📉 Build Time Timeline</h2>
            {"<div class='chart-container'><div class='chart'><img src='data:image/png;base64," + timeline_chart + "' /></div></div>" if timeline_chart else "<div class='no-data'>Graph generation requires matplotlib</div>"}
        </div>
        
        <div class="section">
            <h2 class="section-title">✅ Success Rates</h2>
            {"<div class='chart-container'><div class='chart'><img src='data:image/png;base64," + success_chart + "' /></div></div>" if success_chart else "<div class='no-data'>Graph generation requires matplotlib</div>"}
        </div>
        
        <div class="section">
            <h2 class="section-title">📋 Detailed Results by Host</h2>
            <table>
                <thead>
                    <tr>
                        <th>Host/Configuration</th>
                        <th>Filesystem</th>
                        <th>Total Builds</th>
                        <th>Successful</th>
                        <th>Failed</th>
                        <th>Success Rate</th>
                        <th>Average (s)</th>
                        <th>Median (s)</th>
                        <th>Min (s)</th>
                        <th>Max (s)</th>
                        <th>Std Dev (s)</th>
                    </tr>
                </thead>
                <tbody>
"""

    for hostname in sorted(summaries.keys()):
        data = summaries[hostname]
        stats = data["statistics"]
        success_rate = (
            (data["successful_builds"] / data["total_builds"] * 100)
            if data["total_builds"] > 0
            else 0
        )

        # Extract filesystem type from hostname
        if "xfs" in hostname:
            if "16k" in hostname:
                fs_type = "XFS (16k blocks)"
            elif "32k" in hostname:
                fs_type = "XFS (32k blocks)"
            elif "64k" in hostname:
                fs_type = "XFS (64k blocks)"
            else:
                fs_type = "XFS (4k blocks)"
        elif "ext4" in hostname:
            fs_type = "EXT4"
        elif "btrfs" in hostname:
            fs_type = "Btrfs"
        else:
            fs_type = "Unknown"

        html_content += f"""
                    <tr>
                        <td><strong>{hostname.replace('lpc-build-linux-', '')}</strong></td>
                        <td>{fs_type}</td>
                        <td>{data['total_builds']}</td>
                        <td class="success">{data['successful_builds']}</td>
                        <td class="{'failure' if data['failed_builds'] > 0 else ''}">{data['failed_builds']}</td>
                        <td>{success_rate:.1f}%</td>
                        <td>{stats['average']:.2f}</td>
                        <td>{stats['median']:.2f}</td>
                        <td>{stats['min']:.2f}</td>
                        <td>{stats['max']:.2f}</td>
                        <td>{stats['stddev']:.2f}</td>
                    </tr>
"""

    html_content += f"""
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2 class="section-title">📊 Overall Statistics</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>Value</th>
                </tr>
                <tr>
                    <td>Overall Average Build Time</td>
                    <td>{overall_avg:.2f} seconds</td>
                </tr>
                <tr>
                    <td>Overall Median Build Time</td>
                    <td>{overall_median:.2f} seconds</td>
                </tr>
                <tr>
                    <td>Overall Standard Deviation</td>
                    <td>{overall_stdev:.2f} seconds</td>
                </tr>
                <tr>
                    <td>Fastest Build</td>
                    <td>{overall_min:.2f} seconds</td>
                </tr>
                <tr>
                    <td>Slowest Build</td>
                    <td>{overall_max:.2f} seconds</td>
                </tr>
                <tr>
                    <td>Total CPU Time</td>
                    <td>{total_time_hours:.2f} hours</td>
                </tr>
            </table>
        </div>
    </div>
</body>
</html>"""

    # Save HTML report
    report_path = Path(results_dir) / "build_performance_report.html"
    with open(report_path, "w") as f:
        f.write(html_content)

    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="Visualize build results with graphs and HTML reports"
    )
    parser.add_argument("results_dir", help="Directory containing result files")
    parser.add_argument("--no-html", action="store_true", help="Skip HTML generation")
    args = parser.parse_args()

    results_dir = Path(args.results_dir)
    if not results_dir.exists():
        print(f"Error: Results directory '{results_dir}' does not exist")
        return 1

    # Load data
    print("Loading results...")
    summaries, timings = load_all_results(results_dir)

    if not summaries:
        print("No summary files found in the results directory")
        return 1

    print(f"Found {len(summaries)} host configurations")
    print(f"Found {len(timings)} timing datasets")

    if not args.no_html:
        print("Generating HTML report...")
        report_path = generate_html_report(results_dir, summaries, timings)
        print(f"✅ HTML report generated: {report_path}")
        print(f"   Open in browser: file://{report_path.absolute()}")

    # Print summary to console
    print("\n" + "=" * 60)
    print("Build Performance Summary")
    print("=" * 60)

    for hostname in sorted(summaries.keys()):
        data = summaries[hostname]
        print(f"\n{hostname}:")
        print(f"  Successful: {data['successful_builds']}/{data['total_builds']}")
        print(f"  Average: {data['statistics']['average']:.2f}s")
        print(
            f"  Min/Max: {data['statistics']['min']:.2f}s / {data['statistics']['max']:.2f}s"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())

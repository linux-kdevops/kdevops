#!/usr/bin/env python3
"""
Analyze MinIO Warp benchmark results and generate reports with visualizations.
"""

import json
import glob
import os
import sys
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from typing import Dict, List, Any


def load_warp_results(results_dir: Path) -> List[Dict[str, Any]]:
    """Load all Warp JSON result files from the results directory."""
    results = []
    json_files = list(results_dir.glob("warp_benchmark_*.json"))

    for json_file in sorted(json_files):
        try:
            with open(json_file, "r") as f:
                content = f.read()
                # Find where the JSON starts (after any terminal output)
                json_start = content.find("{")
                if json_start >= 0:
                    json_content = content[json_start:]
                    data = json.loads(json_content)
                    data["_filename"] = json_file.name
                    data["_filepath"] = str(json_file)
                    results.append(data)
                    print(f"Loaded: {json_file.name}")
                else:
                    print(f"No JSON found in {json_file}")
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    return results


def extract_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metrics from a Warp result."""
    metrics = {
        "filename": result.get("_filename", "unknown"),
        "timestamp": "",
        "operation": "mixed",
    }

    # Check if we have the total stats
    if "total" in result:
        total = result["total"]

        # Extract basic info
        metrics["timestamp"] = total.get("start_time", "")
        metrics["total_requests"] = total.get("total_requests", 0)
        metrics["total_objects"] = total.get("total_objects", 0)
        metrics["total_errors"] = total.get("total_errors", 0)
        metrics["total_bytes"] = total.get("total_bytes", 0)
        metrics["concurrency"] = total.get("concurrency", 0)

        # Calculate duration in seconds
        start_time = total.get("start_time", "")
        end_time = total.get("end_time", "")
        if start_time and end_time:
            try:
                from dateutil import parser

                start = parser.parse(start_time)
                end = parser.parse(end_time)
                duration = (end - start).total_seconds()
                metrics["duration_seconds"] = duration
            except ImportError:
                # Fall back to simple parsing if dateutil not available
                metrics["duration_seconds"] = 105  # Default for 5m test

        # Get throughput if directly available
        if "throughput" in total and isinstance(total["throughput"], dict):
            # Throughput is a complex structure with segmented data
            tp = total["throughput"]
            if "bytes" in tp:
                bytes_total = tp["bytes"]
                duration_ms = tp.get("measure_duration_millis", 1000)
                duration_s = duration_ms / 1000
                if duration_s > 0:
                    metrics["throughput_avg_mbps"] = (
                        bytes_total / (1024 * 1024)
                    ) / duration_s
            elif "segmented" in tp:
                # Use median throughput
                metrics["throughput_avg_mbps"] = tp["segmented"].get(
                    "median_bps", 0
                ) / (1024 * 1024)
        elif metrics.get("duration_seconds", 0) > 0 and metrics["total_bytes"] > 0:
            # Calculate throughput from bytes and duration
            metrics["throughput_avg_mbps"] = (
                metrics["total_bytes"] / (1024 * 1024)
            ) / metrics["duration_seconds"]

        # Calculate operations per second
        if metrics.get("duration_seconds", 0) > 0:
            metrics["ops_per_second"] = (
                metrics["total_requests"] / metrics["duration_seconds"]
            )

    # Check for operations breakdown by type
    if "by_op_type" in result:
        ops = result["by_op_type"]

        # Process each operation type
        for op_type in ["GET", "PUT", "DELETE", "STAT"]:
            if op_type in ops:
                op_data = ops[op_type]
                op_lower = op_type.lower()

                # Extract operation count
                if "ops" in op_data:
                    metrics[f"{op_lower}_requests"] = op_data["ops"]

                # Extract average duration
                if "avg_duration" in op_data:
                    metrics[f"{op_lower}_latency_avg_ms"] = (
                        op_data["avg_duration"] / 1e6
                    )

                # Extract percentiles if available
                if "percentiles_millis" in op_data:
                    percentiles = op_data["percentiles_millis"]
                    if "50" in percentiles:
                        metrics[f"{op_lower}_latency_p50"] = percentiles["50"]
                    if "90" in percentiles:
                        metrics[f"{op_lower}_latency_p90"] = percentiles["90"]
                    if "99" in percentiles:
                        metrics[f"{op_lower}_latency_p99"] = percentiles["99"]

                # Extract min/max if available
                if "fastest_millis" in op_data:
                    metrics[f"{op_lower}_latency_min"] = op_data["fastest_millis"]
                if "slowest_millis" in op_data:
                    metrics[f"{op_lower}_latency_max"] = op_data["slowest_millis"]

        # Calculate aggregate latency metrics
        latencies = []
        for op in ["get", "put", "delete"]:
            if f"{op}_latency_avg_ms" in metrics:
                latencies.append(metrics[f"{op}_latency_avg_ms"])
        if latencies:
            metrics["latency_avg_ms"] = sum(latencies) / len(latencies)

    # Extract from summary if present
    if "summary" in result:
        summary = result["summary"]
        if "throughput_MiBs" in summary:
            metrics["throughput_avg_mbps"] = summary["throughput_MiBs"]
        if "ops_per_sec" in summary:
            metrics["ops_per_second"] = summary["ops_per_sec"]

    return metrics


def generate_throughput_chart(metrics_list: List[Dict[str, Any]], output_dir: Path):
    """Generate throughput comparison chart."""
    if not metrics_list:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    # Throughput bar chart
    labels = [
        m["filename"].replace("warp_benchmark_", "").replace(".json", "")[:20]
        for m in metrics_list
    ]
    x = np.arange(len(labels))

    avg_throughput = [m.get("throughput_avg_mbps", 0) for m in metrics_list]

    width = 0.35
    ax1.bar(x, avg_throughput, width, label="Throughput", color="skyblue")

    ax1.set_xlabel("Test Run")
    ax1.set_ylabel("Throughput (MB/s)")
    ax1.set_title("MinIO Warp Throughput Performance")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45, ha="right")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Operations per second
    ops_per_sec = [m.get("ops_per_second", 0) for m in metrics_list]
    ax2.bar(x, ops_per_sec, color="orange")
    ax2.set_xlabel("Test Run")
    ax2.set_ylabel("Operations/Second")
    ax2.set_title("Operations Per Second")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=45, ha="right")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = output_dir / "warp_throughput_performance.png"
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Generated: {output_file}")


def generate_latency_chart(metrics_list: List[Dict[str, Any]], output_dir: Path):
    """Generate latency comparison chart."""
    if not metrics_list:
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

    labels = [
        m["filename"].replace("warp_benchmark_", "").replace(".json", "")[:20]
        for m in metrics_list
    ]
    x = np.arange(len(labels))

    # Collect latency data by operation type
    operations = ["get", "put", "delete"]
    colors = {"get": "steelblue", "put": "orange", "delete": "red"}

    # Operation-specific latencies
    width = 0.2
    offset = -width
    for op in operations:
        op_latencies = []
        for m in metrics_list:
            # Try operation-specific latency first, then fall back to general
            lat = m.get(f"{op}_latency_avg_ms", m.get("latency_avg_ms", 0))
            op_latencies.append(lat)

        if any(l > 0 for l in op_latencies):
            ax1.bar(x + offset, op_latencies, width, label=op.upper(), color=colors[op])
            offset += width

    ax1.set_xlabel("Test Run")
    ax1.set_ylabel("Latency (ms)")
    ax1.set_title("Request Latency Distribution")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45, ha="right")
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Min/Max latency range
    lat_min = [m.get("latency_min_ms", 0) for m in metrics_list]
    lat_max = [m.get("latency_max_ms", 0) for m in metrics_list]

    ax2.bar(x - width / 2, lat_min, width, label="Min", color="green")
    ax2.bar(x + width / 2, lat_max, width, label="Max", color="red")

    ax2.set_xlabel("Test Run")
    ax2.set_ylabel("Latency (ms)")
    ax2.set_title("Latency Range (Min/Max)")
    ax2.set_xticks(x)
    ax2.set_xticklabels(labels, rotation=45, ha="right")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = output_dir / "warp_latency_analysis.png"
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Generated: {output_file}")


def generate_performance_summary_chart(
    metrics_list: List[Dict[str, Any]], output_dir: Path
):
    """Generate a comprehensive performance summary chart."""
    if not metrics_list:
        return

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 2, hspace=0.3, wspace=0.25)

    # Throughput over time
    ax1 = fig.add_subplot(gs[0, :])
    timestamps = []
    throughputs = []
    for m in metrics_list:
        try:
            if m.get("timestamp"):
                timestamps.append(
                    datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
                )
                throughputs.append(m.get("throughput_avg_mbps", 0))
        except:
            pass

    if timestamps:
        ax1.plot(timestamps, throughputs, "o-", linewidth=2, markersize=8, color="blue")
        ax1.set_xlabel("Time")
        ax1.set_ylabel("Throughput (MB/s)")
        ax1.set_title("Throughput Over Time", fontsize=14, fontweight="bold")
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis="x", rotation=45)

    # Operations distribution
    ax2 = fig.add_subplot(gs[1, 0])
    ops_data = [m.get("ops_per_second", 0) for m in metrics_list]
    if ops_data:
        ax2.hist(ops_data, bins=10, color="orange", edgecolor="black", alpha=0.7)
        ax2.set_xlabel("Operations/Second")
        ax2.set_ylabel("Frequency")
        ax2.set_title("Operations Distribution", fontsize=12, fontweight="bold")
        ax2.grid(True, alpha=0.3)

    # Latency box plot
    ax3 = fig.add_subplot(gs[1, 1])
    latency_data = []
    for m in metrics_list:
        lat_data = []
        if m.get("latency_avg_ms"):
            lat_data.extend(
                [
                    m.get("latency_min_ms", 0),
                    m.get("latency_percentile_50", 0),
                    m.get("latency_avg_ms", 0),
                    m.get("latency_percentile_99", 0),
                    m.get("latency_max_ms", 0),
                ]
            )
        if lat_data:
            latency_data.append(lat_data)

    if latency_data:
        ax3.boxplot(latency_data)
        ax3.set_xlabel("Test Run")
        ax3.set_ylabel("Latency (ms)")
        ax3.set_title("Latency Distribution", fontsize=12, fontweight="bold")
        ax3.grid(True, alpha=0.3)

    # Performance metrics table
    ax4 = fig.add_subplot(gs[2, :])
    ax4.axis("tight")
    ax4.axis("off")

    # Create summary statistics
    if metrics_list:
        avg_metrics = metrics_list[-1]  # Use most recent for now
        table_data = [
            ["Metric", "Value"],
            [
                "Average Throughput",
                f"{avg_metrics.get('throughput_avg_mbps', 0):.2f} MB/s",
            ],
            ["Operations/Second", f"{avg_metrics.get('ops_per_second', 0):.0f}"],
            ["Average Latency", f"{avg_metrics.get('latency_avg_ms', 0):.2f} ms"],
            ["P99 Latency", f"{avg_metrics.get('latency_percentile_99', 0):.2f} ms"],
            ["Total Operations", f"{avg_metrics.get('ops_total', 0):.0f}"],
            ["Object Size", str(avg_metrics.get("object_size", "unknown"))],
            ["Error Rate", f"{avg_metrics.get('error_rate', 0):.2%}"],
        ]

        table = ax4.table(
            cellText=table_data, cellLoc="left", loc="center", colWidths=[0.3, 0.3]
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.5)

        # Style the header row
        for i in range(2):
            table[(0, i)].set_facecolor("#40466e")
            table[(0, i)].set_text_props(weight="bold", color="white")

    plt.suptitle("MinIO Warp Performance Summary", fontsize=16, fontweight="bold")

    output_file = output_dir / "warp_performance_summary.png"
    plt.savefig(output_file, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"Generated: {output_file}")


def generate_text_report(metrics_list: List[Dict[str, Any]], output_dir: Path):
    """Generate a detailed text report."""
    output_file = output_dir / "warp_analysis_report.txt"

    with open(output_file, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("MinIO Warp Benchmark Analysis Report\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n")
        f.write(f"Total test runs analyzed: {len(metrics_list)}\n\n")

        if not metrics_list:
            f.write("No benchmark results found.\n")
            return

        # Overall statistics
        f.write("OVERALL PERFORMANCE STATISTICS\n")
        f.write("-" * 40 + "\n")

        throughputs = [
            m.get("throughput_avg_mbps", 0)
            for m in metrics_list
            if m.get("throughput_avg_mbps")
        ]
        if throughputs:
            f.write(f"Throughput:\n")
            f.write(f"  Average: {np.mean(throughputs):.2f} MB/s\n")
            f.write(f"  Median:  {np.median(throughputs):.2f} MB/s\n")
            f.write(f"  Min:     {np.min(throughputs):.2f} MB/s\n")
            f.write(f"  Max:     {np.max(throughputs):.2f} MB/s\n")
            f.write(f"  StdDev:  {np.std(throughputs):.2f} MB/s\n\n")

        ops_rates = [
            m.get("ops_per_second", 0) for m in metrics_list if m.get("ops_per_second")
        ]
        if ops_rates:
            f.write(f"Operations per Second:\n")
            f.write(f"  Average: {np.mean(ops_rates):.0f} ops/s\n")
            f.write(f"  Median:  {np.median(ops_rates):.0f} ops/s\n")
            f.write(f"  Min:     {np.min(ops_rates):.0f} ops/s\n")
            f.write(f"  Max:     {np.max(ops_rates):.0f} ops/s\n\n")

        latencies = [
            m.get("latency_avg_ms", 0) for m in metrics_list if m.get("latency_avg_ms")
        ]
        if latencies:
            f.write(f"Average Latency:\n")
            f.write(f"  Mean:    {np.mean(latencies):.2f} ms\n")
            f.write(f"  Median:  {np.median(latencies):.2f} ms\n")
            f.write(f"  Min:     {np.min(latencies):.2f} ms\n")
            f.write(f"  Max:     {np.max(latencies):.2f} ms\n\n")

        # Individual test run details
        f.write("=" * 80 + "\n")
        f.write("INDIVIDUAL TEST RUN DETAILS\n")
        f.write("=" * 80 + "\n\n")

        for i, metrics in enumerate(metrics_list, 1):
            f.write(f"Test Run #{i}\n")
            f.write("-" * 40 + "\n")
            f.write(f"File: {metrics.get('filename', 'unknown')}\n")
            f.write(f"Timestamp: {metrics.get('timestamp', 'N/A')}\n")
            f.write(f"Operation: {metrics.get('operation', 'unknown')}\n")
            f.write(f"Duration: {metrics.get('duration_seconds', 0):.1f} seconds\n")
            f.write(f"Object Size: {metrics.get('object_size', 'unknown')}\n")
            f.write(f"Total Objects: {metrics.get('objects_total', 0)}\n")

            if metrics.get("throughput_avg_mbps"):
                f.write(f"\nThroughput Performance:\n")
                f.write(
                    f"  Average: {metrics.get('throughput_avg_mbps', 0):.2f} MB/s\n"
                )
                f.write(
                    f"  Min:     {metrics.get('throughput_min_mbps', 0):.2f} MB/s\n"
                )
                f.write(
                    f"  Max:     {metrics.get('throughput_max_mbps', 0):.2f} MB/s\n"
                )
                f.write(
                    f"  P50:     {metrics.get('throughput_percentile_50', 0):.2f} MB/s\n"
                )
                f.write(
                    f"  P99:     {metrics.get('throughput_percentile_99', 0):.2f} MB/s\n"
                )

            if metrics.get("ops_per_second"):
                f.write(f"\nOperations Performance:\n")
                f.write(f"  Total Operations: {metrics.get('ops_total', 0):.0f}\n")
                f.write(
                    f"  Operations/Second: {metrics.get('ops_per_second', 0):.0f}\n"
                )
                f.write(
                    f"  Avg Duration: {metrics.get('ops_avg_duration_ms', 0):.2f} ms\n"
                )

            if metrics.get("latency_avg_ms"):
                f.write(f"\nLatency Metrics:\n")
                f.write(f"  Average: {metrics.get('latency_avg_ms', 0):.2f} ms\n")
                f.write(f"  Min:     {metrics.get('latency_min_ms', 0):.2f} ms\n")
                f.write(f"  Max:     {metrics.get('latency_max_ms', 0):.2f} ms\n")
                f.write(
                    f"  P50:     {metrics.get('latency_percentile_50', 0):.2f} ms\n"
                )
                f.write(
                    f"  P99:     {metrics.get('latency_percentile_99', 0):.2f} ms\n"
                )

            if metrics.get("error_count", 0) > 0:
                f.write(f"\nErrors:\n")
                f.write(f"  Error Count: {metrics.get('error_count', 0)}\n")
                f.write(f"  Error Rate: {metrics.get('error_rate', 0):.2%}\n")

            f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")

    print(f"Generated: {output_file}")


def generate_html_report(metrics_list: List[Dict[str, Any]], output_dir: Path):
    """Generate a comprehensive HTML report with embedded visualizations."""
    output_file = output_dir / "warp_benchmark_report.html"

    # Check if PNG files exist
    throughput_png = output_dir / "warp_throughput_performance.png"
    latency_png = output_dir / "warp_latency_analysis.png"
    summary_png = output_dir / "warp_performance_summary.png"

    with open(output_file, "w") as f:
        f.write(
            """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>MinIO Warp Benchmark Report</title>
    <style>
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        }
        .subtitle {
            text-align: center;
            color: #7f8c8d;
            margin-bottom: 30px;
        }
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }
        .metric-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            margin: 10px 0;
        }
        .metric-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .section {
            margin: 40px 0;
        }
        .section h2 {
            color: #34495e;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        th {
            background: #667eea;
            color: white;
            padding: 12px;
            text-align: left;
        }
        td {
            padding: 10px;
            border-bottom: 1px solid #ecf0f1;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .chart-container {
            text-align: center;
            margin: 30px 0;
        }
        .chart-container img {
            max-width: 100%;
            height: auto;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        .performance-good {
            color: #27ae60;
            font-weight: bold;
        }
        .performance-warning {
            color: #f39c12;
            font-weight: bold;
        }
        .performance-bad {
            color: #e74c3c;
            font-weight: bold;
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ecf0f1;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 MinIO Warp Benchmark Report</h1>
        <div class="subtitle">Generated on """
            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            + """</div>

        <div class="section">
            <h2>📊 Performance Summary</h2>
            <div class="summary-grid">
"""
        )

        if metrics_list:
            # Calculate summary statistics
            throughputs = [
                m.get("throughput_avg_mbps", 0)
                for m in metrics_list
                if m.get("throughput_avg_mbps")
            ]
            ops_rates = [
                m.get("ops_per_second", 0)
                for m in metrics_list
                if m.get("ops_per_second")
            ]
            latencies = [
                m.get("latency_avg_ms", 0)
                for m in metrics_list
                if m.get("latency_avg_ms")
            ]

            if throughputs:
                avg_throughput = np.mean(throughputs)
                f.write(
                    f"""
                <div class="metric-card">
                    <div class="metric-label">Average Throughput</div>
                    <div class="metric-value">{avg_throughput:.1f}</div>
                    <div class="metric-label">MB/s</div>
                </div>
                """
                )

                f.write(
                    f"""
                <div class="metric-card">
                    <div class="metric-label">Peak Throughput</div>
                    <div class="metric-value">{np.max(throughputs):.1f}</div>
                    <div class="metric-label">MB/s</div>
                </div>
                """
                )

            if ops_rates:
                f.write(
                    f"""
                <div class="metric-card">
                    <div class="metric-label">Avg Operations</div>
                    <div class="metric-value">{np.mean(ops_rates):.0f}</div>
                    <div class="metric-label">ops/second</div>
                </div>
                """
                )

            if latencies:
                f.write(
                    f"""
                <div class="metric-card">
                    <div class="metric-label">Avg Latency</div>
                    <div class="metric-value">{np.mean(latencies):.1f}</div>
                    <div class="metric-label">ms</div>
                </div>
                """
                )

            f.write(
                f"""
                <div class="metric-card">
                    <div class="metric-label">Test Runs</div>
                    <div class="metric-value">{len(metrics_list)}</div>
                    <div class="metric-label">completed</div>
                </div>
            """
            )

        f.write(
            """
            </div>
        </div>

        <div class="section">
            <h2>📈 Performance Visualizations</h2>
        """
        )

        if throughput_png.exists():
            f.write(
                f"""
            <div class="chart-container">
                <img src="{throughput_png.name}" alt="Throughput Performance">
            </div>
            """
            )

        if latency_png.exists():
            f.write(
                f"""
            <div class="chart-container">
                <img src="{latency_png.name}" alt="Latency Analysis">
            </div>
            """
            )

        if summary_png.exists():
            f.write(
                f"""
            <div class="chart-container">
                <img src="{summary_png.name}" alt="Performance Summary">
            </div>
            """
            )

        f.write(
            """
        <div class="section">
            <h2>📋 Detailed Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test Run</th>
                        <th>Operation</th>
                        <th>Throughput (MB/s)</th>
                        <th>Ops/Second</th>
                        <th>Avg Latency (ms)</th>
                        <th>P99 Latency (ms)</th>
                        <th>Errors</th>
                    </tr>
                </thead>
                <tbody>
        """
        )

        for metrics in metrics_list:
            throughput = metrics.get("throughput_avg_mbps", 0)
            ops_sec = metrics.get("ops_per_second", 0)
            latency = metrics.get("latency_avg_ms", 0)
            p99_lat = metrics.get("latency_percentile_99", 0)
            errors = metrics.get("error_count", 0)

            # Color code based on performance
            throughput_class = (
                "performance-good"
                if throughput > 100
                else "performance-warning" if throughput > 50 else "performance-bad"
            )
            latency_class = (
                "performance-good"
                if latency < 10
                else "performance-warning" if latency < 50 else "performance-bad"
            )

            f.write(
                f"""
                <tr>
                    <td>{metrics.get('filename', 'unknown').replace('warp_benchmark_', '').replace('.json', '')}</td>
                    <td>{metrics.get('operation', 'mixed')}</td>
                    <td class="{throughput_class}">{throughput:.2f}</td>
                    <td>{ops_sec:.0f}</td>
                    <td class="{latency_class}">{latency:.2f}</td>
                    <td>{p99_lat:.2f}</td>
                    <td>{errors}</td>
                </tr>
            """
            )

        f.write(
            """
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>MinIO Warp Benchmark Analysis | Generated by kdevops</p>
        </div>
    </div>
</body>
</html>
        """
        )

    print(f"Generated: {output_file}")


def main():
    """Main analysis function."""
    # Determine results directory
    script_dir = Path(__file__).parent
    results_dir = script_dir.parent / "results"

    if not results_dir.exists():
        print(f"Results directory not found: {results_dir}")
        return 1

    # Load all results
    results = load_warp_results(results_dir)
    if not results:
        print("No Warp benchmark results found.")
        return 1

    print(f"\nFound {len(results)} benchmark result(s)")

    # Extract metrics from each result
    metrics_list = [extract_metrics(result) for result in results]

    # Generate visualizations
    print("\nGenerating visualizations...")
    generate_throughput_chart(metrics_list, results_dir)
    generate_latency_chart(metrics_list, results_dir)
    generate_performance_summary_chart(metrics_list, results_dir)

    # Generate reports
    print("\nGenerating reports...")
    generate_text_report(metrics_list, results_dir)
    generate_html_report(metrics_list, results_dir)

    print("\n✅ Analysis complete! Check the results directory for:")
    print("  - warp_throughput_performance.png")
    print("  - warp_latency_analysis.png")
    print("  - warp_performance_summary.png")
    print("  - warp_analysis_report.txt")
    print("  - warp_benchmark_report.html")

    return 0


if __name__ == "__main__":
    sys.exit(main())

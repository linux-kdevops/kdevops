#!/usr/bin/env python3
"""
Generate graphs and HTML report from MinIO Warp benchmark results
"""

import json
import os
import sys
import glob
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path


def parse_warp_json(json_file):
    """Parse Warp benchmark JSON output"""
    with open(json_file, "r") as f:
        content = f.read()
        # Find the JSON object in the output (skip any non-JSON prefix)
        json_start = content.find("{")
        if json_start == -1:
            raise ValueError(f"No JSON found in {json_file}")
        json_content = content[json_start:]
        return json.loads(json_content)


def generate_throughput_graph(data, output_dir, filename_prefix):
    """Generate throughput over time graph"""
    segments = data["total"]["throughput"]["segmented"]["segments"]

    # Extract timestamps and throughput values
    times = []
    throughput_mbps = []
    ops_per_sec = []

    for segment in segments:
        time_str = segment["start"]
        # Parse timestamp
        timestamp = datetime.fromisoformat(time_str.replace("-07:00", "+00:00"))
        times.append(timestamp)
        throughput_mbps.append(
            segment["bytes_per_sec"] / (1024 * 1024)
        )  # Convert to MB/s
        ops_per_sec.append(segment["obj_per_sec"])

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

    # Throughput graph
    ax1.plot(times, throughput_mbps, "b-", linewidth=2, marker="o")
    ax1.set_ylabel("Throughput (MB/s)", fontsize=12)
    ax1.set_title("MinIO Warp Benchmark - Throughput Over Time", fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    # Add average line
    avg_throughput = sum(throughput_mbps) / len(throughput_mbps)
    ax1.axhline(
        y=avg_throughput,
        color="r",
        linestyle="--",
        alpha=0.7,
        label=f"Average: {avg_throughput:.1f} MB/s",
    )
    ax1.legend()

    # Operations per second graph
    ax2.plot(times, ops_per_sec, "g-", linewidth=2, marker="s")
    ax2.set_xlabel("Time", fontsize=12)
    ax2.set_ylabel("Operations/sec", fontsize=12)
    ax2.set_title("Operations Per Second", fontsize=14)
    ax2.grid(True, alpha=0.3)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    # Add average line
    avg_ops = sum(ops_per_sec) / len(ops_per_sec)
    ax2.axhline(
        y=avg_ops,
        color="r",
        linestyle="--",
        alpha=0.7,
        label=f"Average: {avg_ops:.1f} ops/s",
    )
    ax2.legend()

    plt.gcf().autofmt_xdate()
    plt.tight_layout()

    graph_file = os.path.join(output_dir, f"{filename_prefix}_throughput.png")
    plt.savefig(graph_file, dpi=100, bbox_inches="tight")
    plt.close()

    return graph_file


def generate_operation_stats_graph(data, output_dir, filename_prefix):
    """Generate operation statistics bar chart"""
    operations = data.get("operations", {})

    if not operations:
        return None

    op_types = []
    throughputs = []
    latencies = []

    for op_type, op_data in operations.items():
        if op_type in ["DELETE", "GET", "PUT", "STAT"]:
            op_types.append(op_type)
            if "throughput" in op_data:
                throughputs.append(op_data["throughput"]["obj_per_sec"])
            if "latency" in op_data:
                # Convert nanoseconds to milliseconds
                latencies.append(op_data["latency"]["mean"] / 1_000_000)

    if not op_types:
        return None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Throughput bar chart
    if throughputs:
        ax1.bar(op_types, throughputs, color=["blue", "green", "red", "orange"])
        ax1.set_ylabel("Operations/sec", fontsize=12)
        ax1.set_title("Operation Throughput", fontsize=14)
        ax1.grid(True, axis="y", alpha=0.3)

    # Latency bar chart
    if latencies:
        ax2.bar(op_types, latencies, color=["blue", "green", "red", "orange"])
        ax2.set_ylabel("Latency (ms)", fontsize=12)
        ax2.set_title("Operation Latency (Mean)", fontsize=14)
        ax2.grid(True, axis="y", alpha=0.3)

    plt.tight_layout()

    graph_file = os.path.join(output_dir, f"{filename_prefix}_operations.png")
    plt.savefig(graph_file, dpi=100, bbox_inches="tight")
    plt.close()

    return graph_file


def generate_html_report(json_files, output_dir):
    """Generate HTML report with all results"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MinIO Warp Benchmark Results</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #666;
            margin-top: 30px;
        }}
        .result-section {{
            background-color: white;
            padding: 20px;
            margin-bottom: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #4CAF50;
        }}
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        .stat-value {{
            font-size: 1.5em;
            font-weight: bold;
            color: #333;
            margin-top: 5px;
        }}
        img {{
            max-width: 100%;
            height: auto;
            margin: 20px 0;
            border: 1px solid #ddd;
            border-radius: 5px;
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
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .timestamp {{
            color: #666;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <h1>MinIO Warp Benchmark Results</h1>
    <p class="timestamp">Generated: {timestamp}</p>
"""

    for json_file in sorted(json_files, reverse=True):
        try:
            data = parse_warp_json(json_file)
            filename = os.path.basename(json_file)
            filename_prefix = filename.replace(".json", "")

            # Extract key metrics
            total = data["total"]
            total_requests = total.get("total_requests", 0)
            total_objects = total.get("total_objects", 0)
            total_errors = total.get("total_errors", 0)
            total_bytes = total.get("total_bytes", 0)
            concurrency = total.get("concurrency", 0)

            throughput_data = total.get("throughput", {}).get("segmented", {})
            fastest_bps = throughput_data.get("fastest_bps", 0) / (1024 * 1024)  # MB/s
            slowest_bps = throughput_data.get("slowest_bps", 0) / (1024 * 1024)  # MB/s
            average_bps = throughput_data.get("average_bps", 0) / (1024 * 1024)  # MB/s

            html_content += f"""
    <div class="result-section">
        <h2>{filename}</h2>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Requests</div>
                <div class="stat-value">{total_requests:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Objects</div>
                <div class="stat-value">{total_objects:,}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Errors</div>
                <div class="stat-value">{total_errors}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Data</div>
                <div class="stat-value">{total_bytes / (1024**3):.2f} GB</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Concurrency</div>
                <div class="stat-value">{concurrency}</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Average Throughput</div>
                <div class="stat-value">{average_bps:.1f} MB/s</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Fastest Throughput</div>
                <div class="stat-value">{fastest_bps:.1f} MB/s</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Slowest Throughput</div>
                <div class="stat-value">{slowest_bps:.1f} MB/s</div>
            </div>
        </div>
"""

            # Generate graphs
            throughput_graph = generate_throughput_graph(
                data, output_dir, filename_prefix
            )
            if throughput_graph:
                rel_path = os.path.basename(throughput_graph)
                html_content += (
                    f'        <img src="{rel_path}" alt="Throughput Graph">\n'
                )

            ops_graph = generate_operation_stats_graph(
                data, output_dir, filename_prefix
            )
            if ops_graph:
                rel_path = os.path.basename(ops_graph)
                html_content += (
                    f'        <img src="{rel_path}" alt="Operations Statistics">\n'
                )

            # Add operations table if available
            operations = data.get("operations", {})
            if operations:
                html_content += """
        <h3>Operation Details</h3>
        <table>
            <tr>
                <th>Operation</th>
                <th>Throughput (ops/s)</th>
                <th>Mean Latency (ms)</th>
                <th>Min Latency (ms)</th>
                <th>Max Latency (ms)</th>
            </tr>
"""
                for op_type, op_data in operations.items():
                    if op_type in ["DELETE", "GET", "PUT", "STAT"]:
                        throughput = op_data.get("throughput", {}).get("obj_per_sec", 0)
                        latency = op_data.get("latency", {})
                        mean_lat = latency.get("mean", 0) / 1_000_000
                        min_lat = latency.get("min", 0) / 1_000_000
                        max_lat = latency.get("max", 0) / 1_000_000

                        html_content += f"""
            <tr>
                <td>{op_type}</td>
                <td>{throughput:.2f}</td>
                <td>{mean_lat:.2f}</td>
                <td>{min_lat:.2f}</td>
                <td>{max_lat:.2f}</td>
            </tr>
"""
                html_content += "        </table>\n"

            html_content += "    </div>\n"

        except Exception as e:
            print(f"Error processing {json_file}: {e}")
            continue

    html_content += """
</body>
</html>
"""

    html_file = os.path.join(output_dir, "warp_benchmark_report.html")
    with open(html_file, "w") as f:
        f.write(html_content)

    return html_file


def main():
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        # Default to workflows/minio/results
        script_dir = Path(__file__).parent.absolute()
        results_dir = script_dir.parent / "results"

    results_dir = Path(results_dir)
    if not results_dir.exists():
        print(f"Results directory {results_dir} does not exist")
        sys.exit(1)

    # Find all JSON files
    json_files = list(results_dir.glob("warp_benchmark_*.json"))

    if not json_files:
        print(f"No warp_benchmark_*.json files found in {results_dir}")
        sys.exit(1)

    print(f"Found {len(json_files)} result files")

    # Generate HTML report with graphs
    html_file = generate_html_report(json_files, results_dir)
    print(f"Generated HTML report: {html_file}")

    # Also generate individual graphs for latest result
    latest_json = max(json_files, key=os.path.getctime)
    data = parse_warp_json(latest_json)
    filename_prefix = latest_json.stem

    throughput_graph = generate_throughput_graph(data, results_dir, filename_prefix)
    if throughput_graph:
        print(f"Generated throughput graph: {throughput_graph}")

    ops_graph = generate_operation_stats_graph(data, results_dir, filename_prefix)
    if ops_graph:
        print(f"Generated operations graph: {ops_graph}")


if __name__ == "__main__":
    main()

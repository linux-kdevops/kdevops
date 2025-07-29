#!/usr/bin/env python3
"""
Generate ASCII and simple HTML graphs from AI benchmark results
"""

import json
import os
import glob
from datetime import datetime
import html


def create_ascii_bar_chart(title, data, width=60):
    """Create a simple ASCII bar chart"""
    if not data:
        return ""

    max_value = max(data.values())
    chart = [f"\n{title}"]
    chart.append("=" * (width + 20))

    for label, value in data.items():
        bar_width = int((value / max_value) * width)
        bar = "█" * bar_width
        chart.append(f"{label:<20} {bar} {value:.2f}")

    return "\n".join(chart)


def create_html_report(results_data):
    """Create an HTML report with SVG graphs"""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Milvus Vector Database - AI Benchmark Results</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.1);
        }}
        h1, h2 {{
            color: #333;
        }}
        .metric-box {{
            display: inline-block;
            margin: 10px;
            padding: 20px;
            background-color: #f0f0f0;
            border-radius: 8px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 2em;
            font-weight: bold;
            color: #2e7d32;
        }}
        .metric-label {{
            font-size: 0.9em;
            color: #666;
        }}
        svg {{
            margin: 20px 0;
            background-color: #fafafa;
            border: 1px solid #ddd;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        .test-info {{
            background-color: #e8f4fd;
            border-left: 5px solid #3498db;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }}
        .test-info h4 {{
            color: #2c3e50;
            margin-top: 0;
            margin-bottom: 10px;
        }}
        .test-info ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .test-info li {{
            margin-bottom: 5px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 Milvus Vector Database - Performance Results</h1>
        <p>Generated: {timestamp} | Test Type: Vector Database Performance Analysis</p>

        <div class="test-info">
            <h3>🔬 Device Under Test (DUT) & Test Configuration</h3>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                <div>
                    <h4>🖥️ System Configuration</h4>
                    <ul>
                        <li><strong>Platform:</strong> {platform}</li>
                        <li><strong>CPU:</strong> {cpu_info}</li>
                        <li><strong>Memory:</strong> {memory_info}</li>
                        <li><strong>Storage:</strong> {storage_info}</li>
                        <li><strong>Virtualization:</strong> {virtualization}</li>
                    </ul>
                </div>
                <div>
                    <h4>🧪 Test Specifications</h4>
                    <ul>
                        <li><strong>Vector Database:</strong> {database_info}</li>
                        <li><strong>Dataset Size:</strong> {dataset_size:,} vectors</li>
                        <li><strong>Vector Dimensions:</strong> {vector_dimensions}</li>
                        <li><strong>Index Type:</strong> {index_type}</li>
                        <li><strong>Index Parameters:</strong> {index_params}</li>
                        <li><strong>Benchmark Runtime:</strong> {runtime} seconds</li>
                    </ul>
                </div>
            </div>
        </div>

        <h2>📊 Performance Summary</h2>
        <div>
            {metrics_boxes}
        </div>

        <h2>Insert Performance</h2>
        {insert_chart}

        <h2>Query Latency Comparison</h2>
        {latency_chart}

        <h2>Throughput Analysis</h2>
        {throughput_chart}

        <h2>Detailed Results</h2>
        {results_table}
    </div>
</body>
</html>"""

    # Extract metrics
    latest_result = list(results_data.values())[0] if results_data else {}
    config = latest_result.get("config", {})
    insert_perf = latest_result.get("insert_performance", {})
    query_configs = latest_result.get("query_performance", {}).get("configurations", [])
    system_info = latest_result.get("system_info", {})

    # Extract DUT and test information
    platform = "kdevops VM (libguestfs/libvirt)"
    cpu_info = "8 vCPUs, host-passthrough"
    memory_info = "4GB RAM"

    # Add filesystem information if available
    filesystem_info = system_info.get("filesystem_type", "N/A")
    mount_options = system_info.get("mount_options", "N/A")
    if filesystem_info != "N/A":
        storage_info = (
            f"NVMe (QEMU emulated), io_uring AIO, {filesystem_info} filesystem"
        )
    else:
        storage_info = "NVMe (QEMU emulated), io_uring AIO"

    virtualization = "QEMU/KVM on libvirt"

    database_info = f"Milvus {system_info.get('milvus_version', 'v2.5.10')} (Docker)"
    dataset_size = config.get("dataset_size", 1000000)
    vector_dimensions = config.get("vector_dimensions", 128)
    index_type = config.get("index_type", "HNSW")
    index_params = "M=16, efConstruction=200, ef=64"
    runtime = config.get("benchmark_runtime", 180)

    # Create metric boxes
    metrics_html = []
    metrics_html.append(
        f'<div class="metric-box"><div class="metric-value">{config.get("dataset_size", 0):,}</div><div class="metric-label">Vectors</div></div>'
    )
    metrics_html.append(
        f'<div class="metric-box"><div class="metric-value">{insert_perf.get("vectors_per_second", 0):.0f}</div><div class="metric-label">Vectors/Second</div></div>'
    )
    if query_configs:
        metrics_html.append(
            f'<div class="metric-box"><div class="metric-value">{query_configs[0].get("avg_latency_ms", 0):.1f}ms</div><div class="metric-label">Avg Query Latency</div></div>'
        )
        metrics_html.append(
            f'<div class="metric-box"><div class="metric-value">{query_configs[0].get("queries_per_second", 0):.0f}</div><div class="metric-label">Queries/Second</div></div>'
        )

    # Create insert performance chart (SVG)
    insert_chart = create_svg_bar_chart(
        "Insert Performance by Batch",
        {
            "Batch " + str(b["batch"]): b["time"]
            for b in insert_perf.get("batches", [])[:5]
        },
        "Batch",
        "Time (seconds)",
        600,
        300,
    )

    # Create latency comparison chart
    latency_data = {}
    for cfg in query_configs:
        key = f"Batch {cfg['batch_size']}, Top-{cfg['top_k']}"
        latency_data[key] = cfg["avg_latency_ms"]

    latency_chart = create_svg_bar_chart(
        "Query Latency by Configuration",
        latency_data,
        "Configuration",
        "Latency (ms)",
        600,
        300,
    )

    # Create throughput chart
    throughput_data = {}
    for cfg in query_configs:
        key = f"Batch {cfg['batch_size']}, Top-{cfg['top_k']}"
        throughput_data[key] = cfg["queries_per_second"]

    throughput_chart = create_svg_bar_chart(
        "Query Throughput by Configuration",
        throughput_data,
        "Configuration",
        "Queries/Second",
        600,
        300,
    )

    # Create results table
    table_rows = []
    for cfg in query_configs:
        table_rows.append(
            f"""
        <tr>
            <td>{cfg['batch_size']}</td>
            <td>{cfg['top_k']}</td>
            <td>{cfg['avg_latency_ms']:.2f}</td>
            <td>{cfg['p50_latency_ms']:.2f}</td>
            <td>{cfg['p95_latency_ms']:.2f}</td>
            <td>{cfg['p99_latency_ms']:.2f}</td>
            <td>{cfg['queries_per_second']:.2f}</td>
        </tr>
        """
        )

    results_table = f"""
    <table>
        <tr>
            <th>Batch Size</th>
            <th>Top-K</th>
            <th>Avg Latency (ms)</th>
            <th>P50 Latency (ms)</th>
            <th>P95 Latency (ms)</th>
            <th>P99 Latency (ms)</th>
            <th>Queries/Second</th>
        </tr>
        {''.join(table_rows)}
    </table>
    """

    return html_content.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        platform=platform,
        cpu_info=cpu_info,
        memory_info=memory_info,
        storage_info=storage_info,
        virtualization=virtualization,
        database_info=database_info,
        dataset_size=dataset_size,
        vector_dimensions=vector_dimensions,
        index_type=index_type,
        index_params=index_params,
        runtime=runtime,
        metrics_boxes="".join(metrics_html),
        insert_chart=insert_chart,
        latency_chart=latency_chart,
        throughput_chart=throughput_chart,
        results_table=results_table,
    )


def create_svg_bar_chart(title, data, x_label, y_label, width=600, height=300):
    """Create an SVG bar chart"""
    if not data:
        return "<p>No data available</p>"

    # Chart dimensions
    margin = {"top": 40, "right": 20, "bottom": 60, "left": 80}
    chart_width = width - margin["left"] - margin["right"]
    chart_height = height - margin["top"] - margin["bottom"]

    # Calculate scales
    max_value = max(data.values()) if data else 1
    bar_width = chart_width / len(data) * 0.8
    bar_spacing = chart_width / len(data) * 0.2

    svg = [f'<svg width="{width}" height="{height}">']

    # Title
    svg.append(
        f'<text x="{width/2}" y="25" text-anchor="middle" font-size="16" font-weight="bold">{html.escape(title)}</text>'
    )

    # Draw axes
    svg.append(
        f'<line x1="{margin["left"]}" y1="{height - margin["bottom"]}" x2="{width - margin["right"]}" y2="{height - margin["bottom"]}" stroke="black"/>'
    )
    svg.append(
        f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{height - margin["bottom"]}" stroke="black"/>'
    )

    # Y-axis label
    svg.append(
        f'<text x="20" y="{height/2}" text-anchor="middle" font-size="12" transform="rotate(-90 20 {height/2})">{html.escape(y_label)}</text>'
    )

    # X-axis label
    svg.append(
        f'<text x="{width/2}" y="{height - 5}" text-anchor="middle" font-size="12">{html.escape(x_label)}</text>'
    )

    # Draw bars and labels
    for i, (label, value) in enumerate(data.items()):
        x = margin["left"] + i * (bar_width + bar_spacing) + bar_spacing / 2
        bar_height = (value / max_value) * chart_height
        y = height - margin["bottom"] - bar_height

        # Bar
        svg.append(
            f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="#4CAF50" opacity="0.8"/>'
        )

        # Value on top of bar
        svg.append(
            f'<text x="{x + bar_width/2}" y="{y - 5}" text-anchor="middle" font-size="10">{value:.1f}</text>'
        )

        # Label
        label_y = height - margin["bottom"] + 15
        svg.append(
            f'<text x="{x + bar_width/2}" y="{label_y}" text-anchor="middle" font-size="10" transform="rotate(45 {x + bar_width/2} {label_y})">{html.escape(label)}</text>'
        )

    # Y-axis scale
    for i in range(5):
        y_value = (max_value / 4) * i
        y_pos = height - margin["bottom"] - (i * chart_height / 4)
        svg.append(
            f'<line x1="{margin["left"] - 5}" y1="{y_pos}" x2="{margin["left"]}" y2="{y_pos}" stroke="black"/>'
        )
        svg.append(
            f'<text x="{margin["left"] - 10}" y="{y_pos + 3}" text-anchor="end" font-size="10">{y_value:.1f}</text>'
        )

    svg.append("</svg>")
    return "\n".join(svg)


def main():
    """Generate graphs from benchmark results"""

    results_dir = "results"

    # Check if multi-filesystem CSV exists and use enhanced generator for that
    csv_file = os.path.join(results_dir, "multifs_performance_metrics.csv")
    if os.path.exists(csv_file):
        print(
            "📊 Multi-filesystem CSV detected - generating enhanced Milvus comparison..."
        )
        os.system("python3 generate_enhanced_graphs.py")

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
    for result_file in result_files:
        with open(result_file, "r") as f:
            results_data[result_file] = json.load(f)

    # Generate ASCII report
    print("\n" + "=" * 80)
    print("🚀 MILVUS VECTOR DATABASE - PERFORMANCE GRAPHS")
    print("=" * 80)

    for filename, data in results_data.items():
        print(f"\nResults from: {filename}")

        # Insert performance
        insert_perf = data.get("insert_performance", {})
        if insert_perf:
            insert_data = {"Total": insert_perf.get("vectors_per_second", 0)}
            print(
                create_ascii_bar_chart(
                    "Insert Performance (vectors/second)", insert_data
                )
            )

        # Query latency
        query_perf = data.get("query_performance", {})
        latency_data = {}
        throughput_data = {}

        for cfg in query_perf.get("configurations", []):
            label = f"B{cfg['batch_size']}_K{cfg['top_k']}"
            latency_data[label] = cfg["avg_latency_ms"]
            throughput_data[label] = cfg["queries_per_second"]

        if latency_data:
            print(create_ascii_bar_chart("Query Latency (ms)", latency_data))

        if throughput_data:
            print(
                create_ascii_bar_chart(
                    "Query Throughput (queries/sec)", throughput_data
                )
            )

    # Generate HTML report with SVG graphs
    html_report = create_html_report(results_data)
    html_file = os.path.join(results_dir, "benchmark_graphs.html")

    with open(html_file, "w") as f:
        f.write(html_report)

    print(f"\n📊 Interactive graphs saved to: {html_file}")
    print("Open this file in a web browser to view colorful charts!")

    # Also create a simple PNG-like visualization using Unicode blocks
    create_unicode_chart(results_data)


def create_unicode_chart(results_data):
    """Create a colorful Unicode block chart"""

    if not results_data:
        return

    latest_result = list(results_data.values())[0]
    query_configs = latest_result.get("query_performance", {}).get("configurations", [])

    if not query_configs:
        return

    print("\n📈 Query Performance Visualization")
    print("─" * 60)

    # Create a simple heat map using Unicode blocks
    blocks = ["░", "▒", "▓", "█"]

    for cfg in query_configs:
        label = f"Batch {cfg['batch_size']}, Top-{cfg['top_k']}"
        latency = cfg["avg_latency_ms"]
        qps = cfg["queries_per_second"]

        # Normalize values for visualization
        latency_blocks = int((latency / 10) * len(blocks))
        qps_blocks = int((qps / 500) * 20)

        print(f"\n{label}:")
        print(f"  Latency : {'█' * min(latency_blocks, 20)} {latency:.2f} ms")
        print(f"  QPS     : {'█' * min(qps_blocks, 20)} {qps:.0f} queries/sec")

    print("\n✅ Performance Summary:")
    print(
        f"  Best Latency: {min(cfg['avg_latency_ms'] for cfg in query_configs):.2f} ms"
    )
    print(
        f"  Best QPS: {max(cfg['queries_per_second'] for cfg in query_configs):.0f} queries/sec"
    )


if __name__ == "__main__":
    main()

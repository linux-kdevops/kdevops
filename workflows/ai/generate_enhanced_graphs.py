#!/usr/bin/env python3
"""
Generate enhanced AI benchmark graphs using multi-filesystem CSV data
"""

import json
import os
import csv
from datetime import datetime
import html


def load_multifs_csv(csv_file):
    """Load multi-filesystem performance data from CSV"""
    data = {}
    if not os.path.exists(csv_file):
        return data

    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            fs_name = row["filesystem"]
            data[fs_name] = {
                "vectors_per_second": float(row["vectors_per_second"]),
                "index_build_time_s": float(row["index_build_time_s"]),
                "avg_query_latency_ms": float(row["avg_query_latency_ms"]),
                "queries_per_second": float(row["queries_per_second"]),
            }
    return data


def create_filesystem_html_report(multifs_data):
    """Create an enhanced HTML report with multi-filesystem comparison"""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Milvus Vector Database - Multi-Filesystem Performance Analysis</title>
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
            background-color: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
        }}
        .subtitle {{
            text-align: center;
            color: #7f8c8d;
            font-size: 1.2em;
            margin-bottom: 30px;
        }}
        .test-info {{
            background-color: #e8f4fd;
            border-left: 5px solid #3498db;
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 30px 0;
        }}
        .metric-box {{
            background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
            color: white;
            padding: 25px;
            border-radius: 12px;
            text-align: center;
            box-shadow: 0 8px 25px rgba(116, 185, 255, 0.3);
            transition: transform 0.3s ease;
        }}
        .metric-box:hover {{
            transform: translateY(-5px);
        }}
        .metric-value {{
            font-size: 2.2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        .metric-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        .chart-container {{
            margin: 40px 0;
            background-color: #fafafa;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        .chart-title {{
            font-size: 1.5em;
            color: #2c3e50;
            margin-bottom: 20px;
            text-align: center;
            font-weight: 600;
        }}
        svg {{
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }}
        th {{
            background: linear-gradient(135deg, #00b894 0%, #00a085 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #ecf0f1;
        }}
        tr:nth-child(even) {{
            background-color: #f8f9fa;
        }}
        tr:hover {{
            background-color: #e3f2fd;
        }}
        .winner {{
            background-color: #d4edda !important;
            font-weight: bold;
            color: #155724;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: #7f8c8d;
            font-style: italic;
        }}
        .milvus-logo {{
            color: #FF6B35;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 <span class="milvus-logo">Milvus</span> Vector Database Performance</h1>
        <div class="subtitle">Multi-Filesystem Benchmark Analysis - 1 Million Vectors</div>

        <div class="test-info">
            <h3>🔬 Test Configuration</h3>
            <ul>
                <li><strong>Vector Database:</strong> Milvus v2.5.10 (Docker)</li>
                <li><strong>Dataset Size:</strong> 1,000,000 vectors</li>
                <li><strong>Vector Dimensions:</strong> 128</li>
                <li><strong>Index Type:</strong> HNSW (M=16, efConstruction=200, ef=64)</li>
                <li><strong>Test Type:</strong> Per-filesystem configuration analysis</li>
                <li><strong>Filesystems:</strong> {filesystem_list}</li>
            </ul>
        </div>

        <h2>📊 Performance Overview</h2>
        <div class="metric-grid">
            {metrics_boxes}
        </div>

        <div class="chart-container">
            <div class="chart-title">📈 Insert Performance (Vectors/Second)</div>
            {insert_chart}
        </div>

        <div class="chart-container">
            <div class="chart-title">⚡ Query Latency (Milliseconds)</div>
            {latency_chart}
        </div>

        <div class="chart-container">
            <div class="chart-title">🎯 Query Throughput (Queries/Second)</div>
            {throughput_chart}
        </div>

        <div class="chart-container">
            <div class="chart-title">⏱️ Index Build Time (Seconds)</div>
            {index_chart}
        </div>

        <h2>📋 Detailed Results Comparison</h2>
        {results_table}

        <div class="footer">
            <p>Generated: {timestamp} | Powered by kdevops AI Workflow</p>
            <p>🎯 <strong>Recommendations:</strong> {recommendations}</p>
        </div>
    </div>
</body>
</html>"""

    if not multifs_data:
        return html_content.format(
            filesystem_list="No data available",
            metrics_boxes="<p>No data available</p>",
            insert_chart="<p>No data available</p>",
            latency_chart="<p>No data available</p>",
            throughput_chart="<p>No data available</p>",
            index_chart="<p>No data available</p>",
            results_table="<p>No data available</p>",
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            recommendations="No recommendations available",
        )

    # Generate filesystem list
    filesystem_list = ", ".join(multifs_data.keys())

    # Create metric boxes with winners
    best_insert = max(multifs_data.items(), key=lambda x: x[1]["vectors_per_second"])
    best_latency = min(multifs_data.items(), key=lambda x: x[1]["avg_query_latency_ms"])
    best_throughput = max(
        multifs_data.items(), key=lambda x: x[1]["queries_per_second"]
    )
    best_index = min(multifs_data.items(), key=lambda x: x[1]["index_build_time_s"])

    metrics_html = []
    metrics_html.append(
        f"""
        <div class="metric-box">
            <div class="metric-value">{len(multifs_data)}</div>
            <div class="metric-label">Filesystems Tested</div>
        </div>
    """
    )
    metrics_html.append(
        f"""
        <div class="metric-box">
            <div class="metric-value">{best_insert[1]['vectors_per_second']:,.0f}</div>
            <div class="metric-label">Best Insert Rate<br>({best_insert[0]})</div>
        </div>
    """
    )
    metrics_html.append(
        f"""
        <div class="metric-box">
            <div class="metric-value">{best_latency[1]['avg_query_latency_ms']:.1f}ms</div>
            <div class="metric-label">Best Query Latency<br>({best_latency[0]})</div>
        </div>
    """
    )
    metrics_html.append(
        f"""
        <div class="metric-box">
            <div class="metric-value">{best_throughput[1]['queries_per_second']:.0f}</div>
            <div class="metric-label">Best Query Throughput<br>({best_throughput[0]})</div>
        </div>
    """
    )

    # Create charts
    insert_data = {fs: data["vectors_per_second"] for fs, data in multifs_data.items()}
    insert_chart = create_enhanced_svg_chart(
        insert_data, "Filesystem", "Vectors/Second", 1000, 400, "#e74c3c"
    )

    latency_data = {
        fs: data["avg_query_latency_ms"] for fs, data in multifs_data.items()
    }
    latency_chart = create_enhanced_svg_chart(
        latency_data,
        "Filesystem",
        "Latency (ms)",
        1000,
        400,
        "#f39c12",
        invert_better=True,
    )

    throughput_data = {
        fs: data["queries_per_second"] for fs, data in multifs_data.items()
    }
    throughput_chart = create_enhanced_svg_chart(
        throughput_data, "Filesystem", "Queries/Second", 1000, 400, "#27ae60"
    )

    index_data = {fs: data["index_build_time_s"] for fs, data in multifs_data.items()}
    index_chart = create_enhanced_svg_chart(
        index_data,
        "Filesystem",
        "Build Time (seconds)",
        1000,
        400,
        "#9b59b6",
        invert_better=True,
    )

    # Create results table with winners highlighted
    table_rows = []
    for fs, data in multifs_data.items():
        is_best_insert = fs == best_insert[0]
        is_best_latency = fs == best_latency[0]
        is_best_throughput = fs == best_throughput[0]
        is_best_index = fs == best_index[0]

        insert_class = "winner" if is_best_insert else ""
        latency_class = "winner" if is_best_latency else ""
        throughput_class = "winner" if is_best_throughput else ""
        index_class = "winner" if is_best_index else ""

        table_rows.append(
            f"""
        <tr>
            <td><strong>{fs}</strong></td>
            <td class="{insert_class}">{data['vectors_per_second']:,.0f}</td>
            <td class="{latency_class}">{data['avg_query_latency_ms']:.2f}</td>
            <td class="{throughput_class}">{data['queries_per_second']:.0f}</td>
            <td class="{index_class}">{data['index_build_time_s']:.1f}</td>
        </tr>
        """
        )

    results_table = f"""
    <table>
        <tr>
            <th>Filesystem Configuration</th>
            <th>Insert Rate (vectors/sec)</th>
            <th>Query Latency (ms)</th>
            <th>Query Throughput (QPS)</th>
            <th>Index Build Time (s)</th>
        </tr>
        {''.join(table_rows)}
    </table>
    """

    # Generate recommendations
    recommendations = generate_recommendations(
        best_insert, best_latency, best_throughput, best_index
    )

    return html_content.format(
        filesystem_list=filesystem_list,
        metrics_boxes="".join(metrics_html),
        insert_chart=insert_chart,
        latency_chart=latency_chart,
        throughput_chart=throughput_chart,
        index_chart=index_chart,
        results_table=results_table,
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        recommendations=recommendations,
    )


def create_enhanced_svg_chart(
    data, x_label, y_label, width=1000, height=400, color="#3498db", invert_better=False
):
    """Create an enhanced SVG bar chart with gradients and better styling"""
    if not data:
        return "<p>No data available</p>"

    margin = {"top": 60, "right": 40, "bottom": 100, "left": 100}
    chart_width = width - margin["left"] - margin["right"]
    chart_height = height - margin["top"] - margin["bottom"]

    max_value = max(data.values()) if data else 1
    min_value = min(data.values()) if data else 0
    value_range = max_value - min_value

    bar_width = chart_width / len(data) * 0.7
    bar_spacing = chart_width / len(data) * 0.3

    # Define gradient colors
    gradient_id = f"gradient_{abs(hash(color))}"

    svg = [f'<svg width="{width}" height="{height}">']

    # Add gradient definition
    svg.append(
        f"""
    <defs>
        <linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style="stop-color:{color};stop-opacity:0.9" />
            <stop offset="100%" style="stop-color:{color};stop-opacity:0.6" />
        </linearGradient>
    </defs>
    """
    )

    # Background
    svg.append(f'<rect width="{width}" height="{height}" fill="#fafafa"/>')

    # Grid lines
    for i in range(5):
        y_pos = margin["top"] + (i * chart_height / 4)
        svg.append(
            f'<line x1="{margin["left"]}" y1="{y_pos}" x2="{width - margin["right"]}" y2="{y_pos}" stroke="#ecf0f1" stroke-width="1"/>'
        )

    # Draw axes
    svg.append(
        f'<line x1="{margin["left"]}" y1="{height - margin["bottom"]}" x2="{width - margin["right"]}" y2="{height - margin["bottom"]}" stroke="#2c3e50" stroke-width="2"/>'
    )
    svg.append(
        f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{height - margin["bottom"]}" stroke="#2c3e50" stroke-width="2"/>'
    )

    # Y-axis label
    svg.append(
        f'<text x="30" y="{height/2}" text-anchor="middle" font-size="14" font-weight="600" fill="#2c3e50" transform="rotate(-90 30 {height/2})">{html.escape(y_label)}</text>'
    )

    # X-axis label
    svg.append(
        f'<text x="{width/2}" y="{height - 20}" text-anchor="middle" font-size="14" font-weight="600" fill="#2c3e50">{html.escape(x_label)}</text>'
    )

    # Find best performer for highlighting
    if invert_better:
        best_fs = min(data.items(), key=lambda x: x[1])[0]
    else:
        best_fs = max(data.items(), key=lambda x: x[1])[0]

    # Draw bars and labels
    for i, (label, value) in enumerate(data.items()):
        x = margin["left"] + i * (bar_width + bar_spacing) + bar_spacing / 2

        # Normalize value for bar height
        if value_range > 0:
            normalized_value = (value - min_value) / value_range
        else:
            normalized_value = 0.5

        bar_height = normalized_value * chart_height + (
            chart_height * 0.1
        )  # Minimum bar height
        y = height - margin["bottom"] - bar_height

        # Choose color - highlight best performer
        bar_color = f"url(#{gradient_id})" if label != best_fs else "#e74c3c"

        # Bar with rounded corners
        svg.append(
            f'<rect x="{x}" y="{y}" width="{bar_width}" height="{bar_height}" fill="{bar_color}" rx="4" ry="4"/>'
        )

        # Value on top of bar
        svg.append(
            f'<text x="{x + bar_width/2}" y="{y - 10}" text-anchor="middle" font-size="12" font-weight="bold" fill="#2c3e50">{value:.1f}</text>'
        )

        # Add crown emoji for best performer
        if label == best_fs:
            svg.append(
                f'<text x="{x + bar_width/2}" y="{y - 30}" text-anchor="middle" font-size="16">👑</text>'
            )

        # Label with rotation for better fit
        label_y = height - margin["bottom"] + 20
        clean_label = label.replace("-", " ").title()
        svg.append(
            f'<text x="{x + bar_width/2}" y="{label_y}" text-anchor="middle" font-size="11" font-weight="500" fill="#2c3e50" transform="rotate(45 {x + bar_width/2} {label_y})">{html.escape(clean_label)}</text>'
        )

    # Y-axis scale
    for i in range(5):
        y_value = min_value + (value_range / 4) * i
        y_pos = height - margin["bottom"] - (i * chart_height / 4)
        svg.append(
            f'<line x1="{margin["left"] - 5}" y1="{y_pos}" x2="{margin["left"]}" y2="{y_pos}" stroke="#2c3e50" stroke-width="1"/>'
        )
        svg.append(
            f'<text x="{margin["left"] - 10}" y="{y_pos + 4}" text-anchor="end" font-size="11" fill="#2c3e50">{y_value:.1f}</text>'
        )

    svg.append("</svg>")
    return "\n".join(svg)


def generate_recommendations(best_insert, best_latency, best_throughput, best_index):
    """Generate performance recommendations based on results"""
    recommendations = []

    if best_insert[0] == best_latency[0]:
        recommendations.append(f"{best_insert[0]} offers excellent overall performance")
    else:
        recommendations.append(
            f"Use {best_insert[0]} for high insert workloads, {best_latency[0]} for low-latency queries"
        )

    if best_throughput[0] != best_latency[0]:
        recommendations.append(f"{best_throughput[0]} maximizes query throughput")

    if "xfs" in best_insert[0].lower():
        recommendations.append("XFS shows strong performance for vector databases")

    return " | ".join(recommendations)


def create_ascii_comparison(multifs_data):
    """Create ASCII comparison chart for console output"""
    if not multifs_data:
        return

    print("\n" + "=" * 80)
    print("🚀 MILVUS VECTOR DATABASE - MULTI-FILESYSTEM PERFORMANCE")
    print("=" * 80)
    print("📊 Dataset: 1,000,000 vectors | Dimensions: 128 | Index: HNSW")
    print("-" * 80)

    # Find max values for normalization
    max_insert = max(data["vectors_per_second"] for data in multifs_data.values())
    max_throughput = max(data["queries_per_second"] for data in multifs_data.values())
    min_latency = min(data["avg_query_latency_ms"] for data in multifs_data.values())
    max_latency = max(data["avg_query_latency_ms"] for data in multifs_data.values())

    for fs, data in multifs_data.items():
        print(f"\n📁 {fs.upper()}")
        print("-" * 40)

        # Insert performance bar
        insert_bar_length = int((data["vectors_per_second"] / max_insert) * 50)
        insert_bar = "█" * insert_bar_length
        print(f"Insert    : {insert_bar:<50} {data['vectors_per_second']:>8.0f} v/s")

        # Query latency bar (inverted - lower is better)
        latency_normalized = (
            1
            - (
                (data["avg_query_latency_ms"] - min_latency)
                / (max_latency - min_latency)
            )
            if max_latency > min_latency
            else 0.5
        )
        latency_bar_length = int(latency_normalized * 50)
        latency_bar = "█" * latency_bar_length
        print(f"Latency   : {latency_bar:<50} {data['avg_query_latency_ms']:>8.2f} ms")

        # Query throughput bar
        throughput_bar_length = int((data["queries_per_second"] / max_throughput) * 50)
        throughput_bar = "█" * throughput_bar_length
        print(
            f"Throughput: {throughput_bar:<50} {data['queries_per_second']:>8.0f} q/s"
        )

        print(f"Index Time: {data['index_build_time_s']:>58.1f} sec")

    # Winners summary
    best_insert = max(multifs_data.items(), key=lambda x: x[1]["vectors_per_second"])
    best_latency = min(multifs_data.items(), key=lambda x: x[1]["avg_query_latency_ms"])
    best_throughput = max(
        multifs_data.items(), key=lambda x: x[1]["queries_per_second"]
    )

    print("\n🏆 PERFORMANCE WINNERS")
    print("-" * 40)
    print(
        f"🚀 Best Insert Rate  : {best_insert[0]} ({best_insert[1]['vectors_per_second']:,.0f} vectors/sec)"
    )
    print(
        f"⚡ Best Latency      : {best_latency[0]} ({best_latency[1]['avg_query_latency_ms']:.2f} ms)"
    )
    print(
        f"🎯 Best Throughput   : {best_throughput[0]} ({best_throughput[1]['queries_per_second']:.0f} QPS)"
    )


def main():
    """Generate enhanced graphs with multi-filesystem data"""
    results_dir = "results"
    csv_file = os.path.join(results_dir, "multifs_performance_metrics.csv")

    # Load multi-filesystem data
    multifs_data = load_multifs_csv(csv_file)

    if not multifs_data:
        print("❌ No multi-filesystem data found in CSV file")
        return

    # Generate ASCII comparison
    create_ascii_comparison(multifs_data)

    # Generate enhanced HTML report
    html_report = create_filesystem_html_report(multifs_data)
    html_file = os.path.join(results_dir, "milvus_multifs_benchmark.html")

    with open(html_file, "w") as f:
        f.write(html_report)

    print(f"\n📊 Enhanced Milvus multi-filesystem report saved to: {html_file}")
    print("🌐 Open this file in a web browser to view the interactive analysis!")
    print("\n✅ Report includes:")
    print("   • Per-filesystem performance comparison")
    print("   • Interactive charts with winner highlighting")
    print("   • Detailed recommendations")
    print("   • Milvus vector database test identification")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Generate HTML report for AI benchmark results
"""

import json
import os
import sys
import glob
from datetime import datetime
from pathlib import Path

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Benchmark Results - {timestamp}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background-color: #2c3e50;
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
            text-align: center;
        }}
        h1 {{
            margin: 0;
            font-size: 2.5em;
        }}
        .subtitle {{
            margin-top: 10px;
            opacity: 0.9;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .card h3 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
        }}
        .card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #3498db;
        }}
        .card .label {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .section {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .graph-container {{
            text-align: center;
            margin: 20px 0;
        }}
        .graph-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .results-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .results-table th, .results-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .results-table th {{
            background-color: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }}
        .results-table tr:hover {{
            background-color: #f8f9fa;
        }}
        .baseline {{
            background-color: #e8f4fd;
        }}
        .dev {{
            background-color: #fff3cd;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        .graph-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .best-config {{
            background-color: #d4edda;
            font-weight: bold;
        }}
        .navigation {{
            position: sticky;
            top: 20px;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .navigation ul {{
            list-style: none;
            padding: 0;
            margin: 0;
        }}
        .navigation li {{
            display: inline-block;
            margin-right: 20px;
        }}
        .navigation a {{
            color: #3498db;
            text-decoration: none;
            font-weight: 500;
        }}
        .navigation a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AI Vector Database Benchmark Results</h1>
        <div class="subtitle">Generated on {timestamp}</div>
    </div>
    
    <nav class="navigation">
        <ul>
            <li><a href="#summary">Summary</a></li>
            <li><a href="#filesystem-comparison">Filesystem Comparison</a></li>
            <li><a href="#block-size-analysis">Block Size Analysis</a></li>
            <li><a href="#performance-heatmap">Performance Heatmap</a></li>
            <li><a href="#detailed-results">Detailed Results</a></li>
        </ul>
    </nav>
    
    <div id="summary" class="summary-cards">
        <div class="card">
            <h3>Total Tests</h3>
            <div class="value">{total_tests}</div>
            <div class="label">Configurations</div>
        </div>
        <div class="card">
            <h3>Best Insert QPS</h3>
            <div class="value">{best_insert_qps}</div>
            <div class="label">{best_insert_config}</div>
        </div>
        <div class="card">
            <h3>Best Query QPS</h3>
            <div class="value">{best_query_qps}</div>
            <div class="label">{best_query_config}</div>
        </div>
        <div class="card">
            <h3>Filesystems Tested</h3>
            <div class="value">{num_filesystems}</div>
            <div class="label">{filesystem_list}</div>
        </div>
    </div>
    
    <div id="filesystem-comparison" class="section">
        <h2>Filesystem Performance Comparison</h2>
        <p>Comparison of vector database performance across different filesystems, showing both baseline and development kernel results.</p>
        <div class="graph-container">
            <img src="graphs/filesystem_comparison.png" alt="Filesystem Comparison">
        </div>
    </div>
    
    <div id="block-size-analysis" class="section">
        <h2>XFS Block Size Analysis</h2>
        <p>Performance analysis of XFS filesystem with different block sizes (4K, 16K, 32K, 64K).</p>
        <div class="graph-container">
            <img src="graphs/xfs_block_size_analysis.png" alt="XFS Block Size Analysis">
        </div>
    </div>
    
    <div id="performance-heatmap" class="section">
        <h2>Performance Heatmap</h2>
        <p>Heatmap visualization showing performance metrics across all tested configurations.</p>
        <div class="graph-container">
            <img src="graphs/performance_heatmap.png" alt="Performance Heatmap">
        </div>
    </div>
    
    <div class="section">
        <h2>Performance Trends by Filesystem</h2>
        <div class="graph-grid">
            {performance_trend_graphs}
        </div>
    </div>
    
    <div id="detailed-results" class="section">
        <h2>Detailed Results Table</h2>
        <table class="results-table">
            <thead>
                <tr>
                    <th>Host</th>
                    <th>Filesystem</th>
                    <th>Block Size</th>
                    <th>Type</th>
                    <th>Insert QPS</th>
                    <th>Query QPS</th>
                    <th>Timestamp</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    
    <div class="footer">
        <p>Generated by kdevops AI Benchmark Suite | <a href="https://github.com/linux-kdevops/kdevops">GitHub</a></p>
    </div>
</body>
</html>
"""


def load_summary(graphs_dir):
    """Load the summary.json file"""
    summary_path = os.path.join(graphs_dir, "summary.json")
    if os.path.exists(summary_path):
        with open(summary_path, "r") as f:
            return json.load(f)
    return None


def load_results(results_dir):
    """Load all result files for detailed table"""
    results = []
    json_files = glob.glob(os.path.join(results_dir, "*.json"))

    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                # Parse filename for metadata
                filename = os.path.basename(json_file)
                if "debian13-ai-" in filename:
                    host_parts = (
                        filename.replace("results_debian13-ai-", "")
                        .replace("_1.json", "")
                        .split("-")
                    )
                    if "xfs" in host_parts[0]:
                        fs_type = "xfs"
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

                    results.append(
                        {
                            "host": data.get(
                                "host",
                                filename.replace("results_", "").replace("_1.json", ""),
                            ),
                            "filesystem": fs_type,
                            "block_size": block_size,
                            "type": "Development" if is_dev else "Baseline",
                            "insert_qps": data.get("performance", {}).get(
                                "insert_qps", 0
                            ),
                            "query_qps": data.get("performance", {}).get(
                                "query_qps", 0
                            ),
                            "timestamp": data.get("timestamp", "N/A"),
                            "is_dev": is_dev,
                        }
                    )
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    # Sort by filesystem, block size, then type
    results.sort(key=lambda x: (x["filesystem"], x["block_size"], x["type"]))
    return results


def generate_table_rows(results, best_configs):
    """Generate HTML table rows"""
    rows = []
    for result in results:
        config_key = f"{result['filesystem']}-{result['block_size']}-{'dev' if result['is_dev'] else 'baseline'}"
        row_class = "dev" if result["is_dev"] else "baseline"

        # Check if this is a best configuration
        if config_key in best_configs:
            row_class += " best-config"

        row = f"""
        <tr class="{row_class}">
            <td>{result['host']}</td>
            <td>{result['filesystem'].upper()}</td>
            <td>{result['block_size']}</td>
            <td>{result['type']}</td>
            <td>{result['insert_qps']:,}</td>
            <td>{result['query_qps']:,}</td>
            <td>{result['timestamp']}</td>
        </tr>
        """
        rows.append(row)

    return "\n".join(rows)


def find_performance_trend_graphs(graphs_dir):
    """Find all performance trend graphs"""
    graphs = []
    for fs in ["xfs", "ext4", "btrfs"]:
        graph_path = f"{fs}_performance_trends.png"
        if os.path.exists(os.path.join(graphs_dir, graph_path)):
            graphs.append(
                f'<div class="graph-container"><img src="graphs/{graph_path}" alt="{fs.upper()} Performance Trends"></div>'
            )
    return "\n".join(graphs)


def generate_html_report(results_dir, graphs_dir, output_path):
    """Generate the HTML report"""
    # Load summary
    summary = load_summary(graphs_dir)
    if not summary:
        print("Warning: No summary.json found")
        summary = {
            "total_tests": 0,
            "filesystems_tested": [],
            "performance_summary": {
                "best_insert_qps": {"value": 0, "config": "N/A"},
                "best_query_qps": {"value": 0, "config": "N/A"},
            },
        }

    # Load detailed results
    results = load_results(results_dir)

    # Find best configurations
    best_configs = set()
    if summary["performance_summary"]["best_insert_qps"]["config"]:
        best_configs.add(summary["performance_summary"]["best_insert_qps"]["config"])
    if summary["performance_summary"]["best_query_qps"]["config"]:
        best_configs.add(summary["performance_summary"]["best_query_qps"]["config"])

    # Generate HTML
    html_content = HTML_TEMPLATE.format(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_tests=summary["total_tests"],
        best_insert_qps=f"{summary['performance_summary']['best_insert_qps']['value']:,}",
        best_insert_config=summary["performance_summary"]["best_insert_qps"]["config"],
        best_query_qps=f"{summary['performance_summary']['best_query_qps']['value']:,}",
        best_query_config=summary["performance_summary"]["best_query_qps"]["config"],
        num_filesystems=len(summary["filesystems_tested"]),
        filesystem_list=", ".join(summary["filesystems_tested"]).upper(),
        performance_trend_graphs=find_performance_trend_graphs(graphs_dir),
        table_rows=generate_table_rows(results, best_configs),
    )

    # Write HTML file
    with open(output_path, "w") as f:
        f.write(html_content)

    print(f"HTML report generated: {output_path}")


def main():
    if len(sys.argv) < 4:
        print("Usage: generate_html_report.py <results_dir> <graphs_dir> <output_html>")
        sys.exit(1)

    results_dir = sys.argv[1]
    graphs_dir = sys.argv[2]
    output_html = sys.argv[3]

    generate_html_report(results_dir, graphs_dir, output_html)


if __name__ == "__main__":
    main()

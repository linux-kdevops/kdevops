#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
Generate HTML visualization report for pynfs test results with charts and summaries.
Creates both an HTML report and PNG chart files.
"""

import json
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime
import re

# Try to import matplotlib for PNG generation
try:
    import matplotlib

    matplotlib.use("Agg")  # Use non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Warning: matplotlib not available, PNG charts will not be generated")
    print("Install with: pip3 install matplotlib")


def load_json_results(filepath):
    """Load and parse a JSON result file."""
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
        return None


def categorize_tests(testcases):
    """Categorize tests by their class/module."""
    categories = {}
    for test in testcases:
        classname = test.get("classname", "unknown")
        if classname not in categories:
            categories[classname] = {
                "passed": [],
                "failed": [],
                "skipped": [],
                "error": [],
            }

        if test.get("skipped"):
            categories[classname]["skipped"].append(test)
        elif test.get("failure"):
            categories[classname]["failed"].append(test)
        elif test.get("error"):
            categories[classname]["error"].append(test)
        else:
            categories[classname]["passed"].append(test)

    return categories


def generate_png_charts(charts, output_dir):
    """Generate PNG charts using matplotlib."""
    if not MATPLOTLIB_AVAILABLE:
        return []

    png_files = []

    # Set up the style
    plt.style.use("seaborn-v0_8-darkgrid")

    for chart in charts:
        version = chart["version"]

        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle(
            f'PyNFS {version.upper()} Test Results - Kernel {chart.get("kernel", "Unknown")}',
            fontsize=16,
            fontweight="bold",
        )

        # Pie chart
        sizes = [chart["passed"], chart["failed"], chart["errors"], chart["skipped"]]
        labels = ["Passed", "Failed", "Errors", "Skipped"]
        colors = ["#48bb78", "#f56565", "#ed8936", "#a0aec0"]
        explode = (0.05, 0.1, 0.1, 0)  # Explode failed and error slices

        # Only show non-zero values
        non_zero_sizes = []
        non_zero_labels = []
        non_zero_colors = []
        non_zero_explode = []
        for i, size in enumerate(sizes):
            if size > 0:
                non_zero_sizes.append(size)
                non_zero_labels.append(f"{labels[i]}: {size}")
                non_zero_colors.append(colors[i])
                non_zero_explode.append(explode[i])

        ax1.pie(
            non_zero_sizes,
            explode=non_zero_explode,
            labels=non_zero_labels,
            colors=non_zero_colors,
            autopct="%1.1f%%",
            startangle=90,
            shadow=True,
        )
        ax1.set_title("Test Distribution")

        # Bar chart
        ax2.bar(labels, sizes, color=colors, edgecolor="black", linewidth=1.5)
        ax2.set_ylabel("Number of Tests", fontweight="bold")
        ax2.set_title("Test Counts")
        ax2.grid(axis="y", alpha=0.3)

        # Add text annotations on bars
        for i, (label, value) in enumerate(zip(labels, sizes)):
            ax2.text(
                i,
                value + max(sizes) * 0.01,
                str(value),
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        # Add summary statistics
        total = chart["total"]
        pass_rate = chart["pass_rate"]
        fig.text(
            0.5,
            0.02,
            f"Total Tests: {total} | Pass Rate: {pass_rate}%",
            ha="center",
            fontsize=12,
            fontweight="bold",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
        )

        plt.tight_layout()

        # Save the figure
        png_filename = f'pynfs-{version.replace(".", "_")}-results.png'
        png_path = output_dir / png_filename
        plt.savefig(png_path, dpi=150, bbox_inches="tight")
        plt.close()

        png_files.append(png_filename)
        print(f"  Generated: {png_path}")

    # Generate a summary chart comparing all versions
    if len(charts) > 1:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle("PyNFS Test Results Comparison", fontsize=18, fontweight="bold")

        # Prepare data
        versions = [c["version"].upper() for c in charts]
        passed = [c["passed"] for c in charts]
        failed = [c["failed"] for c in charts]
        errors = [c["errors"] for c in charts]
        skipped = [c["skipped"] for c in charts]
        pass_rates = [c["pass_rate"] for c in charts]

        x = range(len(versions))
        width = 0.2

        # Grouped bar chart
        ax = axes[0, 0]
        ax.bar(
            [i - width * 1.5 for i in x], passed, width, label="Passed", color="#48bb78"
        )
        ax.bar(
            [i - width * 0.5 for i in x], failed, width, label="Failed", color="#f56565"
        )
        ax.bar(
            [i + width * 0.5 for i in x], errors, width, label="Errors", color="#ed8936"
        )
        ax.bar(
            [i + width * 1.5 for i in x],
            skipped,
            width,
            label="Skipped",
            color="#a0aec0",
        )
        ax.set_xlabel("Version")
        ax.set_ylabel("Number of Tests")
        ax.set_title("Test Results by Version")
        ax.set_xticks(x)
        ax.set_xticklabels(versions)
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        # Pass rate comparison
        ax = axes[0, 1]
        bars = ax.bar(
            versions,
            pass_rates,
            color=[
                "#48bb78" if p >= 90 else "#ed8936" if p >= 70 else "#f56565"
                for p in pass_rates
            ],
        )
        ax.set_ylabel("Pass Rate (%)")
        ax.set_title("Pass Rate Comparison")
        ax.set_ylim(0, 105)
        ax.grid(axis="y", alpha=0.3)

        # Add value labels on bars
        for bar, rate in zip(bars, pass_rates):
            height = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + 1,
                f"{rate:.1f}%",
                ha="center",
                va="bottom",
                fontweight="bold",
            )

        # Stacked bar chart
        ax = axes[1, 0]
        ax.bar(versions, passed, label="Passed", color="#48bb78")
        ax.bar(versions, failed, bottom=passed, label="Failed", color="#f56565")
        ax.bar(
            versions,
            errors,
            bottom=[p + f for p, f in zip(passed, failed)],
            label="Errors",
            color="#ed8936",
        )
        ax.bar(
            versions,
            skipped,
            bottom=[p + f + e for p, f, e in zip(passed, failed, errors)],
            label="Skipped",
            color="#a0aec0",
        )
        ax.set_ylabel("Number of Tests")
        ax.set_title("Stacked Test Results")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)

        # Summary table
        ax = axes[1, 1]
        ax.axis("tight")
        ax.axis("off")

        table_data = [
            ["Version", "Total", "Passed", "Failed", "Errors", "Skipped", "Pass Rate"]
        ]
        for c in charts:
            table_data.append(
                [
                    c["version"].upper(),
                    str(c["total"]),
                    str(c["passed"]),
                    str(c["failed"]),
                    str(c["errors"]),
                    str(c["skipped"]),
                    f"{c['pass_rate']}%",
                ]
            )

        table = ax.table(cellText=table_data, loc="center", cellLoc="center")
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)

        # Style the header row
        for i in range(7):
            table[(0, i)].set_facecolor("#4a5568")
            table[(0, i)].set_text_props(weight="bold", color="white")

        # Color code the cells
        for i in range(1, len(table_data)):
            # Pass rate column
            pass_rate = float(table_data[i][6].strip("%"))
            if pass_rate >= 90:
                table[(i, 6)].set_facecolor("#c6f6d5")
            elif pass_rate >= 70:
                table[(i, 6)].set_facecolor("#feebc8")
            else:
                table[(i, 6)].set_facecolor("#fed7d7")

        plt.tight_layout()

        # Save comparison chart
        comparison_path = output_dir / "pynfs-comparison.png"
        plt.savefig(comparison_path, dpi=150, bbox_inches="tight")
        plt.close()

        png_files.append("pynfs-comparison.png")
        print(f"  Generated: {comparison_path}")

    return png_files


def generate_chart_data(results, kernel_version):
    """Generate data for charts."""
    charts = []
    for version, data in results.items():
        if not data:
            continue

        total = data.get("tests", 0)
        passed = (
            total
            - data.get("failures", 0)
            - data.get("errors", 0)
            - data.get("skipped", 0)
        )
        failed = data.get("failures", 0)
        errors = data.get("errors", 0)
        skipped = data.get("skipped", 0)

        charts.append(
            {
                "version": version,
                "kernel": kernel_version,
                "total": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "skipped": skipped,
                "pass_rate": round((passed / total * 100) if total > 0 else 0, 2),
            }
        )

    return charts


def generate_html_report(results_dir, kernel_version):
    """Generate the main HTML report with embedded charts and links to PNG files."""
    results = {}

    # Load all JSON files for this kernel version
    for json_file in Path(results_dir).glob(f"{kernel_version}*.json"):
        # Extract version from filename (e.g., v4.0, v4.1, vblock)
        match = re.search(r"-v(4\.[01]|block)\.json$", str(json_file))
        if match:
            version = "v" + match.group(1)
            results[version] = load_json_results(json_file)

    if not results:
        print(f"No results found for kernel {kernel_version}")
        return None, []

    # Generate chart data
    charts = generate_chart_data(results, kernel_version)

    # Create output directory for HTML and PNGs
    output_dir = Path(results_dir) / "html"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate PNG charts
    png_files = generate_png_charts(charts, output_dir)

    # Generate detailed test results
    detailed_results = {}
    for version, data in results.items():
        if data and "testcase" in data:
            detailed_results[version] = categorize_tests(data["testcase"])

    # Create HTML content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PyNFS Test Results - {kernel_version}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}

        .header {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}

        h1 {{
            color: #2d3748;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}

        .subtitle {{
            color: #718096;
            font-size: 1.1em;
        }}

        .png-links {{
            margin-top: 20px;
            padding: 15px;
            background: #f7fafc;
            border-radius: 8px;
        }}

        .png-links h3 {{
            color: #2d3748;
            margin-bottom: 10px;
        }}

        .png-links a {{
            color: #667eea;
            text-decoration: none;
            margin-right: 15px;
            font-weight: 500;
        }}

        .png-links a:hover {{
            text-decoration: underline;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}

        .summary-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }}

        .summary-card:hover {{
            transform: translateY(-5px);
        }}

        .card-title {{
            font-size: 1.3em;
            color: #4a5568;
            margin-bottom: 20px;
            font-weight: 600;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
        }}

        .stat-item {{
            padding: 10px;
            background: #f7fafc;
            border-radius: 8px;
        }}

        .stat-label {{
            color: #718096;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}

        .stat-value {{
            font-size: 1.5em;
            font-weight: bold;
        }}

        .stat-value.passed {{
            color: #48bb78;
        }}

        .stat-value.failed {{
            color: #f56565;
        }}

        .stat-value.error {{
            color: #ed8936;
        }}

        .stat-value.skipped {{
            color: #a0aec0;
        }}

        .chart-container {{
            position: relative;
            height: 300px;
            margin-top: 20px;
        }}

        .png-preview {{
            margin-top: 20px;
            text-align: center;
        }}

        .png-preview img {{
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}

        .details-section {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}

        .test-category {{
            margin-bottom: 25px;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }}

        .category-header {{
            font-size: 1.2em;
            color: #2d3748;
            margin-bottom: 15px;
            font-weight: 600;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }}

        .test-list {{
            display: grid;
            gap: 10px;
        }}

        .test-item {{
            padding: 12px;
            border-radius: 6px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s ease;
        }}

        .test-item:hover {{
            transform: translateX(5px);
        }}

        .test-item.passed {{
            background: #c6f6d5;
            border-left: 4px solid #48bb78;
        }}

        .test-item.failed {{
            background: #fed7d7;
            border-left: 4px solid #f56565;
        }}

        .test-item.skipped {{
            background: #e2e8f0;
            border-left: 4px solid #a0aec0;
        }}

        .test-item.error {{
            background: #feebc8;
            border-left: 4px solid #ed8936;
        }}

        .test-name {{
            font-family: 'Courier New', monospace;
            font-size: 0.95em;
        }}

        .test-code {{
            background: rgba(0,0,0,0.1);
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.85em;
            font-family: monospace;
        }}

        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #e2e8f0;
        }}

        .tab-button {{
            padding: 10px 20px;
            background: none;
            border: none;
            color: #718096;
            cursor: pointer;
            font-size: 1em;
            transition: all 0.3s ease;
            position: relative;
        }}

        .tab-button:hover {{
            color: #2d3748;
        }}

        .tab-button.active {{
            color: #667eea;
            font-weight: 600;
        }}

        .tab-button.active::after {{
            content: '';
            position: absolute;
            bottom: -2px;
            left: 0;
            right: 0;
            height: 2px;
            background: #667eea;
        }}

        .tab-content {{
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        .footer {{
            text-align: center;
            color: white;
            margin-top: 40px;
            font-size: 0.9em;
        }}

        .progress-bar {{
            height: 20px;
            background: #e2e8f0;
            border-radius: 10px;
            overflow: hidden;
            margin: 15px 0;
        }}

        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #48bb78, #38a169);
            transition: width 0.5s ease;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 PyNFS Test Results</h1>
            <div class="subtitle">Kernel Version: {kernel_version}</div>
            <div class="subtitle">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
"""

    # Add PNG download links if any were generated
    if png_files:
        html_content += """
            <div class="png-links">
                <h3>📊 Download Charts:</h3>
"""
        for png_file in png_files:
            html_content += (
                f'                <a href="{png_file}" download>{png_file}</a>\n'
            )
        html_content += """            </div>
"""

    html_content += """
        </div>

        <div class="summary-grid">
"""

    # Add summary cards for each version
    for chart in charts:
        version = chart["version"]
        png_file = f'pynfs-{version.replace(".", "_")}-results.png'

        html_content += f"""
            <div class="summary-card">
                <div class="card-title">NFS {version.upper()} Results</div>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">Total Tests</div>
                        <div class="stat-value">{chart['total']}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Pass Rate</div>
                        <div class="stat-value passed">{chart['pass_rate']}%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Passed</div>
                        <div class="stat-value passed">{chart['passed']}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Failed</div>
                        <div class="stat-value failed">{chart['failed']}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Errors</div>
                        <div class="stat-value error">{chart['errors']}</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Skipped</div>
                        <div class="stat-value skipped">{chart['skipped']}</div>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: {chart['pass_rate']}%"></div>
                </div>
"""

        # Add PNG preview if available
        if png_file in png_files:
            html_content += f"""
                <div class="png-preview">
                    <a href="{png_file}" target="_blank">
                        <img src="{png_file}" alt="{version.upper()} Results Chart">
                    </a>
                </div>
"""
        else:
            # Fallback to JavaScript chart
            html_content += f"""
                <div class="chart-container">
                    <canvas id="chart-{version.replace('.', '')}"></canvas>
                </div>
"""

        html_content += """
            </div>
"""

    html_content += """
        </div>
"""

    # Add comparison chart preview if available
    if "pynfs-comparison.png" in png_files:
        html_content += """
        <div class="details-section">
            <h2 style="margin-bottom: 20px; color: #2d3748;">Test Results Comparison</h2>
            <div class="png-preview">
                <a href="pynfs-comparison.png" target="_blank">
                    <img src="pynfs-comparison.png" alt="PyNFS Comparison Chart">
                </a>
            </div>
        </div>
"""

    html_content += """
        <div class="details-section">
            <h2 style="margin-bottom: 20px; color: #2d3748;">Detailed Test Results</h2>
            <div class="tabs">
"""

    # Add tabs for each version
    first = True
    for version in detailed_results.keys():
        active = "active" if first else ""
        html_content += f"""
                <button class="tab-button {active}" onclick="showTab('{version}')">{version.upper()}</button>
"""
        first = False

    html_content += """
            </div>
"""

    # Add tab content for each version
    first = True
    for version, categories in detailed_results.items():
        active = "active" if first else ""
        html_content += f"""
            <div id="tab-{version}" class="tab-content {active}">
"""

        # Sort categories by name
        for category_name in sorted(categories.keys()):
            category = categories[category_name]
            total_in_category = (
                len(category["passed"])
                + len(category["failed"])
                + len(category["skipped"])
                + len(category["error"])
            )

            if total_in_category == 0:
                continue

            html_content += f"""
                <div class="test-category">
                    <div class="category-header">
                        {category_name} ({total_in_category} tests)
                    </div>
                    <div class="test-list">
"""

            # Add passed tests
            for test in sorted(category["passed"], key=lambda x: x.get("name", "")):
                html_content += f"""
                        <div class="test-item passed">
                            <span class="test-name">{test.get('name', 'Unknown')}</span>
                            <span class="test-code">{test.get('code', '')}</span>
                        </div>
"""

            # Add failed tests
            for test in sorted(category["failed"], key=lambda x: x.get("name", "")):
                html_content += f"""
                        <div class="test-item failed">
                            <span class="test-name">{test.get('name', 'Unknown')}</span>
                            <span class="test-code">{test.get('code', '')}</span>
                        </div>
"""

            # Add error tests
            for test in sorted(category["error"], key=lambda x: x.get("name", "")):
                html_content += f"""
                        <div class="test-item error">
                            <span class="test-name">{test.get('name', 'Unknown')}</span>
                            <span class="test-code">{test.get('code', '')}</span>
                        </div>
"""

            # Add skipped tests (collapsed by default)
            if category["skipped"]:
                html_content += f"""
                        <details>
                            <summary style="cursor: pointer; padding: 10px; background: #f0f0f0; border-radius: 5px; margin-top: 10px;">
                                Skipped Tests ({len(category['skipped'])})
                            </summary>
                            <div style="margin-top: 10px;">
"""
                for test in sorted(
                    category["skipped"], key=lambda x: x.get("name", "")
                ):
                    html_content += f"""
                                <div class="test-item skipped">
                                    <span class="test-name">{test.get('name', 'Unknown')}</span>
                                    <span class="test-code">{test.get('code', '')}</span>
                                </div>
"""
                html_content += """
                            </div>
                        </details>
"""

            html_content += """
                    </div>
                </div>
"""

        html_content += """
            </div>
"""
        first = False

    html_content += """
        </div>

        <div class="footer">
            Generated by kdevops pynfs-visualize | 🤖 Generated with Claude Code
        </div>
    </div>

    <script>
        // Tab switching function
        function showTab(version) {
            // Hide all tabs
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.classList.remove('active');
            });
            document.querySelectorAll('.tab-button').forEach(button => {
                button.classList.remove('active');
            });

            // Show selected tab
            document.getElementById('tab-' + version).classList.add('active');
            event.target.classList.add('active');
        }
"""

    # Add fallback JavaScript charts if matplotlib is not available
    if not MATPLOTLIB_AVAILABLE:
        html_content += """
        // Chart initialization (fallback when PNGs are not available)
"""
        for chart in charts:
            version = chart["version"]
            canvas_id = f"chart-{version.replace('.', '')}"

            html_content += f"""
        if (document.getElementById('{canvas_id}')) {{
            new Chart(document.getElementById('{canvas_id}'), {{
                type: 'doughnut',
                data: {{
                    labels: ['Passed', 'Failed', 'Errors', 'Skipped'],
                    datasets: [{{
                        data: [{chart['passed']}, {chart['failed']}, {chart['errors']}, {chart['skipped']}],
                        backgroundColor: [
                            '#48bb78',
                            '#f56565',
                            '#ed8936',
                            '#a0aec0'
                        ],
                        borderWidth: 0
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{
                            position: 'bottom',
                            labels: {{
                                padding: 15,
                                font: {{
                                    size: 12
                                }}
                            }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    let label = context.label || '';
                                    if (label) {{
                                        label += ': ';
                                    }}
                                    label += context.parsed;
                                    let total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    let percentage = ((context.parsed / total) * 100).toFixed(1);
                                    label += ' (' + percentage + '%)';
                                    return label;
                                }}
                            }}
                        }}
                    }}
                }}
            }});
        }}
"""

    html_content += """
    </script>
</body>
</html>
"""

    return html_content, png_files


def main():
    parser = argparse.ArgumentParser(
        description="Generate HTML visualization for pynfs results"
    )
    parser.add_argument("results_dir", help="Path to results directory")
    parser.add_argument("kernel_version", help="Kernel version string")
    parser.add_argument("--output", "-o", help="Output HTML file path")

    args = parser.parse_args()

    # Generate the HTML report and PNG charts
    html_content, png_files = generate_html_report(
        args.results_dir, args.kernel_version
    )

    if not html_content:
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = Path(args.results_dir) / "html"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "index.html"

    # Write the HTML file
    with open(output_path, "w") as f:
        f.write(html_content)

    print(f"✅ HTML report generated: {output_path}")

    if png_files:
        print(f"✅ Generated {len(png_files)} PNG charts in: {output_path.parent}")
    elif MATPLOTLIB_AVAILABLE:
        print("⚠️  No PNG charts generated (no data)")
    else:
        print("⚠️  PNG charts not generated (matplotlib not installed)")
        print("   Install with: pip3 install matplotlib")

    return 0


if __name__ == "__main__":
    sys.exit(main())

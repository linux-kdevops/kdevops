#!/usr/bin/env python3
"""
Generate HTML visualization for NFS test results
"""

import json
import os
import sys
import glob
import base64
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Try to import matplotlib, but make it optional
try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print(
        "Warning: matplotlib not found. Graphs will not be generated.", file=sys.stderr
    )

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NFS Test Results - {timestamp}</title>
    <style>
        :root {{
            --primary-color: #2c3e50;
            --secondary-color: #3498db;
            --success-color: #27ae60;
            --danger-color: #e74c3c;
            --warning-color: #f39c12;
            --light-bg: #ecf0f1;
            --card-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}

        .header {{
            background: var(--primary-color);
            color: white;
            padding: 40px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}

        .header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(52, 152, 219, 0.1), rgba(46, 204, 113, 0.1));
        }}

        h1 {{
            margin: 0;
            font-size: 2.5em;
            position: relative;
            z-index: 1;
        }}

        .subtitle {{
            margin-top: 10px;
            opacity: 0.9;
            font-size: 1.1em;
            position: relative;
            z-index: 1;
        }}

        .content {{
            padding: 40px;
        }}

        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}

        .summary-card {{
            background: white;
            border: 1px solid #e0e0e0;
            padding: 25px;
            border-radius: 10px;
            text-align: center;
            transition: all 0.3s ease;
            box-shadow: var(--card-shadow);
        }}

        .summary-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.15);
        }}

        .summary-card.success {{
            background: linear-gradient(135deg, #667eea20 0%, #27ae6020 100%);
            border-color: var(--success-color);
        }}

        .summary-card.danger {{
            background: linear-gradient(135deg, #e74c3c20 0%, #c0392b20 100%);
            border-color: var(--danger-color);
        }}

        .summary-card .value {{
            font-size: 2.5em;
            font-weight: bold;
            margin: 10px 0;
        }}

        .summary-card.success .value {{
            color: var(--success-color);
        }}

        .summary-card.danger .value {{
            color: var(--danger-color);
        }}

        .summary-card .label {{
            color: #7f8c8d;
            font-size: 0.95em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .test-suite {{
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            margin-bottom: 30px;
            overflow: hidden;
            box-shadow: var(--card-shadow);
        }}

        .suite-header {{
            background: linear-gradient(135deg, var(--secondary-color), #5dade2);
            color: white;
            padding: 20px 30px;
            cursor: pointer;
            position: relative;
            transition: all 0.3s ease;
        }}

        .suite-header:hover {{
            background: linear-gradient(135deg, #2980b9, var(--secondary-color));
        }}

        .suite-header h2 {{
            margin: 0 0 10px 0;
            font-size: 1.5em;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .suite-stats {{
            display: flex;
            gap: 20px;
            font-size: 0.9em;
            opacity: 0.95;
        }}

        .suite-content {{
            padding: 25px;
            background: #fafafa;
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.5s ease;
        }}

        .suite-content.expanded {{
            max-height: 2000px;
        }}

        .test-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
        }}

        .test-table th {{
            background: var(--primary-color);
            color: white;
            padding: 12px;
            text-align: left;
            font-weight: 600;
        }}

        .test-table td {{
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }}

        .test-table tr:last-child td {{
            border-bottom: none;
        }}

        .test-table tr:hover {{
            background: #f5f5f5;
        }}

        .status {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 600;
            text-transform: uppercase;
        }}

        .status.passed {{
            background: var(--success-color);
            color: white;
        }}

        .status.failed {{
            background: var(--danger-color);
            color: white;
        }}

        .status.skipped {{
            background: var(--warning-color);
            color: white;
        }}

        .progress-bar {{
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }}

        .progress-fill {{
            height: 100%;
            display: flex;
            transition: width 0.5s ease;
        }}

        .progress-passed {{
            background: linear-gradient(135deg, var(--success-color), #2ecc71);
        }}

        .progress-failed {{
            background: linear-gradient(135deg, var(--danger-color), #c0392b);
        }}

        .progress-skipped {{
            background: linear-gradient(135deg, var(--warning-color), #e67e22);
        }}

        .graph-container {{
            margin: 30px 0;
            text-align: center;
        }}

        .graph-container img {{
            max-width: 100%;
            height: auto;
            border-radius: 8px;
            box-shadow: var(--card-shadow);
        }}

        .config-section {{
            background: #f8f9fa;
            border-left: 4px solid var(--secondary-color);
            padding: 20px;
            margin: 30px 0;
            border-radius: 4px;
        }}

        .config-section h3 {{
            color: var(--primary-color);
            margin-bottom: 15px;
        }}

        .config-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 10px;
        }}

        .config-item {{
            display: flex;
            padding: 8px;
            background: white;
            border-radius: 4px;
        }}

        .config-key {{
            font-weight: 600;
            color: var(--primary-color);
            margin-right: 10px;
        }}

        .config-value {{
            color: #555;
        }}

        .footer {{
            text-align: center;
            padding: 20px;
            background: var(--light-bg);
            color: #7f8c8d;
            border-top: 1px solid #e0e0e0;
        }}

        .toggle-icon {{
            transition: transform 0.3s ease;
            display: inline-block;
        }}

        .suite-header.expanded .toggle-icon {{
            transform: rotate(90deg);
        }}

        @media (max-width: 768px) {{
            .summary-grid {{
                grid-template-columns: 1fr;
            }}

            .config-grid {{
                grid-template-columns: 1fr;
            }}

            h1 {{
                font-size: 1.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🧪 NFS Test Results</h1>
            <div class="subtitle">Generated on {timestamp}</div>
        </div>

        <div class="content">
            <!-- Summary Cards -->
            <div class="summary-grid">
                <div class="summary-card">
                    <div class="label">Total Tests</div>
                    <div class="value">{total_tests}</div>
                </div>
                <div class="summary-card success">
                    <div class="label">Passed</div>
                    <div class="value">{passed_tests}</div>
                </div>
                <div class="summary-card danger">
                    <div class="label">Failed</div>
                    <div class="value">{failed_tests}</div>
                </div>
                <div class="summary-card">
                    <div class="label">Pass Rate</div>
                    <div class="value">{pass_rate:.1f}%</div>
                </div>
                <div class="summary-card">
                    <div class="label">Total Time</div>
                    <div class="value">{total_time}</div>
                </div>
                <div class="summary-card">
                    <div class="label">Test Suites</div>
                    <div class="value">{num_suites}</div>
                </div>
            </div>

            <!-- Overall Progress Bar -->
            <div class="progress-bar">
                <div class="progress-fill" style="width: 100%;">
                    <div class="progress-passed" style="width: {pass_percentage:.1f}%;"></div>
                    <div class="progress-failed" style="width: {fail_percentage:.1f}%;"></div>
                </div>
            </div>

            <!-- Graphs -->
            {graphs_html}

            <!-- Test Suites -->
            <h2 style="margin: 40px 0 20px 0; color: var(--primary-color);">Test Suite Details</h2>
            {test_suites_html}

            <!-- Configuration -->
            {config_html}
        </div>

        <div class="footer">
            <p>Generated by kdevops NFS Test Visualization</p>
            <p>Report generated at {timestamp}</p>
        </div>
    </div>

    <script>
        // Toggle test suite expansion
        document.querySelectorAll('.suite-header').forEach(header => {{
            header.addEventListener('click', () => {{
                header.classList.toggle('expanded');
                const content = header.nextElementSibling;
                content.classList.toggle('expanded');
            }});
        }});

        // Auto-expand suites with failures
        document.addEventListener('DOMContentLoaded', () => {{
            document.querySelectorAll('.suite-header[data-has-failures="true"]').forEach(header => {{
                header.click();
            }});
        }});
    </script>
</body>
</html>
"""


def format_time(seconds):
    """Format seconds into human-readable time"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def generate_suite_chart(suite_name, suite_data, output_dir):
    """Generate a pie chart for test suite results"""
    if not HAS_MATPLOTLIB:
        return None

    try:
        # Count results
        passed = sum(r["summary"]["passed"] for r in suite_data)
        failed = sum(r["summary"]["failed"] for r in suite_data)

        if passed + failed == 0:
            return None

        # Create pie chart
        fig, ax = plt.subplots(figsize=(6, 6))
        labels = []
        sizes = []
        colors = []

        if passed > 0:
            labels.append(f"Passed ({passed})")
            sizes.append(passed)
            colors.append("#27ae60")

        if failed > 0:
            labels.append(f"Failed ({failed})")
            sizes.append(failed)
            colors.append("#e74c3c")

        ax.pie(
            sizes,
            labels=labels,
            colors=colors,
            autopct="%1.1f%%",
            startangle=90,
            textprops={"fontsize": 12},
        )
        ax.set_title(
            f"{suite_name.upper()} Test Results", fontsize=14, fontweight="bold"
        )

        # Save to file
        chart_path = os.path.join(output_dir, f"{suite_name}_pie_chart.png")
        plt.savefig(chart_path, dpi=100, bbox_inches="tight", transparent=True)
        plt.close()

        return chart_path
    except Exception as e:
        print(
            f"Warning: Could not generate chart for {suite_name}: {e}", file=sys.stderr
        )
        return None


def generate_overall_chart(summary, output_dir):
    """Generate overall test results chart"""
    if not HAS_MATPLOTLIB:
        return None

    try:
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Pie chart for pass/fail
        passed = summary["total_passed"]
        failed = summary["total_failed"]

        if passed + failed > 0:
            sizes = [passed, failed]
            labels = [f"Passed ({passed})", f"Failed ({failed})"]
            colors = ["#27ae60", "#e74c3c"]

            ax1.pie(
                sizes,
                labels=labels,
                colors=colors,
                autopct="%1.1f%%",
                startangle=90,
                textprops={"fontsize": 12},
            )
            ax1.set_title("Overall Test Results", fontsize=14, fontweight="bold")

        # Bar chart for test suites
        if summary["test_suites_run"]:
            suites = summary["test_suites_run"]
            suite_counts = [len(summary.get(s, [])) for s in suites]

            bars = ax2.bar(range(len(suites)), suite_counts, color="#3498db")
            ax2.set_xlabel("Test Suite", fontsize=12)
            ax2.set_ylabel("Number of Tests", fontsize=12)
            ax2.set_title("Tests per Suite", fontsize=14, fontweight="bold")
            ax2.set_xticks(range(len(suites)))
            ax2.set_xticklabels(suites, rotation=45, ha="right")

            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax2.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{int(height)}",
                    ha="center",
                    va="bottom",
                )

        plt.tight_layout()

        # Save to file
        chart_path = os.path.join(output_dir, "overall_results.png")
        plt.savefig(chart_path, dpi=100, bbox_inches="tight", transparent=True)
        plt.close()

        return chart_path
    except Exception as e:
        print(f"Warning: Could not generate overall chart: {e}", file=sys.stderr)
        return None


def embed_image(image_path):
    """Embed image as base64 data URI"""
    if not os.path.exists(image_path):
        return None

    try:
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        return f"data:image/png;base64,{data}"
    except:
        return None


def generate_html(results, output_dir):
    """Generate HTML report from parsed results"""
    summary = results["overall_summary"]

    # Calculate statistics
    total_tests = summary["total_tests"]
    passed_tests = summary["total_passed"]
    failed_tests = summary["total_failed"]
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    pass_percentage = pass_rate
    fail_percentage = 100 - pass_percentage
    total_time = format_time(summary["total_time"])
    num_suites = len(summary["test_suites_run"])

    # Generate graphs
    graphs_html = ""
    overall_chart = generate_overall_chart(summary, output_dir)
    if overall_chart:
        img_data = embed_image(overall_chart)
        if img_data:
            graphs_html += f"""
            <div class="graph-container">
                <h2 style="color: var(--primary-color); margin-bottom: 20px;">Test Results Overview</h2>
                <img src="{img_data}" alt="Overall Results">
            </div>
            """

    # Generate test suites HTML
    test_suites_html = ""
    for suite_name, suite_data in results["test_suites"].items():
        if not suite_data:
            continue

        # Calculate suite statistics
        suite_total = sum(r["summary"]["total"] for r in suite_data)
        suite_passed = sum(r["summary"]["passed"] for r in suite_data)
        suite_failed = sum(r["summary"]["failed"] for r in suite_data)
        suite_time = sum(r["summary"]["total_time"] for r in suite_data)
        has_failures = suite_failed > 0

        # Generate suite chart
        suite_chart = generate_suite_chart(suite_name, suite_data, output_dir)

        # Build test details table
        test_rows = ""
        for result in suite_data:
            for test in result["tests"]:
                status_class = test["status"].lower()
                test_rows += f"""
                <tr>
                    <td>{test['name']}</td>
                    <td>{test['description'][:100]}...</td>
                    <td><span class="status {status_class}">{test['status']}</span></td>
                    <td>{test['duration']:.3f}s</td>
                </tr>
                """

        # Build suite HTML
        test_suites_html += f"""
        <div class="test-suite">
            <div class="suite-header" data-has-failures="{str(has_failures).lower()}">
                <h2>
                    <span><span class="toggle-icon">▶</span> {suite_name.upper()}</span>
                    <span style="font-size: 0.7em; font-weight: normal;">
                        {suite_passed}/{suite_total} passed
                    </span>
                </h2>
                <div class="suite-stats">
                    <span>✓ Passed: {suite_passed}</span>
                    <span>✗ Failed: {suite_failed}</span>
                    <span>⏱ Time: {format_time(suite_time)}</span>
                </div>
            </div>
            <div class="suite-content">
                {f'<div class="graph-container"><img src="{embed_image(suite_chart)}" alt="{suite_name} Results"></div>' if suite_chart and embed_image(suite_chart) else ''}
                <table class="test-table">
                    <thead>
                        <tr>
                            <th>Test Name</th>
                            <th>Description</th>
                            <th>Status</th>
                            <th>Duration</th>
                        </tr>
                    </thead>
                    <tbody>
                        {test_rows}
                    </tbody>
                </table>
            </div>
        </div>
        """

    # Generate configuration HTML
    config_html = ""
    if results["test_suites"]:
        # Get configuration from first test suite
        for suite_data in results["test_suites"].values():
            if suite_data and suite_data[0]["configuration"]:
                config = suite_data[0]["configuration"]
                config_items = ""
                for key, value in sorted(config.items()):
                    if key and value and value != "None":
                        config_items += f"""
                        <div class="config-item">
                            <span class="config-key">{key.replace('_', ' ').title()}:</span>
                            <span class="config-value">{value}</span>
                        </div>
                        """

                if config_items:
                    config_html = f"""
                    <div class="config-section">
                        <h3>Test Configuration</h3>
                        <div class="config-grid">
                            {config_items}
                        </div>
                    </div>
                    """
                break

    # Generate final HTML
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    html_content = HTML_TEMPLATE.format(
        timestamp=timestamp,
        total_tests=total_tests,
        passed_tests=passed_tests,
        failed_tests=failed_tests,
        pass_rate=pass_rate,
        pass_percentage=pass_percentage,
        fail_percentage=fail_percentage,
        total_time=total_time,
        num_suites=num_suites,
        graphs_html=graphs_html,
        test_suites_html=test_suites_html,
        config_html=config_html,
    )

    # Write HTML file
    html_path = os.path.join(output_dir, "index.html")
    with open(html_path, "w") as f:
        f.write(html_content)

    return html_path


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        results_dir = "workflows/nfstest/results/last-run"

    if not os.path.exists(results_dir):
        print(
            f"Error: Results directory '{results_dir}' does not exist", file=sys.stderr
        )
        sys.exit(1)

    # Check for parsed results
    parsed_file = os.path.join(results_dir, "parsed_results.json")
    if not os.path.exists(parsed_file):
        print(
            f"Error: Parsed results file not found. Run parse_nfstest_results.py first.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Load parsed results
    with open(parsed_file, "r") as f:
        results = json.load(f)

    # Create HTML output directory - use absolute path from results_dir
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(results_dir)))
    html_dir = os.path.join(base_dir, "html")
    os.makedirs(html_dir, exist_ok=True)

    # Generate HTML report
    html_path = generate_html(results, html_dir)

    print(f"HTML report generated: {html_path}")
    print(f"Directory ready for transfer: {html_dir}")


if __name__ == "__main__":
    main()

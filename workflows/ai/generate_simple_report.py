#!/usr/bin/env python3
"""
Generate simple text report from AI benchmark results
"""

import json
import os
import glob
from datetime import datetime


def generate_report():
    """Generate a simple text report from benchmark results"""

    results_dir = "results"
    pattern = os.path.join(results_dir, "results_*.json")
    result_files = glob.glob(pattern)

    if not result_files:
        # Try alternative pattern
        pattern = os.path.join(results_dir, "benchmark_results_*.json")
        result_files = glob.glob(pattern)

    if not result_files:
        print("No result files found")
        return

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("AI BENCHMARK RESULTS REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("")

    for result_file in sorted(result_files):
        with open(result_file, "r") as f:
            data = json.load(f)

        report_lines.append(f"Test Run: {os.path.basename(result_file)}")
        report_lines.append("-" * 80)

        # Configuration
        config = data.get("config", {})
        report_lines.append("Configuration:")
        report_lines.append(
            f"  Dataset Size: {config.get('dataset_size', 'N/A')} vectors"
        )
        report_lines.append(
            f"  Vector Dimensions: {config.get('vector_dimensions', 'N/A')}"
        )
        report_lines.append(f"  Index Type: {config.get('index_type', 'N/A')}")
        report_lines.append("")

        # Insert Performance
        insert_perf = data.get("insert_performance", {})
        report_lines.append("Insert Performance:")
        report_lines.append(
            f"  Total Vectors: {insert_perf.get('total_vectors', 'N/A')}"
        )
        report_lines.append(
            f"  Total Time: {insert_perf.get('total_time_seconds', 'N/A')} seconds"
        )
        report_lines.append(
            f"  Throughput: {insert_perf.get('vectors_per_second', 'N/A'):.2f} vectors/second"
        )
        report_lines.append("")

        # Query Performance
        query_perf = data.get("query_performance", {})
        report_lines.append("Query Performance:")
        for config in query_perf.get("configurations", []):
            report_lines.append(
                f"  Batch Size: {config.get('batch_size', 'N/A')}, Top-K: {config.get('top_k', 'N/A')}"
            )
            report_lines.append(
                f"    Average Latency: {config.get('avg_latency_ms', 'N/A'):.2f} ms"
            )
            report_lines.append(
                f"    P95 Latency: {config.get('p95_latency_ms', 'N/A'):.2f} ms"
            )
            report_lines.append(
                f"    Throughput: {config.get('queries_per_second', 'N/A'):.2f} queries/second"
            )
        report_lines.append("")

        # Index Performance
        index_perf = data.get("index_performance", {})
        report_lines.append("Index Performance:")
        report_lines.append(f"  Index Type: {index_perf.get('index_type', 'N/A')}")
        report_lines.append(
            f"  Build Time: {index_perf.get('build_time_seconds', 'N/A'):.2f} seconds"
        )
        report_lines.append("")
        report_lines.append("=" * 80)
        report_lines.append("")

    # Write report
    report_file = os.path.join(results_dir, "benchmark_report.txt")
    with open(report_file, "w") as f:
        f.write("\n".join(report_lines))

    print(f"Report generated: {report_file}")

    # Also print to console
    print("\n".join(report_lines))


if __name__ == "__main__":
    generate_report()

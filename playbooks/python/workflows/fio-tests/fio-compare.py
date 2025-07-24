#!/usr/bin/python3
# SPDX-License-Identifier: copyleft-next-0.3.1

# Compare fio test results between baseline and dev configurations for A/B testing

import pandas as pd
import matplotlib.pyplot as plt
import json
import argparse
import os
import sys
from pathlib import Path

def parse_fio_json(file_path):
    """Parse fio JSON output and extract key metrics"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        if 'jobs' not in data:
            return None

        job = data['jobs'][0]  # Use first job

        # Extract read metrics
        read_stats = job.get('read', {})
        read_bw = read_stats.get('bw', 0) / 1024  # Convert to MB/s
        read_iops = read_stats.get('iops', 0)
        read_lat_mean = read_stats.get('lat_ns', {}).get('mean', 0) / 1000000  # Convert to ms

        # Extract write metrics
        write_stats = job.get('write', {})
        write_bw = write_stats.get('bw', 0) / 1024  # Convert to MB/s
        write_iops = write_stats.get('iops', 0)
        write_lat_mean = write_stats.get('lat_ns', {}).get('mean', 0) / 1000000  # Convert to ms

        return {
            'read_bw': read_bw,
            'read_iops': read_iops,
            'read_lat': read_lat_mean,
            'write_bw': write_bw,
            'write_iops': write_iops,
            'write_lat': write_lat_mean,
            'total_bw': read_bw + write_bw,
            'total_iops': read_iops + write_iops
        }
    except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
        print(f"Error parsing {file_path}: {e}")
        return None

def extract_test_params(filename):
    """Extract test parameters from filename"""
    parts = filename.replace('.json', '').replace('results_', '').split('_')

    params = {}
    for part in parts:
        if part.startswith('bs'):
            params['block_size'] = part[2:]
        elif part.startswith('iodepth'):
            params['io_depth'] = int(part[7:])
        elif part.startswith('jobs'):
            params['num_jobs'] = int(part[4:])
        elif part in ['randread', 'randwrite', 'seqread', 'seqwrite', 'mixed_75_25', 'mixed_50_50']:
            params['pattern'] = part

    return params

def load_results(results_dir, config_name):
    """Load all fio results from a directory"""
    results = []

    json_files = list(Path(results_dir).glob('results_*.json'))
    if not json_files:
        json_files = list(Path(results_dir).glob('results_*.txt'))

    for file_path in json_files:
        if file_path.name.endswith('.json'):
            metrics = parse_fio_json(file_path)
        else:
            continue

        if metrics:
            params = extract_test_params(file_path.name)
            result = {**params, **metrics, 'config': config_name}
            results.append(result)

    return pd.DataFrame(results) if results else None

def plot_comparison_bar_chart(baseline_df, dev_df, metric, output_file, title, ylabel):
    """Create side-by-side bar chart comparison"""
    if baseline_df.empty or dev_df.empty:
        return

    # Group by test configuration and calculate means
    baseline_grouped = baseline_df.groupby(['pattern', 'block_size', 'io_depth'])[metric].mean()
    dev_grouped = dev_df.groupby(['pattern', 'block_size', 'io_depth'])[metric].mean()

    # Find common test configurations
    common_configs = baseline_grouped.index.intersection(dev_grouped.index)

    if len(common_configs) == 0:
        return

    baseline_values = [baseline_grouped[config] for config in common_configs]
    dev_values = [dev_grouped[config] for config in common_configs]
    
    # Create labels from config tuples
    labels = [f"{pattern}\n{bs}@{depth}" for pattern, bs, depth in common_configs]
    
    x = range(len(labels))
    width = 0.35
    
    plt.figure(figsize=(16, 8))

    plt.bar([i - width/2 for i in x], baseline_values, width, 
            label='Baseline', color='skyblue', edgecolor='navy')
    plt.bar([i + width/2 for i in x], dev_values, width, 
            label='Development', color='lightcoral', edgecolor='darkred')

    # Add percentage improvement annotations
    for i, (baseline_val, dev_val) in enumerate(zip(baseline_values, dev_values)):
        if baseline_val > 0:
            improvement = ((dev_val - baseline_val) / baseline_val) * 100
            y_pos = max(baseline_val, dev_val) * 1.05
            color = 'green' if improvement > 0 else 'red'
            plt.text(i, y_pos, f'{improvement:+.1f}%', 
                    ha='center', va='bottom', color=color, fontweight='bold')
    
    plt.xlabel('Test Configuration (Pattern Block_Size@IO_Depth)')
    plt.ylabel(ylabel)
    plt.title(title)
    plt.xticks(x, labels, rotation=45, ha='right')
    plt.legend()
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

def plot_performance_delta(baseline_df, dev_df, output_file):
    """Plot performance delta (percentage improvement) across metrics"""
    if baseline_df.empty or dev_df.empty:
        return

    metrics = ['total_bw', 'total_iops', 'read_lat', 'write_lat']
    metric_names = ['Bandwidth', 'IOPS', 'Read Latency', 'Write Latency']
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()

    for idx, (metric, name) in enumerate(zip(metrics, metric_names)):
        baseline_grouped = baseline_df.groupby(['pattern', 'block_size', 'io_depth'])[metric].mean()
        dev_grouped = dev_df.groupby(['pattern', 'block_size', 'io_depth'])[metric].mean()
        
        common_configs = baseline_grouped.index.intersection(dev_grouped.index)

        if len(common_configs) == 0:
            continue

        # Calculate percentage changes
        percent_changes = []
        config_labels = []

        for config in common_configs:
            baseline_val = baseline_grouped[config]
            dev_val = dev_grouped[config]

            if baseline_val > 0:
                # For latency, lower is better, so invert the calculation
                if 'lat' in metric:
                    change = ((baseline_val - dev_val) / baseline_val) * 100
                else:
                    change = ((dev_val - baseline_val) / baseline_val) * 100

                percent_changes.append(change)
                pattern, bs, depth = config
                config_labels.append(f"{pattern}\n{bs}@{depth}")

        if percent_changes:
            colors = ['green' if x > 0 else 'red' for x in percent_changes]
            bars = axes[idx].bar(range(len(percent_changes)), percent_changes, color=colors)

            # Add value labels on bars
            for bar, value in zip(bars, percent_changes):
                height = bar.get_height()
                axes[idx].text(bar.get_x() + bar.get_width()/2., height,
                             f'{value:.1f}%', ha='center', 
                             va='bottom' if height > 0 else 'top')

            axes[idx].set_title(f'{name} Performance Change')
            axes[idx].set_ylabel('Percentage Change (%)')
            axes[idx].set_xticks(range(len(config_labels)))
            axes[idx].set_xticklabels(config_labels, rotation=45, ha='right')
            axes[idx].axhline(y=0, color='black', linestyle='-', alpha=0.3)
            axes[idx].grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

def generate_summary_report(baseline_df, dev_df, output_file):
    """Generate a text summary report of the comparison"""
    with open(output_file, 'w') as f:
        f.write("FIO Performance Comparison Report\n")
        f.write("=" * 40 + "\n\n")

        f.write(f"Baseline tests: {len(baseline_df)} configurations\n")
        f.write(f"Development tests: {len(dev_df)} configurations\n\n")

        metrics = ['total_bw', 'total_iops', 'read_lat', 'write_lat']
        metric_names = ['Total Bandwidth (MB/s)', 'Total IOPS', 'Read Latency (ms)', 'Write Latency (ms)']

        for metric, name in zip(metrics, metric_names):
            f.write(f"{name}:\n")
            f.write("-" * len(name) + "\n")

            baseline_mean = baseline_df[metric].mean()
            dev_mean = dev_df[metric].mean()

            if baseline_mean > 0:
                if 'lat' in metric:
                    improvement = ((baseline_mean - dev_mean) / baseline_mean) * 100
                    direction = "reduction" if improvement > 0 else "increase"
                else:
                    improvement = ((dev_mean - baseline_mean) / baseline_mean) * 100
                    direction = "improvement" if improvement > 0 else "regression"

                f.write(f"  Baseline average: {baseline_mean:.2f}\n")
                f.write(f"  Development average: {dev_mean:.2f}\n")
                f.write(f"  Change: {improvement:+.1f}% {direction}\n\n")
            else:
                f.write(f"  No data available\n\n")

def main():
    parser = argparse.ArgumentParser(description='Compare fio performance between baseline and development configurations')
    parser.add_argument('baseline_dir', type=str, help='Directory containing baseline results')
    parser.add_argument('dev_dir', type=str, help='Directory containing development results')
    parser.add_argument('--output-dir', type=str, default='.', help='Output directory for comparison graphs')
    parser.add_argument('--prefix', type=str, default='fio_comparison', help='Prefix for output files')
    parser.add_argument('--baseline-label', type=str, default='Baseline', help='Label for baseline configuration')
    parser.add_argument('--dev-label', type=str, default='Development', help='Label for development configuration')

    args = parser.parse_args()

    if not os.path.exists(args.baseline_dir):
        print(f"Error: Baseline directory '{args.baseline_dir}' not found.")
        sys.exit(1)

    if not os.path.exists(args.dev_dir):
        print(f"Error: Development directory '{args.dev_dir}' not found.")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    print("Loading baseline results...")
    baseline_df = load_results(args.baseline_dir, args.baseline_label)

    print("Loading development results...")
    dev_df = load_results(args.dev_dir, args.dev_label)

    if baseline_df is None or baseline_df.empty:
        print("No baseline results found.")
        sys.exit(1)

    if dev_df is None or dev_df.empty:
        print("No development results found.")
        sys.exit(1)

    print(f"Comparing {len(baseline_df)} baseline vs {len(dev_df)} development results...")

    # Generate comparison charts
    plot_comparison_bar_chart(baseline_df, dev_df, 'total_bw', 
                             os.path.join(args.output_dir, f'{args.prefix}_bandwidth_comparison.png'),
                             'Bandwidth Comparison', 'Bandwidth (MB/s)')

    plot_comparison_bar_chart(baseline_df, dev_df, 'total_iops',
                             os.path.join(args.output_dir, f'{args.prefix}_iops_comparison.png'),
                             'IOPS Comparison', 'IOPS')

    plot_performance_delta(baseline_df, dev_df,
                          os.path.join(args.output_dir, f'{args.prefix}_performance_delta.png'))

    # Generate summary report
    generate_summary_report(baseline_df, dev_df,
                           os.path.join(args.output_dir, f'{args.prefix}_summary.txt'))

    print(f"Comparison results saved to {args.output_dir}")

if __name__ == '__main__':
    main()

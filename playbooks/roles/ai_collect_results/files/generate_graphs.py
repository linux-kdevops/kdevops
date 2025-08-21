#!/usr/bin/env python3
"""
Generate graphs and analysis for AI benchmark results
"""

import json
import os
import sys
import glob
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Use non-interactive backend
import matplotlib.pyplot as plt
from datetime import datetime
from pathlib import Path
from collections import defaultdict


def _extract_filesystem_config(result):
    """Extract filesystem type and block size from result data.
    Returns (fs_type, block_size, config_key)"""
    filename = result.get("_file", "")

    # Primary: Extract filesystem type from filename (more reliable than JSON)
    fs_type = "unknown"
    block_size = "default"

    if "xfs" in filename:
        fs_type = "xfs"
        # Check larger sizes first to avoid substring matches
        if "64k" in filename and "64k-" in filename:
            block_size = "64k"
        elif "32k" in filename and "32k-" in filename:
            block_size = "32k"
        elif "16k" in filename and "16k-" in filename:
            block_size = "16k"
        elif "4k" in filename and "4k-" in filename:
            block_size = "4k"
    elif "ext4" in filename:
        fs_type = "ext4"
        if "4k" in filename and "4k-" in filename:
            block_size = "4k"
        elif "16k" in filename and "16k-" in filename:
            block_size = "16k"
    elif "btrfs" in filename:
        fs_type = "btrfs"

    # Fallback: Check JSON data if filename parsing failed
    if fs_type == "unknown":
        fs_type = result.get("filesystem", "unknown")

    # Create descriptive config key
    config_key = f"{fs_type}-{block_size}" if block_size != "default" else fs_type
    return fs_type, block_size, config_key


def _extract_node_info(result):
    """Extract node hostname and determine if it's a dev node.
    Returns (hostname, is_dev_node)"""
    # Get hostname from system_info (preferred) or fall back to filename
    system_info = result.get("system_info", {})
    hostname = system_info.get("hostname", "")
    
    # If no hostname in system_info, try extracting from filename
    if not hostname:
        filename = result.get("_file", "")
        # Remove results_ prefix and .json suffix
        hostname = filename.replace("results_", "").replace(".json", "")
        # Remove iteration number if present (_1, _2, etc.)
        if "_" in hostname and hostname.split("_")[-1].isdigit():
            hostname = "_".join(hostname.split("_")[:-1])
    
    # Determine if this is a dev node
    is_dev = hostname.endswith("-dev")
    
    return hostname, is_dev


def load_results(results_dir):
    """Load all JSON result files from the directory"""
    results = []
    # Only load results_*.json files, not consolidated or other JSON files
    json_files = glob.glob(os.path.join(results_dir, "results_*.json"))

    for json_file in json_files:
        try:
            with open(json_file, "r") as f:
                data = json.load(f)
                # Add filename for filesystem detection
                data["_file"] = os.path.basename(json_file)
                results.append(data)
        except Exception as e:
            print(f"Error loading {json_file}: {e}")

    return results


def create_simple_performance_trends(results, output_dir):
    """Create multi-node performance trends chart"""
    if not results:
        return

    # Group results by node
    node_performance = defaultdict(lambda: {
        "insert_rates": [],
        "insert_times": [],
        "iterations": [],
        "is_dev": False,
    })

    for result in results:
        hostname, is_dev = _extract_node_info(result)
        
        if hostname not in node_performance:
            node_performance[hostname] = {
                "insert_rates": [],
                "insert_times": [],
                "iterations": [],
                "is_dev": is_dev,
            }

        insert_perf = result.get("insert_performance", {})
        if insert_perf:
            node_performance[hostname]["insert_rates"].append(
                insert_perf.get("vectors_per_second", 0)
            )
            fs_performance[config_key]["insert_times"].append(
                insert_perf.get("total_time_seconds", 0)
            )
            fs_performance[config_key]["iterations"].append(
                len(fs_performance[config_key]["insert_rates"])
            )

    # Check if we have multi-filesystem data
    if len(fs_performance) > 1:
        # Multi-filesystem mode: separate lines for each filesystem
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        colors = ["b", "r", "g", "m", "c", "y", "k"]
        color_idx = 0
        
        for config_key, perf_data in fs_performance.items():
            if not perf_data["insert_rates"]:
                continue
                
            color = colors[color_idx % len(colors)]
            iterations = list(range(1, len(perf_data["insert_rates"]) + 1))
            
            # Plot insert rate  
            ax1.plot(
                iterations,
                perf_data["insert_rates"], 
                f"{color}-o",
                linewidth=2,
                markersize=6,
                label=config_key.upper(),
            )
            
            # Plot insert time
            ax2.plot(
                iterations,
                perf_data["insert_times"],
                f"{color}-o", 
                linewidth=2,
                markersize=6,
                label=config_key.upper(),
            )
            
            color_idx += 1
            
        ax1.set_xlabel("Iteration")
        ax1.set_ylabel("Vectors/Second")
        ax1.set_title("Milvus Insert Rate by Storage Filesystem")
        ax1.grid(True, alpha=0.3)
        ax1.legend()
        
        ax2.set_xlabel("Iteration")
        ax2.set_ylabel("Total Time (seconds)")
        ax2.set_title("Milvus Insert Time by Storage Filesystem")
        ax2.grid(True, alpha=0.3)
        ax2.legend()
    else:
        # Single filesystem mode: original behavior
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Extract insert data from single filesystem
        config_key = list(fs_performance.keys())[0] if fs_performance else None
        if config_key:
            perf_data = fs_performance[config_key]
            iterations = list(range(1, len(perf_data["insert_rates"]) + 1))
            
            # Plot insert rate
            ax1.plot(
                iterations,
                perf_data["insert_rates"],
                "b-o",
                linewidth=2,
                markersize=6,
            )
            ax1.set_xlabel("Iteration")
            ax1.set_ylabel("Vectors/Second") 
            ax1.set_title("Vector Insert Rate Performance")
            ax1.grid(True, alpha=0.3)
            
            # Plot insert time
            ax2.plot(
                iterations,
                perf_data["insert_times"],
                "r-o",
                linewidth=2,
                markersize=6,
            )
            ax2.set_xlabel("Iteration")
            ax2.set_ylabel("Total Time (seconds)")
            ax2.set_title("Vector Insert Time Performance") 
            ax2.grid(True, alpha=0.3)
            
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "performance_trends.png"), dpi=150)
    plt.close()


def create_heatmap_analysis(results, output_dir):
    """Create multi-filesystem heatmap showing query performance"""
    if not results:
        return

    # Group data by filesystem configuration
    fs_performance = defaultdict(lambda: {
        "query_data": [],
        "config_key": "",
    })

    for result in results:
        fs_type, block_size, config_key = _extract_filesystem_config(result)
        
        query_perf = result.get("query_performance", {})
        for topk, topk_data in query_perf.items():
            for batch, batch_data in topk_data.items():
                qps = batch_data.get("queries_per_second", 0)
                fs_performance[config_key]["query_data"].append({
                    "topk": topk,
                    "batch": batch,
                    "qps": qps,
                })
                fs_performance[config_key]["config_key"] = config_key

    # Check if we have multi-filesystem data
    if len(fs_performance) > 1:
        # Multi-filesystem mode: separate heatmaps for each filesystem
        num_fs = len(fs_performance)
        fig, axes = plt.subplots(1, num_fs, figsize=(5*num_fs, 6))
        if num_fs == 1:
            axes = [axes]
        
        # Define common structure for consistency
        topk_order = ["topk_1", "topk_10", "topk_100"]
        batch_order = ["batch_1", "batch_10", "batch_100"]
        
        for idx, (config_key, perf_data) in enumerate(fs_performance.items()):
            # Create matrix for this filesystem
            matrix = np.zeros((len(topk_order), len(batch_order)))
            
            # Fill matrix with data
            query_dict = {}
            for item in perf_data["query_data"]:
                query_dict[(item["topk"], item["batch"])] = item["qps"]
                
            for i, topk in enumerate(topk_order):
                for j, batch in enumerate(batch_order):
                    matrix[i, j] = query_dict.get((topk, batch), 0)
            
            # Plot heatmap
            im = axes[idx].imshow(matrix, cmap='viridis', aspect='auto')
            axes[idx].set_title(f"{config_key.upper()} Query Performance")
            axes[idx].set_xticks(range(len(batch_order)))
            axes[idx].set_xticklabels([b.replace("batch_", "Batch ") for b in batch_order])
            axes[idx].set_yticks(range(len(topk_order)))
            axes[idx].set_yticklabels([t.replace("topk_", "Top-") for t in topk_order])
            
            # Add text annotations
            for i in range(len(topk_order)):
                for j in range(len(batch_order)):
                    axes[idx].text(j, i, f'{matrix[i, j]:.0f}',
                                 ha="center", va="center", color="white", fontweight="bold")
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=axes[idx])
            cbar.set_label('Queries Per Second (QPS)')
    else:
        # Single filesystem mode
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))
        
        if fs_performance:
            config_key = list(fs_performance.keys())[0]
            perf_data = fs_performance[config_key]
            
            # Create matrix
            topk_order = ["topk_1", "topk_10", "topk_100"]
            batch_order = ["batch_1", "batch_10", "batch_100"]
            matrix = np.zeros((len(topk_order), len(batch_order)))
            
            # Fill matrix with data
            query_dict = {}
            for item in perf_data["query_data"]:
                query_dict[(item["topk"], item["batch"])] = item["qps"]
                
            for i, topk in enumerate(topk_order):
                for j, batch in enumerate(batch_order):
                    matrix[i, j] = query_dict.get((topk, batch), 0)
            
            # Plot heatmap
            im = ax.imshow(matrix, cmap='viridis', aspect='auto')
            ax.set_title("Milvus Query Performance Heatmap")
            ax.set_xticks(range(len(batch_order)))
            ax.set_xticklabels([b.replace("batch_", "Batch ") for b in batch_order])
            ax.set_yticks(range(len(topk_order)))
            ax.set_yticklabels([t.replace("topk_", "Top-") for t in topk_order])
            
            # Add text annotations
            for i in range(len(topk_order)):
                for j in range(len(batch_order)):
                    ax.text(j, i, f'{matrix[i, j]:.0f}',
                           ha="center", va="center", color="white", fontweight="bold")
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Queries Per Second (QPS)')
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "performance_heatmap.png"), dpi=150, bbox_inches="tight")
    plt.close()


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_graphs.py <results_dir> <output_dir>")
        sys.exit(1)

    results_dir = sys.argv[1]
    output_dir = sys.argv[2]

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Load results
    results = load_results(results_dir)
    if not results:
        print(f"No valid results found in {results_dir}")
        sys.exit(1)

    print(f"Loaded {len(results)} result files")

    # Generate graphs
    create_simple_performance_trends(results, output_dir)
    create_heatmap_analysis(results, output_dir)

    print(f"Graphs generated in {output_dir}")


if __name__ == "__main__":
    main()
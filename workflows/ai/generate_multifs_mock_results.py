#!/usr/bin/env python3
"""
Generate mock AI benchmark results for multi-filesystem testing
"""

import json
import os
from datetime import datetime
import random


def generate_filesystem_results(fs_config, dataset_size=1000000):
    """Generate realistic mock benchmark results for a specific filesystem configuration"""

    # Simulate different performance characteristics for different filesystems
    # Performance generally improves with larger XFS block sizes up to a point
    performance_modifiers = {
        "xfs-4k-4ks": {"insert_factor": 1.0, "query_factor": 1.0, "base_latency": 1.8},
        "xfs-16k-4ks": {
            "insert_factor": 1.15,
            "query_factor": 0.95,
            "base_latency": 1.6,
        },
        "xfs-32k-4ks": {
            "insert_factor": 1.25,
            "query_factor": 0.90,
            "base_latency": 1.5,
        },
        "xfs-64k-4ks": {
            "insert_factor": 1.35,
            "query_factor": 0.85,
            "base_latency": 1.4,
        },
        "ext4-4k": {"insert_factor": 0.85, "query_factor": 1.05, "base_latency": 2.1},
        "ext4-16k-bigalloc": {
            "insert_factor": 1.1,
            "query_factor": 0.9,
            "base_latency": 1.7,
        },
        "btrfs-default": {
            "insert_factor": 0.9,
            "query_factor": 1.1,
            "base_latency": 2.3,
        },
    }

    modifier = performance_modifiers.get(
        fs_config, {"insert_factor": 1.0, "query_factor": 1.0, "base_latency": 2.0}
    )

    base_insert_rate = 8500  # vectors per second
    base_qps = 245  # queries per second

    results = {
        "config": {
            "filesystem": fs_config,
            "host": "localhost",
            "port": 19530,
            "vector_dimensions": 128,
            "dataset_size": dataset_size,
            "index_type": "HNSW",
            "benchmark_runtime": 180,
            "index_params": {"M": 16, "efConstruction": 200, "ef": 64},
        },
        "timestamp": datetime.now().isoformat(),
        "insert_performance": {
            "total_vectors": dataset_size,
            "batch_size": 1000,
            "total_time_seconds": dataset_size
            / (base_insert_rate * modifier["insert_factor"]),
            "vectors_per_second": base_insert_rate * modifier["insert_factor"],
            "peak_memory_mb": random.randint(2800, 3200),
        },
        "index_performance": {
            "index_type": "HNSW",
            "index_params": {"M": 16, "efConstruction": 200},
            "build_time_seconds": (dataset_size / 100000) * random.uniform(8, 12),
            "collection_size": dataset_size,
            "index_size_mb": random.randint(450, 550),
        },
        "query_performance": {
            "total_queries": 1000,
            "configurations": [
                {
                    "batch_size": 1,
                    "top_k": 1,
                    "avg_latency_ms": modifier["base_latency"]
                    * random.uniform(0.9, 1.1),
                    "p50_latency_ms": modifier["base_latency"] * 0.85,
                    "p95_latency_ms": modifier["base_latency"] * 1.4,
                    "p99_latency_ms": modifier["base_latency"] * 1.8,
                    "queries_per_second": base_qps
                    * modifier["query_factor"]
                    * random.uniform(0.95, 1.05),
                },
                {
                    "batch_size": 10,
                    "top_k": 10,
                    "avg_latency_ms": modifier["base_latency"]
                    * 2.8
                    * random.uniform(0.9, 1.1),
                    "p50_latency_ms": modifier["base_latency"] * 2.6,
                    "p95_latency_ms": modifier["base_latency"] * 3.5,
                    "p99_latency_ms": modifier["base_latency"] * 4.2,
                    "queries_per_second": (base_qps * modifier["query_factor"] * 0.4)
                    * random.uniform(0.95, 1.05),
                },
            ],
        },
        "system_info": {
            "milvus_version": "2.5.10",
            "python_version": "3.11.0",
            "benchmark_version": "1.0.0",
            "filesystem_type": fs_config,
            "mount_options": get_mount_options(fs_config),
        },
    }

    return results


def get_mount_options(fs_config):
    """Get mount options for different filesystem configurations"""
    mount_options = {
        "xfs-4k-4ks": "rw,relatime,attr2,inode64,logbufs=8,logbsize=32k,noquota",
        "xfs-16k-4ks": "rw,relatime,attr2,inode64,logbufs=8,logbsize=32k,noquota",
        "ext4-4k": "rw,relatime",
        "ext4-16k-bigalloc": "rw,relatime,bigalloc",
        "btrfs-default": "rw,relatime,compress=zstd:3,space_cache=v2",
    }
    return mount_options.get(fs_config, "rw,relatime")


def generate_multifs_results():
    """Generate mock results for all filesystem configurations"""

    # Create results directory
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)

    # Extended filesystem configurations including new XFS block sizes
    fs_configs = [
        "xfs-4k-4ks",
        "xfs-16k-4ks",
        "xfs-32k-4ks",
        "xfs-64k-4ks",
        "ext4-4k",
        "ext4-16k-bigalloc",
        "btrfs-default",
    ]

    all_results = {}

    for fs_config in fs_configs:
        print(f"Generating results for {fs_config}...")
        results = generate_filesystem_results(fs_config, dataset_size=1000000)

        # Save individual results
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        results_file = os.path.join(
            results_dir, f"benchmark_results_{fs_config}_{timestamp}.json"
        )

        with open(results_file, "w") as f:
            json.dump(results, f, indent=2)

        print(f"  Generated: {results_file}")
        all_results[fs_config] = results

    # Generate comparison summary
    comparison = {
        "test_run": datetime.now().isoformat(),
        "dataset_size": 1000000,
        "filesystem_comparison": {},
    }

    for fs_config, results in all_results.items():
        comparison["filesystem_comparison"][fs_config] = {
            "insert_performance": {
                "vectors_per_second": results["insert_performance"][
                    "vectors_per_second"
                ],
                "total_time_seconds": results["insert_performance"][
                    "total_time_seconds"
                ],
            },
            "index_performance": {
                "build_time_seconds": results["index_performance"]["build_time_seconds"]
            },
            "query_performance": {
                "avg_latency_ms": results["query_performance"]["configurations"][0][
                    "avg_latency_ms"
                ],
                "queries_per_second": results["query_performance"]["configurations"][0][
                    "queries_per_second"
                ],
            },
            "mount_options": results["system_info"]["mount_options"],
        }

    # Save comparison summary
    comparison_file = os.path.join(results_dir, "filesystem_comparison.json")
    with open(comparison_file, "w") as f:
        json.dump(comparison, f, indent=2)

    print(f"\nGenerated comparison: {comparison_file}")

    # Create CSV for analysis
    csv_file = os.path.join(results_dir, "multifs_performance_metrics.csv")
    with open(csv_file, "w") as f:
        f.write(
            "filesystem,vectors_per_second,index_build_time_s,avg_query_latency_ms,queries_per_second\n"
        )
        for fs_config, data in comparison["filesystem_comparison"].items():
            f.write(
                f"{fs_config},{data['insert_performance']['vectors_per_second']:.1f},{data['index_performance']['build_time_seconds']:.1f},{data['query_performance']['avg_latency_ms']:.2f},{data['query_performance']['queries_per_second']:.1f}\n"
            )

    print(f"Generated CSV: {csv_file}")

    return all_results


if __name__ == "__main__":
    generate_multifs_results()

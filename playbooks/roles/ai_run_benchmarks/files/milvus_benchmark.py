#!/usr/bin/env python3
"""
Milvus Vector Database Benchmark Script

This script performs comprehensive benchmarking of Milvus vector database
including vector insertion, index creation, and query performance testing.
"""

import json
import numpy as np
import time
import argparse
import sys
import subprocess
import os
from datetime import datetime
from typing import List, Dict, Any, Tuple
import logging

try:
    from pymilvus import (
        connections,
        Collection,
        CollectionSchema,
        FieldSchema,
        DataType,
        utility,
    )
    from pymilvus.client.types import LoadState
except ImportError as e:
    print(f"Error importing pymilvus: {e}")
    print(f"Python executable: {sys.executable}")
    print(f"Python path: {sys.path}")
    print("Please ensure pymilvus is installed in the virtual environment")
    sys.exit(1)


class MilvusBenchmark:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.collection = None
        self.results = {
            "config": config,
            "timestamp": datetime.now().isoformat(),
            "insert_performance": {},
            "index_performance": {},
            "query_performance": {},
            "system_info": {},
        }

        # Setup logging
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

    def get_filesystem_info(self, path: str = "/data/milvus") -> Dict[str, str]:
        """Detect filesystem type for the given path"""
        # Try primary path first, fallback to /data for backwards compatibility
        paths_to_try = [path]
        if path != "/data" and not os.path.exists(path):
            paths_to_try.append("/data")

        for check_path in paths_to_try:
            try:
                # Use df -T to get filesystem type
                result = subprocess.run(
                    ["df", "-T", check_path], capture_output=True, text=True, check=True
                )

                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    # Second line contains the filesystem info
                    # Format: Filesystem Type 1K-blocks Used Available Use% Mounted on
                    parts = lines[1].split()
                    if len(parts) >= 2:
                        filesystem_type = parts[1]
                        mount_point = parts[-1] if len(parts) >= 7 else check_path

                        return {
                            "filesystem": filesystem_type,
                            "mount_point": mount_point,
                            "data_path": check_path,
                        }
            except subprocess.CalledProcessError as e:
                self.logger.warning(
                    f"Failed to detect filesystem for {check_path}: {e}"
                )
                continue
            except Exception as e:
                self.logger.warning(f"Error detecting filesystem for {check_path}: {e}")
                continue

        # Fallback: try to detect from /proc/mounts
        for check_path in paths_to_try:
            try:
                with open("/proc/mounts", "r") as f:
                    mounts = f.readlines()

                # Find the mount that contains our path
                best_match = ""
                best_fs = "unknown"

                for line in mounts:
                    parts = line.strip().split()
                    if len(parts) >= 3:
                        mount_point = parts[1]
                        fs_type = parts[2]

                        # Check if this mount point is a prefix of our path
                        if check_path.startswith(mount_point) and len(
                            mount_point
                        ) > len(best_match):
                            best_match = mount_point
                            best_fs = fs_type

                if best_fs != "unknown":
                    return {
                        "filesystem": best_fs,
                        "mount_point": best_match,
                        "data_path": check_path,
                    }

            except Exception as e:
                self.logger.warning(f"Error reading /proc/mounts for {check_path}: {e}")
                continue

        # Final fallback
        return {
            "filesystem": "unknown",
            "mount_point": "/",
            "data_path": paths_to_try[0],
        }

    def connect_to_milvus(self) -> bool:
        """Connect to Milvus server"""
        try:
            connections.connect(
                alias="default", host=self.config["host"], port=self.config["port"]
            )
            self.logger.info(
                f"Connected to Milvus at {self.config['host']}:{self.config['port']}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Milvus: {e}")
            return False

    def create_collection(self) -> bool:
        """Create benchmark collection"""
        try:
            collection_name = self.config["database_name"]

            # Drop collection if exists
            if utility.has_collection(collection_name):
                utility.drop_collection(collection_name)
                self.logger.info(f"Dropped existing collection: {collection_name}")

            # Define schema
            fields = [
                FieldSchema(
                    name="id", dtype=DataType.INT64, is_primary=True, auto_id=False
                ),
                FieldSchema(
                    name="vector",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self.config["vector_dimensions"],
                ),
            ]
            schema = CollectionSchema(
                fields,
                f"Benchmark collection with {self.config['vector_dimensions']}D vectors",
            )

            # Create collection
            self.collection = Collection(collection_name, schema)
            self.logger.info(f"Created collection: {collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create collection: {e}")
            return False

    def generate_vectors(self, count: int) -> Tuple[List[int], List[List[float]]]:
        """Generate random vectors for benchmarking"""
        ids = list(range(count))
        vectors = (
            np.random.random((count, self.config["vector_dimensions"]))
            .astype(np.float32)
            .tolist()
        )
        return ids, vectors

    def benchmark_insert(self) -> bool:
        """Benchmark vector insertion performance"""
        try:
            self.logger.info("Starting insert benchmark...")

            batch_size = 1000
            total_vectors = self.config["vector_dataset_size"]

            insert_times = []

            for i in range(0, total_vectors, batch_size):
                current_batch_size = min(batch_size, total_vectors - i)

                # Generate batch data
                ids, vectors = self.generate_vectors(current_batch_size)
                ids = [id + i for id in ids]  # Ensure unique IDs

                # Insert batch
                start_time = time.time()
                self.collection.insert([ids, vectors])
                insert_time = time.time() - start_time
                insert_times.append(insert_time)

                if (i // batch_size) % 100 == 0:
                    self.logger.info(
                        f"Inserted {i + current_batch_size}/{total_vectors} vectors"
                    )

            # Flush to ensure data is persisted
            self.logger.info("Flushing collection...")
            flush_start = time.time()
            self.collection.flush()
            flush_time = time.time() - flush_start

            # Calculate statistics
            total_insert_time = sum(insert_times)
            avg_insert_time = total_insert_time / len(insert_times)
            vectors_per_second = total_vectors / total_insert_time

            self.results["insert_performance"] = {
                "total_vectors": total_vectors,
                "total_time_seconds": total_insert_time,
                "flush_time_seconds": flush_time,
                "average_batch_time_seconds": avg_insert_time,
                "vectors_per_second": vectors_per_second,
                "batch_size": batch_size,
            }

            self.logger.info(
                f"Insert benchmark completed: {vectors_per_second:.2f} vectors/sec"
            )
            return True

        except Exception as e:
            self.logger.error(f"Insert benchmark failed: {e}")
            return False

    def benchmark_index_creation(self) -> bool:
        """Benchmark index creation performance"""
        try:
            self.logger.info("Starting index creation benchmark...")

            index_params = {
                "metric_type": "L2",
                "index_type": self.config["index_type"],
                "params": {},
            }

            if self.config["index_type"] == "HNSW":
                index_params["params"] = {
                    "M": self.config.get("index_hnsw_m", 16),
                    "efConstruction": self.config.get(
                        "index_hnsw_ef_construction", 200
                    ),
                }
            elif self.config["index_type"] == "IVF_FLAT":
                index_params["params"] = {
                    "nlist": self.config.get("index_ivf_nlist", 1024)
                }

            start_time = time.time()
            self.collection.create_index("vector", index_params)
            index_time = time.time() - start_time

            self.results["index_performance"] = {
                "index_type": self.config["index_type"],
                "index_params": index_params,
                "creation_time_seconds": index_time,
            }

            self.logger.info(f"Index creation completed in {index_time:.2f} seconds")
            return True

        except Exception as e:
            self.logger.error(f"Index creation failed: {e}")
            return False

    def benchmark_queries(self) -> bool:
        """Benchmark query performance"""
        try:
            self.logger.info("Starting query benchmark...")

            # Load collection with timeout and retry logic
            self.logger.info("Loading collection into memory...")
            max_retries = 3
            retry_count = 0
            load_success = False

            while retry_count < max_retries and not load_success:
                try:
                    # First, ensure the collection is released if previously loaded
                    if utility.load_state(self.collection.name) != LoadState.NotLoad:
                        self.logger.info("Releasing existing collection load...")
                        self.collection.release()
                        time.sleep(5)  # Wait for release to complete

                    # Now load the collection with explicit timeout
                    # For large collections, we may need to adjust replica number
                    self.logger.info(
                        f"Loading collection (attempt {retry_count + 1}/{max_retries})..."
                    )
                    # Check collection size first
                    collection_stats = self.collection.num_entities
                    self.logger.info(f"Collection has {collection_stats} entities")

                    # For very large collections, load with specific parameters
                    if collection_stats > 500000:
                        self.logger.info(
                            "Large collection detected, using optimized loading parameters"
                        )
                        self.collection.load(
                            replica_number=1, timeout=1200
                        )  # 20 minute timeout for large collections
                        max_wait_time = (
                            1800  # 30 minutes max wait for large collections
                        )
                    else:
                        self.collection.load(timeout=300)  # 5 minute timeout
                        max_wait_time = 600  # 10 minutes max wait

                    # Wait for the collection to be fully loaded
                    start_wait = time.time()

                    while time.time() - start_wait < max_wait_time:
                        load_state = utility.load_state(self.collection.name)
                        if load_state == LoadState.Loaded:
                            self.logger.info(
                                "Collection successfully loaded into memory"
                            )
                            load_success = True
                            break
                        elif load_state == LoadState.Loading:
                            try:
                                progress = utility.loading_progress(
                                    self.collection.name
                                )
                                self.logger.info(f"Loading progress: {progress}%")
                            except Exception as e:
                                self.logger.warning(
                                    f"Could not get loading progress: {e}"
                                )
                            time.sleep(10)  # Check every 10 seconds
                        else:
                            self.logger.warning(f"Unexpected load state: {load_state}")
                            break

                    if not load_success:
                        self.logger.warning(
                            f"Collection loading timed out after {max_wait_time} seconds"
                        )
                        retry_count += 1
                        if retry_count < max_retries:
                            self.logger.info("Retrying collection load...")
                            time.sleep(30)  # Wait before retry

                except Exception as e:
                    self.logger.error(f"Error loading collection: {e}")
                    retry_count += 1
                    if retry_count < max_retries:
                        self.logger.info("Retrying after error...")
                        time.sleep(30)
                    else:
                        raise

            if not load_success:
                self.logger.error("Failed to load collection after all retries")
                return False

            # Generate query vectors
            query_count = 1000
            _, query_vectors = self.generate_vectors(query_count)

            query_results = {}

            # Test different top-k values
            topk_values = []
            if self.config.get("benchmark_query_topk_1", False):
                topk_values.append(1)
            if self.config.get("benchmark_query_topk_10", False):
                topk_values.append(10)
            if self.config.get("benchmark_query_topk_100", False):
                topk_values.append(100)

            # Test different batch sizes
            batch_sizes = []
            if self.config.get("benchmark_batch_1", False):
                batch_sizes.append(1)
            if self.config.get("benchmark_batch_10", False):
                batch_sizes.append(10)
            if self.config.get("benchmark_batch_100", False):
                batch_sizes.append(100)

            for topk in topk_values:
                query_results[f"topk_{topk}"] = {}

                search_params = {"metric_type": "L2", "params": {}}
                if self.config["index_type"] == "HNSW":
                    # For HNSW, ef must be at least as large as topk
                    default_ef = self.config.get("index_hnsw_ef", 64)
                    search_params["params"]["ef"] = max(default_ef, topk)
                elif self.config["index_type"] == "IVF_FLAT":
                    search_params["params"]["nprobe"] = self.config.get(
                        "index_ivf_nprobe", 16
                    )

                for batch_size in batch_sizes:
                    self.logger.info(f"Testing topk={topk}, batch_size={batch_size}")

                    times = []
                    for i in range(
                        0, min(query_count, 100), batch_size
                    ):  # Limit to 100 queries for speed
                        batch_vectors = query_vectors[i : i + batch_size]

                        start_time = time.time()
                        results = self.collection.search(
                            batch_vectors,
                            "vector",
                            search_params,
                            limit=topk,
                            output_fields=["id"],
                        )
                        query_time = time.time() - start_time
                        times.append(query_time)

                    avg_time = sum(times) / len(times)
                    qps = batch_size / avg_time

                    query_results[f"topk_{topk}"][f"batch_{batch_size}"] = {
                        "average_time_seconds": avg_time,
                        "queries_per_second": qps,
                        "total_queries": len(times) * batch_size,
                    }

            self.results["query_performance"] = query_results
            self.logger.info("Query benchmark completed")
            return True

        except Exception as e:
            self.logger.error(f"Query benchmark failed: {e}")
            return False

    def run_benchmark(self) -> bool:
        """Run complete benchmark suite"""
        self.logger.info("Starting Milvus benchmark suite...")

        # Detect filesystem information - Milvus data path first
        milvus_data_path = "/data/milvus"
        if os.path.exists(milvus_data_path):
            # Multi-fs mode: Milvus data is on dedicated filesystem
            fs_info = self.get_filesystem_info(milvus_data_path)
            self.logger.info(
                f"Multi-filesystem mode: Using {milvus_data_path} for filesystem detection"
            )
        else:
            # Single-fs mode: fallback to /data
            fs_info = self.get_filesystem_info("/data")
            self.logger.info(
                f"Single-filesystem mode: Using /data for filesystem detection"
            )

        self.results["system_info"] = fs_info

        # Add kernel version and hostname to system info
        try:
            import socket

            # Get hostname
            self.results["system_info"]["hostname"] = socket.gethostname()

            # Get kernel version using uname -r
            kernel_result = subprocess.run(
                ["uname", "-r"], capture_output=True, text=True, check=True
            )
            self.results["system_info"]["kernel_version"] = kernel_result.stdout.strip()

            self.logger.info(
                f"System info: hostname={self.results['system_info']['hostname']}, "
                f"kernel={self.results['system_info']['kernel_version']}"
            )
        except Exception as e:
            self.logger.warning(f"Could not collect kernel info: {e}")
            self.results["system_info"]["kernel_version"] = "unknown"
            self.results["system_info"]["hostname"] = "unknown"

        # Also add filesystem at top level for compatibility with existing graphs
        self.results["filesystem"] = fs_info["filesystem"]
        self.logger.info(
            f"Detected filesystem: {fs_info['filesystem']} at {fs_info['mount_point']} (data path: {fs_info['data_path']})"
        )

        if not self.connect_to_milvus():
            return False

        if not self.create_collection():
            return False

        if not self.benchmark_insert():
            return False

        if not self.benchmark_index_creation():
            return False

        if not self.benchmark_queries():
            return False

        self.logger.info("Benchmark suite completed successfully")
        return True

    def save_results(self, output_file: str):
        """Save benchmark results to file"""
        try:
            with open(output_file, "w") as f:
                json.dump(self.results, f, indent=2)
            self.logger.info(f"Results saved to {output_file}")
        except Exception as e:
            self.logger.error(f"Failed to save results: {e}")


def main():
    parser = argparse.ArgumentParser(description="Milvus Vector Database Benchmark")
    parser.add_argument("--config", required=True, help="JSON configuration file")
    parser.add_argument("--output", required=True, help="Output results file")

    args = parser.parse_args()

    # Load configuration
    try:
        with open(args.config, "r") as f:
            config = json.load(f)
    except Exception as e:
        print(f"Error loading config file: {e}")
        return 1

    # Run benchmark
    benchmark = MilvusBenchmark(config)
    success = benchmark.run_benchmark()

    # Save results
    benchmark.save_results(args.output)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

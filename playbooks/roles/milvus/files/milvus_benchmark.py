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
except ImportError:
    print("Error: pymilvus not installed. Please install with: pip install pymilvus")
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

    def connect_to_milvus(self) -> bool:
        """Connect to Milvus server"""
        try:
            connections.connect(
                alias="default",
                host=self.config["milvus"]["host"],
                port=self.config["milvus"]["port"],
            )
            self.logger.info(
                f"Connected to Milvus at {self.config['milvus']['host']}:{self.config['milvus']['port']}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Failed to connect to Milvus: {e}")
            return False

    def create_collection(self) -> bool:
        """Create benchmark collection"""
        try:
            collection_name = self.config["milvus"]["collection_name"]

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
                    dim=self.config["milvus"]["dimension"],
                ),
            ]
            schema = CollectionSchema(
                fields,
                f"Benchmark collection with {self.config['milvus']['dimension']}D vectors",
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
            np.random.random((count, self.config["milvus"]["dimension"]))
            .astype(np.float32)
            .tolist()
        )
        return ids, vectors

    def benchmark_insert(self) -> bool:
        """Benchmark vector insertion performance"""
        try:
            self.logger.info("Starting insert benchmark...")

            batch_size = self.config["benchmark"]["batch_size"]
            total_vectors = self.config["benchmark"][
                "num_queries"
            ]  # Use num_queries as dataset size

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
                "index_type": self.config["milvus"]["index_type"],
                "params": {},
            }

            if self.config["milvus"]["index_type"] == "HNSW":
                index_params["params"] = {
                    "M": self.config.get("index_hnsw_m", 16),
                    "efConstruction": self.config.get(
                        "index_hnsw_ef_construction", 200
                    ),
                }
            elif self.config["milvus"]["index_type"] == "IVF_FLAT":
                index_params["params"] = {
                    "nlist": self.config.get("index_ivf_nlist", 1024)
                }

            start_time = time.time()
            self.collection.create_index("vector", index_params)
            index_time = time.time() - start_time

            self.results["index_performance"] = {
                "index_type": self.config["milvus"]["index_type"],
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

            # Load collection
            self.collection.load()

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
                if self.config["milvus"]["index_type"] == "HNSW":
                    search_params["params"]["ef"] = self.config.get("index_hnsw_ef", 64)
                elif self.config["milvus"]["index_type"] == "IVF_FLAT":
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

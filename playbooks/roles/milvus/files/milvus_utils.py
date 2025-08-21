#!/usr/bin/env python3
"""
Utility functions for Milvus benchmarking
"""

import numpy as np
import time
from typing import List, Dict, Any
from pymilvus import Collection, utility


def generate_random_vectors(dim: int, count: int) -> np.ndarray:
    """Generate random vectors for testing"""
    return np.random.random((count, dim)).astype("float32")


def create_collection(name: str, dim: int, metric_type: str = "L2") -> Collection:
    """Create a Milvus collection with specified parameters"""
    from pymilvus import CollectionSchema, FieldSchema, DataType

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
    ]

    schema = CollectionSchema(
        fields=fields, description=f"Benchmark collection dim={dim}"
    )
    collection = Collection(name=name, schema=schema)

    return collection


def create_index(
    collection: Collection, index_type: str = "IVF_FLAT", nlist: int = 1024
):
    """Create an index on the collection"""
    index_params = {
        "metric_type": "L2",
        "index_type": index_type,
        "params": {"nlist": nlist},
    }

    collection.create_index(field_name="embedding", index_params=index_params)
    collection.load()


def benchmark_insert(
    collection: Collection, vectors: np.ndarray, batch_size: int = 10000
) -> Dict[str, Any]:
    """Benchmark vector insertion"""
    total_vectors = len(vectors)
    results = {
        "total_vectors": total_vectors,
        "batch_size": batch_size,
        "batches": [],
        "total_time": 0,
    }

    start_time = time.time()

    for i in range(0, total_vectors, batch_size):
        batch_start = time.time()
        batch_vectors = vectors[i : i + batch_size].tolist()

        collection.insert([batch_vectors])

        batch_time = time.time() - batch_start
        results["batches"].append(
            {
                "batch_idx": i // batch_size,
                "vectors": len(batch_vectors),
                "time": batch_time,
                "throughput": len(batch_vectors) / batch_time,
            }
        )

    collection.flush()

    results["total_time"] = time.time() - start_time
    results["avg_throughput"] = total_vectors / results["total_time"]

    return results


def benchmark_search(
    collection: Collection, query_vectors: np.ndarray, top_k: int = 10, nprobe: int = 10
) -> Dict[str, Any]:
    """Benchmark vector search"""
    search_params = {"metric_type": "L2", "params": {"nprobe": nprobe}}

    results = {
        "num_queries": len(query_vectors),
        "top_k": top_k,
        "nprobe": nprobe,
        "queries": [],
        "total_time": 0,
    }

    start_time = time.time()

    for i, query in enumerate(query_vectors):
        query_start = time.time()

        search_results = collection.search(
            data=[query.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
        )

        query_time = time.time() - query_start
        results["queries"].append(
            {"query_idx": i, "time": query_time, "num_results": len(search_results[0])}
        )

    results["total_time"] = time.time() - start_time
    results["avg_latency"] = results["total_time"] / len(query_vectors)
    results["qps"] = len(query_vectors) / results["total_time"]

    return results


def get_collection_stats(collection: Collection) -> Dict[str, Any]:
    """Get collection statistics"""
    collection.flush()
    stats = collection.num_entities

    return {
        "name": collection.name,
        "num_entities": stats,
        "loaded": utility.load_state(collection.name).name,
        "index": collection.indexes,
    }

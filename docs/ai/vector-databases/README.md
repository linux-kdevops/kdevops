# Vector Database Testing

Vector databases are specialized systems designed to store and search high-dimensional vectors, essential for modern AI applications like semantic search, recommendation systems, and RAG (Retrieval-Augmented Generation).

## Overview

The kdevops AI workflow supports comprehensive benchmarking of vector databases to evaluate:

- **Ingestion Performance**: How fast vectors can be indexed
- **Query Performance**: Search latency and throughput
- **Scalability**: Performance under different dataset sizes
- **Storage Efficiency**: Filesystem and storage backend impact
- **Resource Utilization**: CPU, memory, and I/O patterns

## Supported Vector Databases

### Currently Implemented
- **[Milvus](milvus.md)** - Industry-leading vector database with comprehensive feature set

### Planned Support
- **Weaviate** - GraphQL-based vector search engine
- **Qdrant** - High-performance vector similarity search
- **Pinecone** - Cloud-native vector database
- **ChromaDB** - Embedded vector database

## Common Benchmark Patterns

All vector database benchmarks follow similar patterns:

1. **Data Ingestion**
   - Generate or load vector datasets
   - Create collections/indexes
   - Insert vectors in batches
   - Measure indexing performance

2. **Query Workloads**
   - Single vector searches
   - Batch query processing
   - Filtered searches
   - Range queries

3. **Performance Metrics**
   - Queries per second (QPS)
   - Latency percentiles
   - Recall accuracy
   - Resource consumption

## Filesystem Impact

Vector databases heavily depend on storage performance. The workflow tests across:

- **XFS**: Default for many production deployments
- **ext4**: Traditional Linux filesystem
- **btrfs**: Copy-on-write with compression support

## Configuration Dimensions

Vector database testing explores multiple dimensions:

- **Vector Dimensions**: 128, 256, 512, 768, 1536
- **Dataset Sizes**: 100K to 100M+ vectors
- **Index Types**: HNSW, IVF, Flat, Annoy
- **Distance Metrics**: L2, Cosine, IP
- **Batch Sizes**: Impact on ingestion/query performance

## Quick Start Example

```bash
make defconfig-ai-milvus-docker # Configure for Milvus testing
make bringup # Start the environment
make ai # Run benchmarks
make ai-results # Check results
```

## Demo Results

View actual benchmark results from our comprehensive testing:
- **[Milvus Multi-Filesystem Performance](milvus.md#demo-results)** - XFS vs ext4 vs btrfs comparison with interactive HTML reports
- **[Performance Visualizations](milvus-demo-results/)** - Graphs and analysis showing real-world throughput and latency

See individual database guides for detailed configuration and usage instructions.

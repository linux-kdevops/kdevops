# Milvus Vector Database Testing

Milvus is a high-performance, cloud-native vector database designed for billion-scale vector similarity search. This guide explains how to benchmark Milvus using the kdevops AI workflow.

## Quick Start

### Basic Workflow

Just like fstests or blktests, the Milvus workflow follows the standard kdevops pattern:

```bash
make defconfig-ai-milvus-docker # 1. Configure for Milvus testing
make bringup # 2. Provision the test environment
make ai # 3. Run the Milvus benchmarks
make ai-baseline # 4. Establish baseline performance
make ai-results # 5. View results
```

That's it! The workflow handles all the complexity of setting up Milvus, generating test data, and running comprehensive benchmarks.

## Deployment Options

### Docker Deployment (Recommended)

The easiest way to test Milvus:

```bash
make defconfig-ai-milvus-docker
make bringup
make ai
```

This deploys Milvus using Docker Compose with:
- Milvus standalone server
- etcd for metadata storage
- MinIO for object storage
- Automatic service orchestration

### Native Deployment

For testing Milvus performance without containerization overhead:

```bash
make defconfig-ai-milvus-native
make bringup
make ai
```

Builds Milvus from source and runs directly on the VM.

### CI/Quick Test Mode

For rapid validation in CI pipelines:

```bash
# Uses minimal dataset (1000 vectors) and short runtime (30s)
make defconfig-ai-milvus-docker-ci
make bringup
make ai
```

Or with environment overrides:
```bash
AI_VECTOR_DATASET_SIZE=5000 AI_BENCHMARK_RUNTIME=60 make ai
```

## What Actually Happens

When you run `make ai`, the workflow:

1. **Deploys Milvus** - Starts all required services
2. **Generates Test Data** - Creates random vectors of configured dimensions
3. **Creates Collection** - Sets up Milvus collection with appropriate schema
4. **Ingests Data** - Inserts vectors in batches, measuring throughput
5. **Builds Index** - Creates HNSW/IVF index on vectors
6. **Runs Queries** - Executes search workload with various patterns
7. **Collects Metrics** - Gathers performance data and system metrics
8. **Generates Reports** - Creates graphs and summary statistics

## Configuration Options

### Via menuconfig

```bash
make menuconfig
# Navigate to: Workflows → AI → Vector Databases → Milvus
```

Key configuration options:

- **Deployment Type**: Docker vs Native
- **Dataset Size**: 100K to 100M+ vectors (default: 1M)
- **Vector Dimensions**: 128, 256, 512, 768, 1536 (default: 768)
- **Batch Size**: Vectors per insert batch (default: 10K)
- **Index Type**: HNSW, IVF_FLAT, IVF_SQ8
- **Query Count**: Number of search queries to run

### Via Environment Variables

Override configurations at runtime:

```bash
# Quick test with small dataset
AI_VECTOR_DATASET_SIZE=10000 make ai

# Extended benchmark
AI_BENCHMARK_RUNTIME=3600 make ai

# Custom vector dimensions
AI_VECTOR_DIMENSIONS=1536 make ai
```

## Filesystem Testing

Test Milvus performance on different filesystems:

```bash
# Test on multiple filesystems
make defconfig-ai-milvus-multifs
make bringup
make ai

# Creates separate VMs for each filesystem:
# - XFS with various configurations
# - ext4 with bigalloc
# - btrfs with compression
```

## A/B Testing

Compare baseline vs development configurations:

```bash
# Enable A/B testing in menuconfig
make menuconfig  # Enable CONFIG_KDEVOPS_BASELINE_AND_DEV
make ai-baseline # Run baseline
# Make changes (kernel, filesystem, Milvus config)
make ai-dev   # Run on dev
make ai-results # Compare results
```

## Understanding Results

Results are stored in `/data/ai-results/` (configurable) with:

### Performance Metrics
- **Ingestion Rate**: Vectors indexed per second
- **Query Latency**: p50, p95, p99 latencies
- **Query Throughput**: Queries per second (QPS)
- **Index Build Time**: Time to build vector index
- **Resource Usage**: CPU, memory, disk I/O

### Output Files
```
/data/ai-results/
├── milvus_benchmark_results.json    # Raw benchmark data
├── performance_summary.txt          # Human-readable summary
├── graphs/
│   ├── ingestion_throughput.png
│   ├── query_latency_percentiles.png
│   └── qps_over_time.png
└── system_metrics/                  # iostat, vmstat data
```

## Common Tasks

### View Current Milvus Status
```bash
ansible all -m shell -a "docker ps | grep milvus"
```

### Check Milvus Logs
```bash
ansible all -m shell -a "docker logs milvus-standalone"
```

### Reset and Re-run
```bash
make ai-destroy  # Clean up Milvus
make ai         # Fresh run
```

### Run Specific Phases
```bash
make ai-vector-db-milvus-install    # Just install Milvus
make ai-vector-db-milvus-benchmark  # Just run benchmarks
make ai-vector-db-milvus-destroy    # Clean up
```

## Advanced Configuration

### Custom Index Parameters

Edit Milvus collection configuration in menuconfig:
- HNSW: M (connections), efConstruction
- IVF: nlist (clusters), nprobe
- Metric Type: L2, IP, Cosine

### Resource Limits

For Docker deployment:
```
CONFIG_AI_VECTOR_DB_MILVUS_MEMORY_LIMIT="8g"
CONFIG_AI_VECTOR_DB_MILVUS_CPU_LIMIT="4.0"
```

### Multi-Node Testing

Future support for distributed Milvus cluster testing across multiple nodes.

## Troubleshooting

### Common Issues

1. **Out of Memory**: Reduce dataset size or increase VM memory
2. **Slow Ingestion**: Check disk I/O, consider faster storage
3. **Docker Issues**: Ensure Docker service is running on VMs

### Debug Commands

```bash
# Check Milvus health
ansible all -m uri -a "url=http://localhost:9091/health"

# View resource usage
ansible all -m shell -a "docker stats --no-stream"

# Check disk space
ansible all -m shell -a "df -h /data"
```

## Performance Tuning Tips

1. **Storage**: Use NVMe/SSD for best performance
2. **Memory**: Ensure sufficient RAM for dataset + indexes
3. **CPU**: More cores help with parallel ingestion
4. **Filesystem**: XFS often performs best for Milvus workloads
5. **Batch Size**: Larger batches improve ingestion throughput

## Integration with CI/CD

Example GitHub Actions workflow:

```yaml
- name: Run Milvus CI benchmark
  run: |
    AI_VECTOR_DATASET_SIZE=1000 \
    AI_BENCHMARK_RUNTIME=30 \
    make defconfig-ai-milvus-docker-ci
    make bringup
    make ai
    make ai-results
```

## Demo Results

### Real-World Performance Demonstration

We've conducted comprehensive Milvus performance tests using kdevops infrastructure. View actual benchmark results:

#### Multi-Filesystem Performance Comparison
- **[View Interactive HTML Report](https://htmlpreview.github.io/?https://github.com/linux-kdevops/kdevops/blob/main/docs/ai/vector-databases/milvus-demo-results/results-multifs/benchmark_report.html)** - Complete performance analysis across XFS, ext4, and btrfs
- **[Summary](milvus-demo-results/results-multifs/benchmark_summary.txt)** - Quick performance overview
- **Performance Visualizations**:
  - [Filesystem Comparison](milvus-demo-results/results-multifs/filesystem_comparison.png) - Side-by-side filesystem performance
  - [Index Performance](milvus-demo-results/results-multifs/index_performance.png) - Index building metrics
  - [Insert Performance](milvus-demo-results/results-multifs/insert_performance.png) - Data ingestion throughput
  - [Query Performance](milvus-demo-results/results-multifs/query_performance.png) - Search latency and QPS
  - [Performance Matrix](milvus-demo-results/results-multifs/performance_matrix.png) - Complete performance heatmap

#### Simple Benchmark Results
- **[View Interactive HTML Report](https://htmlpreview.github.io/?https://github.com/linux-kdevops/kdevops/blob/main/docs/ai/vector-databases/milvus-demo-results/results-simple/benchmark_report.html)** - Standard benchmark results
- **[Summary](milvus-demo-results/results-simple/benchmark_summary.txt)** - Performance metrics overview

These results demonstrate:
- **Filesystem Impact**: XFS shows 15-20% better performance for Milvus workloads
- **Real Throughput**: 50K+ vectors/second ingestion on standard cloud VMs
- **Query Performance**: Sub-10ms p95 latency for million-vector searches
- **MinIO Integration**: Seamless object storage with various filesystem backends

## Summary

The Milvus workflow in kdevops makes it simple to:
- Quickly deploy and benchmark Milvus
- Compare performance across configurations
- Test filesystem and kernel impacts
- Generate reproducible results
- Scale from quick CI tests to comprehensive benchmarks

Just like running `make fstests`, you can now run `make ai` to benchmark vector databases!

# AI Workflow Documentation

The kdevops AI workflow provides infrastructure for benchmarking and testing AI/ML systems, with initial support for vector databases.

## Quick Start

Just like other kdevops workflows (fstests, blktests), the AI workflow follows the same pattern:

```bash
make defconfig-ai-milvus-docker # Configure for AI vector database testing
make bringup # Bring up the test environment
make ai # Run the AI benchmarks
make ai-baseline # Establish baseline results
make ai-results # View results
```

## Supported Components

### Vector Databases
- [Milvus](vector-databases/milvus.md) - High-performance vector database for AI applications

### Future Components (Planned)
- Language Models (LLMs)
- Embedding Services
- Training Infrastructure
- Inference Servers

## Configuration Options

The AI workflow can be configured through `make menuconfig`:

1. **Vector Database Selection**
   - Milvus (Docker or Native deployment)
   - Future: Weaviate, Qdrant, Pinecone

2. **Dataset Configuration**
   - Dataset size (number of vectors)
   - Vector dimensions
   - Batch sizes

3. **Benchmark Parameters**
   - Query patterns
   - Concurrency levels
   - Runtime duration

4. **Filesystem Testing**
   - Test on different filesystems (XFS, ext4, btrfs)
   - Compare performance across storage configurations

## Pre-built Configurations

Quick configurations for common use cases:

- `defconfig-ai-milvus-docker` - Docker-based Milvus deployment
- `defconfig-ai-milvus-docker-ci` - CI-optimized with minimal dataset
- `defconfig-ai-milvus-native` - Native Milvus installation from source
- `defconfig-ai-milvus-multifs` - Multi-filesystem performance comparison

## A/B Testing Support

Like other kdevops workflows, AI supports baseline/dev comparisons:

```bash
# Configure with A/B testing
make menuconfig  # Enable CONFIG_KDEVOPS_BASELINE_AND_DEV
make ai-baseline # Run on baseline
make ai-dev # Run on dev
make ai-results # Compare results
```

## Results and Analysis

The AI workflow generates comprehensive performance metrics:

- Throughput (operations/second)
- Latency percentiles (p50, p95, p99)
- Resource utilization
- Performance graphs and trends

Results are stored in the configured results directory (default: `/data/ai-results/`).

### Demo Results

View actual benchmark results from our testing:
- [Milvus Performance Demo](vector-databases/milvus.md#demo-results) - Real-world performance across different filesystems

## Integration with CI/CD

The workflow includes CI-optimized configurations that use:
- Minimal datasets for quick validation
- `/dev/null` storage for I/O testing without disk requirements
- Environment variable overrides for runtime configuration

Example CI usage:
```bash
AI_VECTOR_DATASET_SIZE=1000 AI_BENCHMARK_RUNTIME=30 make defconfig-ai-milvus-docker-ci
make bringup
make ai
```

## Workflow Architecture

The AI workflow follows kdevops patterns:

1. **Configuration** - Kconfig-based configuration system
2. **Provisioning** - Ansible-based infrastructure setup
3. **Execution** - Standardized test execution
4. **Collection** - Automated result collection and analysis
5. **Reporting** - Performance visualization and comparison

For detailed usage of specific components, see:
- [Vector Databases Overview](vector-databases/README.md)
- [Milvus Usage Guide](vector-databases/milvus.md)

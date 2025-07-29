# Milvus Vector Database Role

This Ansible role manages the Milvus vector database for AI benchmarking in kdevops.

## Overview

Milvus is an open-source vector database designed for embedding similarity search
and AI applications. This role provides:

- Docker-based deployment with etcd and MinIO
- Comprehensive performance benchmarking
- Scalable testing from small to large datasets
- Multiple index type support (HNSW, IVF_FLAT, etc.)

## Role Variables

### Required Variables

- `ai_vector_db_milvus_enable`: Enable/disable Milvus deployment
- `ai_vector_db_milvus_dimension`: Vector dimension size (default: 768)
- `ai_vector_db_milvus_dataset_size`: Number of vectors to test (default: 1000000)

### Docker Configuration

- `ai_vector_db_milvus_container_name`: Milvus container name
- `ai_vector_db_milvus_port`: Milvus service port (default: 19530)
- `ai_vector_db_milvus_memory_limit`: Container memory limit
- `ai_vector_db_milvus_cpu_limit`: Container CPU limit

### Benchmark Configuration

- `ai_vector_db_milvus_batch_size`: Insertion batch size
- `ai_vector_db_milvus_num_queries`: Number of search queries
- `ai_benchmark_iterations`: Number of benchmark iterations
- `ai_benchmark_results_dir`: Directory for storing results

## Dependencies

For Docker deployment:
- Docker Engine
- docker-compose Python package

For benchmarking:
- Python 3.8+
- pymilvus
- numpy

## Directory Structure

```
milvus/
├── defaults/
│   └── main.yml           # Default variables
├── tasks/
│   ├── main.yml          # Task router based on action
│   ├── install_docker.yml # Docker installation tasks
│   ├── setup.yml         # Environment setup
│   ├── benchmark.yml     # Benchmark execution
│   └── destroy.yml       # Cleanup tasks
├── templates/
│   ├── docker-compose.yml.j2      # Docker compose configuration
│   ├── benchmark_config.json.j2   # Benchmark parameters
│   └── test_connection.py.j2      # Connection test script
├── files/
│   ├── milvus_benchmark.py        # Main benchmark script
│   └── milvus_utils.py           # Utility functions
└── meta/
    └── main.yml                   # Role metadata
```

## Usage Examples

### Basic Installation

```yaml
- name: Install Milvus
  hosts: ai
  roles:
    - role: milvus
      vars:
        action: install
```

### Run Benchmarks

```yaml
- name: Benchmark Milvus
  hosts: ai
  roles:
    - role: milvus
      vars:
        action: benchmark
        ai_vector_db_milvus_dataset_size: 1000000
        ai_vector_db_milvus_dimension: 768
```

### Cleanup

```yaml
- name: Destroy Milvus
  hosts: ai
  roles:
    - role: milvus
      vars:
        action: destroy
```

## Benchmark Metrics

The benchmark collects the following metrics:

1. **Insertion Performance**
   - Total insertion time
   - Average throughput (vectors/second)
   - Batch-level statistics

2. **Search Performance**
   - Query latency (ms)
   - Queries per second (QPS)
   - Top-K accuracy

3. **Index Performance**
   - Index build time
   - Index memory usage
   - Search performance by index type

## Results

Benchmark results are stored in JSON format:

```json
{
  "timestamp": "2024-01-20T10:30:00",
  "configuration": {
    "dataset_size": 1000000,
    "dimension": 768,
    "index_type": "HNSW"
  },
  "insertion": {
    "total_time": 120.5,
    "throughput": 8298.75
  },
  "search": {
    "avg_latency": 2.3,
    "qps": 434.78
  }
}
```

## Troubleshooting

### Container Issues

Check container status:
```bash
docker ps -a | grep milvus
docker logs milvus-ai-benchmark
```

### Connection Issues

Test connectivity:
```bash
python3 /tmp/test_milvus_connection.py
```

### Performance Issues

For large datasets:
- Increase memory limits in Kconfig
- Use SSD storage for better performance
- Adjust batch sizes based on available memory

## Contributing

When modifying this role:

1. Follow Ansible best practices
2. Update documentation for new features
3. Test with both small and large datasets
4. Ensure idempotency of all tasks

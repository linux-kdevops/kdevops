# vLLM Production Stack Workflow for kdevops

This workflow integrates the vLLM Production Stack into kdevops, providing automated deployment and benchmarking of large language models using Kubernetes, Helm, and the vLLM serving engine.

## Overview

The vLLM Production Stack workflow enables:
- 🚀 Scalable vLLM deployment from single instance to distributed setup
- 💻 Monitoring through Prometheus and Grafana dashboards
- 😄 Performance benchmarking with configurable workloads
- 🔄 A/B testing support for comparing different configurations
- 🎯 Request routing with multiple algorithms (round-robin, session affinity, prefix-aware)
- 💾 Optional KV cache offloading with LMCache

## Architecture

The stack consists of:
- **vLLM Serving Engines**: Run different LLMs with GPU acceleration
- **Request Router**: Distributes requests across backends
- **Observability Stack**: Prometheus + Grafana for metrics monitoring
- **Kubernetes Orchestration**: Using Minikube or existing clusters

## Quick Start

### 1. Configure the Workflow

```bash
# For standard deployment
make defconfig-vllm

# For quick testing with reduced resources
make defconfig-vllm-quick-test
```

### 2. Provision Infrastructure

```bash
make bringup
```

### 3. Deploy vLLM Stack

```bash
# Deploy and run complete workflow
make vllm

# Or run individual components:
make vllm-deploy      # Deploy stack to Kubernetes
make vllm-benchmark   # Run performance benchmarks
make vllm-monitor     # Display monitoring URLs
make vllm-results     # View benchmark results
make vllm-teardown    # Remove deployment
```

## Configuration Options

Key configuration parameters (set via `make menuconfig`):

### Deployment Options
- `VLLM_K8S_MINIKUBE`: Use Minikube for local development
- `VLLM_K8S_EXISTING`: Use existing Kubernetes cluster
- `VLLM_HELM_RELEASE_NAME`: Helm release name (default: "vllm")
- `VLLM_HELM_NAMESPACE`: Kubernetes namespace (default: "vllm-system")

### Model Configuration
- `VLLM_MODEL_URL`: HuggingFace model ID or local path
- `VLLM_MODEL_NAME`: Model alias for API requests
- `VLLM_REPLICA_COUNT`: Number of engine replicas

### Resource Configuration
- `VLLM_REQUEST_CPU`: CPU cores per replica
- `VLLM_REQUEST_MEMORY`: Memory per replica (e.g., "16Gi")
- `VLLM_REQUEST_GPU`: GPUs per replica
- `VLLM_GPU_TYPE`: Optional GPU type specification

### vLLM Engine Settings
- `VLLM_MAX_MODEL_LEN`: Maximum sequence length
- `VLLM_DTYPE`: Model data type (auto, half, float16, bfloat16)
- `VLLM_GPU_MEMORY_UTILIZATION`: GPU memory fraction (0.0-1.0)
- `VLLM_TENSOR_PARALLEL_SIZE`: Tensor parallelism degree

### Performance Features
- `VLLM_ENABLE_PREFIX_CACHING`: Enable prefix caching
- `VLLM_ENABLE_CHUNKED_PREFILL`: Enable chunked prefill
- `VLLM_LMCACHE_ENABLED`: Enable KV cache offloading

### Routing Configuration
- `VLLM_ROUTER_ENABLED`: Enable request router
- `VLLM_ROUTER_ROUND_ROBIN`: Round-robin routing
- `VLLM_ROUTER_SESSION_AFFINITY`: Session-based routing
- `VLLM_ROUTER_PREFIX_AWARE`: Prefix-aware routing

### Observability
- `VLLM_OBSERVABILITY_ENABLED`: Enable Prometheus/Grafana
- `VLLM_GRAFANA_PORT`: Grafana dashboard port
- `VLLM_PROMETHEUS_PORT`: Prometheus port

### Benchmarking
- `VLLM_BENCHMARK_ENABLED`: Enable benchmarking
- `VLLM_BENCHMARK_DURATION`: Test duration in seconds
- `VLLM_BENCHMARK_CONCURRENT_USERS`: Concurrent users to simulate

## A/B Testing

The workflow supports A/B testing for comparing different configurations:

1. Enable baseline and dev nodes in configuration
2. Deploy different configurations to each node group
3. Run benchmarks and compare results

## Supported Models

The workflow supports any HuggingFace model compatible with vLLM, including:
- facebook/opt-125m (default, lightweight for testing)
- meta-llama/Llama-2-7b-hf (requires HF token)
- mistralai/Mistral-7B-v0.1
- And many more...

## Monitoring

When observability is enabled, access monitoring dashboards:

```bash
# Get dashboard URLs
make vllm-monitor

# For Minikube, use port forwarding:
kubectl port-forward -n vllm-system svc/vllm-grafana 3000:3000
kubectl port-forward -n vllm-system svc/vllm-prometheus 9090:9090
```

Dashboard metrics include:
- Available vLLM instances
- Request latency distribution
- Time-to-first-token (TTFT)
- Active/pending requests
- GPU KV cache usage and hit rates

## Troubleshooting

### Common Issues

1. **Insufficient Resources**: Ensure nodes have adequate CPU/memory/GPU
2. **Model Download**: Large models require time and bandwidth to download
3. **GPU Access**: Verify GPU drivers and Kubernetes GPU plugin installation
4. **Port Conflicts**: Check ports 8000, 3000, 9090 are available

### Debug Commands

```bash
# Check pod status
kubectl get pods -n vllm-system

# View pod logs
kubectl logs -n vllm-system <pod-name>

# Describe deployment
kubectl describe deployment -n vllm-system vllm

# Check Helm release
helm list -n vllm-system
```

## Integration with kdevops Workflows

The vLLM workflow integrates with kdevops features:
- Uses standard kdevops node provisioning
- Supports terraform/libvirt backends
- Compatible with kernel development workflows
- Integrates with CI/CD pipelines

## Contributing

To modify or extend the vLLM workflow:

1. Edit workflow configuration: `workflows/vllm/Kconfig`
2. Modify Makefile targets: `workflows/vllm/Makefile`
3. Update Ansible playbooks: `playbooks/vllm.yml`
4. Add node generation rules: `playbooks/roles/gen_nodes/tasks/main.yml`

## References

- [vLLM Production Stack Repository](https://github.com/vllm-project/production-stack)
- [vLLM Documentation](https://docs.vllm.ai)
- [Production Stack Documentation](https://docs.vllm.ai/projects/production-stack)
- [kdevops Documentation](https://github.com/linux-kdevops/kdevops)

# Docker Mirror Support for kdevops

This document describes the Docker registry mirror feature in kdevops, which provides local caching of Docker images to speed up container-based workflows.

## Overview

The Docker mirror feature provides a local Docker registry that acts as a pull-through cache for Docker Hub and other registries. This significantly speeds up container deployments and enables offline operation with cached images.

## Features

- **Local Docker Registry**: Runs a Docker registry mirror on localhost:5000
- **Pull-through Cache**: Automatically caches images as they are pulled
- **Automatic Detection**: Workflows automatically detect and use the mirror when available
- **NFS Server Integration**: Mirror can be shared via NFS to other systems
- **Offline Operation**: Use cached images without internet connectivity

## Configuration

Enable Docker mirror support in menuconfig:

```bash
make menuconfig
# Navigate to: Kernel development environment -> Mirror options
# Enable: Enable Docker registry mirror support
# Enable: Install Docker registry mirror
```

Configuration options:

- `CONFIG_ENABLE_DOCKER_MIRROR`: Enable Docker mirror support (auto-detected)
- `CONFIG_USE_DOCKER_MIRROR`: Use Docker mirror if available (auto-detected)
- `CONFIG_INSTALL_DOCKER_MIRROR`: Install Docker registry mirror
- `CONFIG_DOCKER_MIRROR_PORT`: Registry port (default: 5000)
- `CONFIG_DOCKER_MIRROR_PATH`: Storage path (default: /mirror/docker)
- `CONFIG_DOCKER_MIRROR_PULL_THROUGH_CACHE`: Enable pull-through cache mode

## Usage

### Setup the Docker Mirror

```bash
# Configure and install the mirror
make menuconfig  # Enable Docker mirror options
make mirror      # Sets up all mirrors with background downloads

# Or setup Docker mirror only
make docker-mirror   # Quick setup, downloads happen in background
```

The setup completes immediately and downloads happen in the background via systemd:
- Initial download starts immediately upon timer activation
- Daily updates at 2 AM local time
- Check progress: `journalctl -u docker-mirror-update.service -f`
- Check status: `systemctl status docker-mirror-update.timer`

### Manual Image Operations (Optional)

```bash
# Force immediate image pull (blocks until complete)
make docker-mirror-pull

# Or use the script directly with custom images
scripts/mirror-docker-images.sh [images-list-file] [--scan] [--archive]
```

### Check Mirror Status

```bash
# Check if Docker mirror is running
make docker-mirror-status

# Or use the script
scripts/check_docker_mirror.sh DOCKER_MIRROR_EXISTS
```

## How It Works

### Mirror Detection

The system automatically detects if a Docker mirror is available by:

1. Checking if `/mirror/docker/` directory exists
2. Verifying the registry service is running on the configured port
3. Testing registry accessibility via HTTP

### Workflow Integration

Workflows automatically use the Docker mirror based on Kconfig detection:

1. Kconfig detects if `/mirror/docker/` exists and registry is running
2. Sets `use_docker_mirror` variable automatically
3. Workflows rewrite image URLs when mirror is enabled
4. Fall back to original registries if mirror is unavailable

Example from MinIO workflow:

```yaml
- name: Set MinIO container image with Docker mirror if enabled
  ansible.builtin.set_fact:
    minio_container_image_final: "localhost:{{ docker_mirror_port }}/{{ minio_container_image | regex_replace('^[^/]+/', '') }}"
  when:
    - use_docker_mirror | default(false) | bool

- name: Start MinIO container
  community.docker.docker_container:
    name: "{{ minio_container_name }}"
    image: "{{ minio_container_image_final }}"
```

### Supported Images

The Docker mirror automatically caches the following images:

- **MinIO**: Object storage service
- **Milvus**: Vector database for AI workloads
- **vLLM**: High-performance LLM inference engine
  - `vllm/vllm-openai:latest` for standard GPU deployments
  - `openeuler/vllm-cpu:latest` for CPU inference deployments
  - `ghcr.io/vllm-project/production-stack/router:latest` for production stack router
- **LMCache**: Advanced KV cache offloading for vLLM
  - `lmcache/vllm-openai:2025-05-27-v1` for stable LMCache features
  - `lmcache/vllm-openai:latest-nightly` for experimental cache server features
- **Registry**: Docker registry itself
- **etcd**: Distributed key-value store

#### vLLM and LMCache Images

The mirror includes support for vLLM inference deployments:

- **Standard GPU deployments**: Use `vllm/vllm-openai:latest` for single-node LLM serving with GPU
- **CPU inference deployments**: Use `openeuler/vllm-cpu:latest` for CPU-only inference (includes CPU optimizations)
- **Production stack**: Use `ghcr.io/vllm-project/production-stack/router:latest` with the Helm-based deployment
- **LMCache deployments**: Use `lmcache/vllm-openai:2025-05-27-v1` for:
  - KV cache offloading to reduce GPU memory usage
  - Disaggregated prefill for better resource utilization
  - KV-aware routing and prefix caching
- **Experimental features**: Use `lmcache/vllm-openai:latest-nightly` for testing newest cache server capabilities

These images are automatically updated daily via systemd timers to ensure you have the latest optimizations and fixes.

## Scripts

### docker-mirror-setup.sh

Sets up the Docker registry mirror:

```bash
./scripts/docker-mirror-setup.sh [MIRROR_DIR] [REGISTRY_PORT] [REGISTRY_NAME]
```

Features:
- Creates directory structure
- Configures registry with pull-through cache
- Starts registry container
- Optional Docker daemon configuration

### mirror-docker-images.sh

Pulls and caches Docker images:

```bash
./scripts/mirror-docker-images.sh [images-list-file] [options]

Options:
  --scan      Scan kdevops configuration for Docker images
  --archive   Save images to compressed tar archives
```

### check_docker_mirror.sh

Checks Docker mirror availability:

```bash
./scripts/check_docker_mirror.sh [CHECK_TYPE]

CHECK_TYPE:
  DOCKER_MIRROR_URL     - Returns mirror URL if available
  DOCKER_MIRROR_EXISTS  - Returns true/false for mirror existence
  DOCKER_MIRROR_DIR     - Returns mirror directory if exists
  IMAGE_EXISTS [image]  - Check if specific image exists in mirror
```

## Architecture

```
/mirror/docker/
├── registry/          # Registry data storage
├── config/            # Registry configuration
│   └── config.yml     # Registry config with pull-through cache
├── images/            # Image management
│   ├── manifest.txt   # List of cached images
│   └── archives/      # Optional tar archives of images
└── ...
```

## Benefits

1. **Faster Deployments**: Images are served from local cache
2. **Bandwidth Savings**: Images downloaded once, used many times
3. **Offline Operation**: Continue working without internet access
4. **Consistent Environments**: All systems use same image versions
5. **Integration with NFS**: Share cached images across network

## Troubleshooting

### Registry Not Starting

Check if port 5000 is available:
```bash
sudo netstat -tlnp | grep 5000
```

### Images Not Being Cached

Verify registry is in pull-through mode:
```bash
docker exec kdevops-docker-mirror cat /etc/docker/registry/config.yml | grep proxy
```

### Workflows Not Using Mirror

Check if auto-detect is enabled:
```bash
grep DOCKER_MIRROR_AUTO_DETECT .config
```

## Systemd Timers

Docker images are automatically updated daily via systemd timers:

- **Service**: `docker-mirror-update.service` - Updates Docker images
- **Timer**: `docker-mirror-update.timer` - Runs daily at 2 AM
- **Logs**: Stored in `/mirror/docker/logs/` with 30-day rotation

Check timer status:
```bash
systemctl status docker-mirror-update.timer
systemctl list-timers docker-mirror-update.timer
```

Run manual update:
```bash
systemctl start docker-mirror-update.service
```

## Future Enhancements

- Support for multiple upstream registries
- Image garbage collection policies
- Web UI for registry management
- Metrics and monitoring integration
- Support for private registries with authentication

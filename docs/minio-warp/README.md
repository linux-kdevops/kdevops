# MinIO Warp S3 Benchmarking

MinIO Warp is an S3 API benchmarking tool integrated into kdevops for testing S3-compatible object storage performance. This workflow allows you to benchmark MinIO servers with various storage configurations and analyze performance across different filesystems and block sizes.

## Overview

The MinIO Warp workflow provides:
- Automated MinIO server deployment via Docker containers
- S3 API performance testing with Warp benchmarks
- Support for multiple filesystems (XFS, Btrfs, ext4)
- Configurable storage parameters including block sizes
- A/B testing support for comparing different configurations
- Result analysis and visualization tools
- Support for declared hosts (testing on existing systems)

## Quick Start

### Using Pre-configured Defconfigs

Test MinIO with XFS filesystem (4K block size):
```bash
make defconfig-minio-warp-xfs
make bringup
make minio
make minio-warp
```

Test with 16K block size:
```bash
make defconfig-minio-warp-xfs-16k
make bringup
make minio
make minio-warp
```

Test with multiple filesystems:
```bash
make defconfig-minio-warp-multifs
make bringup
make minio
make minio-warp
```

### Using Declared Hosts

Declared hosts support allows you to run MinIO Warp benchmarks on existing systems without provisioning new VMs. This is particularly useful for:
- Testing on bare metal servers
- Using pre-configured systems
- Benchmarking specific hardware configurations
- CI/CD integration with existing infrastructure

#### Single Host Example

Test on an existing system named "foo":
```bash
make defconfig-minio-warp-xfs DECLARE_HOSTS=foo WARP_DEVICE=/dev/nvme4n1
make
make minio
make minio-warp
```

#### Multiple Hosts Example

Test on multiple existing systems:
```bash
make defconfig-minio-warp-xfs DECLARE_HOSTS="server1,server2,server3" WARP_DEVICE=/dev/nvme0n1
make
make minio
make minio-warp
```

#### Different Block Sizes on Declared Hosts

For 16K block size testing:
```bash
make defconfig-minio-warp-xfs-16k DECLARE_HOSTS=foo WARP_DEVICE=/dev/nvme4n1
make
make minio
make minio-warp
```

For large block size (64K) testing:
```bash
make defconfig-minio-warp-xfs-lbs DECLARE_HOSTS=myserver WARP_DEVICE=/dev/nvme2n1
make
make minio
make minio-warp
```

#### A/B Testing with Declared Hosts

Compare baseline and development configurations:
```bash
# Use two hosts for A/B comparison
make defconfig-minio-warp-ab DECLARE_HOSTS="prod-server,dev-server" WARP_DEVICE=/dev/nvme1n1
make
make minio
make minio-warp
make minio-results  # Compare results between hosts
```

#### Important Notes for Declared Hosts

1. **Host Requirements**:
   - SSH access must be configured
   - Docker must be installed and running
   - The specified WARP_DEVICE must be available and not in use
   - Sufficient permissions to format and mount devices

2. **Device Selection**:
   - Always specify WARP_DEVICE when using declared hosts
   - Ensure the device is not mounted or in use
   - Device will be formatted - ensure no important data exists

3. **Network Configuration**:
   - Hosts must be reachable via SSH
   - Port 9000 (MinIO) should be available
   - Firewall rules should allow MinIO traffic if testing across hosts

## Configuration Options

### Manual Configuration

```bash
make menuconfig
# Navigate to: Workflows → MinIO S3 Storage Testing
# Enable MinIO Warp benchmarking
# Configure storage, Docker, and benchmark parameters
```

### Key Configuration Areas

#### Storage Configuration
- **Filesystem Type**: XFS (default), Btrfs, ext4
- **Block Size**: 4K (default), 8K, 16K, 32K, 64K
- **Device Management**: Automatic or manual device selection
- **Mount Options**: Filesystem-specific optimization flags

#### Benchmark Types
- **Full Suite**: All benchmark operation types
- **Mixed Workload**: Realistic GET/PUT/DELETE mix
- **GET Operations**: Download performance testing
- **PUT Operations**: Upload performance testing
- **DELETE Operations**: Object deletion performance
- **LIST Operations**: Bucket/object listing performance
- **MULTIPART Upload**: Large file upload testing

#### Benchmark Parameters
- **Object Size**: 256KiB to 256MiB (default: 10MiB)
- **Duration**: 30s to 600s (default: 120s)
- **Concurrency**: 1 to 256 (default: 16)
- **Number of Objects**: 100 to 100000 (default: 1000)

## Available Defconfigs

- `defconfig-minio-warp` - Basic MinIO Warp setup
- `defconfig-minio-warp-ab` - A/B testing configuration
- `defconfig-minio-warp-btrfs` - Btrfs filesystem testing
- `defconfig-minio-warp-xfs` - XFS filesystem testing
- `defconfig-minio-warp-xfs-16k` - XFS with 16K block size
- `defconfig-minio-warp-xfs-lbs` - XFS with large block size support
- `defconfig-minio-warp-multifs` - Multiple filesystem comparison
- `defconfig-minio-warp-storage` - Advanced storage configuration
- `defconfig-minio-warp-declared-hosts` - For existing systems

## Workflow Commands

### Setup and Deployment
```bash
make minio           # Deploy MinIO server
make minio-uninstall # Remove MinIO server
make minio-destroy   # Clean up MinIO data and containers
```

### Running Benchmarks
```bash
make minio-warp      # Run configured Warp benchmarks
make minio-results   # View and analyze benchmark results
```

## Results and Analysis

Benchmark results are stored in `workflows/minio/results/` with:
- Raw Warp JSON output files
- Performance analysis reports
- Throughput and latency graphs
- HTML reports with embedded visualizations

### Result Files

After running benchmarks, you'll find:
- `warp_benchmark_<host>_<timestamp>.json` - Raw benchmark data
- `warp_benchmark_<host>_<timestamp>_throughput.png` - Throughput graphs
- `warp_benchmark_<host>_<timestamp>_latency.png` - Latency graphs
- `warp_benchmark_report.html` - Full HTML report with metrics

### Demo Results

Example benchmark results are available in [demo-results/](demo-results/) containing throughput graphs from actual MinIO Warp test runs.

## Performance Analysis Tools

### Automated Analysis Script
```bash
python3 workflows/minio/scripts/analyze_warp_results.py \
    workflows/minio/results/warp_benchmark_*.json
```

Generates:
- Throughput over time graphs
- Latency distribution charts
- Operation rate comparisons
- Statistical summaries

### Report Generation
```bash
python3 workflows/minio/scripts/generate_warp_report.py \
    --results workflows/minio/results/
```

Creates an HTML report with:
- Performance metrics summary
- Embedded graphs and charts
- Comparative analysis across runs
- Recommendations based on results

## A/B Testing

Compare different configurations:

```bash
# Setup A/B testing with different filesystems
make defconfig-minio-warp-ab
make bringup
make minio
make minio-warp

# Results will show baseline vs dev node comparisons
make minio-results
```

## Advanced Usage

### Custom Storage Device

Specify a particular device for MinIO storage:
```bash
make menuconfig
# Navigate to: MinIO S3 Storage Testing → Storage configuration
# Set "Storage device path" to your device (e.g., /dev/nvme1n1)
```

### Running Specific Benchmarks

For targeted testing, disable full suite and select specific operations:
```bash
make menuconfig
# Navigate to: MinIO S3 Storage Testing → MinIO Warp benchmark configuration
# Disable "Run full benchmark suite"
# Select specific benchmark type (GET, PUT, DELETE, etc.)
```

### Adjusting Benchmark Parameters

Fine-tune benchmark behavior:
```bash
make menuconfig
# Navigate to: MinIO S3 Storage Testing → MinIO Warp benchmark configuration
# Adjust object size, duration, concurrency, etc.
```

### Declared Hosts Advanced Examples

#### Custom SSH Configuration

Use specific SSH key and user:
```bash
# First, ensure your SSH config is set up (~/.ssh/config):
# Host myserver
#     HostName 192.168.1.100
#     User admin
#     IdentityFile ~/.ssh/custom_key

make defconfig-minio-warp-xfs DECLARE_HOSTS=myserver WARP_DEVICE=/dev/sdb
make
make minio
make minio-warp
```

#### Testing with Different Filesystems on Declared Hosts

Test Btrfs on declared host:
```bash
make defconfig-minio-warp-btrfs DECLARE_HOSTS=storage-server WARP_DEVICE=/dev/nvme3n1
make
make minio
make minio-warp
```

Test ext4 on declared host:
```bash
make defconfig-minio-warp DECLARE_HOSTS=test-node WARP_DEVICE=/dev/sda3
make menuconfig  # Change filesystem to ext4
make
make minio
make minio-warp
```

#### Continuous Integration Example

For CI/CD pipelines with declared hosts:
```bash
#!/bin/bash
# CI script example
CI_HOST="ci-runner-01"
CI_DEVICE="/dev/nvme0n1"

# Run full benchmark suite
make defconfig-minio-warp-storage DECLARE_HOSTS=$CI_HOST WARP_DEVICE=$CI_DEVICE
make
make minio
make minio-warp

# Collect results
make minio-results
cp -r workflows/minio/results/ $CI_ARTIFACTS_DIR/
```

#### Multi-Node MinIO Cluster Testing

Test distributed MinIO setup:
```bash
# Configure for multi-node cluster
make defconfig-minio-warp-declared-hosts \
    DECLARE_HOSTS="minio-1,minio-2,minio-3,minio-4" \
    WARP_DEVICE=/dev/nvme0n1

# Edit configuration for distributed mode
make menuconfig
# Enable distributed MinIO options if available

make
make minio
make minio-warp
```

## Integration with Other Workflows

MinIO Warp can be combined with:
- **fstests**: Filesystem correctness testing before performance benchmarks
- **blktests**: Block layer testing for storage verification
- **Linux kernel testing**: Test with different kernel versions

## Troubleshooting

### Common Issues

1. **Docker not running**: Ensure Docker service is active
   ```bash
   sudo systemctl start docker
   ```

2. **Storage device busy**: Unmount device before testing
   ```bash
   sudo umount /dev/device
   ```

3. **Port conflicts**: Default MinIO port 9000 may be in use
   - Change port in configuration or stop conflicting service

### Debug Commands

```bash
# Check MinIO server status
docker ps | grep minio

# View MinIO logs
docker logs minio-server

# Verify storage mount
mount | grep minio

# Check Warp process
ps aux | grep warp
```

## Performance Tuning Tips

1. **Storage Optimization**:
   - Use dedicated NVMe devices for best performance
   - Enable filesystem-specific optimizations in mount options
   - Consider larger block sizes for large object workloads

2. **Network Optimization**:
   - Use high-bandwidth network interfaces
   - Configure jumbo frames if supported
   - Minimize network latency between client and server

3. **Benchmark Tuning**:
   - Increase concurrency for throughput testing
   - Use appropriate object sizes for your workload
   - Run longer duration tests for stable results

## Contributing

When adding new features or improvements:
1. Update relevant Kconfig options
2. Add corresponding Ansible playbook tasks
3. Update analysis scripts for new metrics
4. Document changes in this README

## References

- [MinIO Documentation](https://min.io/docs/)
- [Warp Benchmark Tool](https://github.com/minio/warp)
- [S3 API Reference](https://docs.aws.amazon.com/s3/index.html)

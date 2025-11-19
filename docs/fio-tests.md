# kdevops fio-tests workflow

kdevops includes comprehensive storage performance testing through the fio-tests
workflow, providing flexible I/O benchmarking with configurable test matrices,
A/B testing capabilities, and advanced graphing and visualization support.

## Origin and inspiration

The fio-tests workflow in kdevops is adapted from the original
[fio-tests framework](https://github.com/mcgrof/fio-tests), which was designed
to provide systematic storage performance testing with dynamic test generation
and comprehensive analysis capabilities. The kdevops implementation brings
these capabilities into the kdevops ecosystem with seamless integration to
support virtualization, cloud providers, and bare metal testing.

## Overview

The fio-tests workflow enables comprehensive storage device performance testing
by generating configurable test matrices across multiple dimensions:

- **Block sizes**: 4K, 8K, 16K, 32K, 64K, 128K
- **I/O depths**: 1, 4, 8, 16, 32, 64
- **Job counts**: 1, 2, 4, 8, 16 concurrent fio jobs
- **Workload patterns**: Random/sequential read/write, mixed workloads
- **A/B testing**: Baseline vs development configuration comparison

## Filesystem testing

In addition to raw block device testing, fio-tests supports comprehensive
filesystem-specific performance testing with different filesystem configurations.
This enables analysis of filesystem-level optimizations, block size impacts,
and feature interactions.

For detailed information about filesystem testing capabilities, see
[fio-tests filesystem testing documentation](fio-tests-fs.md).

## Quick start

### Basic configuration

Configure fio-tests for quick testing:

```bash
make defconfig-fio-tests-ci    # Use minimal CI configuration
make menuconfig                # Or configure interactively
make bringup                   # Provision test environment
make fio-tests                 # Run performance tests
```

### Comprehensive testing

For full performance analysis:

```bash
make menuconfig                # Select fio-tests dedicated workflow
# Configure test matrix, block sizes, IO depths, patterns
make bringup                   # Provision baseline and dev nodes
make fio-tests                 # Run comprehensive test suite
make fio-tests-graph           # Generate performance graphs
make fio-tests-compare         # Compare baseline vs dev results
```

## Configuration options

### Test types

The workflow supports multiple test types optimized for different analysis goals:

- **Performance analysis**: Comprehensive testing across all configured parameters
- **Latency analysis**: Focus on latency characteristics and tail latency
- **Throughput scaling**: Optimize for maximum throughput analysis
- **Mixed workloads**: Real-world application pattern simulation

### Test matrix configuration

Configure the test matrix through menuconfig:

```
Block size configuration →
  [*] 4K block size tests
  [*] 8K block size tests
  [*] 16K block size tests
  [ ] 32K block size tests
  [ ] 64K block size tests
  [ ] 128K block size tests

IO depth configuration →
  [*] IO depth 1
  [*] IO depth 4
  [*] IO depth 8
  [*] IO depth 16
  [ ] IO depth 32
  [ ] IO depth 64

Thread/job configuration →
  [*] Single job
  [*] 2 jobs
  [*] 4 jobs
  [ ] 8 jobs
  [ ] 16 jobs

Workload patterns →
  [*] Random read
  [*] Random write
  [*] Sequential read
  [*] Sequential write
  [ ] Mixed 75% read / 25% write
  [ ] Mixed 50% read / 50% write
```

### Advanced configuration

Advanced settings for fine-tuning:

- **I/O engine**: io_uring (recommended), libaio, psync, sync
- **Direct I/O**: Bypass page cache for accurate device testing
- **Test duration**: Runtime per test job (default: 60 seconds)
- **Ramp time**: Warm-up period before measurements (default: 10 seconds)
- **Results directory**: Storage location for test results and logs

## Device configuration

The workflow automatically selects appropriate storage devices based on your
infrastructure configuration:

### Virtualization (libvirt)
- NVMe: `/dev/disk/by-id/nvme-QEMU_NVMe_Ctrl_kdevops1`
- VirtIO: `/dev/disk/by-id/virtio-kdevops1`
- IDE: `/dev/disk/by-id/ata-QEMU_HARDDISK_kdevops1`
- SCSI: `/dev/sdc`

### Cloud providers
- AWS: `/dev/nvme2n1` (instance store)
- GCE: `/dev/nvme1n1`
- Azure: `/dev/sdd`
- OCI: Configurable sparse volume device

### Testing/CI
- `/dev/null`: For configuration validation and CI testing

## A/B testing

The fio-tests workflow supports comprehensive A/B testing through the
`KDEVOPS_BASELINE_AND_DEV` configuration, which provisions separate
nodes for baseline and development testing.

### Baseline establishment

```bash
make fio-tests                 # Run tests on both baseline and dev
make fio-tests-baseline        # Save current results as baseline
```

### Comparison analysis

```bash
make fio-tests-compare         # Generate A/B comparison analysis
```

This creates comprehensive comparison reports including:
- Side-by-side performance metrics
- Percentage improvement/regression analysis
- Statistical summaries
- Visual comparison charts

## Graphing and visualization

The fio-tests workflow includes comprehensive graphing capabilities through
Python scripts with matplotlib, pandas, and seaborn.

### Enable graphing

```bash
# In menuconfig:
Advanced configuration →
  [*] Enable graphing and visualization
      Graph output format (png)  --->
      (300) Graph resolution (DPI)
      (default) Matplotlib theme
```

### Available visualizations

#### Performance analysis graphs
```bash
make fio-tests-graph
```

Generates:
- **Bandwidth heatmaps**: Performance across block sizes and I/O depths
- **IOPS scaling**: Scaling behavior with increasing I/O depth
- **Latency distributions**: Read/write latency characteristics
- **Pattern comparisons**: Performance across different workload patterns

#### A/B comparison analysis
```bash
make fio-tests-compare
```

Creates:
- **Comparison bar charts**: Side-by-side baseline vs development
- **Performance delta analysis**: Percentage improvements across metrics
- **Summary reports**: Detailed statistical analysis

#### Trend analysis
```bash
make fio-tests-trend-analysis
```

Provides:
- **Block size trends**: Performance scaling with block size
- **I/O depth scaling**: Efficiency analysis across patterns
- **Latency percentiles**: P95, P99 latency analysis
- **Correlation matrices**: Relationships between test parameters

### Graph customization

Configure graph output through Kconfig:

- **Format**: PNG (default), SVG, PDF, JPG
- **Resolution**: 150 DPI (CI), 300 DPI (standard), 600 DPI (high quality)
- **Theme**: default, seaborn, dark_background, ggplot, bmh

## Workflow targets

The fio-tests workflow provides several make targets:

### Core testing
- `make fio-tests`: Run the configured test matrix
- `make fio-tests-baseline`: Establish performance baseline
- `make fio-tests-results`: Collect and summarize test results

### Analysis and visualization
- `make fio-tests-graph`: Generate performance graphs
- `make fio-tests-compare`: Compare baseline vs development results
- `make fio-tests-trend-analysis`: Analyze performance trends

### Help
- `make fio-tests-help-menu`: Display available fio-tests targets

## Results and output

### Test results structure

Results are organized in the configured results directory (default: `/data/fio-tests`):

```
/data/fio-tests/
├── jobs/                          # Generated fio job files
│   ├── randread_bs4k_iodepth1_jobs1.ini
│   └── ...
├── results_*.json                 # JSON format results
├── results_*.txt                  # Human-readable results
├── bw_*, iops_*, lat_*            # Performance logs
├── graphs/                        # Generated visualizations
│   ├── performance_bandwidth_heatmap.png
│   ├── performance_iops_scaling.png
│   └── ...
├── analysis/                      # Trend analysis
│   ├── block_size_trends.png
│   └── correlation_heatmap.png
└── baseline/                      # Baseline results
    └── baseline_*.txt
```

### Result interpretation

#### JSON output structure
Each test produces detailed JSON output with:
- Bandwidth metrics (KB/s)
- IOPS measurements
- Latency statistics (mean, stddev, percentiles)
- Job-specific performance data

#### Performance logs
Detailed time-series logs for:
- Bandwidth over time
- IOPS over time
- Latency over time

## CI integration

The fio-tests workflow includes CI-optimized configuration:

```bash
make defconfig-fio-tests-ci
```

CI-specific optimizations:
- Uses `/dev/null` as target device
- Minimal test matrix (4K block size, IO depth 1, single job)
- Short test duration (10 seconds) and ramp time (2 seconds)
- Lower DPI (150) for faster graph generation
- Essential workload patterns only (random read)

## Troubleshooting

### Common issues

#### Missing dependencies
```bash
# Ensure graphing dependencies are installed
# This is handled automatically when FIO_TESTS_ENABLE_GRAPHING=y
```

#### No test results
- Verify device permissions and accessibility
- Check fio installation: `fio --version`
- Examine fio job files in results directory

#### Graph generation failures
- Verify Python dependencies: matplotlib, pandas, seaborn
- Check results directory contains JSON output files
- Ensure sufficient disk space for graph files

### Debug information

Enable verbose output:
```bash
make V=1 fio-tests              # Verbose build output
make AV=2 fio-tests             # Ansible verbose output
```

## Performance considerations

### Test duration vs coverage
- **Short tests** (10-60 seconds): Quick validation, less accurate
- **Medium tests** (5-10 minutes): Balanced accuracy and time
- **Long tests** (30+ minutes): High accuracy, comprehensive analysis

### Resource requirements
- **CPU**: Scales with job count and I/O depth
- **Memory**: Minimal for fio, moderate for graphing (pandas/matplotlib)
- **Storage**: Depends on test duration and logging configuration
- **Network**: Minimal except for result collection

### Optimization tips
- Use dedicated storage for results directory
- Enable direct I/O for accurate device testing
- Configure appropriate test matrix for your analysis goals
- Use A/B testing for meaningful performance comparisons

## Integration with other workflows

The fio-tests workflow integrates seamlessly with other kdevops workflows:

### Combined testing
- Run fio-tests alongside fstests for comprehensive filesystem analysis
- Use with sysbench for database vs raw storage performance comparison
- Combine with blktests for block layer and device-level testing

### Steady state preparation
- Use `KDEVOPS_WORKFLOW_ENABLE_SSD_STEADY_STATE` for SSD conditioning
- Run steady state before fio-tests for consistent results

## Best practices

### Configuration
1. Start with CI configuration for validation
2. Gradually expand test matrix based on analysis needs
3. Use A/B testing for meaningful comparisons
4. Enable graphing for visual analysis

### Testing methodology
1. Establish baseline before configuration changes
2. Run multiple iterations for statistical significance
3. Use appropriate test duration for your workload
4. Document test conditions and configuration

### Result analysis
1. Focus on relevant metrics for your use case
2. Use trend analysis to identify optimal configurations
3. Compare against baseline for regression detection
4. Share graphs and summaries for team collaboration

## Contributing

The fio-tests workflow follows kdevops development practices:

- Use atomic commits with DCO sign-off
- Include "Generated-by: Claude AI" for AI-assisted contributions
- Test changes with CI configuration
- Update documentation for new features
- Follow existing code style and patterns

For more information about contributing to kdevops, see the main project
documentation and CLAUDE.md for AI development guidelines.

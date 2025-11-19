# fio-tests filesystem testing

The fio-tests workflow includes comprehensive filesystem-specific performance
testing capabilities, enabling detailed analysis of filesystem optimizations,
block size configurations, and feature interactions. This extends beyond raw
block device testing to provide insights into real-world filesystem performance
characteristics.

## Overview

Filesystem testing in fio-tests allows you to:

- Test multiple filesystems (XFS, ext4, btrfs) with different configurations
- Compare filesystem performance across various block sizes and features
- Analyze impact of filesystem-specific optimizations
- Support block size ranges for realistic I/O pattern testing
- Enable multi-filesystem comparison testing with section-based configurations
- Integrate with A/B testing infrastructure for kernel comparison

Unlike raw block device testing which measures device-level performance,
filesystem testing evaluates performance against mounted filesystems with
specific configurations, providing insights into:

- Filesystem block size impact on I/O performance
- Feature overhead (reflink, compression, checksumming)
- Metadata operation performance
- Real-world application I/O pattern behavior

## Architecture

### Third drive usage

Filesystem testing uses a dedicated third storage drive separate from:
- **kdevops0**: Data partition (`/data`)
- **kdevops1**: Block device testing target
- **kdevops2**: Filesystem testing target (new)

This separation ensures filesystem tests don't interfere with block device
testing and allows running both test types within the same infrastructure.

### Filesystem lifecycle

The workflow automatically handles:
1. **Filesystem creation**: mkfs with configured parameters
2. **Mounting**: Mount with specified options
3. **Testing**: Run fio tests against mount point
4. **Cleanup**: Unmount and optionally destroy filesystem

### Integration with test matrix

Filesystem testing inherits all fio-tests capabilities:
- Block size matrix configuration
- I/O depth testing
- Job count scaling
- Workload pattern selection
- A/B testing support

## Supported filesystems

### XFS

XFS testing supports various block sizes and modern features:

#### Block sizes
- **4K**: Standard small block size
- **16K**: Common large block size (default)
- **32K**: Medium large block size
- **64K**: Maximum block size

#### Features
- **reflink**: Copy-on-write file cloning
- **rmapbt**: Reverse mapping B-tree
- **sparse inodes**: Efficient inode allocation

#### Example configuration
```bash
make defconfig-fio-tests-fs-xfs
```

This configures XFS with:
- Block size: 16K
- Sector size: 4K
- Features: reflink=1, rmapbt=1, sparse=1

### ext4

ext4 testing includes standard and bigalloc configurations:

#### Standard configuration
- Traditional ext4 with 4K blocks
- Standard features enabled
- Suitable for general workload testing

#### Bigalloc configuration
- Cluster-based allocation
- Cluster sizes: 16K, 32K, 64K
- Optimized for large file operations

#### Example configuration
```bash
make defconfig-fio-tests-fs-ext4-bigalloc
```

This configures ext4 with:
- Bigalloc enabled
- Cluster size: 32K
- Optimized for large sequential I/O

### btrfs

btrfs testing supports modern features:

#### Features
- **no-holes**: Optimized sparse file support
- **free-space-tree**: Fast free space management
- **Compression**: zstd, lzo, zlib support
- **Checksumming**: Data integrity verification

#### Example configuration
```bash
make defconfig-fio-tests-fs-btrfs-zstd
```

This configures btrfs with:
- Compression: zstd level 3
- Modern features: no-holes, free-space-tree
- Mount options optimized for performance

## Quick start

### Single filesystem testing

Test a specific filesystem configuration:

```bash
# XFS with 16K blocks
make defconfig-fio-tests-fs-xfs
make bringup
make fio-tests
make fio-tests-results
```

### Multi-filesystem comparison

Compare multiple filesystem configurations:

```bash
# XFS 4K vs 16K block size
make defconfig-fio-tests-fs-xfs-4k-vs-16k
make bringup                     # Creates demo-fio-tests-xfs-4k and demo-fio-tests-xfs-16k VMs
make fio-tests                   # Run tests on both configurations
make fio-tests-multi-fs-compare  # Generate comparison analysis
```

### Cross-filesystem comparison

Compare XFS, ext4, and btrfs:

```bash
# XFS 16K vs ext4 bigalloc vs btrfs zstd
make defconfig-fio-tests-fs-xfs-vs-ext4-vs-btrfs
make bringup                     # Creates 3 VMs with different filesystems
make fio-tests
make fio-tests-multi-fs-compare
```

### Comprehensive XFS analysis

Test all XFS block sizes:

```bash
make defconfig-fio-tests-fs-xfs-all-fsbs
make bringup                     # Creates VMs for 4K, 16K, 32K, 64K
make fio-tests
make fio-tests-multi-fs-compare
```

## Block size configuration

### Fixed block sizes

Traditional testing with specific block sizes:

```bash
make menuconfig
# Navigate to: fio-tests → Block size configuration
# Select specific sizes: 4K, 16K, 32K, etc.
```

Each enabled block size creates a separate test job.

### Block size ranges

Test realistic I/O patterns with ranges:

```bash
make defconfig-fio-tests-fs-ranges
```

This enables block size ranges such as:
- **4K-16K**: Mix of small and medium I/O
- **16K-64K**: Large sequential I/O patterns
- **4K-128K**: Full range realistic patterns

Block size ranges better simulate real-world application behavior where
I/O sizes vary rather than remaining constant.

#### Range configuration

In menuconfig:
```
fio-tests → Block size configuration →
  Block size ranges →
    [*] Enable block size range testing
    [*] 4K-16K range
    [*] 16K-64K range
    [ ] 4K-128K range
```

## CLI override for quick testing

For rapid iteration and CI scenarios, use CLI overrides to bypass full
configuration:

### Quick test mode

Run minimal tests for validation:

```bash
FIO_TESTS_QUICK_TEST=y make defconfig-fio-tests-fs-xfs
make bringup
make fio-tests    # Runs ~1 minute test instead of full suite
```

Quick mode automatically:
- Reduces test matrix to essential tests
- Sets short runtime (15 seconds)
- Uses minimal I/O depth and job counts
- Enables fast iteration for development

### Custom runtime override

Adjust test duration without reconfiguration:

```bash
# 5-minute tests
FIO_TESTS_RUNTIME=300 make defconfig-fio-tests-fs-xfs
make bringup
make fio-tests

# 30-minute comprehensive tests
FIO_TESTS_RUNTIME=1800 make defconfig-fio-tests-fs-xfs
make bringup
make fio-tests
```

### Combined overrides

Use multiple overrides together:

```bash
# Quick validation with custom device
FIO_TESTS_QUICK_TEST=y FIO_TESTS_DEVICE=/dev/nvme0n1 make defconfig-fio-tests-fs-xfs
make bringup
make fio-tests
```

### Available CLI overrides

Environment variables that can override configuration:

- `FIO_TESTS_QUICK_TEST=y`: Enable quick test mode
- `FIO_TESTS_RUNTIME=<seconds>`: Test runtime per job
- `FIO_TESTS_DEVICE=<path>`: Override target device
- `FIO_TESTS_RAMP_TIME=<seconds>`: Warmup time before measurement

#### Override detection

The kconfig system automatically detects CLI-set variables:

```kconfig
config FIO_TESTS_QUICK_TEST_SET_BY_CLI
    bool
    output yaml
    default $(shell, scripts/check-cli-set-var.sh FIO_TESTS_QUICK_TEST)

config FIO_TESTS_QUICK_TEST
    bool "Enable quick test mode for CI/demo"
    default y if FIO_TESTS_QUICK_TEST_SET_BY_CLI
```

This enables seamless integration between manual configuration and CLI overrides.

## Multi-filesystem testing

### Section-based architecture

Multi-filesystem testing uses a section-based approach similar to fstests,
where each filesystem configuration gets its own dedicated VM and section
identifier.

#### Section naming

Sections follow the pattern: `<filesystem>-<variant>`

**XFS sections:**
- `xfs-4k`: XFS with 4K block size
- `xfs-16k`: XFS with 16K block size
- `xfs-32k`: XFS with 32K block size
- `xfs-64k`: XFS with 64K block size

**ext4 sections:**
- `ext4-std`: Standard ext4 configuration
- `ext4-bigalloc`: ext4 with bigalloc enabled

**btrfs sections:**
- `btrfs-std`: Standard btrfs configuration
- `btrfs-zstd`: btrfs with zstd compression

### Section configuration file

Filesystem configurations are defined in `workflows/fio-tests/sections.conf`:

```conf
[xfs-16k]
mkfs_type=xfs
mkfs_cmd=-f -m reflink=1,rmapbt=1 -i sparse=1 -b size=16k
mount_opts=defaults

[ext4-bigalloc]
mkfs_type=ext4
mkfs_cmd=-F -O bigalloc -C 32k
mount_opts=defaults

[btrfs-zstd]
mkfs_type=btrfs
mkfs_cmd=-f
mount_opts=defaults,compress=zstd:3
```

### Node generation

Multi-filesystem setups dynamically generate nodes based on enabled sections:

```bash
# This configuration:
make defconfig-fio-tests-fs-xfs-4k-vs-16k

# Creates these VMs:
# - demo-fio-tests-xfs-4k       (baseline)
# - demo-fio-tests-xfs-4k-dev   (if A/B testing enabled)
# - demo-fio-tests-xfs-16k      (baseline)
# - demo-fio-tests-xfs-16k-dev  (if A/B testing enabled)
```

### Ansible group organization

Each section gets dedicated Ansible groups:

```
[all]
demo-fio-tests-xfs-4k
demo-fio-tests-xfs-16k

[baseline]
demo-fio-tests-xfs-4k
demo-fio-tests-xfs-16k

[fio_tests]
demo-fio-tests-xfs-4k
demo-fio-tests-xfs-16k

[fio_tests_xfs_4k]
demo-fio-tests-xfs-4k

[fio_tests_xfs_16k]
demo-fio-tests-xfs-16k
```

This enables targeted execution:
```bash
# Run tests on specific section
ansible-playbook playbooks/fio-tests.yml --limit fio_tests_xfs_4k

# Run on all sections
ansible-playbook playbooks/fio-tests.yml
```

## Results and analysis

### Result collection

Collect results from all filesystem configurations:

```bash
make fio-tests-results
```

Results are organized by hostname:
```
workflows/fio-tests/results/
├── demo-fio-tests-xfs-4k/
│   ├── results_randread_bs4k_iodepth1_jobs1.json
│   └── ...
├── demo-fio-tests-xfs-16k/
│   ├── results_randread_bs4k_iodepth1_jobs1.json
│   └── ...
└── demo-fio-tests-ext4-bigalloc/
    └── ...
```

### Multi-filesystem comparison

Generate comprehensive comparison analysis:

```bash
make fio-tests-multi-fs-compare
```

This creates:
```
workflows/fio-tests/results/comparison/
├── overview.txt                    # Summary statistics
├── comparison.csv                  # Exportable data
├── bandwidth_heatmap.png           # Visual comparison
├── iops_scaling.png                # Scaling analysis
└── comprehensive_analysis.html     # Full HTML report
```

### Comparison features

The multi-filesystem comparison tool provides:

#### Performance overview
- Side-by-side metrics for all configurations
- Percentage improvements/regressions
- Statistical summaries (mean, median, stddev)

#### Visual analysis
- **Bandwidth heatmaps**: Performance across block sizes and filesystems
- **IOPS scaling charts**: Scaling behavior comparison
- **Latency distributions**: Latency characteristics per filesystem
- **Block size trends**: Optimal block size identification

#### Export formats
- **CSV**: Spreadsheet import for further analysis
- **HTML**: Interactive browsing with embedded graphs
- **PNG**: Individual graph files for presentations
- **TXT**: Plain text summaries for logs

### Graph generation

Generate individual graphs per filesystem:

```bash
make fio-tests-graph
```

Creates per-host graph directories:
```
workflows/fio-tests/results/demo-fio-tests-xfs-4k/graphs/
├── performance_bandwidth_heatmap.png
├── performance_iops_scaling.png
├── latency_distribution.png
└── ...
```

## Configuration examples

### XFS block size comparison

Test XFS performance across block sizes:

```bash
make defconfig-fio-tests-fs-xfs-all-blocksizes
```

Enables sections:
- xfs-4k
- xfs-8k
- xfs-16k
- xfs-32k
- xfs-64k

Use case: Identify optimal XFS block size for workload.

### Filesystem feature analysis

Compare btrfs compression algorithms:

```bash
make menuconfig
# Navigate to: fio-tests → Filesystem configuration → btrfs configuration
# Enable multiple compression variants
```

Enables sections:
- btrfs-std (no compression)
- btrfs-lzo (lzo compression)
- btrfs-zstd (zstd compression)

Use case: Evaluate compression overhead vs space savings.

### Real-world I/O simulation

Use block size ranges with realistic patterns:

```bash
make defconfig-fio-tests-fs-ranges
```

Configuration:
- Block size ranges: 4K-16K, 16K-64K
- Mixed read/write patterns
- Varied I/O depths
- Multiple job counts

Use case: Simulate database or application I/O patterns.

## A/B testing with filesystems

### Kernel comparison

Test kernel versions with filesystem configurations:

```bash
# Configure A/B testing
make menuconfig
# Enable: Baseline and dev node support
# Enable: Different kernel refs for baseline and dev

# Configure filesystem testing
make defconfig-fio-tests-fs-xfs

make bringup
make linux                          # Build kernels
make linux HOSTS=demo-fio-tests-dev # Build dev kernel
make fio-tests                      # Test both kernels
make fio-tests-compare              # Compare results
```

This creates:
- `demo-fio-tests`: Baseline kernel with XFS 16K
- `demo-fio-tests-dev`: Development kernel with XFS 16K

### Feature comparison

Compare filesystem features across kernel versions:

```bash
# Test XFS reflink performance in different kernels
make menuconfig
# Enable: A/B testing
# Enable: XFS with reflink

make bringup
make linux                          # Baseline kernel
make linux HOSTS=demo-fio-tests-dev # Dev kernel with XFS improvements
make fio-tests
make fio-tests-compare
```

## Performance tuning

### Long-duration testing

For comprehensive analysis, extend test duration:

```bash
make menuconfig
# fio-tests → Advanced configuration
# Runtime: 3600 seconds (1 hour)
# Ramp time: 30 seconds

make bringup
make fio-tests    # ~1 hour per filesystem configuration
```

Benefits of longer tests:
- Better statistical accuracy
- Reduced variance in measurements
- Identification of steady-state performance
- More reliable comparison data

### Resource optimization

Multi-filesystem testing runs VMs in parallel:

```bash
# Monitor resource usage
virsh list --all
virsh domstats demo-fio-tests-xfs-4k
virsh domstats demo-fio-tests-xfs-16k
```

Resource considerations:
- **CPU**: Each VM runs tests independently
- **Memory**: Per-VM memory allocation
- **Storage**: Multiple test drives allocated
- **I/O**: Parallel I/O from multiple VMs

### Result validation

Ensure result quality:

```bash
# Check for failed tests
grep -r "error" workflows/fio-tests/results/

# Verify JSON output
for f in workflows/fio-tests/results/*/results_*.json; do
    jq . "$f" > /dev/null || echo "Invalid: $f"
done

# Compare result counts
find workflows/fio-tests/results/ -name "results_*.json" | wc -l
```

## Troubleshooting

### Filesystem creation failures

Check mkfs parameters:

```bash
# Verify configuration in extra_vars.yaml
grep fio_tests_mkfs extra_vars.yaml

# Check available space on test device
ansible all -m shell -a "lsblk"
ansible all -m shell -a "parted -l"
```

Common issues:
- Insufficient device size for large block sizes
- Unsupported features on kernel version
- Missing filesystem utilities (xfsprogs, e2fsprogs, btrfs-progs)

### Mount failures

Verify mount options:

```bash
# Check mount attempts in ansible output
make AV=2 fio-tests

# Verify mount options compatibility
ansible all -m shell -a "mount | grep fio-tests"
```

Common issues:
- Incompatible mount options for filesystem
- Missing kernel module support
- Device already mounted

### Missing results

Verify test execution:

```bash
# Check for fio execution
ansible all -m shell -a "ps aux | grep fio"

# Verify job file generation
ansible all -m shell -a "ls -la /data/fio-tests/jobs/"

# Check for errors
ansible all -m shell -a "journalctl -xe | grep fio"
```

### Comparison analysis failures

Ensure results are complete:

```bash
# Verify all VMs have results
ls -la workflows/fio-tests/results/

# Check JSON validity
python3 workflows/fio-tests/scripts/generate_comparison_graphs.py \
    workflows/fio-tests/results/ \
    --output-dir workflows/fio-tests/results/comparison/ \
    --verbose
```

Common issues:
- Incomplete result collection
- Missing Python dependencies (matplotlib, pandas, seaborn)
- Insufficient results for comparison (need 2+ configurations)

## Best practices

### Configuration

1. **Start simple**: Begin with single filesystem testing before multi-filesystem
2. **Use defconfigs**: Leverage pre-built configurations for common scenarios
3. **Enable quick mode**: Use `FIO_TESTS_QUICK_TEST=y` for rapid iteration
4. **Document changes**: Note filesystem parameters for result interpretation

### Testing methodology

1. **Establish baseline**: Run tests multiple times to verify consistency
2. **Control variables**: Change one parameter at a time for clear analysis
3. **Use appropriate duration**: Longer tests for production analysis, short for development
4. **Verify results**: Check for anomalies before drawing conclusions

### Analysis

1. **Compare like with like**: Ensure same test matrix across configurations
2. **Look for patterns**: Identify consistent trends across multiple tests
3. **Consider overhead**: Account for filesystem feature overhead in analysis
4. **Share results**: Export CSV and graphs for team collaboration

### CI/CD integration

1. **Use quick mode**: Enable fast validation in pipelines
2. **Limit configurations**: Focus on critical filesystems for CI
3. **Archive results**: Save comparison data for historical analysis
4. **Set thresholds**: Define acceptable performance ranges for automated validation

## Example workflows

### Development workflow

Iterative testing during development:

```bash
# 1. Quick validation
FIO_TESTS_QUICK_TEST=y make defconfig-fio-tests-fs-xfs
make bringup
make fio-tests    # ~2 minutes

# 2. Extended validation
FIO_TESTS_RUNTIME=300 make defconfig-fio-tests-fs-xfs
make fio-tests    # ~10 minutes

# 3. Full comprehensive analysis
make defconfig-fio-tests-fs-xfs-all-fsbs
make fio-tests    # ~1 hour
make fio-tests-multi-fs-compare
```

### Kernel patch testing

Validate kernel changes impact:

```bash
# 1. Configure A/B testing
make menuconfig
# Enable: Baseline and dev nodes
# Enable: Different kernel refs
# Select: XFS filesystem testing

# 2. Build and test
make bringup
make linux                          # Baseline v6.6
make linux HOSTS=demo-fio-tests-dev # Dev v6.7-rc1
make fio-tests
make fio-tests-compare

# 3. Analyze results
cat workflows/fio-tests/results/comparison.txt
xdg-open workflows/fio-tests/results/comparison.html
```

### Filesystem optimization

Find optimal configuration:

```bash
# 1. Test all XFS block sizes
make defconfig-fio-tests-fs-xfs-all-fsbs
make bringup
make fio-tests
make fio-tests-multi-fs-compare

# 2. Analyze optimal block size
grep "IOPS" workflows/fio-tests/results/comparison.csv | sort -t',' -k3 -n

# 3. Test feature impact with optimal size
# Edit configuration to test reflink/rmapbt combinations
make menuconfig
make fio-tests
make fio-tests-multi-fs-compare
```

## Advanced topics

### Custom filesystem configurations

Add custom filesystem variants to `workflows/fio-tests/sections.conf`:

```conf
[xfs-custom]
mkfs_type=xfs
mkfs_cmd=-f -m reflink=1,rmapbt=1 -i sparse=1 -b size=16k -s size=4k -d agcount=16
mount_opts=defaults,inode64,largeio
```

Enable in Kconfig:
```kconfig
config FIO_TESTS_ENABLE_XFS_CUSTOM
    bool "Enable XFS custom configuration"
    depends on FIO_TESTS_ENABLE_XFS
```

### Integration with other workflows

Combine with other kdevops workflows:

```bash
# fio-tests + fstests for comprehensive analysis
make menuconfig
# Enable: fio-tests workflow
# Enable: fstests workflow (shared VMs)

make bringup
make fio-tests    # Performance baseline
make fstests      # Correctness validation
```

### Performance regression detection

Set up automated regression testing:

```bash
#!/bin/bash
# regression-test.sh

# Run baseline
make defconfig-fio-tests-fs-xfs
make bringup
make fio-tests
make fio-tests-baseline

# Apply changes
git checkout feature-branch

# Run comparison
make fio-tests
make fio-tests-compare

# Check for regressions
if grep -q "regression" workflows/fio-tests/results/comparison.txt; then
    echo "Performance regression detected!"
    exit 1
fi
```

## Using declared hosts (bare metal and pre-existing systems)

The fio-tests workflow supports declared hosts for testing on bare metal
servers, pre-provisioned VMs, or any pre-existing infrastructure with SSH
access. This allows you to skip the bringup process and use hosts you've
already configured.

### Enabling declared hosts

Configure kdevops to use declared hosts:

```bash
make menuconfig
# Navigate to: General setup
# Enable: [*] Use declared hosts (skip bringup process)
# Enter list of hosts when prompted
```

Or use environment variable:

```bash
DECLARED_HOSTS="server1 server2 server3" make menuconfig
# The hosts will be automatically populated
```

### Prerequisites for declared hosts

Before using declared hosts, ensure:

1. **SSH access**: SSH keys configured for passwordless access
2. **Required packages**: fio, python3, and other dependencies installed
3. **Storage devices**: Test devices available and accessible
4. **Permissions**: Appropriate user permissions for device access
5. **Filesystems**: Filesystem utilities installed (xfsprogs, e2fsprogs, btrfs-progs)

### Single filesystem testing with declared hosts

Test a specific filesystem on existing hosts:

```bash
# Configure
make menuconfig
# Enable: [*] Use declared hosts
# Enter: "server1 server2"
# Select: Dedicate workflows → fio-tests
# Configure: fio-tests → Filesystem configuration → XFS

# Run tests (no bringup needed)
make fio-tests
make fio-tests-results
```

### Multi-filesystem testing with declared hosts

For multi-filesystem comparison, name your hosts to match filesystem sections:

```bash
# Host naming pattern: hostname-fio-tests-<section>
DECLARED_HOSTS="server1-fio-tests-xfs-4k server2-fio-tests-xfs-16k server3-fio-tests-ext4-bigalloc"

make menuconfig
# Enable: [*] Use declared hosts
# The hosts will be automatically parsed and grouped by section

make fio-tests
make fio-tests-multi-fs-compare
```

The host names must follow the pattern `<prefix>-fio-tests-<section>` where:
- `<prefix>`: Your host prefix (e.g., server, demo, test)
- `<section>`: Filesystem section name (e.g., xfs-4k, xfs-16k, ext4-bigalloc)

### A/B testing with declared hosts

For kernel comparison testing, use paired hosts:

```bash
# Odd-numbered hosts become baseline, even-numbered become dev
DECLARED_HOSTS="baseline-server dev-server"

make menuconfig
# Enable: [*] Use declared hosts
# Enable: [*] Baseline and dev node support

# Install different kernels on each
ansible baseline -m shell -a "uname -r"
ansible dev -m shell -a "uname -r"

make fio-tests
make fio-tests-compare
```

### Filesystem configuration on declared hosts

When using declared hosts, you're responsible for:

1. **Device preparation**: Ensure test devices exist and are accessible
2. **Filesystem creation**: kdevops will create filesystems using configured parameters
3. **Cleanup**: Filesystems will be unmounted and optionally destroyed after tests

Example device setup on declared hosts:

```bash
# On your bare metal servers
# Ensure test device exists
ansible all -m shell -a "lsblk"

# Verify device is not mounted
ansible all -m shell -a "mount | grep /dev/sdb"

# kdevops will handle mkfs and mount based on configuration
```

### Environment variable usage

Combine declared hosts with CLI overrides for rapid testing:

```bash
# Quick validation on bare metal
DECLARED_HOSTS="server1" FIO_TESTS_QUICK_TEST=y make defconfig-fio-tests-fs-xfs
make fio-tests

# Extended test with custom runtime
DECLARED_HOSTS="server1 server2" FIO_TESTS_RUNTIME=1800 make defconfig-fio-tests-fs-xfs-4k-vs-16k
make fio-tests
```

### Advantages of declared hosts

Using declared hosts provides several benefits:

1. **Real hardware testing**: Test on actual production hardware
2. **Resource optimization**: Reuse existing infrastructure
3. **Custom configurations**: Pre-configure hosts with specific settings
4. **Faster iteration**: Skip VM provisioning for quick tests
5. **Heterogeneous testing**: Mix different hardware configurations

### Example workflows with declared hosts

#### Bare metal filesystem comparison

```bash
# Setup
export DECLARED_HOSTS="metal1-fio-tests-xfs-4k metal2-fio-tests-xfs-16k metal3-fio-tests-xfs-64k"

# Configure
make menuconfig
# Enable: Use declared hosts
# Select: fio-tests workflow
# Configure: Multi-filesystem testing

# Run comparison
make fio-tests
make fio-tests-multi-fs-compare

# Results in workflows/fio-tests/results/comparison/
```

#### Production hardware validation

```bash
# Test XFS on actual hardware before deployment
DECLARED_HOSTS="prod-candidate1 prod-candidate2" make defconfig-fio-tests-fs-xfs

# Run comprehensive tests
FIO_TESTS_RUNTIME=3600 make fio-tests
make fio-tests-results

# Analyze for production readiness
cat workflows/fio-tests/results/*/results_*.txt
```

#### Kernel regression testing on bare metal

```bash
# Setup hosts with baseline and dev kernels
export DECLARED_HOSTS="server-baseline server-dev"

make menuconfig
# Enable: Use declared hosts
# Enable: A/B testing

make fio-tests
make fio-tests-compare

# Check for regressions
diff workflows/fio-tests/results/server-baseline/results_*.txt \
     workflows/fio-tests/results/server-dev/results_*.txt
```

### Troubleshooting declared hosts

#### SSH access issues

```bash
# Test SSH connectivity
ansible all -m ping

# Verify SSH keys
ssh-copy-id user@server1
```

#### Device access issues

```bash
# Check device permissions
ansible all -m shell -a "ls -la /dev/sdb"

# Verify user can access device
ansible all -m shell -a "sudo -l"
```

#### Missing dependencies

```bash
# Install fio and filesystem utilities
ansible all -m package -a "name=fio state=present" --become
ansible all -m package -a "name=xfsprogs state=present" --become
ansible all -m package -a "name=e2fsprogs state=present" --become
ansible all -m package -a "name=btrfs-progs state=present" --become
```

#### Filesystem creation failures

```bash
# Check device is not mounted
ansible all -m shell -a "mount | grep fio-tests"

# Verify device size
ansible all -m shell -a "blockdev --getsize64 /dev/sdb"

# Check for existing filesystems
ansible all -m shell -a "blkid /dev/sdb"
```

## Contributing

When contributing filesystem testing features:

1. **Test defconfigs**: Add example configurations in `defconfigs/`
2. **Document sections**: Update `workflows/fio-tests/sections.conf`
3. **Extend Kconfig**: Add filesystem options in appropriate Kconfig files
4. **Update docs**: Document new features in this file
5. **Follow conventions**: Use existing patterns for consistency

For more information about kdevops contribution guidelines, see CLAUDE.md and
the main project documentation.

## See also

- [fio-tests main documentation](fio-tests.md): General fio-tests workflow
- [CLAUDE.md](../CLAUDE.md): AI development guidelines
- [Filesystem Testing Implementation Validation](../CLAUDE.md#filesystem-testing-implementation-validation): Technical details
- [Multi-Filesystem Testing Architecture](../CLAUDE.md#multi-filesystem-testing-architecture): Architecture overview

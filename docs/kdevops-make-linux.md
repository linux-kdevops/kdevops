# Booting into a configured version of Linux

As an example of a target workflow, if you decided you want to enable the
workflow of Linux kernel development, to get the configured version of Linux on
the systems we just brought up, all you have to run is:

```bash
make linux
```

To verify the kernel on it:

```bash
make uname
```

## A/B Kernel Testing

kdevops supports A/B testing with different kernel versions when
`KDEVOPS_BASELINE_AND_DEV` is enabled. This allows you to compare performance
or behavior between different kernel versions across baseline and development nodes.

### Configuration Options

When A/B testing is enabled, you can choose between two approaches:

#### Same Kernel Reference (Default)
Use the same kernel tree and reference for both baseline and dev nodes:
```
A/B kernel testing configuration (BOOTLINUX_AB_SAME_REF) [Y/n/?]
```

This is useful for testing configuration changes or different test parameters
with identical kernels.

#### Different Kernel References
Use different kernel references for baseline and dev nodes:
```
A/B kernel testing configuration
  1. Use same kernel reference for baseline and dev (BOOTLINUX_AB_SAME_REF)
> 2. Use different kernel references for baseline and dev (BOOTLINUX_AB_DIFFERENT_REF)
```

This enables testing between different kernel versions, commits, or branches.

When using different references, configure:
- **Development kernel tree URL**: Git repository (defaults to baseline tree)
- **Development kernel reference**: Branch, tag, or commit (e.g., "v6.8", "linux-next")
- **Development kernel release/local version**: Custom version strings for identification

### Make Targets

#### Standard Linux Building
```bash
make linux                 # Build and install kernels for all nodes
```

When A/B testing with different references is enabled, this automatically:
1. Builds and installs baseline kernel on baseline nodes
2. Builds and installs development kernel on dev nodes
3. Leaves the working directory with the dev kernel checked out

#### Individual Node Targeting
```bash
make linux-baseline        # Build and install kernel for baseline nodes only
make linux-dev             # Build and install kernel for dev nodes only
```

These targets are available when `KDEVOPS_BASELINE_AND_DEV=y` and allow
selective building and installation.

### Usage Examples

#### Testing Kernel Versions
Compare v6.7 (baseline) vs v6.8 (development):

```bash
# Configure baseline kernel
menuconfig → Workflows → Linux kernel → Git tree to clone: linus
            Reference to use: v6.7

# Configure A/B testing
menuconfig → Workflows → Linux kernel → A/B kernel testing
            → Use different kernel references
            → Development kernel reference: v6.8

make bringup               # Provision baseline and dev nodes
make linux                 # Install v6.7 on baseline, v6.8 on dev
make fstests               # Run tests on both kernel versions
make fstests-compare       # Compare results between versions
```

#### Testing Development Branches
Compare stable vs linux-next:

```bash
# Baseline: stable kernel
menuconfig → Reference to use: v6.8

# Development: linux-next
menuconfig → A/B kernel testing → Development kernel reference: linux-next

make linux-baseline        # Install stable kernel on baseline nodes
make linux-dev             # Install linux-next on dev nodes
```

#### Bisection Support
Test specific commits during bisection:

```bash
# Update development reference for bisection
menuconfig → Development kernel reference: abc123def

make linux-dev             # Install bisection commit on dev nodes
# Run tests and analyze results
```

### Working Directory State

After running `make linux` with different references:
- The Linux source directory contains the **development kernel** checkout
- Both baseline and dev nodes have their respective kernels installed
- Use `git log --oneline -5` to verify the current checkout

To switch the working directory to baseline:
```bash
git checkout v6.7          # Switch to baseline reference
```

### Integration with Testing Workflows

A/B kernel testing integrates seamlessly with all kdevops testing workflows:

```bash
# Run fstests with kernel comparison
make linux                 # Install different kernels
make fstests               # Test both kernel versions
make fstests-compare       # Generate comparison analysis

# Run fio-tests with kernel comparison
make linux                 # Install different kernels
make fio-tests             # Performance test both kernels
make fio-tests-compare     # Compare performance metrics

# Run sysbench with kernel comparison
make linux                 # Install different kernels
make sysbench              # Database tests on both kernels
```

### Best Practices

1. **Version Identification**: Use descriptive kernel release versions to distinguish builds
2. **Sequential Testing**: Install kernels before running test workflows
3. **Result Organization**: Use baseline/dev labels in test result analysis
4. **Git Management**: Keep track of which reference is currently checked out
5. **Systematic Comparison**: Use `*-compare` targets for meaningful analysis

### Troubleshooting

#### Build Failures
- Ensure both kernel references are valid and accessible
- Check that build dependencies are installed on all nodes
- Verify git repository permissions and network connectivity

#### Version Conflicts
- Use different `kernelrelease` and `localversion` settings for clear identification
- Check `/boot` directory for kernel installation conflicts
- Verify GRUB configuration after kernel installation

#### Node Targeting Issues
- Confirm `KDEVOPS_BASELINE_AND_DEV=y` is enabled
- Verify baseline and dev node groups exist in inventory
- Check ansible host patterns with `make linux-baseline HOSTS=baseline`

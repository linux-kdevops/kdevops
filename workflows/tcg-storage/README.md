# TCG Storage Testing Workflow

This workflow provides automated testing for TCG (Trusted Computing Group) Storage
and OPAL (Open Protocol for Authentication and Locking) functionality on
self-encrypting drives using the [go-tcg-storage](https://github.com/open-source-firmware/go-tcg-storage) test suite.

## Overview

The TCG Storage workflow allows you to:
- Test TCG/OPAL functionality on NVMe, SATA, and SAS drives
- Run unit tests for the go-tcg-storage library
- Perform integration tests on actual hardware
- Test drive ownership, locking ranges, and device revert operations
- Support A/B testing between baseline and development kernels

## Quick Start

### Using defconfig (Virtual Environment)

The easiest way to get started is using the provided defconfig:

```bash
make defconfig-tcg-storage
make
make bringup
make tcg-storage
```

### Using Declared Hosts (Bare Metal/Existing Systems)

For testing on real hardware with TCG/Opal support:

```bash
# Specify your host and NVMe device
make defconfig-tcg-storage-declared-hosts DECLARE_HOSTS=myserver TCG_DEVICE=/dev/nvme0n1
make
make tcg-storage
```

This skips the bringup phase and runs directly on the specified host.

### Manual Configuration

```bash
make menuconfig
# Navigate to: Workflows -> Dedicated workflow -> tcg-storage
# Configure TCG storage options as needed
make
make bringup
make tcg-storage
```

## Configuration Options

### Test Device Configuration

- **Device Path**: Configure the test device (default: `/dev/nvme0n1`)
- **Device Type**: Specify device type: `nvme`, `sata`, or `sas`
- **Password**: Set the password for TCG operations

### Test Types

- **Unit Tests**: Run go-tcg-storage library unit tests
- **Integration Tests**: Run tests on actual TCG/OPAL hardware
- **Take Ownership**: Test taking ownership of TCG device
- **Locking Ranges**: Test locking range operations
- **Device Revert**: Test reverting device to factory defaults

### Local Development

For local development of go-tcg-storage:

1. Enable `TCG_STORAGE_USE_LOCAL` in menuconfig
2. Set `TCG_STORAGE_LOCAL_PATH` to your local go-tcg-storage directory
3. The workflow will use your local code instead of cloning from GitHub

## Available Make Targets

```bash
make tcg-storage              # Run TCG storage tests
make tcg-storage-baseline     # Establish baseline
make tcg-storage-dev          # Run on development kernel
make tcg-storage-results      # View test results
make tcg-storage-results-full # View detailed results
make tcg-storage-clean        # Clean test results
make tcg-storage-tools-info   # Show TCG tools information
make tcg-storage-device-info  # Show TCG device information
make tcg-storage-take-ownership # Test device ownership
make tcg-storage-locking-ranges # Test locking ranges
make tcg-storage-revert       # Test device revert
```

## Tools Installed

The workflow installs the following tools from go-tcg-storage:

- **sedlockctl**: Manage SED/TCG drives
- **tcgsdiag**: Diagnostic tool for TCG drives
- **tcgdiskstat**: Display TCG drive statistics (like blkid for TCG)
- **gosedctl**: Alternative SED control tool

## Test Results

Test results are stored in `workflows/tcg-storage/results/` including:
- Unit test results
- Integration test results
- Device information
- Test summaries

## A/B Testing

To enable A/B testing between baseline and development kernels:

1. Enable `TCG_STORAGE_BASELINE_AND_DEV` in menuconfig
2. Configure different kernel versions for baseline and dev
3. Run tests: `make tcg-storage`
4. Compare results between baseline and dev nodes

## Declared Hosts Support

The TCG storage workflow fully supports declared hosts for testing on bare metal
or pre-existing infrastructure:

### Benefits of Declared Hosts
- Test on real TCG/Opal hardware
- No virtualization overhead
- Full integration test support
- Direct hardware access

### Example Usage

```bash
# Single host with specific NVMe device
make defconfig-tcg-storage-declared-hosts DECLARE_HOSTS=server1 TCG_DEVICE=/dev/nvme1n1
make
make tcg-storage

# Multiple hosts (comma-separated)
make defconfig-tcg-storage-declared-hosts DECLARE_HOSTS=server1,server2 TCG_DEVICE=/dev/nvme0n1
make
make tcg-storage
```

### Prerequisites for Declared Hosts
1. SSH access to the target hosts
2. Hosts listed in your SSH config or /etc/hosts
3. Root/sudo access on target hosts
4. NVMe device with TCG/Opal support
5. Go and build tools will be installed automatically

## Supported Hardware

The go-tcg-storage library has been tested with drives from:
- Samsung (PM961, PM981, 970 EVO Plus, 980 Pro, etc.)
- Intel (P4510, P4610)
- Seagate (Momentus, Exos)
- Corsair (Force MP510)
- SK hynix (PC611)
- Toshiba (MG08SCP16TE)
- Sabrent (Rocket 4.0)

See the full list in the [go-tcg-storage README](https://github.com/open-source-firmware/go-tcg-storage#tested-drives).

## Virtual Environment Limitations

**IMPORTANT**: Testing TCG/Opal in QEMU/KVM virtual environments has significant limitations:

1. **QEMU NVMe Controller**: The standard QEMU NVMe controller does NOT emulate TCG/Opal features.
   Most TCG commands will fail or return "not supported" errors.

2. **Unit Tests Only**: In virtual environments, only the go-tcg-storage unit tests will work.
   Integration tests that require actual TCG/Opal hardware will fail.

3. **Hardware Testing**: For full TCG/Opal testing, you need:
   - Physical hardware with TCG/Opal support
   - PCIe passthrough of NVMe devices to VMs
   - Or bare metal testing

To enable PCIe passthrough for real hardware testing in VMs, see the kdevops
PCIe passthrough documentation.

## Safety Warning

**WARNING**: TCG/OPAL operations can modify drive security settings. Only use
dedicated test devices. Operations like device revert will erase all TCG
configuration on the device.

## Troubleshooting

### Device Not Found

If your test device is not found:
1. Verify the device path in menuconfig
2. Check device permissions
3. Ensure the device supports TCG/OPAL

### Go Build Failures

If Go build fails:
1. Check Go version (requires 1.21+)
2. Enable `TCG_STORAGE_INSTALL_DEPS` to install Go
3. Check network connectivity for downloading dependencies

### TCG Operations Fail

If TCG operations fail:
1. Verify device supports TCG/OPAL: `make tcg-storage-device-info`
2. Check if device is already owned (may need revert)
3. Ensure correct password is configured

## Contributing

To contribute to this workflow:
1. Test changes with both unit and integration tests
2. Update documentation for new features
3. Follow kdevops coding standards
4. Submit patches to the kdevops mailing list

## License

This workflow is part of kdevops and licensed under copyleft-next-0.3.1.
The go-tcg-storage tools are licensed under BSD 3-Clause.
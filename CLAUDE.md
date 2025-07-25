# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository.

## Project Overview

kdevops is a comprehensive DevOps framework for Linux kernel development and
testing. It provides automation for setting up kernel development environments
and complex testing laboratories for kernel subsystems.

**Version**: 5.0.2
**Main Repository**: https://github.com/linux-kdevops/kdevops
**License**: copyleft-next-0.3.1

## Core Architecture

### Build System
- **Configuration**: Uses Linux kernel Kconfig system (`make menuconfig`,
                     `make nconfig`, `make dynconfig`)
- **Build**: Make-based with modular Makefiles (`Makefile.*`)
- **Automation**: Ansible playbooks in `playbooks/` directory
- **Infrastructure**: Supports virtualization (libguestfs/libvirt),
                      cloud providers (AWS, Azure, GCE, OCI), and bare metal

### Key Components
- `workflows/` - Testing workflows (fstests, blktests, selftests, CXL,
                 mmtests, NFS, etc.)
- `playbooks/` - Ansible automation with 40+ specialized roles
- `kconfigs/` - Modular configuration system. Provides modeling variabiilty
                support. This is essentially support for kconfig taken from
                the Linux kernel, with support for special "output yaml"
                support to allow the project to leverage kconfig symbols on
                ansible through the `extra_vars.yaml` file which is always
                present.
- `defconfigs/` - Pre-built configurations for common setups. These are
                  extremely useful for supporting not only easy quick setups
                  but are also instrumental for our continuous integration
                  support.
- `scripts/` - Workflow automation and helper scripts

## Common Development Commands

### Configuration and Setup
```bash
make menuconfig          # Interactive configuration
make dynconfig           # Supports dynamically generated kconfig files
make defconfig-<name>    # Use predefined configuration (see defconfigs/)
make                     # Build dependencies and setup
make bringup            # Provision and configure systems
make destroy            # Destroy provisioned systems
```

### Kernel Development
```bash
make linux              # Build and install kernel
make linux HOSTS="host1 host2"  # Target specific hosts
make linux-uninstall KVER="6.6.0-rc2"  # Uninstall specific kernel version
```

### Testing Workflows
```bash
# Filesystem testing
make fstests            # Run filesystem tests
make fstests-baseline   # Establish baseline
make fstests-results    # View results

# Block layer testing
make blktests           # Run block layer tests
make blktests-baseline  # Establish baseline
make blktests-results   # View results

# Linux kernel selftests
make selftests          # Run all selftests
make selftests-firmware # Run specific test suite
make selftests-kmod     # Run kernel module tests

# Other workflows
make pynfs              # NFS testing
make gitr               # Git regression testing
make ltp                # Linux Test Project
make sysbench           # Database performance testing
make mmtests            # Memory management tests from mmtests
```

### Development Utilities
```bash
make help               # Show available targets
make V=1 [target]       # Verbose build output
make AV=1-6 [target]    # Ansible verbose output (levels 0-6)
make dynconfig          # Generate dynamic configuration
make style              # Check for whitespace issues - ALWAYS run before completing work
make mrproper           # Clean everything and restart from scratch
```

## Key Workflows

### fstests (Filesystem Testing)
- **Purpose**: Comprehensive filesystem testing for XFS, Btrfs, EXT4, CIFS, NFS, tmpfs
- **Features**: Expunge list management, baseline tracking, regression detection
- **Location**: `workflows/fstests/`
- **Config**: Enable fstests workflow in menuconfig

### blktests (Block Layer Testing)
- **Purpose**: Block layer subsystem testing
- **Supports**: NVMe, SCSI, loop devices, NBD, ZBD
- **Location**: `workflows/blktests/`
- **Features**: Similar baseline/regression tracking as fstests

### Linux Kernel Building
- **Source Management**: Multiple git trees (Linus, stable, next, subsystem trees)
- **Features**: 9P filesystem for host-guest development, mirror support
- **Location**: `workflows/linux/`

### selftests (Kernel Selftests)
- **Purpose**: Parallel execution of Linux kernel selftests
- **Supports**: firmware, kmod, sysctl, and other kernel subsystem tests
- **Location**: `workflows/selftests/`

## Architecture Highlights

### Configuration System
- Uses Linux kernel Kconfig for consistent configuration management
- Modular configuration files in `kconfigs/` for different subsystems
- Dynamic configuration generation with `make dynconfig`
- Pre-built configurations in `defconfigs/` directory

### Workflow System
- Each workflow has dedicated Kconfig and Makefile
- Workflow-specific scripts in `scripts/workflows/`
- Ansible roles for automation in `playbooks/roles/`
- Result collection and baseline management

### Infrastructure Support
- **Virtualization**: libguestfs with libvirt (recommended), legacy Vagrant
- **Cloud**: AWS, Azure, GCE, OCI, OpenStack support via Terraform
- **PCIe Passthrough**: Real hardware testing in VMs with dynamic device assignment
- **Mirror Support**: For air-gapped environments

### Kernel CI Features
- Built-in continuous integration support
- Baseline management for known test failures
- Regression detection with git-style diff output
- Watchdog systems for automated recovery from hung tests

## Important File Locations

- `Kconfig` - Main configuration entry point
- `workflows/*/Kconfig` - Workflow-specific configuration options
- `workflows/*/Makefile` - Workflow automation targets
- `playbooks/roles/` - Reusable Ansible automation components
- `scripts/workflows/` - Workflow-specific helper scripts
- `docs/` - Comprehensive documentation

## Development Patterns

1. **Configuration-Driven**: Everything configurable through Kconfig
2. **Modular Design**: Workflow-specific components included conditionally
3. **Ansible Automation**: Role-based infrastructure and testing automation
4. **Baseline Management**: Comprehensive tracking of known failures and regressions
5. **Template Generation**: Dynamic file generation based on configuration

## Quick Setup Examples

### XFS Filesystem Testing
```bash
make defconfig-xfs      # Configure for XFS testing
make bringup           # Setup test environment
make fstests           # Run filesystem tests
```

### Kernel Development Environment
```bash
make menuconfig        # Configure kernel workflow
make bringup          # Setup development VMs
make linux            # Build and install kernel
```

### Block Layer Testing with NVMe
```bash
make defconfig-blktests_nvme
make bringup
make blktests
```

## Testing and Quality Assurance

- Expunge lists track known test failures in `workflows/*/expunges/`
- Baseline commands establish expected test results
- Results commands show test outcomes and regressions
- Watchdog scripts provide automated monitoring for long-running tests
- Integration with kernel development workflows and patchwork systems

This framework is designed by kernel developers for kernel developers,
providing production-ready automation for kernel testing and development
workflows.

## One commit per change

As with the Linux kernel, this project prefers commits to be atomic and to
the point. We don't want spell fixes to be blended in with code changes.
Spell fixes should go into separate commits. When in doubt, just don't do
any spell fixes unless asked explicitly to do that.

## Use the Signed-off-by tag

We want to use the Signed-off-by tag which embodies the application of the
Developer Certificate or Origin.

## Use Generated-by: Claude AI

Use this tag for code generated by Claude code AI. Put this before the
Signed-off-by tag.

**CRITICAL FORMATTING RULE**: When using "Generated-by: Claude AI", it MUST be
immediately followed by the "Signed-off-by:" tag with NO empty lines between them.
These two lines must be consecutive.

Correct format:
```
Subject line

Detailed description of changes...

Generated-by: Claude AI
Signed-off-by: Your Name <email@example.com>
```

**WRONG** - Do NOT add empty lines between Generated-by and Signed-off-by:
```
Generated-by: Claude AI

Signed-off-by: Your Name <email@example.com>
```

**WRONG** - Do NOT add extra empty lines:
```
Generated-by: Claude AI


Signed-off-by: Your Name <email@example.com>
```

## Code Quality Requirements

**IMPORTANT**: Before completing any work, you MUST run `make style` to check for
both whitespace issues and commit message formatting. This ensures code consistency
and prevents formatting issues from being introduced into the codebase.

The style checker will identify:
- Trailing whitespace
- Mixed tabs and spaces
- Files without newlines at EOF
- Other whitespace-related issues
- Incorrect commit message formatting (Generated-by/Signed-off-by spacing)

Fix all reported issues before submitting your work. The `make style` command
checks both file whitespace and the most recent commit message format.

### Automatic Whitespace Fixing

For convenience, you can automatically fix whitespace issues using:
```bash
python3 scripts/fix_whitespace_issues.py              # Fix all modified files
python3 scripts/fix_whitespace_issues.py file1 file2  # Fix specific files
```

The fixer script will:
- Remove trailing whitespace from lines
- Add missing newlines at end of files
- Reduce excessive blank lines to maximum 2 consecutive

Always run `make style` after using the fixer to verify all issues are resolved.

## Prompt Examples

Refer to PROMPTS.md for example set of prompts used to generate code on
kdevops using different AI agents and their respective commits and gradings.
This can be useful for humans but also for generative AI so it can improve.

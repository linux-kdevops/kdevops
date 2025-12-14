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

## ⚠️ CRITICAL RULE: NEVER FAKE TEST RESULTS

**ABSOLUTELY NEVER generate, synthesize, mock, or fake test results of any kind.**

kdevops is a professional testing framework used for Linux kernel development and
performance analysis. All test results MUST come from actual execution on real
Device Under Test (DUT) systems.

### What this means:
- **NEVER** create synthetic performance data or benchmark results
- **NEVER** generate mock IOPS, bandwidth, latency, or throughput numbers
- **NEVER** create fake JSON test output or fabricated metrics
- **ALWAYS** run actual tests on real VMs, bare metal, or cloud instances
- **ALWAYS** collect real data from actual fio, fstests, blktests execution
- **ALWAYS** verify that test systems are running and accessible before analysis

**Violation of this rule undermines the entire purpose of the kdevops testing framework
and produces misleading results that could affect important development decisions.**

## Core Architecture

### Build System
- **Configuration**: Linux kernel Kconfig system (`make menuconfig`, `make nconfig`, `make dynconfig`)
- **Build**: Make-based with modular Makefiles (`Makefile.*`)
- **Automation**: Ansible playbooks in `playbooks/` directory
- **Infrastructure**: Virtualization (libguestfs/libvirt), cloud (AWS, Azure, GCE, OCI), bare metal

### Key Components
- `workflows/` - Testing workflows (fstests, blktests, selftests, CXL, mmtests, NFS, etc.)
- `playbooks/` - Ansible automation with 40+ specialized roles
- `kconfigs/` - Modular configuration system with "output yaml" support for `extra_vars.yaml`
- `defconfigs/` - Pre-built configurations for quick setups and CI support
- `scripts/` - Workflow automation and helper scripts

## Common Development Commands

```bash
# Configuration
make menuconfig             # Interactive configuration
make dynconfig              # Generate dynamic configuration
make defconfig-<name>       # Use predefined configuration
make                        # Build dependencies and setup
make bringup               # Provision and configure systems
make destroy               # Destroy provisioned systems

# Kernel Development
make linux                 # Build and install kernel
make linux HOSTS="host1"   # Target specific hosts

# Testing Workflows
make fstests               # Run filesystem tests
make blktests              # Run block layer tests
make mmtests               # Run memory management tests
make mmtests-compare       # A/B testing comparison
make fio-tests             # Run storage performance tests
make selftests             # Run kernel selftests

# Quality Control
make style                 # Check whitespace/formatting - ALWAYS run before completing
make fix-whitespace-last-commit  # Fix whitespace in last commit
make help                  # Show available targets
ANSIBLE_VERBOSITY=1-6 make [target]  # Ansible verbose output
```

See [docs/ansible-callbacks.md](docs/ansible-callbacks.md) for Ansible callback plugin configuration.

## Key Workflows Summary

| Workflow | Purpose | Location | Key Features |
|----------|---------|----------|--------------|
| **fstests** | Filesystem testing | `workflows/fstests/` | XFS, Btrfs, EXT4, NFS; expunge lists; baseline tracking |
| **blktests** | Block layer testing | `workflows/blktests/` | NVMe, SCSI, loop, NBD, ZBD; regression detection |
| **mmtests** | Memory/performance | `workflows/mmtests/` | A/B testing, statistical analysis, HTML reports with graphs |
| **fio-tests** | Storage performance | `workflows/fio-tests/` | Block/filesystem testing, multi-FS comparison, graphing |
| **selftests** | Kernel selftests | `workflows/selftests/` | Parallel execution of firmware, kmod, sysctl tests |
| **linux** | Kernel building | `workflows/linux/` | Multiple git trees, 9P filesystem, mirror support |

### fio-tests Filesystem Testing
- **Block Device Testing**: Direct I/O for raw performance
- **Filesystem Testing**: XFS (4K-64K blocks), ext4 (bigalloc), btrfs (compression)
- **Multi-Filesystem**: Section-based comparison (xfs-4k vs xfs-16k, xfs vs ext4 vs btrfs)
- **Key Features**: Block size ranges, A/B testing, performance visualization

## Architecture Highlights

### Configuration System
- Linux kernel Kconfig for configuration management
- Dynamic configuration with `make dynconfig`
- CLI overrides via environment variables (see Kconfig CLI Override Patterns below)

### Workflow System
- Dedicated Kconfig and Makefile per workflow
- Workflow scripts in `scripts/workflows/`
- Ansible roles in `playbooks/roles/`
- Result collection and baseline management

### Infrastructure Support
- Virtualization: libguestfs/libvirt (recommended), legacy Vagrant
- Cloud: AWS, Azure, GCE, OCI via Terraform
- PCIe Passthrough: Real hardware in VMs
- Mirror Support: Air-gapped environments
- Kernel CI: Baseline management, regression detection, watchdog systems

## Important File Locations

- `Kconfig` - Main configuration entry point
- `workflows/*/Kconfig` - Workflow-specific configuration options
- `workflows/*/Makefile` - Workflow automation targets
- `playbooks/roles/` - Reusable Ansible automation components
- `scripts/workflows/` - Workflow-specific helper scripts
- `docs/` - Comprehensive documentation

## Adding New Workflows

When adding a workflow, add node generation rules to:
1. `playbooks/roles/gen_nodes/tasks/main.yml` (individual test flags or choice-based config)
2. `playbooks/roles/gen_hosts/tasks/main.yml` (host file generation)
3. `playbooks/roles/gen_hosts/templates/hosts.j2` (extend generic template with workflow logic)

**Examples**: See mmtests (individual test flags) or fio-tests (choice-based) implementations.
**Important**: Do NOT create workflow-specific template files; extend the generic hosts template.

## Git Commit Guidelines

All commits must follow these 5 rules:

### Rule 1/5: One Commit Per Change
Atomic commits only. Don't mix spell fixes with code changes. When in doubt, don't do spell fixes unless explicitly asked.

### Rule 2/5: Use the Signed-off-by Tag
Use git configured user name and email (check with `git config user.name` and `git config user.email`).

### Rule 3/5: Use Generated-by: Claude AI
Add this tag before Signed-off-by for AI-generated code.

**CRITICAL FORMATTING**: Generated-by MUST be immediately followed by Signed-off-by with NO empty lines between them.

```
Subject line

Detailed description...

Generated-by: Claude AI
Signed-off-by: Name <email@example.com>
```

### Rule 4/5: Avoid Shopping Cart Lists

**CRITICAL RULE: NEVER USE BULLET POINTS OR ITEMIZED LISTS IN COMMIT MESSAGES**

Use plain English paragraphs. Be clear and focused on helping reviewers understand the implementation.

**WRONG**:
```
Refactored to separate concerns:
- Distribution files handle package installation
- Single systemd task handles service enablement
```

**Correct**:
```
Each distribution file now handles package installation and sets the
nfs_server_service variable. A single systemd task in main.yml then
handles service enablement using the variable.
```

### Rule 5/5: Run make style Before Committing

**IMPORTANT**: Always run `make style` before completing work. This checks:
- Trailing whitespace, mixed tabs/spaces, missing newlines at EOF
- Commit message formatting (Generated-by/Signed-off-by spacing)

### Commit Message Template

```
subsystem: brief description in imperative mood (max 50 chars)

Detailed explanation of the problem and why the change is needed.
Use plain English paragraphs - NEVER bullet points or lists.

Explain what the change does and how it solves the problem. Focus
on clarity for reviewers.

Generated-by: Claude AI
Signed-off-by: Name <email@example.com>
```

## Code Quality Requirements

### Rust Code Quality
Always run for Rust code (workflows/rcloud, etc.):
```bash
cargo fmt    # Format using Linux kernel rustfmt standards
cargo clippy --all-targets --all-features -- -D warnings
```

### Automatic Whitespace Fixing
```bash
python3 scripts/fix_whitespace_issues.py              # Fix all modified files
python3 scripts/fix_whitespace_issues.py file1 file2  # Fix specific files
make style  # Verify all issues resolved
```

### Testing Generated Kconfig Files
Jinja2 templates (.j2) cannot be validated directly. Generate output and test that:
```bash
# Example: Testing AWS AMI Kconfig generation
python3 gen_kconfig_ami --quiet > /tmp/Kconfig.ami.test 2>&1
python3 ../../../scripts/detect_indentation_issues.py /tmp/Kconfig.ami.test
```

## Complex System Interactions

### Ansible Architecture Patterns

**Execution Contexts**:
- **Normal node**: Runs on each target node, variables are per-node
- **Control host**: `run_once: true, delegate_to: localhost` - runs once on control host
- **Per-node vars not available in localhost context** - use `hostvars[groups['group'][0]]['var']`

**A/B Testing Variable Management**:
- Detect dev nodes: `bootlinux_is_dev_node: "{{ ansible_hostname | regex_search('^.*-dev$') is not none }}"`
- Resolve for 9P builds: Use global config vars instead of fragile hostvars access

### Kconfig Dynamic Configuration Patterns

**Shell Command Integration**:
```kconfig
config BOOTLINUX_DEV_TREE_REF
    string "Development kernel reference"
    default $(shell, scripts/infer_last_stable_kernel.sh)
```
Best practices: Fallback values, test in different environments

**Dependencies and Conflicts**:
```kconfig
config BOOTLINUX_SHALLOW_CLONE
    bool "Shallow git clone"
    depends on !BOOTLINUX_AB_DIFFERENT_REF  # Prevent incompatible combinations
```

**CLI Override Pattern**:
```kconfig
config WORKFLOW_QUICK_TEST_SET_BY_CLI
    bool
    output yaml
    default $(shell, scripts/check-cli-set-var.sh WORKFLOW_QUICK_TEST)

config WORKFLOW_QUICK_TEST
    bool "Enable quick test mode"
    default y if WORKFLOW_QUICK_TEST_SET_BY_CLI
    help
      Can be enabled via environment variable: WORKFLOW_QUICK_TEST=y
```
Use `*_SET_BY_CLI` detection, conditional defaults, intelligent test matrix reduction for CI.

### Git Repository Management
- **Shallow clones**: Conflict with A/B testing different refs (missing git history)
- **Version detection**: Use `sort -V` for semantic versioning, filter `-rc` releases
- **Mirror access**: `git --git-dir=/path/to/mirror.git` for repository queries

### Debugging Methodology

**Configuration Tracing**:
1. Check `extra_vars.yaml` for resolved variables
2. Identify execution context (localhost vs target nodes)
3. Verify prerequisites (git refs exist before checkout)
4. Follow Ansible variable precedence

**A/B Testing Debug**:
```bash
grep "BOOTLINUX.*REF" .config
grep "bootlinux.*tree.*ref" extra_vars.yaml
git describe --tags --always
scripts/infer_last_stable_kernel.sh
```

### Common Root Causes
- Variable scope mismatches: Per-node vars unavailable on localhost
- Git ref unavailability: Shallow clones missing refs
- Execution context confusion: Code expecting node context on localhost
- Configuration interdependencies: Features conflicting unexpectedly

## Per-Node Variable Management

**Common Problems**:
1. Per-node variables not available on localhost
2. Host scope limiting with `HOSTS=` parameter
3. Race conditions in variable resolution

**Best Practices**:
- Prefer global variables for cross-context access
- Use explicit resolution with fallbacks
- Validate variable availability
- Use consistent naming: `global_*`, `node_*`, `active_*`

**Recommended Pattern**:
```yaml
# Use global configuration variables instead of fragile hostvars
- name: Resolve kernel reference
  set_fact:
    active_kernel_ref: >-
      {{
        bootlinux_dev_tree_ref
        if (kdevops_baseline_and_dev|bool and bootlinux_ab_different_ref|bool)
        else target_linux_ref
      }}
  run_once: true
  delegate_to: localhost
```

**Debugging**:
```bash
ANSIBLE_VERBOSITY=3 make target  # Verbose output
grep "active_.*:" extra_vars.yaml  # Check resolved variables
```

## Filesystem Testing Implementation Validation

**Checklist for fio-tests filesystem features**:

1. **Configuration**: Verify `.config` and `extra_vars.yaml` values
2. **Third Drive Integration**: Check device mapping (kdevops0=data, kdevops1=block, kdevops2=filesystem)
3. **Template Engine**: Verify fio job template handles block/filesystem modes
4. **A/B Testing**: Check both baseline and dev VMs created
5. **Kconfig Dependencies**: Verify auto-enabled dependencies
6. **Block Size Ranges**: Test fixed and range configurations
7. **Filesystem Features**: Verify mkfs commands (XFS reflink, ext4 bigalloc, btrfs compression)

**Known Issues**:
- VM provisioning can take 30+ minutes for package upgrades
- Use `CONFIG_KDEVOPS_WORKFLOW_ENABLE_FIO_TESTS=y` (not old `CONFIG_WORKFLOW_FIO_TESTS`)
- Missing newlines in Kconfig files cause syntax errors

**Debugging**:
```bash
ansible-playbook playbooks/fio-tests.yml --tags debug -v
ansible all -m shell -a "lsblk"
ansible all -m shell -a "mount | grep fio-tests"
```

## Multi-Filesystem Testing Architecture

**Section-Based Approach**: Separate VMs for each filesystem configuration

```bash
make defconfig-fio-tests-fs-xfs-4k-vs-16k          # Compare XFS block sizes
make defconfig-fio-tests-fs-xfs-all-fsbs           # All XFS block sizes
make defconfig-fio-tests-fs-xfs-vs-ext4-vs-btrfs  # Cross-filesystem comparison
make bringup
make fio-tests
make fio-tests-multi-fs-compare  # Generate comparison graphs
```

**Node Generation**: Dynamic based on `CONFIG_FIO_TESTS_SECTION_*=y` patterns
**Results**: Performance heatmaps, IO depth scaling, statistical summaries
**Integration**: Baseline management, A/B testing, existing result infrastructure

## AI Assistant Development Guidelines

**Investigation Sequence**:
1. Understand the problem
2. Trace execution path: config → ansible → execution
3. Identify context and scope
4. Find subsystem intersection points
5. Design holistic solutions (fix root cause)
6. Validate across use cases

**Common Anti-Patterns to Avoid**:
- Band-aid fixes ignoring root cause
- Breaking existing functionality
- Ignoring variable scope and execution context
- Missing cross-feature impact analysis

**Quality Gates**:
- Always run `make style` before completion
- Test both specific case and general functionality
- Consider impact on existing users
- Verify across different execution contexts

## Quick Setup Examples

```bash
# XFS Filesystem Testing
make defconfig-xfs && make bringup && make fstests

# Kernel Development
make menuconfig && make bringup && make linux

# Storage Performance with fio-tests
make defconfig-fio-tests-fs-xfs && make bringup && make fio-tests

# Multi-Filesystem Comparison
make defconfig-fio-tests-fs-xfs-vs-ext4-vs-btrfs && make bringup && make fio-tests
```

## Testing and Quality Assurance

- Expunge lists: Track known failures in `workflows/*/expunges/`
- Baseline commands: Establish expected test results
- Results commands: Show outcomes and regressions
- Watchdog scripts: Automated monitoring for long-running tests

This framework is designed by kernel developers for kernel developers,
providing production-ready automation for kernel testing and development
workflows.

## Prompt Examples

Refer to PROMPTS.md for examples of prompts used to generate code on kdevops
using different AI agents with their respective commits and gradings.

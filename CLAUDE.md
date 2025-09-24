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

### Valid approaches:
- ✅ Execute real tests: `ansible all -m shell -a "fio --output-format=json ..."`
- ✅ Collect actual JSON output from running VMs
- ✅ Parse and analyze real performance data from live systems
- ✅ Generate graphs and reports from actual test execution results

### Forbidden approaches:
- ❌ Creating synthetic performance numbers for demonstrations
- ❌ Generating mock test results for visualization examples
- ❌ Fabricating benchmark data to show workflows
- ❌ Using placeholder values like "let's assume 50K IOPS"

**Violation of this rule undermines the entire purpose of the kdevops testing framework
and produces misleading results that could affect important development decisions.**

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

# Memory management testing
make mmtests            # Run memory management tests
make mmtests-compare    # Compare baseline vs dev results (A/B testing)
```

### Development Utilities
```bash
make help               # Show available targets
make V=1 [target]       # Verbose build output
make AV=1-6 [target]    # Ansible verbose output (levels 0-6)
make dynconfig          # Generate dynamic configuration
make style              # Check for whitespace issues - ALWAYS run before completing work
make fix-whitespace-last-commit # Fixes commit white space damage
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

### mmtests (Memory Management Testing)
- **Purpose**: Comprehensive memory management and performance testing
- **Features**: A/B testing support, automated performance comparison, visual analysis
- **Location**: `workflows/mmtests/`
- **Key Capabilities**:
  - Run various memory and performance benchmarks (thpcompact, thpchallenge, etc.)
  - A/B testing between baseline and development kernels
  - Automated performance comparison with statistical analysis
  - Graph generation for performance visualization
  - HTML reports with embedded performance graphs

#### mmtests A/B Testing and Comparison
The mmtests workflow supports advanced A/B testing for kernel performance regression detection:

```bash
# Setup A/B testing configuration
make defconfig-mmtests-ab-testing     # Basic A/B testing
make defconfig-mmtests-ab-testing-thpcompact  # With monitoring

# Run the workflow
make bringup           # Provision baseline and dev nodes
make mmtests          # Run tests on both nodes
make mmtests-compare  # Generate comparison reports

# Results location
# workflows/mmtests/results/compare/
#   - comparison.html       # Main HTML report
#   - comparison.txt        # Text-based comparison
#   - graph-*.png          # Performance graphs
#   - comparison_report.html # Enhanced report with embedded graphs
```

**Comparison Features**:
- Automated collection of results from baseline and dev nodes
- Statistical analysis of performance differences
- Multiple visualization formats:
  - Performance trend graphs
  - Sorted performance comparisons
  - Smoothed data analysis
  - System monitoring graphs (vmstat, mpstat, proc stats)
- Professional HTML reports with:
  - Summary statistics
  - Detailed per-metric comparisons
  - Embedded performance graphs
  - Color-coded performance indicators

**Technical Implementation**:
- Local mmtests repository management with patch support
- Support for fixing known mmtests issues via patches in `workflows/mmtests/fixes/`
- Python and shell scripts for advanced graph generation
- Robust error handling and dependency management

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

## Adding New Workflows

When adding a new workflow to kdevops, you must add node generation rules to both
`playbooks/roles/gen_nodes/tasks/main.yml` and `playbooks/roles/gen_hosts/tasks/main.yml`
to avoid the failure "dedicated workflow has no rules for node configuration".

### Required Additions

For each new workflow, add the following sections to both playbooks:

#### gen_nodes playbook
Add node generation rules with appropriate conditional logic based on whether the
workflow uses individual test configuration flags (like mmtests) or choice-based
configuration (like fio-tests):

```yaml
# For workflows with individual test flags (like mmtests)
- name: Infer enabled WORKFLOW test section types
  set_fact:
    workflow_enabled_test_types: >-
      {{
        [kdevops_host_prefix + '-']
        | product(
            lookup('file', topdir_path + '/.config')
            | regex_findall('^CONFIG_WORKFLOW_ENABLE_(.*)=y$', multiline=True)
            | map('lower')
            | list
        )
        | map('join')
        | list
      }}
  when:
    - kdevops_workflows_dedicated_workflow
    - kdevops_workflow_enable_WORKFLOW
    - ansible_nodes_template.stat.exists
    - not kdevops_baseline_and_dev

# For workflows with choice-based configuration (like fio-tests)
- name: Generate the WORKFLOW kdevops nodes file using {{ kdevops_nodes_template }} as jinja2 source template
  tags: [ 'hosts' ]
  vars:
    node_template: "{{ kdevops_nodes_template | basename }}"
    nodes: "{{ [kdevops_host_prefix + '-WORKFLOW'] }}"
    all_generic_nodes: "{{ [kdevops_host_prefix + '-WORKFLOW'] }}"
  template:
    src: "{{ node_template }}"
    dest: "{{ topdir_path }}/{{ kdevops_nodes }}"
    force: yes
  when:
    - kdevops_workflows_dedicated_workflow
    - kdevops_workflow_enable_WORKFLOW
    - ansible_nodes_template.stat.exists
```

#### gen_hosts playbook
Add host file generation task for the workflow:

```yaml
- name: Generate the Ansible hosts file for a dedicated WORKFLOW setup
  tags: [ 'hosts' ]
  template:
    src: "{{ kdevops_hosts_template }}"
    dest: "{{ topdir_path }}/{{ kdevops_hosts }}"
    force: yes
    trim_blocks: True
    lstrip_blocks: True
  when:
    - kdevops_workflows_dedicated_workflow
    - kdevops_workflow_enable_WORKFLOW
    - ansible_hosts_template.stat.exists
```

#### Update the generic hosts template
Add support for your workflow in the generic hosts template at
`playbooks/roles/gen_hosts/templates/hosts.j2`. Find the dedicated workflow
section and add your workflow's conditional logic:

```jinja2
{% if kdevops_workflows_dedicated_workflow %}
{% if kdevops_workflow_enable_WORKFLOW %}
[all]
{{ kdevops_host_prefix }}-WORKFLOW
{% if kdevops_baseline_and_dev %}
{{ kdevops_host_prefix }}-WORKFLOW-dev
{% endif %}

[all:vars]
ansible_python_interpreter = "{{ kdevops_python_interpreter }}"

[baseline]
{{ kdevops_host_prefix }}-WORKFLOW

[baseline:vars]
ansible_python_interpreter = "{{ kdevops_python_interpreter }}"

{% if kdevops_baseline_and_dev %}
[dev]
{{ kdevops_host_prefix }}-WORKFLOW-dev

[dev:vars]
ansible_python_interpreter = "{{ kdevops_python_interpreter }}"

{% endif %}
[WORKFLOW]
{{ kdevops_host_prefix }}-WORKFLOW
{% if kdevops_baseline_and_dev %}
{{ kdevops_host_prefix }}-WORKFLOW-dev
{% endif %}

[WORKFLOW:vars]
ansible_python_interpreter = "{{ kdevops_python_interpreter }}"
{% else %}
```

### Examples

Refer to the existing mmtests implementation for workflows with multiple individual
test configuration flags, or the fio-tests implementation for workflows with
choice-based configuration patterns.

**Important**: All workflows use the same generic hosts template in
`playbooks/roles/gen_hosts/templates/hosts.j2`. Do NOT create workflow-specific
template files. Instead, extend the generic template with conditional logic
for your workflow.

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
Developer Certificate or Origin. Use the git configured user name and email
for the Signed-off-by tag (check with `git config user.name` and
`git config user.email`).

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

## Avoid Shopping cart lists

Generative AI seems to like to make commit logs long itemized lists of things
it did. This is stupid. This should be avoided. It is creating very silly
commit logs. Use plain english and get to the point. Be as clear a possible
and get to the point of not what you want to communicate, but rather what
will make a reviewer easily understand what the heck you are implementing.

You should *think* hard about your commit log, always.

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

### Verifying commit has no white space damage

Run the following after you commit something:
```bash
make fix-whitespace-last-commit
```

This will fix all white space only for new files you add.

## Complex System Interactions

kdevops integrates multiple subsystems (Ansible, Kconfig, Git, Make) that often
interact in non-obvious ways. Understanding these interactions is crucial for
effective debugging and development.

### Ansible Architecture Patterns

#### Host vs Control Node Execution
kdevops uses several Ansible execution patterns that affect variable scope:

- **Control Host Execution**: `run_once: true, delegate_to: localhost`
  - Executes once on the control host, not on target nodes
  - Per-node variables may not be available in localhost context
  - Common in 9P filesystem builds where single build is shared to all guests
  - Use `hostvars[groups['group_name'][0]]['variable_name']` to access node-specific vars

- **Variable Resolution Issues**:
  - Variables set per-node (like A/B testing configs) aren't automatically available on localhost
  - Need explicit variable resolution for cross-context access
  - Git repository state must be managed carefully when switching between refs

#### A/B Testing Variable Management
```yaml
# Detect dev nodes by hostname pattern
- name: Determine if this is a dev node for A/B testing
  set_fact:
    bootlinux_is_dev_node: "{{ ansible_hostname | regex_search('^.*-dev$') is not none }}"

# Resolve active parameters for 9P builds
- name: Determine active kernel parameters for A/B testing with 9P
  set_fact:
    active_linux_ref: "{{ hostvars[groups['dev'][0]]['target_linux_ref'] if 'dev' in group_names else target_linux_ref }}"
  run_once: true
  delegate_to: localhost
```

### Kconfig Dynamic Configuration Patterns

#### Shell Command Integration
```kconfig
config BOOTLINUX_DEV_TREE_REF
    string "Development kernel reference"
    default $(shell, scripts/infer_last_stable_kernel.sh)
    help
      The default is automatically inferred as the most recent stable
      kernel version from the git repository.
```

**Best Practices**:
- Always provide fallback values in scripts
- Place scripts in `scripts/` directory
- Use conditional defaults: `default VALUE if CONDITION`
- Test scripts work in different environments

#### Dependencies and Conflicts
```kconfig
config BOOTLINUX_SHALLOW_CLONE
    bool "Shallow git clone"
    default y if !KDEVOPS_BASELINE_AND_DEV
    depends on !BOOTLINUX_AB_DIFFERENT_REF
    help
      This option is automatically disabled when using A/B testing with
      different kernel references, as shallow clones may not contain all
      the required refs for checkout.
```

**Key Patterns**:
- `depends on !CONFIG_OPTION` - Prevent incompatible combinations
- `default y if !OTHER_CONFIG` - Conditional defaults
- Document why restrictions exist in help text

### Git Repository Management

#### Shallow Clone Limitations
- **Problem**: A/B testing with different refs requires full git history
- **Solution**: Make shallow clones depend on `!BOOTLINUX_AB_DIFFERENT_REF`
- **Detection**: Use `git --git-dir=/path/to/mirror.git` for mirror access

#### Version Detection Scripts
```bash
# Get latest stable kernel version, excluding release candidates
LAST_STABLE=$(git --git-dir="$GIT_TREE" tag --list 'v6.*' | \
    grep -v -- '-rc' | \
    sort -V | \
    tail -1)
```

**Patterns**:
- Use `sort -V` for proper semantic version ordering
- Filter out pre-release versions with `grep -v -- '-rc'`
- Always provide fallback values
- Handle missing git repositories gracefully

### Systematic Debugging Methodology

#### Configuration Tracing
1. **Check actual values**: Look at `extra_vars.yaml` for resolved variables
2. **Trace execution context**: Identify if code runs on localhost vs target nodes
3. **Verify prerequisites**: Ensure git refs exist before checkout attempts
4. **Follow variable inheritance**: Understand Ansible variable precedence

#### A/B Testing Debug Steps
```bash
# Check current configuration
grep "BOOTLINUX.*REF" .config
grep "bootlinux.*tree.*ref" extra_vars.yaml

# Verify git repository state
git branch -v
git describe --tags --always

# Test kernel version detection
scripts/infer_last_stable_kernel.sh

# Check available refs in mirror
git --git-dir=/mirror/linux.git tag --list 'v6.*' | sort -V | tail -10
```

#### Common Root Causes
- **Variable scope mismatches**: Per-node vars not available on localhost
- **Git ref unavailability**: Shallow clones missing required refs
- **Execution context confusion**: Code expecting node context running on localhost
- **Configuration interdependencies**: Features conflicting in unexpected ways

### Feature Integration Patterns

#### When Features Conflict
1. **Identify early**: Use Kconfig dependencies to prevent invalid combinations
2. **Provide alternatives**: Suggest compatible configurations
3. **Clear messaging**: Explain why restrictions exist
4. **Graceful degradation**: Disable conflicting features automatically

Example: Shallow clones + A/B different refs
- **Problem**: Shallow clone may not have required git refs
- **Solution**: `depends on !BOOTLINUX_AB_DIFFERENT_REF`
- **User experience**: Feature automatically disabled with explanation

#### Smart Defaults Philosophy
- **Infer from system state**: Use dynamic detection where possible
- **Show off capabilities**: Make examples compelling and useful
- **Balance automation with control**: Provide overrides for advanced users
- **Fail gracefully**: Always have sensible fallbacks

### AI Assistant Development Guidelines

#### Investigation Sequence
1. **Understand the problem**: What's not working as expected?
2. **Trace execution path**: Follow code from config → ansible → execution
3. **Identify context and scope**: Where does code run? What variables are available?
4. **Find intersection points**: Issues often emerge where subsystems meet
5. **Design holistic solutions**: Fix root cause, enhance the feature
6. **Validate across use cases**: Test both specific case and general functionality

#### Common Anti-Patterns to Avoid
- Band-aid fixes that ignore root cause
- Breaking existing functionality while fixing edge cases
- Ignoring variable scope and execution context
- Missing cross-feature impact analysis
- Not considering user experience implications

#### Quality Gates
- Always run `make style` before completion
- Test both the specific case and general functionality
- Consider impact on existing users and configurations
- Document new patterns for future reference
- Verify changes work across different execution contexts

### Examples from Practice

#### A/B Kernel Testing Issue
**Symptoms**: `bootlinux_dev_tree_kernelrelease` not being used in dev builds

**Root Cause Analysis**:
- 9P builds execute `run_once: true, delegate_to: localhost`
- Per-node A/B variables not available in localhost context
- Git checkout failed due to shallow clone missing refs

**Solution Components**:
1. Variable resolution: `hostvars[groups['dev'][0]]['target_linux_ref']`
2. Git ref management: Force checkout correct ref before build
3. Configuration fix: Disable shallow clones for A/B different refs
4. Smart defaults: Auto-detect latest stable kernel version

**Key Insight**: Complex issues often involve multiple subsystem interactions
rather than bugs in individual components.

## Per-Node Variable Management and Scope Issues

One of the most common and subtle sources of bugs in kdevops is per-node variable
scope issues, particularly when combining Ansible's execution contexts with
complex features like A/B testing and 9P builds.

### Understanding Ansible Execution Contexts

kdevops uses multiple Ansible execution patterns that affect variable visibility:

#### 1. Normal Node Execution
```yaml
- name: Set per-node variable
  set_fact:
    my_node_var: "{{ some_value }}"
  # Runs on each target node, variable is per-node
```

#### 2. Control Host Execution (run_once + delegate_to: localhost)
```yaml
- name: Process shared data
  set_fact:
    shared_var: "{{ processed_value }}"
  run_once: true
  delegate_to: localhost
  # Runs once on control host, not on target nodes
```

#### 3. Mixed Context Operations
```yaml
- name: Access per-node data from control host
  set_fact:
    aggregated_data: "{{ hostvars[groups['target'][0]]['node_var'] }}"
  run_once: true
  delegate_to: localhost
  # Attempts to access per-node variable from control context
```

### Common Variable Scope Problems

#### Problem 1: Per-Node Variables Not Available on localhost

**Symptom**: Variables set on target nodes are undefined when accessed from
localhost tasks.

**Example**:
```yaml
# This sets target_linux_ref ONLY on nodes matching the condition
- name: Set development kernel parameters for dev nodes
  set_fact:
    target_linux_ref: "{{ bootlinux_dev_tree_ref }}"
  when:
    - kdevops_baseline_and_dev|bool
    - bootlinux_ab_different_ref|bool
    - bootlinux_is_dev_node|default(false)|bool

# This tries to access per-node variable from localhost - MAY FAIL
- name: Use dev node's kernel ref for 9P build
  set_fact:
    active_ref: "{{ hostvars[groups['dev'][0]]['target_linux_ref'] }}"
  run_once: true
  delegate_to: localhost
```

**Root Cause**: The first task only runs on dev nodes and sets a per-node
variable. The second task runs on localhost but may not have access to the
per-node variable if there are timing or context issues.

#### Problem 2: Host Scope Limiting with HOSTS Parameter

**Symptom**: When using `make target HOSTS=specific-host`, variables set on
other hosts become inaccessible.

**Example**:
```bash
# This limits the playbook scope to only the dev node
make linux HOSTS=demo-fio-tests-dev
```

If your playbook tries to access variables from baseline nodes or uses
`hostvars[groups['baseline'][0]]`, these may fail because the baseline
nodes are not in the current run scope.

#### Problem 3: Race Conditions in Variable Resolution

**Symptom**: Variables appear to be set inconsistently or use wrong values.

**Root Cause**: Tasks with `run_once: true` may execute before per-node
tasks complete, leading to variable access before they're properly set.

### Best Practices for Variable Management

#### 1. Prefer Global Variables for Cross-Context Access

**Bad**:
```yaml
# Set per-node, access from localhost - fragile
- name: Set node-specific value
  set_fact:
    node_value: "{{ some_computation }}"

- name: Use in shared context
  command: "process {{ hostvars[groups['target'][0]]['node_value'] }}"
  run_once: true
  delegate_to: localhost
```

**Good**:
```yaml
# Use global variable that's accessible everywhere
- name: Use global configuration
  command: "process {{ global_config_value }}"
  run_once: true
  delegate_to: localhost
```

#### 2. Explicit Variable Resolution with Fallbacks

**Recommended Pattern**:
```yaml
- name: Resolve variable with robust fallback
  set_fact:
    active_value: >-
      {{
        hostvars[groups['dev'][0]]['target_value']
        if (groups['dev'] | length > 0 and
            hostvars[groups['dev'][0]]['target_value'] is defined)
        else fallback_global_value
      }}
  run_once: true
  delegate_to: localhost
```

#### 3. Validate Variable Availability

**Add Validation Tasks**:
```yaml
- name: Validate required variables are available
  fail:
    msg: "Required variable {{ item }} not found in dev node context"
  when: hostvars[groups['dev'][0]][item] is not defined
  loop:
    - target_linux_ref
    - target_linux_config
  run_once: true
  delegate_to: localhost
```

#### 4. Use Consistent Variable Naming

**Pattern**: Use prefixes to indicate variable scope:
- `global_*` - Available everywhere
- `node_*` - Per-node variables
- `active_*` - Resolved variables for shared operations

### Debugging Variable Scope Issues

#### 1. Add Debug Tasks

```yaml
- name: Debug variable availability
  debug:
    msg: |
      Groups: {{ groups }}
      Dev group: {{ groups['dev'] | default([]) }}
      Hostvars keys: {{ hostvars.keys() | list }}
      Target var: {{ hostvars[groups['dev'][0]]['target_var'] | default('UNDEFINED') }}
  run_once: true
  delegate_to: localhost
```

#### 2. Check Execution Context

```yaml
- name: Show execution context
  debug:
    msg: |
      Running on: {{ inventory_hostname }}
      Delegate to: {{ ansible_delegated_vars | default('none') }}
      Group names: {{ group_names }}
  tags: debug
```

#### 3. Use Ansible Verbose Mode

```bash
# Run with verbose output to see variable resolution
make target AV=3  # Ansible verbose level 3
```

### A/B Testing Variable Resolution Example

The A/B testing feature demonstrates proper variable resolution:

```yaml
# Step 1: Set per-node variables (runs on dev nodes only)
- name: Set development kernel parameters for dev nodes
  set_fact:
    target_linux_ref: "{{ bootlinux_dev_tree_ref }}"
  when:
    - kdevops_baseline_and_dev|bool
    - bootlinux_ab_different_ref|bool
    - bootlinux_is_dev_node|default(false)|bool

# Step 2: Resolve for shared operations (robust fallback)
- name: Determine active kernel parameters for A/B testing with 9P
  set_fact:
    active_linux_ref: "{{ bootlinux_dev_tree_ref }}"
    # Direct use of global var instead of fragile hostvars access
  when:
    - kdevops_baseline_and_dev|bool
    - bootlinux_ab_different_ref|bool
    - bootlinux_9p|bool
  run_once: true
  delegate_to: localhost

# Step 3: Use resolved variable
- name: Checkout correct git ref for A/B testing with 9P
  git:
    version: "{{ active_linux_ref | default(target_linux_ref) }}"
  run_once: true
  delegate_to: localhost
```

### Testing Variable Resolution

When developing features that involve per-node variables:

1. **Test with different HOSTS parameters**:
   ```bash
   make target HOSTS=demo-fio-tests      # baseline only
   make target HOSTS=demo-fio-tests-dev  # dev only
   make target                           # both nodes
   ```

2. **Test with different configurations**:
   - A/B testing enabled/disabled
   - Different node configurations
   - Varying group memberships

3. **Validate variable values**:
   ```bash
   # Check resolved variables
   grep "active_.*:" extra_vars.yaml

   # Verify node-specific settings
   make target AV=2 | grep -A5 -B5 "Set.*fact"
   ```

### Common Patterns to Avoid

#### Anti-Pattern 1: Assuming Variable Availability
```yaml
# DON'T: Assume hostvars access will work
- name: Use dev node variable
  command: "build {{ hostvars[groups['dev'][0]]['target_ref'] }}"
```

#### Anti-Pattern 2: Complex Conditional Logic in Variable Access
```yaml
# DON'T: Bury complex logic in variable expressions
- name: Set complex variable
  set_fact:
    value: "{{ 'dev' in group_names | ternary(dev_value, baseline_value) if condition else other_value }}"
```

#### Anti-Pattern 3: Side Effects in Variable Resolution
```yaml
# DON'T: Modify state during variable resolution
- name: Set variable with side effects
  set_fact:
    computed_value: "{{ some_value }}"
  changed_when: true  # Misleading change indication
```

### Recommended Patterns

#### Pattern 1: Explicit Variable Resolution Phase
```yaml
# Phase 1: Collect per-node data
- name: Collect node-specific configurations
  set_fact:
    node_config: "{{ local_config }}"

# Phase 2: Resolve for shared operations
- name: Resolve shared configuration
  set_fact:
    shared_config: "{{ resolved_value }}"
  run_once: true
  delegate_to: localhost

# Phase 3: Execute with resolved config
- name: Execute shared operation
  command: "process {{ shared_config }}"
  run_once: true
  delegate_to: localhost
```

#### Pattern 2: Configuration-Driven Variable Resolution
```yaml
# Use configuration variables that are globally accessible
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

This approach avoids the fragile `hostvars` access pattern and relies on
configuration variables that are available in all execution contexts.

## Prompt Examples

Refer to PROMPTS.md for example set of prompts used to generate code on
kdevops using different AI agents and their respective commits and gradings.
This can be useful for humans but also for generative AI so it can improve.

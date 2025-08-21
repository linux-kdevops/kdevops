# NixOS Support in kdevops

## Overview

kdevops provides NixOS as a third bringup option alongside guestfs and SKIP_BRINGUP. This integration offers a declarative, reproducible way to provision test VMs using NixOS's functional package management and configuration system.

## Architecture

### Virtualization Method

NixOS VMs in kdevops are managed through libvirt using the system session. This provides:
- Proper VM lifecycle management through libvirt
- Standard DHCP-based networking on the default libvirt network  
- Integration with existing libvirt infrastructure
- Professional VM management with `virsh` commands

### SSH Session Management

NixOS VMs use a sophisticated SSH session management system that enables multiple kdevops instances to coexist without conflicts:

#### Dynamic Key Generation
SSH keys are dynamically generated based on the directory location of your kdevops instance:
- **Key Naming Format**: `~/.ssh/kdevops-nixos-<directory>-<hash>`
- **Example**: For `/home/user/work/kdevops/`, the key would be `~/.ssh/kdevops-nixos-work-kdevops-a1b2c3d4`
- **Benefit**: Prevents SSH key conflicts when running multiple kdevops instances
- **Implementation**: `scripts/nixos_ssh_key_name.py` generates consistent key names

#### Network Configuration
VMs use standard libvirt networking with DHCP assignment:
- **Network**: Connected to libvirt's default network (virbr0)
- **IP Assignment**: Dynamic DHCP allocation from 192.168.122.x range
- **SSH Access**: Direct connection to VM IP address (no port forwarding needed)
- **Integration**: Works with existing libvirt network infrastructure

#### Automatic SSH Configuration
The system automatically manages SSH client configuration:
- **Config Management**: `update_ssh_config_nixos.py` updates `~/.ssh/config`
- **Per-VM Entries**: Each VM gets a dedicated SSH config block
- **Key Features**:
  ```
  Host kdevops
      HostName 192.168.122.169
      Port 22
      User kdevops
      IdentityFile ~/.ssh/kdevops-nixos-<dir>-<hash>
      StrictHostKeyChecking no
      UserKnownHostsFile /dev/null
  ```
- **Development Mode**: Host key checking disabled for convenience (not for production)

### Path Compatibility

NixOS uses different system paths than traditional Linux distributions. The implementation automatically handles:

| Component | Traditional Path | NixOS Path |
|-----------|-----------------|------------|
| Python interpreter | `/usr/bin/python3` | `/run/current-system/sw/bin/python3` |
| Bash shell | `/bin/bash` | `/run/current-system/sw/bin/bash` |

These paths are automatically detected and used in:
- Generated Ansible inventory files
- Ansible playbook tasks
- Shell script execution

## Supported Workflows

### Currently Supported

The following workflows have full NixOS support with automatic dependency resolution:

- **fstests**: Filesystem testing (XFS, Btrfs, EXT4)
- **blktests**: Block layer testing (NVMe, SCSI, NBD)
- **selftests**: Linux kernel selftests
- **mmtests**: Memory management performance testing
- **sysbench**: Database performance benchmarking
- **pynfs**: NFS protocol testing
- **ltp**: Linux Test Project
- **gitr**: Git regression testing

### Adding New Workflow Support

To add support for a new workflow:

1. Update `playbooks/templates/nixos/workflow-deps.nix.j2`
2. Add the necessary NixOS packages for your workflow
3. Test with `make defconfig-nixos && make bringup`

## Quick Start

### Basic NixOS VM

```bash
make defconfig-nixos
make
make bringup
```

### Workflow-Specific Configurations

```bash
# For XFS filesystem testing
make defconfig-nixos-xfs
make
make bringup
make fstests

# For block layer testing
make defconfig-nixos-blktests
make
make bringup
make blktests
```

## VM Management

### Libvirt Integration

NixOS VMs are managed through the standard libvirt system session, providing professional VM lifecycle management:

```bash
# VM lifecycle management
virsh start kdevops        # Start the VM
virsh shutdown kdevops     # Graceful shutdown
virsh destroy kdevops      # Force stop
virsh reboot kdevops       # Restart the VM

# VM information and monitoring
virsh list --all          # List all VMs and their states
virsh dominfo kdevops      # Show VM details
virsh domifaddr kdevops    # Get VM IP address
virsh console kdevops      # Connect to VM console
```

#### Libvirt Features
- **Standard Management**: Uses industry-standard libvirt commands
- **System Integration**: Integrates with existing libvirt infrastructure  
- **Network Management**: Automatic DHCP IP assignment and DNS resolution
- **Resource Control**: CPU, memory, and disk configuration via libvirt XML
- **Monitoring**: Built-in resource monitoring and logging
- **Snapshots**: Full snapshot and cloning capabilities (if needed)

#### VM Configuration
VMs are configured with libvirt XML templates:
- **Memory**: Configurable via `nixos_vm_memory_mb` (default: 4096MB)
- **CPUs**: Set by `nixos_vm_vcpus` (default: 4)  
- **Networking**: Connected to default libvirt network with DHCP
- **Storage**: QCOW2 disk images with virtio drivers
- **Boot**: Direct disk boot (no kernel/initrd specification needed)

### Access Methods

#### Primary Access (SSH)
```bash
# Using SSH config entry (auto-generated during bringup)
ssh kdevops

# Direct SSH to DHCP-assigned IP
ssh kdevops@192.168.122.169

# Via Ansible (uses SSH config automatically)
ansible kdevops -m ping
```

#### Alternative Access
- **Libvirt Console**: `virsh console kdevops` (direct VM console)
- **VNC Access**: Available via libvirt VNC configuration if enabled
- **Serial Console**: Configured through libvirt XML template

### VM Lifecycle Operations

#### Starting VMs
```bash
# Start all NixOS VMs (full automation)
make bringup

# Start specific VM manually
virsh start kdevops
```

#### Stopping VMs
```bash
# Graceful shutdown all VMs
make destroy

# Stop specific VM
/path/to/nixos/run-hostname-wrapper.sh stop
```

#### VM Health Checks
```bash
# Check all VM status
scripts/status_nixos.sh

# Check specific VM
/path/to/nixos/run-hostname-wrapper.sh status
```

## Configuration

### Key Configuration Files

- `kconfigs/Kconfig.nixos`: NixOS-specific options
- `nixos/flake.nix`: Nix flake for reproducible builds
- `nixos/generated/`: Generated NixOS configurations
- `playbooks/nixos.yml`: Ansible playbook for VM management

### Configuration Options

Key options in menuconfig:

- `NIXOS_VM_MEMORY_MB`: VM memory allocation (default: 4096)
- `NIXOS_VM_VCPUS`: Number of virtual CPUs (default: 4)
- `NIXOS_VM_DISK_SIZE_GB`: Disk size (default: 20)
- `NIXOS_SSH_PORT`: Base SSH port (default: 10022)
- `NIXOS_USE_FLAKES`: Enable Nix flakes (default: yes)

## Troubleshooting

### Common Issues

#### SSH Connection Refused
- Ensure VM is running: `./run-kdevops-wrapper.sh status`
- Check SSH port: `netstat -tlnp | grep 10022`
- Verify SSH key: `ls ~/.ssh/kdevops-nixos-*`

#### Python/Bash Not Found
- The templates automatically handle NixOS paths
- If issues persist, check `ansible_python_interpreter` in hosts file
- Should be set to `/run/current-system/sw/bin/python3`

#### VM Won't Start
- Check disk space: NixOS images require ~20GB
- Verify QEMU installation: `which qemu-system-x86_64`
- Check for port conflicts on 10022, 55555, and 5900

### Debug Mode

Enable debug output for troubleshooting:

```bash
make menuconfig
# Navigate to: Bring up methods -> NixOS options
# Enable: Enable debug mode for NixOS provisioning
```

## Technical Details

### File Structure

```
kdevops/
├── nixos/
│   ├── flake.nix                 # Nix flake configuration
│   ├── generated/                 # Generated NixOS configs
│   │   ├── configuration.nix      # Main NixOS configuration
│   │   ├── hardware-configuration.nix
│   │   ├── workflow-deps.nix      # Workflow dependencies
│   │   └── vms.nix               # VM definitions
│   └── result -> /nix/store/...  # Built VM image
├── playbooks/
│   ├── nixos.yml                 # Main NixOS playbook
│   └── templates/nixos/          # Jinja2 templates
└── scripts/
    ├── nixos.Makefile            # NixOS-specific make targets
    ├── nixos_ssh_key_name.py     # SSH key generation
    └── update_ssh_config_nixos.py # SSH config management
```

### Implementation Architecture

#### Core Design Decisions

1. **Native QEMU Over libvirt**
   - **Rationale**: Simpler setup, no daemon requirements
   - **Benefits**: Direct control over QEMU parameters, easier debugging
   - **Trade-off**: Less integration with existing libvirt tooling

2. **Directory-Based Instance Isolation**
   - **SSH Keys**: Unique per kdevops directory location
   - **Port Ranges**: Configurable base ports prevent conflicts
   - **VM Storage**: Separate directories for each instance
   - **Result**: Multiple kdevops instances can run simultaneously

3. **Declarative Configuration via Nix**
   - **Single Source of Truth**: `configuration.nix` defines entire VM state
   - **Reproducibility**: Nix flakes pin exact package versions
   - **Rollback Support**: Previous configurations can be restored
   - **Package Management**: Automatic dependency resolution for workflows

4. **Ansible Integration Strategy**
   - **Path Detection**: Templates automatically detect NixOS vs traditional Linux
   - **Python Interpreter**: Set correctly in generated inventory
   - **Shell Commands**: Use appropriate bash path based on OS
   - **Distribution Tasks**: Skip non-applicable tasks for NixOS

5. **Workflow Dependency Management**
   - **Template-Based**: `workflow-deps.nix.j2` generates package lists
   - **Automatic Inclusion**: Enabled workflows get required packages
   - **Extensible**: Easy to add support for new workflows
   - **Cached Builds**: Nix caches built packages for faster provisioning

## Integration with kdevops Workflows

### Workflow Compatibility

NixOS integrates seamlessly with existing kdevops workflows through:

1. **Automatic Package Resolution**: Each workflow's dependencies are automatically installed
2. **Path Translation**: Templates handle path differences transparently
3. **Ansible Compatibility**: Playbooks work across NixOS and traditional Linux
4. **Result Collection**: Standard kdevops result paths are maintained

### Adding Workflow Support

To enable a new workflow for NixOS:

1. **Identify Dependencies**
   ```bash
   # List packages needed for your workflow
   nix-env -qaP | grep package-name
   ```

2. **Update Template**
   Edit `playbooks/templates/nixos/workflow-deps.nix.j2`:
   ```nix
   {% if kdevops_workflow_enable_yourworkflow %}
   # Your workflow dependencies
   pkgs.package1
   pkgs.package2
   {% endif %}
   ```

3. **Test Integration**
   ```bash
   make defconfig-nixos-yourworkflow
   make bringup
   make yourworkflow
   ```

4. **Verify Results**
   - Check workflow execution completes
   - Validate results in standard locations
   - Ensure baseline/dev comparison works

### Workflow-Specific Considerations

#### fstests
- Kernel modules loaded via NixOS configuration
- Test devices created as loop devices
- Results in `workflows/fstests/results/`

#### blktests
- NVMe/SCSI modules configured in NixOS
- Block devices accessible via `/dev/`
- Expunge lists work identically

#### selftests
- Kernel source mounted via 9P if configured
- Build dependencies included automatically
- Parallel execution supported

#### mmtests
- A/B testing fully supported
- Performance monitoring tools included
- Comparison reports work as expected

## Contributing

To contribute NixOS support for additional workflows:

1. Identify required packages for your workflow
2. Update `workflow-deps.nix.j2` template
3. Test with a clean build
4. Submit PR with test results

### Testing Your Changes

```bash
# Clean build test
make mrproper
make defconfig-nixos-yourworkflow
make bringup
make yourworkflow

# Verify no missing dependencies
journalctl -u your-service  # Check for errors
which required-command       # Verify binaries present
```

## Limitations

- Currently supports x86_64 architecture only
- Requires Nix package manager on the host
- VMs run with user-mode networking (no bridged networking)
- Limited to QEMU/KVM virtualization

## Future Enhancements

Planned improvements:
- libvirt integration option
- Bridged networking support
- ARM64 architecture support
- Distributed build support with Nix
- Integration with Hydra CI system

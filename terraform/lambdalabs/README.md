# Lambda Labs Terraform Provider for kdevops

This directory contains the Terraform configuration for deploying kdevops infrastructure on Lambda Labs cloud GPU platform.

> **Architecture Note**: Lambda Labs serves as the reference implementation for kdevops' dynamic cloud configuration system. For details on how the dynamic Kconfig generation works, see [Dynamic Cloud Kconfig Documentation](../../docs/dynamic-cloud-kconfig.md).

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Dynamic Configuration](#dynamic-configuration)
- [SSH Key Security](#ssh-key-security)
- [Configuration Options](#configuration-options)
- [Provider Limitations](#provider-limitations)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)

## Prerequisites

1. **Lambda Labs Account**: Sign up at https://cloud.lambdalabs.com
2. **API Key**: Generate at https://cloud.lambdalabs.com/api-keys
3. **Terraform**: Version 1.0 or higher

### API Key Setup

Configure your Lambda Labs API key using the credentials file method:

**Credentials File Configuration (Required)**
```bash
# Using the helper script:
python3 scripts/lambdalabs_credentials.py set "your-api-key-here"

# Or manually:
mkdir -p ~/.lambdalabs
cat > ~/.lambdalabs/credentials << EOF
[default]
lambdalabs_api_key = your-api-key-here
EOF
chmod 600 ~/.lambdalabs/credentials
```

The system uses file-based authentication for consistency with other cloud providers.
Environment variables are NOT supported to avoid configuration complexity.

## Quick Start

```bash
# Step 1: Configure API credentials
python3 scripts/lambdalabs_credentials.py set "your-api-key"

# Step 2: Generate cloud configuration (queries available instances)
make cloud-config

# Step 3: Configure for Lambda Labs with smart defaults
make defconfig-lambdalabs

# Step 4: Deploy infrastructure (SSH keys handled automatically)
make bringup

# Step 5: When done, clean up everything
make destroy
```

## Dynamic Configuration

Lambda Labs support includes dynamic configuration generation that queries the Lambda Labs API to provide:

- **Real-time availability**: Only shows instance types with current capacity
- **Smart defaults**: Automatically selects cheapest available instances
- **Regional awareness**: Shows which regions have capacity for each instance type
- **Current pricing**: Displays up-to-date pricing information

### How It Works

1. **API Query**: When you run `make cloud-config` or `make menuconfig`, the system uses `lambda-cli` to query Lambda Labs API
2. **Kconfig Generation**: Available instances and regions are written to `.generated` files
3. **Menu Integration**: Generated files are included in the Kconfig menu system
4. **Smart Selection**: The system can automatically choose optimal configurations

### lambda-cli Tool

The `lambda-cli` tool is the central interface for Lambda Labs operations:

```bash
# List available instances
scripts/lambda-cli instance-types list --available-only

# Get pricing information
scripts/lambda-cli pricing list

# Smart selection (finds cheapest available)
scripts/lambda-cli smart-select --mode cheapest

# Generate Kconfig files
scripts/lambda-cli generate-kconfig
```

### Manual API Queries

You can manually query Lambda Labs availability:

```bash
# Check what's available right now
scripts/lambda-cli --output json instance-types list --available-only

# Check specific region
scripts/lambda-cli --output json instance-types list --region us-west-1

# Get current pricing
scripts/lambda-cli --output json pricing list
```

For more details on the dynamic configuration system, see [Dynamic Cloud Kconfig Documentation](../../docs/dynamic-cloud-kconfig.md).

## SSH Key Security

### Automatic Unique Keys (Default - Recommended)

Each kdevops project directory automatically gets its own unique SSH key:

- **Key Format**: `kdevops-<project>-<hash>` (e.g., `kdevops-lambda-kdevops-611374da`)
- **Automatic Creation**: Keys are created and uploaded on first `make bringup`
- **Automatic Cleanup**: Keys are removed when you run `make destroy`
- **No Manual Setup**: Everything is handled automatically

### Legacy Shared Key Mode

For backwards compatibility, you can use a shared key across projects:

```bash
# Use the shared key configuration
make defconfig-lambdalabs-shared-key

# Manually add your key to Lambda Labs console
# https://cloud.lambdalabs.com/ssh-keys
```

### SSH Key Management Commands

```bash
# List all SSH keys in your account
make lambdalabs-ssh-list

# Manually setup project SSH key
make lambdalabs-ssh-setup

# Remove project SSH key
make lambdalabs-ssh-clean

# Direct CLI usage
python3 scripts/lambdalabs_ssh_keys.py list
python3 scripts/lambdalabs_ssh_keys.py add <name> <keyfile>
python3 scripts/lambdalabs_ssh_keys.py delete <name_or_id>
```

## Configuration Options

### Smart Instance Selection

The default configuration automatically:
1. Detects your geographic location from your public IP
2. Queries Lambda Labs API for available instances
3. Finds the cheapest available GPU instance
4. Deploys to the closest region with that instance

### Available Defconfigs

| Config | Description | Use Case |
|--------|-------------|----------|
| `defconfig-lambdalabs` | Smart instance + unique SSH keys | Production (recommended) |
| `defconfig-lambdalabs-shared-key` | Smart instance + shared SSH key | Legacy/testing |

### Manual Configuration

```bash
# Configure specific options
make menuconfig

# Navigate to:
# → Bring up methods → Terraform → Lambda Labs
```

Configuration options:
- **Instance Type**: Choose specific GPU (or use smart selection)
- **Region**: Choose specific region (or use smart selection)
- **SSH Key Strategy**: Unique per-project or shared

## Provider Limitations

The Lambda Labs Terraform provider (elct9620/lambdalabs v0.3.0) has significant limitations:

| Feature | Supported | Notes |
|---------|-----------|-------|
| Instance Creation | ✅ Yes | Basic instance provisioning |
| GPU Selection | ✅ Yes | All Lambda Labs GPU types |
| Region Selection | ✅ Yes | With availability checking |
| SSH Key Reference | ✅ Yes | By name only |
| OS Image Selection | ❌ No | Always Ubuntu 22.04 |
| Custom User Creation | ❌ No | Always uses 'ubuntu' user |
| Storage Volumes | ❌ No | Cannot attach additional storage |
| User Data/Cloud-Init | ❌ No | No initialization scripts |
| Network Configuration | ❌ No | Basic networking only |
| SSH Key Creation | ❌ No | Must exist in console first |

## Troubleshooting

### SSH Authentication Failures

**Problem**: `Permission denied (publickey)` when connecting

**Solutions**:
1. Verify SSH key exists in Lambda Labs:
   ```bash
   make lambdalabs-ssh-list
   ```

2. Check key name matches configuration:
   ```bash
   grep TERRAFORM_LAMBDALABS_SSH_KEY_NAME .config
   ```

3. Ensure using correct private key:
   ```bash
   ssh -i ~/.ssh/kdevops_terraform ubuntu@<instance-ip>
   ```

### No Capacity Available

**Problem**: `No capacity available for instance type`

**Solutions**:
1. Smart inference automatically finds available regions
2. Regenerate configs to check current availability:
   ```bash
   make cloud-config
   cat terraform/lambdalabs/kconfigs/Kconfig.compute.generated | grep "✓"
   ```
3. Try different instance type or wait for capacity

### API Key Issues

**Problem**: `Invalid API key` or 403 errors

**Solutions**:
1. Verify credentials:
   ```bash
   cat ~/.lambdalabs/credentials
   ```

2. Test API access:
   ```bash
   python3 scripts/lambdalabs_list_instances.py
   ```

3. Generate new API key at https://cloud.lambdalabs.com/api-keys

### Instance Creation Fails

**Problem**: `Bad Request` when creating instances

**Solutions**:
1. Ensure SSH key exists with exact name
2. Verify instance type is available in region
3. Check terraform output:
   ```bash
   cd terraform/lambdalabs
   terraform plan
   ```

## API Reference

### Scripts

| Script | Purpose |
|--------|---------|
| `lambdalabs_api.py` | Main API integration, generates Kconfig |
| `lambdalabs_smart_inference.py` | Smart instance/region selection |
| `lambdalabs_ssh_keys.py` | SSH key management |
| `lambdalabs_list_instances.py` | List running instances |
| `lambdalabs_credentials.py` | Manage API credentials |
| `lambdalabs_ssh_key_name.py` | Generate unique key names |
| `generate_cloud_configs.py` | Update all cloud configurations |

### Make Targets

| Target | Description |
|--------|-------------|
| `cloud-config` | Generate/update cloud configurations |
| `defconfig-lambdalabs` | Configure with smart defaults |
| `bringup` | Deploy infrastructure |
| `destroy` | Destroy infrastructure and cleanup |
| `lambdalabs-ssh-list` | List SSH keys |
| `lambdalabs-ssh-setup` | Setup SSH key |
| `lambdalabs-ssh-clean` | Remove SSH key |

### Authentication Architecture

The Lambda Labs provider uses file-based authentication exclusively:

1. **Credentials File**: `~/.lambdalabs/credentials` contains the API key
2. **Extraction Script**: `extract_api_key.py` reads and validates the key
3. **Terraform Integration**: External data source provides the key to the provider
4. **No Environment Variables**: Consistent with AWS/GCE authentication patterns

## Files

```
terraform/lambdalabs/
├── README.md                   # This file
├── main.tf                     # Instance configuration
├── provider.tf                 # Provider setup
├── vars.tf                     # Variable definitions
├── output.tf                   # Output definitions
└── kconfigs/                   # Kconfig integration
    ├── Kconfig                 # Main configuration
    ├── Kconfig.compute         # Instance selection
    ├── Kconfig.identity        # SSH key configuration
    ├── Kconfig.location        # Region selection
    ├── Kconfig.storage         # Storage placeholder
    └── *.generated             # Dynamic configs from API
```

## Testing Your Setup

```bash
# 1. Test API connectivity
python3 scripts/lambdalabs_list_instances.py

# 2. Test smart inference
python3 scripts/lambdalabs_smart_inference.py

# 3. Validate terraform
cd terraform/lambdalabs
terraform init
terraform validate
terraform plan

# 4. Test SSH key management
make lambdalabs-ssh-list
```

## Support

- **kdevops Issues**: https://github.com/linux-kdevops/kdevops/issues
- **Lambda Labs Support**: support@lambdalabs.com
- **Lambda Labs Status**: https://status.lambdalabs.com

---

*Generated for kdevops v5.0.2 with Lambda Labs provider v0.3.0*

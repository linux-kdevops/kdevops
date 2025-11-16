# DataCrunch Terraform Provider for kdevops

This directory contains the Terraform configuration for deploying kdevops infrastructure on DataCrunch cloud GPU platform.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [API Key Setup](#api-key-setup)
- [Configuration](#configuration)
- [Provider Status](#provider-status)
- [Troubleshooting](#troubleshooting)

## Prerequisites

1. **DataCrunch Account**: Sign up at https://cloud.datacrunch.io/
2. **API Key (Client Secret)**: Generate at https://cloud.datacrunch.io/dashboard/api
3. **Terraform**: Version 1.0 or higher
4. **SSH Key**: Upload your public SSH key to DataCrunch

## Quick Start

### Step 1: Get Your API Key

1. Log in to https://cloud.datacrunch.io/
2. Navigate to Dashboard → API
3. Create a new API key (client secret)
4. Copy the client secret value

### Step 2: Configure API Credentials

```bash
# Run the interactive credential setup
python3 scripts/datacrunch_credentials.py set
```

You'll be prompted for:
- **client_id**: Your OAuth2 client ID (e.g., BypkQ5IUujDl1XlOMLtKT)
- **client_secret**: Your OAuth2 client secret (input is hidden)

Example session:
```
Setting up DataCrunch credentials (profile: default)

Get your credentials from: https://cloud.datacrunch.io/dashboard/api

Enter your client_id: BypkQ5IUujDl1XlOMLtKT
Enter your client_secret (hidden): ********
✓ Credentials saved to /home/user/.datacrunch/credentials (profile: default)

Test your credentials with:
  python3 scripts/datacrunch_credentials.py test
```

The credentials are stored in `~/.datacrunch/credentials` with restricted permissions (600).

```bash
# Verify credentials are configured
python3 scripts/datacrunch_credentials.py check

# Test API connectivity
python3 scripts/datacrunch_credentials.py test
```

### Step 3: SSH Key Setup (Automatic)

**Good news**: SSH keys are managed automatically! kdevops will:
1. Generate a unique SSH key for this project directory (if it doesn't exist)
2. Upload it to DataCrunch automatically during `make bringup`
3. Clean it up when you run `make destroy`

Each project directory gets its own unique key name like: `kdevops-datacrunch-6c707244`

**No manual SSH key setup required!**

If you want to manually verify or setup the key beforehand:
```bash
# Setup SSH key (optional - done automatically during bringup)
python3 scripts/datacrunch_ssh_keys.py setup

# List SSH keys in your DataCrunch account
python3 scripts/datacrunch_ssh_keys.py list
```

### Step 4: Generate Cloud Configuration

Query the DataCrunch API to get available H100 instances and PyTorch images:

```bash
# Generate dynamic Kconfig files with current availability and pricing
python3 scripts/generate_cloud_configs.py --provider datacrunch
```

This queries the API and generates menu options for:
- H100 GPU instance types with current pricing
- PyTorch-enabled OS images
- Available datacenter locations

### Step 5: Configure kdevops

```bash
# Use the H100 + PyTorch defconfig
make defconfig-datacrunch-h100-pytorch

# Or configure manually
make menuconfig
# Navigate to: Bring up methods → Terraform → DataCrunch
```

### Step 6: Deploy Infrastructure

⚠️ **IMPORTANT**: The Terraform provider (linux-kdevops/datacrunch v0.0.1) is in early development.
Before running `make bringup`, you need to test and complete the resource definitions in `main.tf`.

```bash
# When ready (after completing main.tf):
make bringup
```

## API Key Setup

### Credentials File Format

The credentials file (`~/.datacrunch/credentials`) uses INI format:

```ini
[default]
client_id = BypkQ5IUujDl1XlOMLtKT
client_secret = your-actual-client-secret-here
```

**IMPORTANT**: You need BOTH `client_id` and `client_secret` from DataCrunch. These are OAuth2 credentials, not just an API key.

### Multiple Profiles

You can have multiple credential sets for different accounts:

```ini
[default]
client_id = personal-client-id
client_secret = personal-client-secret

[work]
client_id = work-client-id
client_secret = work-client-secret
```

Set up a specific profile:
```bash
python3 scripts/datacrunch_credentials.py set work
```

Use a specific profile:
```bash
python3 scripts/datacrunch_credentials.py test work
```

### Environment Variable Alternative

You can also specify a custom credentials file location:
```bash
export DATACRUNCH_CREDENTIALS_FILE=/path/to/credentials
```

## Configuration

### Available Defconfigs

| Config | Description | Use Case |
|--------|-------------|----------|
| `defconfig-datacrunch-h100-pytorch` | H100 PCIe + PyTorch | Quick ML development (pay-as-you-go) |

### Manual Configuration Options

When running `make menuconfig`, you can configure:

#### Resource Location
- **Location**: Select datacenter (default: FIN-01 - Finland)

#### Compute
- **Instance Type**: H100 PCIe, H100 SXM, or other GPU types
- Pricing shown is pay-as-you-go hourly rate

#### OS Image
- **Image**: PyTorch pre-installed images (recommended for ML)
- Ubuntu base images
- Other available OS images

#### Identity & Access
- **SSH Key Name**: Name of your SSH key in DataCrunch (must match what you uploaded)
- **SSH Key File**: Path to your private key (default: `~/.ssh/kdevops_terraform`)

## Provider Status

### Current Implementation Status

**Working:**
- ✅ API integration and authentication (OAuth2)
- ✅ Dynamic configuration generation
- ✅ Kconfig menu integration
- ✅ Credentials management

**Incomplete:**
- ⚠️ Terraform resource definitions (needs provider testing)
- ⚠️ Instance provisioning workflow
- ⚠️ SSH configuration automation

### Terraform Provider Limitations

The DataCrunch Terraform provider (linux-kdevops/datacrunch v0.0.1) is in **early development**:

- **Version**: v0.0.1 (very early stage)
- **Source**: https://github.com/squat/terraform-provider-datacrunch
- **Status**: Minimal documentation, needs testing
- **Resources**: Unknown - need to test what's actually implemented

### Next Steps for Full Functionality

1. **Test the Provider**:
   ```bash
   cd terraform/datacrunch
   terraform init
   terraform providers
   ```

2. **Discover Available Resources**:
   - Check provider documentation
   - Test resource definitions
   - Verify API coverage

3. **Complete main.tf**: Add actual resource definitions for:
   - Instance creation
   - SSH key management
   - Network configuration (if supported)

4. **Alternative Approach**: If the provider is too immature, consider:
   - Using DataCrunch API directly (we have the library)
   - Building a custom null_resource wrapper
   - Contributing to the provider upstream

## Testing Your Setup

### Test API Access

```bash
# Test API library directly
python3 scripts/datacrunch_api.py
```

This will:
- Verify API credentials
- List available H100 instance types with pricing
- Show PyTorch images
- Display datacenter locations
- Show current instances in your account

### Test Kconfig Generation

```bash
# Generate configs and see what's available
python3 scripts/generate_cloud_configs.py --provider datacrunch

# Check generated files
cat terraform/datacrunch/kconfigs/Kconfig.compute.generated
cat terraform/datacrunch/kconfigs/Kconfig.images.generated
cat terraform/datacrunch/kconfigs/Kconfig.location.generated
```

### Test Terraform Provider

```bash
cd terraform/datacrunch

# Initialize Terraform
terraform init

# Check provider is installed
terraform providers

# Validate configuration
terraform validate

# See what would be created (once main.tf is complete)
terraform plan
```

## Troubleshooting

### API Credential Issues

**Problem**: `Invalid credentials` or `401 Unauthorized`

**Solutions**:
1. Verify both client_id AND client_secret are configured:
   ```bash
   python3 scripts/datacrunch_credentials.py check
   ```

2. Test credentials validity:
   ```bash
   python3 scripts/datacrunch_credentials.py test
   ```

3. Make sure you have BOTH values from DataCrunch:
   - Go to https://cloud.datacrunch.io/dashboard/api
   - You need the **client_id** (looks like: BypkQ5IUujDl1XlOMLtKT)
   - AND the **client_secret** (long string shown when you create the API key)

4. Re-run the setup if either is missing:
   ```bash
   python3 scripts/datacrunch_credentials.py set
   ```

### SSH Key Issues

**Problem**: SSH key not found during provisioning

**Solutions**:
1. If using automatic key management (default), the key should be created automatically.
   Check if it was uploaded:
   ```bash
   python3 scripts/datacrunch_ssh_keys.py list
   ```

2. Manually setup the key if automatic creation failed:
   ```bash
   python3 scripts/datacrunch_ssh_keys.py setup
   ```

3. Verify SSH key name matches configuration:
   ```bash
   grep TERRAFORM_DATACRUNCH_SSH_KEY_NAME .config
   python3 scripts/datacrunch_ssh_key_name.py  # Should match
   ```

4. If using manual mode, verify the key exists in DataCrunch:
   - Go to https://cloud.datacrunch.io/dashboard/ssh-keys
   - Confirm your key is listed with the exact name from your config

### Configuration Generation Fails

**Problem**: `Failed to generate Kconfig files - using defaults`

**Solutions**:
1. Check API credentials are set up
2. Verify internet connectivity
3. Check DataCrunch API status: https://status.datacrunch.io/
4. The system will use fallback defaults if API is unavailable

### Terraform Provider Not Found

**Problem**: `terraform init` fails with provider not found

**Solutions**:
1. The provider source is `linux-kdevops/datacrunch` - ensure provider.tf is correct
2. Check Terraform Registry: https://registry.terraform.io/providers/linux-kdevops/datacrunch
3. Provider may not be published to registry - may need to build from source

## API Reference

### DataCrunch API Endpoints

The integration uses these DataCrunch API v1 endpoints:

| Endpoint | Purpose |
|----------|---------|
| `/oauth2/token` | Get OAuth2 access token |
| `/instance-types` | List available GPU instance types with pricing |
| `/images` | List available OS images |
| `/locations` | List datacenter locations |
| `/instances` | List/create/manage instances |
| `/ssh-keys` | Manage SSH keys |

### Python Scripts

| Script | Purpose |
|--------|---------|
| `scripts/datacrunch_credentials.py` | Manage API credentials |
| `scripts/datacrunch_api.py` | Low-level API library |
| `scripts/datacrunch_ssh_keys.py` | Manage SSH keys via API |
| `scripts/datacrunch_ssh_key_name.py` | Generate unique key names |
| `scripts/generate_datacrunch_kconfig.py` | Generate dynamic Kconfig |
| `scripts/generate_cloud_configs.py` | Main cloud config generator |

### Make Targets (when complete)

| Target | Description |
|--------|-------------|
| `make defconfig-datacrunch-h100-pytorch` | Configure for H100 + PyTorch |
| `make bringup` | Deploy infrastructure |
| `make destroy` | Destroy infrastructure |

## Provider Comparison

### DataCrunch vs Lambda Labs

| Feature | DataCrunch API | Lambda Labs Provider | DataCrunch Provider Status |
|---------|----------------|---------------------|---------------------------|
| Instance Creation | ✅ Yes | ✅ Yes | ⚠️ Needs testing |
| SSH Key Management | ✅ Full CRUD | ⚠️ Reference only | ⚠️ Unknown |
| OS/Image Selection | ✅ Yes | ❌ No (Ubuntu 22.04 only) | ⚠️ Unknown |
| Storage Volumes | ✅ Yes | ❌ No | ⚠️ Unknown |
| User Data/Scripts | ✅ Yes | ❌ No | ⚠️ Unknown |
| GPU Selection | ✅ H100, A100, etc. | ✅ Yes | ⚠️ Unknown |
| Provider Maturity | N/A | v0.3.0 (stable) | v0.0.1 (early) |

### DataCrunch Advantages

- **Better API**: More complete than Lambda Labs
- **More features**: Volumes, OS selection, user data support
- **H100 GPUs**: Latest generation GPUs available
- **PyTorch images**: Pre-configured ML environments
- **Pay-as-you-go**: No commitments, cheap for testing

### Current Challenges

- **Immature provider**: v0.0.1, minimal documentation
- **Unknown resource coverage**: Need to test what works
- **No community**: Limited usage and support

## Support

- **kdevops Issues**: https://github.com/linux-kdevops/kdevops/issues
- **DataCrunch Support**: support@datacrunch.io
- **DataCrunch Status**: https://status.datacrunch.io/
- **DataCrunch Docs**: https://docs.datacrunch.io/
- **DataCrunch API Docs**: https://api.datacrunch.io/v1/docs

## Files Structure

```
terraform/datacrunch/
├── README.md                   # This file
├── provider.tf                 # Terraform provider configuration
├── vars.tf                     # Variable definitions
├── main.tf                     # Instance resources (incomplete)
├── output.tf                   # Output definitions
├── nodes.tf                    # Node configuration (generated)
├── extract_api_key.py          # API key extraction for Terraform
├── Kconfig                     # Main Kconfig integration
├── shared.tf -> ../shared.tf   # Symlink to shared config
├── ansible_provision_cmd.tpl -> ../ansible_provision_cmd.tpl
└── kconfigs/                   # Kconfig menu files
    ├── Kconfig.compute         # Instance type selection
    ├── Kconfig.images          # OS image selection
    ├── Kconfig.location        # Datacenter location
    ├── Kconfig.identity        # SSH key configuration
    ├── Kconfig.compute.generated    # Dynamic instance types
    ├── Kconfig.images.generated     # Dynamic images
    └── Kconfig.location.generated   # Dynamic locations
```

---

*DataCrunch integration for kdevops v5.0.2 - Provider testing required for full functionality*

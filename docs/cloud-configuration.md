# Cloud Configuration Management in kdevops

kdevops supports dynamic cloud provider configuration, allowing administrators to generate up-to-date instance types, locations, and AMI options directly from cloud provider APIs. Since generating these configurations can take several minutes (approximately 6 minutes for AWS), kdevops implements a two-tier system to optimize the user experience.

## Overview

The cloud configuration system dynamically generates configuration options by querying cloud provider APIs. This approach provides:

- **Always up-to-date options** from cloud provider APIs
- **Automatic discovery** of new instance types and regions
- **No manual maintenance** of configuration files
- **Fallback defaults** when cloud CLI tools are unavailable

## Prerequisites for Cloud Providers

Before configuring dynamic cloud options, ensure you have Terraform properly set up
for your chosen cloud provider. For general Terraform setup and cloud provider
configuration instructions, see the [Terraform Support documentation](kdevops-terraform.md).

### AWS Prerequisites

The AWS dynamic configuration system uses the official AWS CLI tool and requires proper authentication to access AWS APIs.

#### Requirements

1. **AWS CLI Installation**
   ```bash
   # Using pip
   pip install awscli

   # On Debian/Ubuntu
   sudo apt-get install awscli

   # On Fedora/RHEL
   sudo dnf install aws-cli

   # On macOS
   brew install awscli
   ```

2. **AWS Credentials Configuration**

   You need valid AWS credentials configured in one of these ways:

   a. **AWS credentials file** (`~/.aws/credentials`):
   ```ini
   [default]
   aws_access_key_id = YOUR_ACCESS_KEY
   aws_secret_access_key = YOUR_SECRET_KEY
   ```

   b. **Environment variables**:
   ```bash
   export AWS_ACCESS_KEY_ID=YOUR_ACCESS_KEY
   export AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
   export AWS_DEFAULT_REGION=us-east-1  # Optional
   ```

   c. **IAM Instance Role** (when running on EC2):
   - Automatically uses instance metadata service
   - No explicit credentials needed

3. **Required AWS Permissions**

   The IAM user or role needs the following read-only permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "ec2:DescribeRegions",
           "ec2:DescribeAvailabilityZones",
           "ec2:DescribeInstanceTypes",
           "ec2:DescribeImages",
           "pricing:GetProducts"
         ],
         "Resource": "*"
       },
       {
         "Effect": "Allow",
         "Action": [
           "sts:GetCallerIdentity"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

#### Verifying AWS Setup

Test your AWS CLI configuration:
```bash
# Check AWS CLI is installed
aws --version

# Verify credentials are configured
aws sts get-caller-identity

# Test EC2 access
aws ec2 describe-regions --output table
```

#### Fallback Behavior

If AWS CLI is not available or credentials are not configured:
- The system automatically uses fallback functions in `scripts/aws_api.py`:
  - `generate_default_instance_families_kconfig()` - provides M5, M7a, T3, C5, I4i families
  - `generate_default_regions_kconfig()` - provides common regions (us-east-1, eu-west-1, etc.)
  - `generate_default_gpu_amis_kconfig()` - provides standard GPU AMI options
- kdevops remains fully functional for AWS deployments without AWS CLI
- Users simply get a limited but functional set of hardcoded options instead of
  the full list from AWS APIs

### Lambda Labs Prerequisites

Lambda Labs configuration requires an API key:

1. **Obtain API Key**: Sign up at [Lambda Labs](https://lambdalabs.com) and generate an API key

2. **Configure API Key**:
   ```bash
   export LAMBDA_API_KEY=your_api_key_here
   ```

3. **Fallback Behavior**: Without an API key, default GPU instance types are provided

## Configuration Generation Flow

```
Cloud Provider API → Generated Files → Kconfig System
       ↑                    ↑
  make cloud-config   (automatic)
```

## Available Targets

### `make cloud-config`

Generates dynamic cloud configurations by querying cloud provider APIs.

**Purpose**: Fetches current instance types, regions, availability zones, and AMI options from cloud providers.

**Usage**:
```bash
make cloud-config
```

**What it does**:
- Queries AWS EC2 API for all available instance types and their specifications
- Fetches current regions and availability zones
- Discovers available AMIs including GPU-optimized images
- Generates Kconfig files with all discovered options
- Creates `.generated` files in provider-specific directories
- Sets a marker file (`.aws_cloud_config_generated`) to enable dynamic config

**Time required**: Approximately 6 minutes for AWS (similar for other providers)

**Generated files**:
- `terraform/aws/kconfigs/Kconfig.compute.generated`
- `terraform/aws/kconfigs/Kconfig.location.generated`
- `terraform/aws/kconfigs/Kconfig.gpu-amis.generated`
- `terraform/aws/kconfigs/instance-types/Kconfig.*.generated`
- Similar files for other cloud providers

### `make clean-cloud-config`

Removes all generated cloud configuration files.

**Usage**:
```bash
make clean-cloud-config
```

**What it does**:
- Removes all `.generated` files
- Removes cloud initialization marker files
- Forces regeneration on next `make cloud-config`

## Usage Workflow

### For All Users

The cloud configuration system automatically generates options when needed:

1. **Initial setup** (first time only):
   ```bash
   make cloud-config    # Generate cloud configurations (~6 minutes for AWS)
   ```

2. **Regular usage**:
   ```bash
   make menuconfig     # Cloud options are available
   make defconfig-aws-large
   make
   ```

### Fallback Behavior

If cloud CLI tools are not available or API access fails:
- Fallback functions in the API scripts provide hardcoded defaults:
  - AWS: `generate_default_*_kconfig()` functions in `scripts/aws_api.py`
  - Lambda Labs: Similar fallback functions for GPU instances
- Common instance types (M5, T3, etc.) and major regions remain available
- Full deployment functionality continues to work
- Users can still configure and deploy, just with a smaller set of options
- No error occurs - the system seamlessly falls back to these functions

## How It Works

### Implementation Architecture

The cloud configuration system consists of several key components:

1. **API Wrapper Scripts** (`scripts/aws-cli`, `scripts/lambda-cli`):
   - Provide CLI interfaces to cloud provider APIs
   - Handle authentication and error checking
   - Format API responses for Kconfig generation

2. **API Libraries** (`scripts/aws_api.py`, `scripts/lambdalabs_api.py`):
   - Core functions for API interactions
   - Generate Kconfig syntax from API data
   - Fallback functions (`generate_default_*_kconfig()`) provide hardcoded
     defaults when APIs unavailable

3. **Generation Orchestrator** (`scripts/generate_cloud_configs.py`):
   - Coordinates parallel generation across providers
   - Provides summary information
   - Handles errors gracefully

4. **Makefile Integration** (`scripts/dynamic-cloud-kconfig.Makefile`):
   - Defines make targets
   - Manages file dependencies
   - Handles cleanup and updates

### AWS Implementation Details

The AWS implementation wraps the official AWS CLI tool rather than implementing its own API client:

```python
# scripts/aws_api.py
def run_aws_command(command: List[str], region: str = None) -> Optional[Any]:
    cmd = ["aws"] + command + ["--output", "json"]
    # ... executes via subprocess
```

Key features:
- **Parallel Generation**: Uses ThreadPoolExecutor to generate instance family files concurrently
- **GPU Detection**: Automatically identifies GPU instances and enables GPU AMI options
- **Categorized Instance Types**: Groups instances by use case (general, compute, memory, etc.)
- **Pricing Integration**: Queries pricing API when available
- **Smart Defaults**: Falls back to hardcoded defaults when API unavailable, ensuring kdevops always works

### Dynamic Configuration System

kdevops uses dynamic configuration to provide up-to-date cloud options:

- **Generated files** (`.generated`) are created by `make cloud-config`
- Files are sourced directly by the Kconfig system
- If generation fails or APIs are unavailable, fallback defaults are provided automatically

The system is designed to be simple and automatic - run `make cloud-config` once
to generate configurations, then use them with `make menuconfig`.

### Instance Type Organization

Instance types are organized by family for better navigation:

```
terraform/aws/kconfigs/instance-types/
├── Kconfig.m5.static       # M5 family instances
├── Kconfig.m7a.static      # M7a family instances
├── Kconfig.g6e.static      # G6E GPU instances
└── ...                     # Other families
```

## Supported Cloud Providers

### AWS
- **Instance types**: All EC2 instance families and sizes
- **Regions**: All AWS regions and availability zones
- **AMIs**: Standard distributions and GPU-optimized Deep Learning AMIs
- **Time to generate**: ~6 minutes

### Azure
- **Instance types**: All Azure VM sizes
- **Regions**: All Azure regions
- **Images**: Standard and specialized images
- **Time to generate**: ~5-7 minutes

### Google Cloud (GCE)
- **Instance types**: All GCE machine types
- **Regions**: All GCE regions and zones
- **Images**: Public and custom images
- **Time to generate**: ~5-7 minutes

### Lambda Labs
- **Instance types**: GPU-optimized instances
- **Regions**: Available data centers
- **Images**: ML-optimized images
- **Time to generate**: ~1-2 minutes

## Benefits

### For Regular Users
- **Instant configuration** - No waiting for API queries
- **No cloud CLI required** - Works without AWS CLI, gcloud, or Azure CLI
- **Consistent experience** - Same options for all users
- **Offline capable** - Works without internet access

### For Administrators
- **Centralized updates** - Update once for all users
- **Version control** - Track configuration changes over time
- **Reduced API calls** - Query once, use many times
- **Flexibility** - Can still generate fresh configs when needed

## Best Practices

1. **Update regularly**: Cloud administrators should regenerate configurations monthly or when significant changes occur

2. **Document updates**: Include cloud CLI version and date in commit messages

3. **Test before committing**: Verify generated configurations work correctly:
   ```bash
   make cloud-config
   make menuconfig    # Test that options appear correctly
   ```

4. **Use defconfigs**: Create defconfigs for common cloud configurations:
   ```bash
   make savedefconfig
   cp defconfig defconfigs/aws-gpu-large
   ```

5. **Handle errors gracefully**: If cloud-config fails, static files still work

## Troubleshooting

### Configuration not appearing in menuconfig

Check if dynamic config is enabled:
```bash
ls -la .aws_cloud_config_generated
grep USE_DYNAMIC_CONFIG .config
```

### Generated files missing

Run `make cloud-config` to generate the configuration files.

### Old instance types appearing

Regenerate configurations:
```bash
make clean-cloud-config
make cloud-config
```

## Troubleshooting

### AWS Issues

#### "AWS CLI not found" Error
```bash
# Verify AWS CLI installation
which aws
aws --version

# Install if missing (see Prerequisites section)
```

#### "Credentials not configured" Error
```bash
# Check current identity
aws sts get-caller-identity

# If fails, configure credentials:
aws configure
# OR
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
```

#### "Access Denied" Errors
- Verify your IAM user/role has the required permissions (see Prerequisites)
- Check if you're in the correct AWS account
- Ensure your credentials haven't expired

#### Slow Generation Times
- Normal for AWS (6+ minutes due to API pagination)
- Generation only needed once, then configs are cached
- Run generation during off-peak hours

#### Missing Instance Types
```bash
# Force regeneration
make clean-cloud-config
make cloud-config
```

### General Issues

#### Generated Files Not Loading
```bash
# Verify generated files exist
ls terraform/aws/kconfigs/*.generated

# If missing, regenerate:
make cloud-config
```

#### Changes Not Reflected in Menuconfig
```bash
# Clear Kconfig cache
make mrproper
make menuconfig
```

#### Debugging API Calls
```bash
# Enable debug output
export DEBUG=1
make cloud-config

# Test API directly
scripts/aws-cli --output json regions list
scripts/aws-cli --output json instance-types list --family m5
```

## Best Practices

1. **Regular Updates**: Administrators should regenerate configurations monthly or when new instance types are announced

2. **Commit Messages**: Include generation date and tool versions when committing static files:
   ```bash
   git commit -m "cloud: update AWS static configurations

   Generated with AWS CLI 2.15.0 on 2024-01-15
   - Added new G6e instance family
   - Updated GPU AMI options
   - 127 instance families now available"
   ```

3. **Testing**: Always test generated configurations before committing:
   ```bash
   make cloud-config

   make menuconfig  # Verify options appear correctly
   ```

4. **Partial Generation**: For faster testing, generate only specific providers:
   ```bash
   make cloud-config-aws      # AWS only
   make cloud-config-lambdalabs  # Lambda Labs only
   ```

5. **CI/CD Integration**: Consider automating configuration updates in CI pipelines

## Advanced Usage

### Custom AWS Profiles
```bash
# Use non-default AWS profile
export AWS_PROFILE=myprofile
make cloud-config
```

### Specific Region Generation
```bash
# Generate for specific region (affects default selections)
export AWS_DEFAULT_REGION=eu-west-1
make cloud-config
```

### Parallel Generation
The system automatically uses parallel processing:
- AWS: Up to 10 concurrent instance family generations
- Reduces total generation time significantly

## File Reference

### AWS Files
- `terraform/aws/kconfigs/Kconfig.compute.{generated,static}` - Instance families
- `terraform/aws/kconfigs/Kconfig.location.{generated,static}` - Regions and zones
- `terraform/aws/kconfigs/Kconfig.gpu-amis.{generated,static}` - GPU AMI options
- `terraform/aws/kconfigs/instance-types/Kconfig.*.{generated,static}` - Per-family sizes

### Marker Files
- `.aws_cloud_config_generated` - Enables dynamic AWS config
- `.cloud.initialized` - General cloud config marker

### Scripts
- `scripts/aws-cli` - AWS CLI wrapper with user-friendly commands
- `scripts/aws_api.py` - AWS API library and Kconfig generation
- `scripts/generate_cloud_configs.py` - Main orchestrator for all providers
- `scripts/dynamic-cloud-kconfig.Makefile` - Make targets and integration

## Implementation Details

The cloud configuration system is implemented using:

- **AWS CLI Wrapper**: Uses official AWS CLI via subprocess calls
- **Parallel Processing**: ThreadPoolExecutor for concurrent API calls
- **Fallback Defaults**: Pre-defined configurations when API unavailable
- **Two-tier System**: Generated (dynamic) → Static (committed) files
- **Kconfig Integration**: Seamless integration with Linux kernel-style configuration

### Key Design Decisions

1. **Why wrap AWS CLI instead of using boto3?**
   - Reduces dependencies (AWS CLI often already installed)
   - Leverages AWS's official tool and authentication methods
   - Simpler credential management (uses standard AWS config)

2. **Why the two-tier system?**
   - Fast loading for regular users (no API calls needed)
   - Fresh data when administrators regenerate
   - Works offline and in restricted environments

3. **Why 6 minutes generation time?**
   - AWS API pagination limits (100 items per request)
   - Comprehensive data collection (all regions, all instance types)
   - Parallel processing already optimized

## See Also

- [AWS Instance Types](https://aws.amazon.com/ec2/instance-types/)
- [Azure VM Sizes](https://docs.microsoft.com/en-us/azure/virtual-machines/sizes)
- [GCE Machine Types](https://cloud.google.com/compute/docs/machine-types)
- [kdevops Terraform Documentation](terraform.md)
- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/)

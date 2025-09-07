# Cloud Configuration Management in kdevops

kdevops supports dynamic cloud provider configuration, allowing administrators to generate up-to-date instance types, locations, and AMI options directly from cloud provider APIs. Since generating these configurations can take several minutes (approximately 6 minutes for AWS), kdevops implements a two-tier system to optimize the user experience.

## Overview

The cloud configuration system follows a pattern similar to Linux kernel refs management (`make refs-default`), where administrators generate fresh configurations that are then committed to the repository as static files for regular users. This approach provides:

- **Fast configuration loading** for regular users (using pre-generated static files)
- **Fresh, up-to-date options** when administrators regenerate configurations
- **No dependency on cloud CLI tools** for regular users
- **Reduced API calls** to cloud providers

## Prerequisites for Cloud Providers

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
- The system automatically falls back to pre-defined static defaults
- Basic instance families (M5, T3, C5, etc.) are still available
- Common regions (us-east-1, eu-west-1, etc.) are provided
- Default GPU AMI options are included
- Users can still use kdevops without AWS API access

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
Cloud Provider API → Generated Files → Static Files → Git Repository
       ↑                    ↑              ↑
  make cloud-config   (automatic)    make cloud-update
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

### `make cloud-update`

Converts dynamically generated configurations to static files for committing to git.

**Purpose**: Creates static copies of generated configurations that load instantly without requiring cloud API access.

**Usage**:
```bash
make cloud-update
```

**What it does**:
- Copies all `.generated` files to `.static` equivalents
- Updates internal references from `.generated` to `.static`
- Prepares files for git commit
- Allows regular users to benefit from pre-generated configurations

**Static files created**:
- All `.generated` files get `.static` counterparts
- References within files are updated to use `.static` versions

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

### For Cloud Administrators/Maintainers

Cloud administrators are responsible for keeping the static configurations up-to-date:

1. **Generate fresh configurations**:
   ```bash
   make cloud-config    # Wait ~6 minutes for API queries
   ```

2. **Convert to static files**:
   ```bash
   make cloud-update    # Instant - just copies files
   ```

3. **Commit the static files**:
   ```bash
   git add terraform/*/kconfigs/*.static
   git add terraform/*/kconfigs/instance-types/*.static
   git commit -m "cloud: update static configurations for AWS/Azure/GCE

   Update instance types, regions, and AMI options to current offerings.

   Generated with AWS CLI version X.Y.Z on YYYY-MM-DD."
   git push
   ```

### For Regular Users

Regular users benefit from pre-generated static configurations:

1. **Clone or pull the repository**:
   ```bash
   git clone https://github.com/linux-kdevops/kdevops
   cd kdevops
   ```

2. **Use cloud configurations immediately**:
   ```bash
   make menuconfig     # Cloud options load instantly from static files
   make defconfig-aws-large
   make
   ```

No cloud CLI tools or API access required - everything loads from committed static files.

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
   - Provide fallback defaults when APIs unavailable

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
- **Smart Defaults**: Falls back to well-tested defaults when API unavailable

### Dynamic Configuration Detection

kdevops automatically detects whether to use dynamic or static configurations:

```kconfig
config TERRAFORM_AWS_USE_DYNAMIC_CONFIG
    bool "Use dynamically generated instance types"
    default $(shell, test -f .aws_cloud_config_generated && echo y || echo n)
```

- If `.aws_cloud_config_generated` exists, dynamic configs are used
- Otherwise, static configs are used (default for most users)

### File Precedence

The Kconfig system sources files in this order:

1. **Static files** (`.static`) - Pre-generated by administrators
2. **Generated files** (`.generated`) - Created by `make cloud-config`

Static files take precedence and are preferred for faster loading.

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
   make cloud-update
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

### Generated files have wrong references

Run `make cloud-update` to fix references from `.generated` to `.static`.

### Old instance types appearing

Regenerate configurations:
```bash
make clean-cloud-config
make cloud-config
make cloud-update
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
- Consider using `make cloud-update` with pre-generated configs
- Run generation during off-peak hours

#### Missing Instance Types
```bash
# Force regeneration
make clean-cloud-config
make cloud-config
make cloud-update
```

### General Issues

#### Static Files Not Loading
```bash
# Verify static files exist
ls terraform/aws/kconfigs/*.static

# If missing, regenerate:
make cloud-config
make cloud-update
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
   make cloud-update
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

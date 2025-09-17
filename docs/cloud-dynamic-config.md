# Dynamic Cloud Configuration

kdevops supports dynamic configuration generation for cloud providers, automatically
querying cloud APIs to provide up-to-date instance types, regions, and pricing
information.

## Overview

Dynamic cloud configuration ensures your kdevops setup always has access to the
latest cloud provider offerings without manual updates. This system:

- Queries cloud provider APIs for current instance types and regions
- Generates Kconfig files with accurate specifications
- Caches data for performance (24-hour TTL)
- Supports parallel processing for fast generation
- Integrates with standard kdevops workflows

## Supported Cloud Providers

### AWS (Amazon Web Services)

AWS dynamic configuration provides:
- 146+ instance families (vs 6 in static configs)
- 900+ instance types with current specs
- 30+ regions with availability zones
- GPU instance support (P5, G5, etc.)
- Cost tracking integration

### Lambda Labs

Lambda Labs dynamic configuration provides:
- GPU-focused instance types
- Real-time availability checking
- Automatic region discovery
- Pricing information

## Quick Start

### Generate Cloud Configurations

```bash
# Generate all cloud provider configurations
make cloud-config

# Generate specific provider configurations
make cloud-config-aws
make cloud-config-lambdalabs
```

### Update Cloud Data

To refresh cached data and get the latest information:

```bash
# Update all providers
make cloud-update

# Update specific provider
make cloud-update-aws
```

### Check Cloud Costs

Monitor your cloud spending:

```bash
# Show current month's costs
make cloud-bill

# AWS-specific billing
make cloud-bill-aws
```

## AWS Dynamic Configuration

### How It Works

1. **Data Collection**: Uses Chuck's AWS scripts to query EC2 APIs
   - `terraform/aws/scripts/ec2_instance_info.py`: Instance specifications
   - `terraform/aws/scripts/aws_regions_info.py`: Region information
   - `terraform/aws/scripts/aws_ami_info.py`: AMI details

2. **Caching**: JSON data cached in `~/.cache/kdevops/aws/`
   - 24-hour TTL for cached data
   - Automatic refresh on cache expiry
   - Manual refresh with `make cloud-update-aws`

3. **Generation**: Parallel processing creates Kconfig files
   - Main configs in `terraform/aws/kconfigs/*.generated`
   - Instance types in `terraform/aws/kconfigs/instance-types/*.generated`
   - ~21 seconds for fresh generation (vs 6 minutes unoptimized)
   - ~0.04 seconds when using cache

### Configuration Structure

```
terraform/aws/kconfigs/
├── Kconfig.compute.generated     # Instance family selection
├── Kconfig.location.generated    # AWS regions
├── Kconfig.gpu-amis.generated    # GPU AMI configurations
└── instance-types/
    ├── Kconfig.m5.generated      # M5 family sizes
    ├── Kconfig.p5.generated      # P5 GPU instances
    └── ... (146+ families)
```

### Using AWS GPU Instances

kdevops includes pre-configured defconfigs for GPU workloads:

```bash
# High-end: 8x NVIDIA H100 80GB GPUs
make defconfig-aws-gpu-p5-48xlarge

# Cost-effective: 1x NVIDIA A10G 24GB GPU
make defconfig-aws-gpu-g5-xlarge

# Then provision
make bringup
```

### Cost Management

Track AWS costs with integrated billing support:

```bash
# Check current month's spending
make cloud-bill-aws
```

Output shows:
- Total monthly cost to date
- Breakdown by AWS service
- Daily average spending
- Projected monthly cost (when mid-month)

## Lambda Labs Dynamic Configuration

Lambda Labs configuration focuses on GPU instances for ML/AI workloads:

```bash
# Generate Lambda Labs configs
make cloud-config-lambdalabs

# Use a Lambda Labs defconfig
make defconfig-lambdalabs-gpu-8x-h100
```

## Technical Details

### Performance Optimizations

The dynamic configuration system uses several optimizations:

1. **Parallel API Queries**: 10 concurrent workers fetch instance data
2. **Parallel File Writing**: 20 concurrent workers write Kconfig files
3. **JSON Caching**: 24-hour cache reduces API calls
4. **Batch Processing**: Fetches all data in single API call where possible

### Cache Management

Cache location: `~/.cache/kdevops/<provider>/`

Cache files:
- `aws_families.json`: Instance family list
- `aws_family_<name>.json`: Per-family instance data
- `aws_regions.json`: Region information
- `aws_all_instances.json`: Complete dataset

Clear cache manually:
```bash
rm -rf ~/.cache/kdevops/aws/
make cloud-update-aws
```

### Adding New Cloud Providers

To add support for a new cloud provider:

1. Create provider-specific scripts in `terraform/<provider>/scripts/`
2. Add Kconfig directory structure in `terraform/<provider>/kconfigs/`
3. Update `scripts/dynamic-cloud-kconfig.Makefile` with new targets
4. Implement generation in `scripts/generate_cloud_configs.py`

## Troubleshooting

### AWS Credentials Not Configured

If you see "AWS: Credentials not configured":

```bash
# Configure AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_DEFAULT_REGION=us-east-1
```

### Kconfig Errors

If menuconfig shows errors after generation:

1. Clear cache and regenerate:
   ```bash
   make cloud-update-aws
   ```

2. Check for syntax issues:
   ```bash
   grep -n "error:" terraform/aws/kconfigs/*.generated
   ```

### Slow Generation

If generation takes longer than 30 seconds:

1. Check network connectivity to AWS
2. Verify credentials are valid
3. Try different AWS region:
   ```bash
   export AWS_DEFAULT_REGION=eu-west-1
   make cloud-update-aws
   ```

## Development

### Running Scripts Directly

```bash
# Generate AWS configs with Chuck's scripts
python3 terraform/aws/scripts/generate_aws_kconfig.py

# Clear cache and regenerate
python3 terraform/aws/scripts/generate_aws_kconfig.py clear-cache

# Query specific instance family
python3 terraform/aws/scripts/ec2_instance_info.py m5 --format json

# List all families
python3 terraform/aws/scripts/ec2_instance_info.py --families --format json
```

### Debugging

Enable debug output:
```bash
# Debug AWS script
python3 terraform/aws/scripts/ec2_instance_info.py --debug m5

# Verbose Makefile execution
make V=1 cloud-config-aws
```

## Best Practices

1. **Regular Updates**: Run `make cloud-update` weekly for latest offerings
2. **Cost Monitoring**: Check `make cloud-bill` before major deployments
3. **Cache Management**: Let cache expire naturally unless testing changes
4. **Region Selection**: Choose regions close to you for lower latency
5. **Instance Right-Sizing**: Use dynamic configs to find optimal instance sizes

## Future Enhancements

Planned improvements:
- Azure dynamic configuration support
- GCE (Google Cloud) dynamic configuration
- Real-time pricing integration
- Spot instance availability checking
- Instance recommendation based on workload
- Cost optimization suggestions
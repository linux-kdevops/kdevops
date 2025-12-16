# DataCrunch GPU Cloud Provider Integration

kdevops provides comprehensive support for DataCrunch GPU cloud instances,
enabling automated provisioning of high-performance GPU infrastructure for
kernel development, machine learning research, and testing workflows.

## Overview

DataCrunch offers on-demand GPU instances with NVIDIA GPUs ranging from the
latest Blackwell B300 architecture down to cost-effective Tesla V100 GPUs.
The kdevops DataCrunch integration addresses the primary challenge of GPU
cloud providers: **inconsistent capacity availability**.

## The Capacity Availability Problem

GPU cloud providers face constant capacity challenges:

- **High-tier GPUs sell out quickly**: H100, A100, and Blackwell instances are
  in high demand and frequently unavailable
- **Regional variations**: Capacity varies significantly by datacenter location
- **Variant fragmentation**: Multiple variants of the same GPU (e.g., H100 with
  30V vs 32V CPUs) may have different availability
- **Dynamic capacity**: Availability changes minute-to-minute as users provision
  and terminate instances

### Traditional Approach (Frustrating)

Without intelligent selection, users face this workflow:

1. Try to provision H100 → **FAILED: No capacity**
2. Manually check which GPUs are available → Time consuming
3. Try to provision A100-80 → **FAILED: No capacity**
4. Repeat until something works → **Extremely frustrating**
5. Give up or settle for checking capacity manually via web dashboard

### kdevops Solution (Intelligent)

kdevops provides three automated selection strategies to maximize provisioning
success:

1. **Wildcard variant selection** (ANY_1H100)
2. **Tier-based fallback** (H100_OR_LESS, B300_OR_LESS)
3. **Explicit instance types** (for when you know exactly what you want)

## GPU Instance Selection Strategies

### Strategy 1: Wildcard Variant Selection

Use when you want a specific GPU tier but don't care about CPU/RAM variants.

**Example**: ANY_1H100

```bash
make defconfig-datacrunch-h100-pytorch
make bringup
```

**What it does**:
- Checks all H100 variants (1H100.80S.30V, 1H100.80S.32V)
- Provisions whichever variant has capacity
- Automatically updates terraform.tfvars with selected variant

**When to use**:
- You need H100 performance specifically
- You don't care about exact CPU/RAM configuration
- You want higher success rate than specifying exact variant

### Strategy 2: Tier-Based Fallback (Recommended)

Use when you want the best available GPU within budget constraints, with
automatic fallback to lower tiers when top options are unavailable.

**Example**: H100_OR_LESS

```bash
make defconfig-datacrunch-h100-pytorch-or-less
make bringup
```

**What it does**:
- Tries tiers in order: H100 → A100-80 → A100-40 → RTX PRO 6000 →
  RTX 6000 Ada → L40S → RTX A6000 → Tesla V100
- Provisions the highest-tier GPU that has available capacity
- Displays verbose selection process showing which tiers were checked

**When to use** (Recommended for most users):
- You want best available performance within H100 pricing tier
- You need high provisioning success rate
- You're doing development/testing where exact GPU doesn't matter
- You want to avoid manual capacity checking

**Available tier groups**:
- `B300_OR_LESS`: Best available GPU (any tier) - maximum performance
- `B200_OR_LESS`: Best available up to B200
- `H100_OR_LESS`: Best available up to H100 - **recommended default**
- `A100_80_OR_LESS`: Best available up to A100-80
- `A100_40_OR_LESS`: Best available up to A100-40

### Strategy 3: Explicit Instance Type

Use when you need a specific GPU and are willing to wait or handle failures.

**Example**: 1H100.80S.30V

```bash
# Via menuconfig
make menuconfig
# Navigate to: Terraform → DataCrunch → Compute
# Select: "1H100.80S.30V - $1.99/hr"

make bringup
```

**What it does**:
- Attempts to provision exactly the specified instance type
- Fails if that specific variant is unavailable
- No automatic fallback

**When to use**:
- Benchmarking specific GPU configurations
- Reproducing exact test environments
- You've verified capacity is available
- Production workloads requiring specific hardware

## GPU Tier Hierarchy

kdevops implements a 10-tier GPU hierarchy from highest to lowest performance:

| Tier | GPU | Instance Type | vCPUs | RAM | Performance | Cost |
|------|-----|---------------|-------|-----|-------------|------|
| 1 | B300 | 1B300.30V | 30 | TBD | Highest | $$$$$ |
| 2 | B200 | 1B200.30V | 30 | TBD | Excellent | $$$$ |
| 3 | H100 | 1H100.80S.30V / 32V | 30-32 | 120-185 GB | Excellent | $$$ |
| 4 | A100-80 | 1A100.80S.22V | 22 | 80 GB | Very Good | $$$ |
| 5 | A100-40 | 1A100.40S.22V | 22 | 80 GB | Very Good | $$ |
| 6 | RTX PRO 6000 | 1RTXPRO6000.30V | 30 | TBD | Good | $$ |
| 7 | RTX 6000 Ada | 1RTX6000ADA.10V | 10 | TBD | Good | $$ |
| 8 | L40S | 1L40S.20V | 20 | TBD | Good | $$ |
| 9 | A6000 | 1A6000.10V | 10 | TBD | Moderate | $ |
| 10 | V100 | 1V100.6V | 6 | 23 GB | Moderate | $ |

**Notes**:
- Pricing is relative (more $ = more expensive)
- H100 typically ~$1.99/hr, V100 is significantly cheaper
- Blackwell B200/B300 pricing TBD (newest generation)
- A100 and H100 provide best performance/cost for ML workloads

## Defconfig Files

Pre-built configurations for common use cases:

### Tier-Based Fallback (Recommended)

- **`defconfig-datacrunch-b300-or-less`**
  - Best available GPU (any tier)
  - Maximum performance with full fallback
  - Falls back through all 10 tiers down to V100

- **`defconfig-datacrunch-b200-or-less`**
  - Best available GPU up to B200 tier
  - Falls back through 9 tiers down to V100
  - Use when you want high-end performance with B200 cap

- **`defconfig-datacrunch-h100-pytorch-or-less`**
  - Best available GPU up to H100 tier
  - Falls back through 7 tiers down to V100
  - Recommended for most development and testing (~$1.99/hr cap)

- **`defconfig-datacrunch-a100-80-or-less`**
  - Best available GPU up to A100-80 tier
  - Falls back through 6 tiers down to V100
  - Budget-friendly option with good performance

- **`defconfig-datacrunch-a100-40-or-less`**
  - Best available GPU up to A100-40 tier
  - Falls back through 5 tiers down to V100
  - Cost-effective option for development and testing

### Specific GPU Tiers

- **`defconfig-datacrunch-h100-pytorch`**
  - Any H100 variant (30V or 32V)
  - No fallback to other GPU tiers
  - Use when you specifically need H100

- **`defconfig-datacrunch-a100`**
  - Single A100 40GB SXM GPU
  - Good performance at moderate cost

- **`defconfig-datacrunch-b300`**
  - Single Blackwell B300 GPU
  - Latest generation, highest performance
  - May have limited availability

- **`defconfig-datacrunch-v100`**
  - Tesla V100 GPU (cheapest option)
  - Good for testing and budget-constrained workloads
  - Usually high availability

## Usage Examples

### Example 1: Development with Automatic Fallback

Most developers should use tier-based fallback for maximum reliability:

```bash
cd ~/kdevops
make defconfig-datacrunch-h100-pytorch-or-less KDEVOPS_HOSTS_PREFIX=kn1 KNLP=1

# This configures:
# - Tier-based GPU selection (H100 or less)
# - KNLP ML research workflow
# - Host prefix "kn1" for instance naming

# Generate SSH keys and install dependencies
make

# Provision the infrastructure
make bringup AV=2
```

The `make` step is important - it generates SSH keys with a directory-based
checksum and installs Terraform dependencies. The `AV=2` flag enables verbose
Ansible output to see the tier selection process.

During bringup, you'll see output like:

```
Checking tier group: h100-or-less
Tiers to check (highest to lowest): h100, a100-80, a100-40, rtx-pro-6000, rtx-6000-ada, l40s, a6000, v100

Checking tier 'h100': 1H100.80S.30V, 1H100.80S.32V
  Checking 1H100.80S.30V... ✗ not available
  Checking 1H100.80S.32V... ✗ not available

Checking tier 'a100-80': 1A100.80S.22V
  Checking 1A100.80S.22V... ✗ not available

Checking tier 'a100-40': 1A100.40S.22V
  Checking 1A100.40S.22V... ✓ AVAILABLE

Selected: 1A100.40S.22V (tier: a100-40)
Auto-selected DataCrunch location: FIN-01
```

The system automatically:
1. Checked H100 variants (not available)
2. Checked A100-80 (not available)
3. Found A100-40 available
4. Selected optimal datacenter location
5. Proceeded with provisioning

### Example 2: Budget-Constrained Testing

Use tier-based fallback with A100-40 as maximum for cost-effective provisioning:

```bash
make defconfig-datacrunch-a100-40-or-less
make
make bringup
```

This caps at A100-40 pricing but automatically falls back to cheaper options
(RTX PRO 6000, RTX 6000 Ada, L40S, A6000, V100) when A100 GPUs are unavailable,
maximizing your chances of successful provisioning while controlling costs.

Alternatively, use explicit V100 for guaranteed lowest cost:

```bash
make defconfig-datacrunch-v100
make
make bringup
```

### Example 3: Maximum Performance

Try for the best available GPU:

```bash
make defconfig-datacrunch-b300-or-less
make
make bringup
```

This will try B300 → B200 → H100 → ... → V100 in order.

### Example 4: Specific GPU Requirement

When you absolutely need a specific GPU:

```bash
make menuconfig
# Navigate to: Terraform → DataCrunch → Compute
# Select the exact instance type you need

make
make bringup
```

**Warning**: This will fail if that specific instance type is unavailable.

## Manual Capacity Checking

You can check DataCrunch capacity before provisioning:

```bash
# Check specific instance type
scripts/datacrunch_check_capacity.py --instance-type 1H100.80S.30V

# Check with JSON output
scripts/datacrunch_check_capacity.py --instance-type 1A100.40S.22V --json

# Test tier-based selection
scripts/datacrunch_select_tier.py h100-or-less --verbose

# List all tier groups
scripts/datacrunch_select_tier.py --list-tiers
```

## Credentials Setup

Before using DataCrunch, configure your API credentials:

```bash
# Option 1: Use the credential management tool (recommended)
python3 scripts/datacrunch_credentials.py set 'your-api-key-here'

# Option 2: Manual setup
mkdir -p ~/.datacrunch
cat > ~/.datacrunch/credentials << EOF
[default]
datacrunch_api_key=your-api-key-here
EOF
chmod 600 ~/.datacrunch/credentials
```

Get your API key from: https://cloud.datacrunch.io

## Advanced Configuration

### Custom Instance Selection

You can create custom defconfig files with specific instance types:

```bash
# Start with base defconfig
make defconfig-datacrunch-h100-pytorch-or-less

# Customize via menuconfig
make menuconfig
# Navigate to: Terraform → DataCrunch → Compute
# Select your preferred instance selection strategy

# Save as custom defconfig
cp .config defconfigs/my-custom-datacrunch
```

### Terraform Provider Development

kdevops uses a local development build of the DataCrunch Terraform provider
with `dev_overrides` in `~/.terraformrc`. This allows using the latest provider
features before official release.

**Important implications**:
- `terraform init` with `force_init: true` will fail
- kdevops uses raw `terraform apply` and `terraform destroy` commands
- Lock file generation is handled specially during bringup
- Provider updates require rebuilding in `~/devel/terraform-provider-datacrunch`

### SSH Key Management

kdevops generates SSH keys with directory-based checksums to support multiple
installations:

```
~/.ssh/kdevops_terraform_<checksum>.pub
~/.ssh/kdevops_terraform_<checksum>
```

The checksum is the first 8 characters of the SHA256 hash of your kdevops
directory path. This allows multiple kdevops installations to coexist with
separate SSH keys.

### Using Multiple kdevops Directories

You can safely maintain multiple kdevops directories to run parallel DataCrunch
instances without interference by using different `KDEVOPS_HOSTS_PREFIX` values
for each directory.

**What gets isolated per directory**:
- Instance hostnames (e.g., `kn1-knlp` vs `kn2-knlp`)
- Terraform state files (`terraform.tfstate`)
- Ansible hosts files (`hosts`)
- Configuration files (`.config`)
- Volume cache files (`~/.cache/kdevops/datacrunch/<prefix>.yml`)

**What gets shared across directories**:
- API credentials (`~/.datacrunch/credentials`)
- SSH keys (but each directory gets its own based on path checksum)

**Example: Running two parallel KNLP instances**

First instance in `~/kdevops`:
```bash
cd ~/kdevops
make defconfig-datacrunch-h100-pytorch-or-less KDEVOPS_HOSTS_PREFIX=kn1 KNLP=1
make
make bringup
```

Second instance in `~/kdevops-experiment`:
```bash
cd ~/kdevops-experiment
make defconfig-datacrunch-h100-pytorch-or-less KDEVOPS_HOSTS_PREFIX=kn2 KNLP=1
make
make bringup
```

These two setups will:
- Create instances named `kn1-knlp` and `kn2-knlp` (no hostname conflicts)
- Use separate terraform state files (no state corruption)
- Use separate volume caches (`~/.cache/kdevops/datacrunch/kn1.yml` and `kn2.yml`)
- Share API credentials (no duplicate credential setup needed)
- Use different SSH keys (based on directory path checksums)

**Important**: Always use different `KDEVOPS_HOSTS_PREFIX` values when running
multiple kdevops directories. Using the same prefix across directories will
cause hostname conflicts and instance management issues.

**Use cases**:
- Testing different configurations simultaneously
- Running baseline vs development kernel comparisons
- Isolating production from experimental setups
- Managing different project workflows independently

## Troubleshooting

### No Capacity Available

**Problem**: All tiers show "not available"

**Solutions**:
1. Try a different tier group (e.g., switch from H100_OR_LESS to B300_OR_LESS)
2. Wait and retry (capacity changes frequently)
3. Use the cheapest tier: `make defconfig-datacrunch-v100`
4. Check DataCrunch dashboard for current availability

### Terraform Init Failures

**Problem**: `Failed to query available provider packages`

**Cause**: Using Ansible's terraform module with `force_init: true` conflicts
with dev_overrides

**Solution**: This is expected. kdevops handles DataCrunch specially:
- Initialization happens during external provider setup
- Uses raw `terraform apply/destroy` instead of Ansible terraform module
- Lock files are managed specially

### Instance Provisioning Hangs

**Problem**: Instance stuck in "ordered" or "provisioning" status

**Cause**: DataCrunch backend provisioning delays

**Solution**:
1. Wait (can take 5-10 minutes for some instance types)
2. Check DataCrunch dashboard for instance status
3. If stuck >15 minutes, destroy and retry:
   ```bash
   make destroy
   make bringup
   ```

### Wrong Instance Type Selected

**Problem**: System selected lower tier than expected

**Explanation**: This is intentional behavior when higher tiers are unavailable.

**Solutions**:
1. Use explicit instance type if you require specific GPU
2. Check capacity manually: `scripts/datacrunch_check_capacity.py --instance-type 1H100.80S.30V`
3. Wait for capacity on higher tiers to become available

### Destroy Doesn't Remove Instances

**Problem**: `make destroy` completed but instances still show in dashboard

**Cause**: Terraform state file was cleaned up manually, losing instance tracking

**Solution**: Manually delete instances via DataCrunch dashboard

## Best Practices

### Development and Testing

**Recommended**: Use tier-based fallback for maximum reliability

```bash
make defconfig-datacrunch-h100-pytorch-or-less
```

**Why**: Development rarely requires specific GPU hardware. Tier-based fallback
maximizes provisioning success while staying within reasonable cost limits.

### Production Workloads

**Recommended**: Use explicit instance types

**Why**: Production workloads should use known, tested configurations.
Validate capacity before deployment.

### Cost Optimization

**For testing**: Use V100 tier explicitly

```bash
make defconfig-datacrunch-v100
```

**For development**: Use H100_OR_LESS which caps at ~$1.99/hr but falls back
to cheaper options when unavailable

### Capacity Planning

1. **Check availability patterns**: DataCrunch capacity varies by time of day
   and day of week
2. **Use tier-based fallback**: Reduces dependency on specific GPU availability
3. **Have fallback workflows**: Design workloads that can run on different GPU tiers
4. **Monitor costs**: Higher-tier GPUs cost significantly more per hour

## Integration Status

DataCrunch integration is **fully supported** with the following status:

✅ **Working**:
- Automated instance provisioning via Terraform
- Tier-based intelligent GPU selection
- Capacity checking and location auto-selection
- SSH key management with directory checksums
- Full workflow support (KNLP, fstests, selftests, etc.)
- Custom defconfig support
- API credential management

⚠️ **Known Limitations**:
- Requires local provider build with dev_overrides
- Cannot use Ansible terraform module's force_init
- Some instance types may have limited regional availability
- Blackwell B200/B300 pricing not yet published

🔧 **In Development**:
- Additional instance type variants as they become available
- Enhanced capacity prediction
- Multi-region failover

## Related Documentation

- [Terraform Integration](terraform.md)
- [Cloud Provider Support](cloud-providers.md)
- [Workflows Overview](workflows.md)
- [KNLP ML Research Workflow](../workflows/knlp/README.md)

## Getting Help

- Report issues: https://github.com/linux-kdevops/kdevops/issues
- DataCrunch support: https://cloud.datacrunch.io/support
- kdevops documentation: docs/

## Summary

The kdevops DataCrunch integration solves GPU capacity availability challenges
through intelligent tier-based selection and automatic fallback. The recommended
approach for most users is tier-based fallback (H100_OR_LESS), which provides:

- **High success rate**: Automatic fallback through 8 GPU tiers
- **Cost control**: Caps at H100 pricing (~$1.99/hr)
- **Simplicity**: One-command provisioning
- **Flexibility**: Falls back to V100 when nothing else available

For users who absolutely require specific GPU hardware, explicit instance type
selection is available, but expect higher failure rates due to capacity
constraints.

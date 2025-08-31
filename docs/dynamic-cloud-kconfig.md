# Dynamic Cloud Kconfig Generation

This document describes how kdevops implements dynamic configuration generation for cloud providers, using Lambda Labs as the reference implementation. This approach can be adapted for other cloud providers.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Lambda Labs Implementation](#lambda-labs-implementation)
4. [Creating a New Cloud Provider](#creating-a-new-cloud-provider)
5. [API Reference](#api-reference)

## Overview

Dynamic cloud Kconfig generation allows kdevops to query cloud provider APIs at configuration time to present users with:
- Currently available instance types
- Regions with capacity
- Real-time pricing information
- Smart selection of optimal configurations

This eliminates hardcoded lists that become outdated and helps users make informed decisions based on current availability.

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────┐
│                   User Interface                     │
│                  (make menuconfig)                   │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│                    Kconfig System                    │
│                                                      │
│  ┌──────────────────────────────────────────────┐   │
│  │ Static Kconfig Files                         │   │
│  │ - Kconfig.location                           │   │
│  │ - Kconfig.compute                            │   │
│  │ - Kconfig.smart                              │   │
│  └────────────┬─────────────────────────────────┘   │
│               │ sources                              │
│  ┌────────────▼─────────────────────────────────┐   │
│  │ Generated Kconfig Files                      │   │
│  │ - Kconfig.location.generated                 │   │
│  │ - Kconfig.compute.generated                  │   │
│  └────────────▲─────────────────────────────────┘   │
└───────────────┼─────────────────────────────────────┘
                │ generates
┌───────────────┼─────────────────────────────────────┐
│               │     Dynamic Generation Layer         │
│  ┌────────────┴─────────────────────────────────┐   │
│  │ Makefile Rules (dynamic-cloud-kconfig.mk)    │   │
│  └────────────┬─────────────────────────────────┘   │
│               │ calls                                │
│  ┌────────────▼─────────────────────────────────┐   │
│  │ CLI Tool (lambda-cli)                        │   │
│  └────────────┬─────────────────────────────────┘   │
└───────────────┼─────────────────────────────────────┘
                │ uses
┌───────────────▼─────────────────────────────────────┐
│                   API Library Layer                  │
│  ┌──────────────────────────────────────────────┐   │
│  │ lambdalabs_api.py                            │   │
│  │ - API communication                          │   │
│  │ - Data transformation                        │   │
│  │ - Kconfig generation                         │   │
│  └────────────┬─────────────────────────────────┘   │
└───────────────┼─────────────────────────────────────┘
                │ queries
┌───────────────▼─────────────────────────────────────┐
│              Cloud Provider API                      │
│            (Lambda Labs REST API)                    │
└─────────────────────────────────────────────────────┘
```

### Data Flow

1. **Configuration Time** (`make menuconfig`):
   - Makefile detects cloud provider selection
   - Triggers dynamic Kconfig generation
   - CLI tool queries cloud API
   - Generates `.generated` files
   - Kconfig includes generated files

2. **Runtime** (Terraform/Ansible):
   - Uses values from `extra_vars.yaml`
   - No API calls needed
   - Configuration already resolved

## Lambda Labs Implementation

### 1. CLI Tool (scripts/lambda-cli)

The `lambda-cli` tool provides a unified interface for all Lambda Labs operations:

```bash
# Generate Kconfig files
lambda-cli generate-kconfig

# Query available instances
lambda-cli --output json instance-types list

# Smart selection
lambda-cli --output json smart-select --mode cheapest
```

**Key Features:**
- Structured command interface (mimics AWS CLI)
- JSON and human-readable output formats
- Error handling with fallbacks
- Caching for performance

### 2. API Library (scripts/lambdalabs_api.py)

Core API functionality:

```python
def get_instance_types_with_capacity(api_key: str) -> Tuple[Dict, Dict[str, List[str]]]:
    """
    Get instance types and their regional availability.
    Returns: (instances_dict, capacity_map)
    """
    response = make_api_request("/instance-types", api_key)
    # Process and return structured data
```

### 3. Kconfig Integration

#### Static Kconfig (terraform/lambdalabs/kconfigs/Kconfig.location)

```kconfig
choice
    prompt "Lambda Labs region selection method"
    default TERRAFORM_LAMBDALABS_REGION_SMART_CHEAPEST

config TERRAFORM_LAMBDALABS_REGION_SMART_CHEAPEST
    bool "Smart selection - automatically select cheapest"
    help
      Uses lambda-cli to find the cheapest instance globally

config TERRAFORM_LAMBDALABS_REGION_MANUAL
    bool "Manual region selection"
    help
      Manually select from available regions

endchoice

# Include dynamically generated regions when manual selection
if TERRAFORM_LAMBDALABS_REGION_MANUAL
source "terraform/lambdalabs/kconfigs/Kconfig.location.generated"
endif

# Smart inference using lambda-cli
config TERRAFORM_LAMBDALABS_REGION
    string
    output yaml
    default $(shell, python3 scripts/lambdalabs_smart_inference.py region) if TERRAFORM_LAMBDALABS_REGION_SMART_CHEAPEST
```

#### Generated Kconfig (Kconfig.location.generated)

```kconfig
# Dynamically generated from Lambda Labs API
# Generated at: 2025-08-27 12:00:00

choice
    prompt "Lambda Labs region"
    default TERRAFORM_LAMBDALABS_REGION_US_WEST_1

config TERRAFORM_LAMBDALABS_REGION_US_WEST_1
    bool "us-west-1 - US West (California)"
    depends on TERRAFORM_LAMBDALABS_REGION_MANUAL

config TERRAFORM_LAMBDALABS_REGION_US_EAST_1
    bool "us-east-1 - US East (Virginia)"
    depends on TERRAFORM_LAMBDALABS_REGION_MANUAL

# ... more regions
endchoice
```

### 4. Makefile Integration

The `dynamic-cloud-kconfig.Makefile` handles generation:

```makefile
# Lambda Labs dynamic Kconfig generation
terraform/lambdalabs/kconfigs/Kconfig.compute.generated: .config
	@echo "Generating Lambda Labs compute Kconfig..."
	@python3 scripts/lambda-cli --output json generate-kconfig \
		--output-dir terraform/lambdalabs/kconfigs

terraform/lambdalabs/kconfigs/Kconfig.location.generated: .config
	@echo "Generating Lambda Labs location Kconfig..."
	@python3 scripts/lambda-cli --output json generate-kconfig \
		--output-dir terraform/lambdalabs/kconfigs

# Include generated files as dependencies
KCONFIG_DEPS += terraform/lambdalabs/kconfigs/Kconfig.compute.generated
KCONFIG_DEPS += terraform/lambdalabs/kconfigs/Kconfig.location.generated
```

### 5. Smart Inference

The system provides intelligent defaults through shell command execution in Kconfig:

```kconfig
config TERRAFORM_LAMBDALABS_INSTANCE_TYPE
    string
    output yaml
    default $(shell, python3 scripts/lambdalabs_smart_inference.py instance)
```

The `lambdalabs_smart_inference.py` wrapper calls lambda-cli:

```python
def get_smart_selection():
    """Get smart selection from lambda-cli"""
    result = subprocess.run(
        ['scripts/lambda-cli', '--output', 'json', 
         'smart-select', '--mode', 'cheapest'],
        capture_output=True
    )
    return json.loads(result.stdout)
```

## Creating a New Cloud Provider

To add dynamic Kconfig support for a new cloud provider, follow this pattern:

### Step 1: Create the CLI Tool

Create `scripts/provider-cli`:

```python
#!/usr/bin/env python3
"""CLI tool for Provider cloud management."""

import argparse
import json
from provider_api import get_instances, get_regions

class ProviderCLI:
    def list_instance_types(self):
        # Query API and return structured data
        pass
    
    def generate_kconfig(self, output_dir):
        # Generate Kconfig files
        pass

def main():
    parser = argparse.ArgumentParser()
    # Add commands and options
    # Handle commands
```

### Step 2: Create API Library

Create `scripts/provider_api.py`:

```python
def get_instance_types():
    """Get available instance types from provider."""
    # API communication
    # Data transformation
    return instances

def generate_instance_kconfig(instances):
    """Generate Kconfig choices for instances."""
    kconfig = "choice\n"
    kconfig += '    prompt "Instance type"\n'
    for instance in instances:
        kconfig += f"config PROVIDER_INSTANCE_{instance['id']}\n"
        kconfig += f'    bool "{instance["name"]}"\n'
    kconfig += "endchoice\n"
    return kconfig
```

### Step 3: Create Kconfig Structure

```
terraform/provider/kconfigs/
├── Kconfig.compute      # Static configuration
├── Kconfig.location     # Static configuration
└── Kconfig.smart        # Smart defaults
```

### Step 4: Add Makefile Rules

In `scripts/dynamic-cloud-kconfig.Makefile`:

```makefile
ifdef CONFIG_TERRAFORM_PROVIDER
terraform/provider/kconfigs/Kconfig.%.generated:
	@python3 scripts/provider-cli generate-kconfig
endif
```

### Step 5: Integration Points

1. **Credentials Management**: Create `provider_credentials.py`
2. **Smart Inference**: Create wrapper scripts for Kconfig shell commands
3. **Terraform Integration**: Add provider configuration
4. **Ansible Integration**: Add provisioning support

## API Reference

### lambda-cli Commands

#### generate-kconfig
Generate dynamic Kconfig files from API data.

```bash
lambda-cli generate-kconfig [--output-dir DIR]
```

**Output**: Creates `.generated` files with current API data

#### instance-types list
List available instance types.

```bash
lambda-cli --output json instance-types list [--available-only] [--region REGION]
```

**Output JSON Structure**:
```json
[
  {
    "name": "gpu_1x_a10",
    "price_per_hour": "$0.75",
    "specs": "1x NVIDIA A10 (24GB)",
    "available_regions": 3
  }
]
```

#### smart-select
Intelligently select instance and region.

```bash
lambda-cli --output json smart-select --mode cheapest
```

**Output JSON Structure**:
```json
{
  "instance_type": "gpu_1x_a10",
  "region": "us-west-1",
  "price_per_hour": "$0.75",
  "selection_mode": "cheapest_global"
}
```

### Key Design Principles

1. **Fallback Values**: Always provide sensible defaults when API is unavailable
2. **Caching**: Cache API responses to avoid rate limits
3. **Error Handling**: Graceful degradation when API fails
4. **Separation of Concerns**: 
   - CLI tool for interface
   - API library for communication
   - Kconfig for configuration
   - Makefile for orchestration

### Testing Dynamic Generation

```bash
# Test API access
scripts/lambda-cli --output json regions list

# Test Kconfig generation
make clean
make menuconfig  # Select Lambda Labs provider
# Check generated files
ls terraform/lambdalabs/kconfigs/*.generated

# Test smart inference
python3 scripts/lambdalabs_smart_inference.py instance
python3 scripts/lambdalabs_smart_inference.py region
```

## Best Practices

1. **API Key Management**
   - Store in `~/.provider/credentials`
   - Support environment variables
   - Never commit keys to repository

2. **Performance**
   - Generate files only when provider is selected
   - Cache API responses (15-minute TTL)
   - Minimize API calls during configuration

3. **User Experience**
   - Provide clear status messages
   - Show availability information
   - Offer smart defaults
   - Graceful fallbacks

4. **Maintainability**
   - Single CLI tool for all operations
   - Consistent command structure
   - Comprehensive error messages
   - Well-documented API

## Troubleshooting

### Generated files not appearing
```bash
# Check if provider is enabled
grep CONFIG_TERRAFORM_PROVIDER .config

# Manually trigger generation
make terraform/provider/kconfigs/Kconfig.compute.generated

# Check for API errors
scripts/provider-cli --output json instance-types list
```

### API authentication failures
```bash
# Check credentials
scripts/provider_credentials.py check

# Set credentials
scripts/provider_credentials.py set YOUR_API_KEY
```

### Stale data in menus
```bash
# Force regeneration
rm terraform/provider/kconfigs/*.generated
make menuconfig
```

## Future Enhancements

1. **Multi-Region Optimization**: Select instances across regions for best price/performance
2. **Spot Instance Support**: Include spot pricing in smart selection
3. **Resource Prediction**: Estimate resource needs based on workload
4. **Cost Tracking**: Integration with cloud billing APIs
5. **Availability Monitoring**: Real-time capacity updates

## Contributing

When adding a new cloud provider:
1. Follow the Lambda Labs pattern
2. Implement all required commands in CLI tool
3. Provide comprehensive fallbacks
4. Document API endpoints and data structures
5. Add integration tests
6. Update this documentation

## References

- [Lambda Labs Implementation](../terraform/lambdalabs/README.md)
- [Kconfig Documentation](https://www.kernel.org/doc/html/latest/kbuild/kconfig-language.html)
- [kdevops Cloud Providers](https://github.com/linux-kdevops/kdevops)

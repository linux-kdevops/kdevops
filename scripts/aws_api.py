#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
AWS API library for kdevops.

Provides AWS CLI wrapper functions for dynamic configuration generation.
Used by aws-cli and other kdevops components.
"""

import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Any


def check_aws_cli() -> bool:
    """Check if AWS CLI is installed and configured."""
    try:
        # Check if AWS CLI is installed
        result = subprocess.run(
            ["aws", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False

        # Check if credentials are configured
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_default_region() -> str:
    """Get the default AWS region from configuration or environment."""
    # Try to get from environment
    region = os.environ.get("AWS_DEFAULT_REGION")
    if region:
        return region

    # Try to get from AWS config
    try:
        result = subprocess.run(
            ["aws", "configure", "get", "region"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass

    # Default to us-east-1
    return "us-east-1"


def run_aws_command(command: List[str], region: Optional[str] = None) -> Optional[Dict]:
    """
    Run an AWS CLI command and return the JSON output.

    Args:
        command: AWS CLI command as a list
        region: Optional AWS region

    Returns:
        Parsed JSON output or None on error
    """
    cmd = ["aws"] + command + ["--output", "json"]

    # Always specify a region (use default if not provided)
    if not region:
        region = get_default_region()
    cmd.extend(["--region", region])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return json.loads(result.stdout) if result.stdout else {}
        else:
            print(f"AWS command failed: {result.stderr}", file=sys.stderr)
            return None
    except (subprocess.SubprocessError, json.JSONDecodeError) as e:
        print(f"Error running AWS command: {e}", file=sys.stderr)
        return None


def get_regions() -> List[Dict[str, Any]]:
    """Get available AWS regions."""
    response = run_aws_command(["ec2", "describe-regions"])
    if response and "Regions" in response:
        return response["Regions"]
    return []


def get_availability_zones(region: str) -> List[Dict[str, Any]]:
    """Get availability zones for a specific region."""
    response = run_aws_command(
        ["ec2", "describe-availability-zones"],
        region=region,
    )
    if response and "AvailabilityZones" in response:
        return response["AvailabilityZones"]
    return []


def get_instance_types(
    family: Optional[str] = None,
    region: Optional[str] = None,
    max_results: int = 100,
    fetch_all: bool = True,
) -> List[Dict[str, Any]]:
    """
    Get available instance types.

    Args:
        family: Instance family filter (e.g., 'm5', 't3')
        region: AWS region
        max_results: Maximum number of results per API call (max 100)
        fetch_all: If True, fetch all pages using NextToken pagination

    Returns:
        List of instance type information
    """
    all_instances = []
    next_token = None
    page_count = 0

    # Ensure max_results doesn't exceed AWS limit
    max_results = min(max_results, 100)

    while True:
        cmd = ["ec2", "describe-instance-types"]

        filters = []
        if family:
            # Filter by instance type pattern
            filters.append(f"Name=instance-type,Values={family}*")

        if filters:
            cmd.append("--filters")
            cmd.extend(filters)

        cmd.extend(["--max-results", str(max_results)])

        if next_token:
            cmd.extend(["--next-token", next_token])

        response = run_aws_command(cmd, region=region)
        if response and "InstanceTypes" in response:
            batch_size = len(response["InstanceTypes"])
            all_instances.extend(response["InstanceTypes"])
            page_count += 1

            if fetch_all and not family:
                # Only show progress for full fetches (not family-specific)
                print(
                    f"  Fetched page {page_count}: {batch_size} instance types (total: {len(all_instances)})",
                    file=sys.stderr,
                )

            # Check if there are more results
            if fetch_all and "NextToken" in response:
                next_token = response["NextToken"]
            else:
                break
        else:
            break

    if fetch_all and page_count > 1:
        filter_desc = f" for family '{family}'" if family else ""
        print(
            f"  Total: {len(all_instances)} instance types fetched{filter_desc}",
            file=sys.stderr,
        )

    return all_instances


def get_pricing_info(region: str = "us-east-1") -> Dict[str, Dict[str, float]]:
    """
    Get pricing information for instance types.

    Note: AWS Pricing API requires us-east-1 region.
    Returns a simplified pricing structure.

    Args:
        region: AWS region for pricing

    Returns:
        Dictionary mapping instance types to pricing info
    """
    # For simplicity, we'll use hardcoded common instance prices
    # In production, you'd query the AWS Pricing API
    pricing = {
        # T3 family (burstable)
        "t3.nano": {"on_demand": 0.0052},
        "t3.micro": {"on_demand": 0.0104},
        "t3.small": {"on_demand": 0.0208},
        "t3.medium": {"on_demand": 0.0416},
        "t3.large": {"on_demand": 0.0832},
        "t3.xlarge": {"on_demand": 0.1664},
        "t3.2xlarge": {"on_demand": 0.3328},
        # T3a family (AMD)
        "t3a.nano": {"on_demand": 0.0047},
        "t3a.micro": {"on_demand": 0.0094},
        "t3a.small": {"on_demand": 0.0188},
        "t3a.medium": {"on_demand": 0.0376},
        "t3a.large": {"on_demand": 0.0752},
        "t3a.xlarge": {"on_demand": 0.1504},
        "t3a.2xlarge": {"on_demand": 0.3008},
        # M5 family (general purpose Intel)
        "m5.large": {"on_demand": 0.096},
        "m5.xlarge": {"on_demand": 0.192},
        "m5.2xlarge": {"on_demand": 0.384},
        "m5.4xlarge": {"on_demand": 0.768},
        "m5.8xlarge": {"on_demand": 1.536},
        "m5.12xlarge": {"on_demand": 2.304},
        "m5.16xlarge": {"on_demand": 3.072},
        "m5.24xlarge": {"on_demand": 4.608},
        # M7a family (general purpose AMD)
        "m7a.medium": {"on_demand": 0.0464},
        "m7a.large": {"on_demand": 0.0928},
        "m7a.xlarge": {"on_demand": 0.1856},
        "m7a.2xlarge": {"on_demand": 0.3712},
        "m7a.4xlarge": {"on_demand": 0.7424},
        "m7a.8xlarge": {"on_demand": 1.4848},
        "m7a.12xlarge": {"on_demand": 2.2272},
        "m7a.16xlarge": {"on_demand": 2.9696},
        "m7a.24xlarge": {"on_demand": 4.4544},
        "m7a.32xlarge": {"on_demand": 5.9392},
        "m7a.48xlarge": {"on_demand": 8.9088},
        # C5 family (compute optimized)
        "c5.large": {"on_demand": 0.085},
        "c5.xlarge": {"on_demand": 0.17},
        "c5.2xlarge": {"on_demand": 0.34},
        "c5.4xlarge": {"on_demand": 0.68},
        "c5.9xlarge": {"on_demand": 1.53},
        "c5.12xlarge": {"on_demand": 2.04},
        "c5.18xlarge": {"on_demand": 3.06},
        "c5.24xlarge": {"on_demand": 4.08},
        # C7a family (compute optimized AMD)
        "c7a.medium": {"on_demand": 0.0387},
        "c7a.large": {"on_demand": 0.0774},
        "c7a.xlarge": {"on_demand": 0.1548},
        "c7a.2xlarge": {"on_demand": 0.3096},
        "c7a.4xlarge": {"on_demand": 0.6192},
        "c7a.8xlarge": {"on_demand": 1.2384},
        "c7a.12xlarge": {"on_demand": 1.8576},
        "c7a.16xlarge": {"on_demand": 2.4768},
        "c7a.24xlarge": {"on_demand": 3.7152},
        "c7a.32xlarge": {"on_demand": 4.9536},
        "c7a.48xlarge": {"on_demand": 7.4304},
        # I4i family (storage optimized)
        "i4i.large": {"on_demand": 0.117},
        "i4i.xlarge": {"on_demand": 0.234},
        "i4i.2xlarge": {"on_demand": 0.468},
        "i4i.4xlarge": {"on_demand": 0.936},
        "i4i.8xlarge": {"on_demand": 1.872},
        "i4i.16xlarge": {"on_demand": 3.744},
        "i4i.32xlarge": {"on_demand": 7.488},
    }

    # Adjust pricing based on region (simplified)
    # Some regions are more expensive than others
    region_multipliers = {
        "us-east-1": 1.0,
        "us-east-2": 1.0,
        "us-west-1": 1.08,
        "us-west-2": 1.0,
        "eu-west-1": 1.1,
        "eu-central-1": 1.15,
        "ap-southeast-1": 1.2,
        "ap-northeast-1": 1.25,
    }

    multiplier = region_multipliers.get(region, 1.1)
    if multiplier != 1.0:
        adjusted_pricing = {}
        for instance_type, prices in pricing.items():
            adjusted_pricing[instance_type] = {
                "on_demand": prices["on_demand"] * multiplier
            }
        return adjusted_pricing

    return pricing


def sanitize_kconfig_name(name: str) -> str:
    """Convert a name to a valid Kconfig symbol."""
    # Replace special characters with underscores
    name = name.replace("-", "_").replace(".", "_").replace(" ", "_")
    # Convert to uppercase
    name = name.upper()
    # Remove any non-alphanumeric characters (except underscore)
    name = "".join(c for c in name if c.isalnum() or c == "_")
    # Ensure it doesn't start with a number
    if name and name[0].isdigit():
        name = "_" + name
    return name


# Cache for instance families to avoid redundant API calls
_cached_families = None


def get_generated_instance_families() -> set:
    """Get the set of instance families that will have generated Kconfig files."""
    global _cached_families

    # Return cached result if available
    if _cached_families is not None:
        return _cached_families

    # Return all families - we'll generate Kconfig files for all of them
    # This function will be called by the aws-cli tool to determine which files to generate
    if not check_aws_cli():
        # Return a minimal set if AWS CLI is not available
        _cached_families = {"m5", "t3", "c5"}
        return _cached_families

    # Get all available instance types
    print("  Discovering available instance families...", file=sys.stderr)
    instance_types = get_instance_types(fetch_all=True)

    # Extract unique families
    families = set()
    for instance_type in instance_types:
        type_name = instance_type.get("InstanceType", "")
        # Extract family prefix (e.g., "m5" from "m5.large")
        if "." in type_name:
            family = type_name.split(".")[0]
            families.add(family)

    print(f"  Found {len(families)} instance families", file=sys.stderr)
    _cached_families = families
    return families


def generate_instance_families_kconfig() -> str:
    """Generate Kconfig content for AWS instance families."""
    # Check if AWS CLI is available
    if not check_aws_cli():
        return generate_default_instance_families_kconfig()

    # Get all available instance types (with pagination)
    instance_types = get_instance_types(fetch_all=True)

    # Extract unique families
    families = set()
    family_info = {}
    for instance in instance_types:
        instance_type = instance.get("InstanceType", "")
        if "." in instance_type:
            family = instance_type.split(".")[0]
            families.add(family)
            if family not in family_info:
                family_info[family] = {
                    "architectures": set(),
                    "count": 0,
                }
            family_info[family]["count"] += 1
            for arch in instance.get("ProcessorInfo", {}).get(
                "SupportedArchitectures", []
            ):
                family_info[family]["architectures"].add(arch)

    if not families:
        return generate_default_instance_families_kconfig()

    # Group families by category - use prefix patterns to catch all variants
    def categorize_family(family_name):
        """Categorize a family based on its prefix."""
        if family_name.startswith(("m", "t")):
            return "general_purpose"
        elif family_name.startswith("c"):
            return "compute_optimized"
        elif family_name.startswith(("r", "x", "z")):
            return "memory_optimized"
        elif family_name.startswith(("i", "d", "h")):
            return "storage_optimized"
        elif family_name.startswith(("p", "g", "dl", "trn", "inf", "vt", "f")):
            return "accelerated"
        elif family_name.startswith(("mac", "hpc")):
            return "specialized"
        else:
            return "other"

    # Organize families by category
    categorized_families = {
        "general_purpose": [],
        "compute_optimized": [],
        "memory_optimized": [],
        "storage_optimized": [],
        "accelerated": [],
        "specialized": [],
        "other": [],
    }

    for family in sorted(families):
        category = categorize_family(family)
        categorized_families[category].append(family)

    kconfig = """# AWS instance families (dynamically generated)
# Generated by aws-cli from live AWS data

choice
	prompt "AWS instance family"
	default TERRAFORM_AWS_INSTANCE_TYPE_M5
	help
	  Select the AWS instance family for your deployment.
	  Different families are optimized for different workloads.

"""

    # Category headers
    category_headers = {
        "general_purpose": "# General Purpose - balanced compute, memory, and networking\n",
        "compute_optimized": "# Compute Optimized - ideal for CPU-intensive applications\n",
        "memory_optimized": "# Memory Optimized - for memory-intensive applications\n",
        "storage_optimized": "# Storage Optimized - for high sequential read/write workloads\n",
        "accelerated": "# Accelerated Computing - GPU and other accelerators\n",
        "specialized": "# Specialized - for specific use cases\n",
        "other": "# Other instance families\n",
    }

    # Add each category of families
    for category in [
        "general_purpose",
        "compute_optimized",
        "memory_optimized",
        "storage_optimized",
        "accelerated",
        "specialized",
        "other",
    ]:
        if categorized_families[category]:
            kconfig += category_headers[category]
            for family in categorized_families[category]:
                kconfig += generate_family_config(family, family_info.get(family, {}))
            if category != "other":  # Don't add extra newline after the last category
                kconfig += "\n"

    kconfig += "\nendchoice\n"

    # Add instance type source includes for each family
    # Only include families that we actually generate files for
    generated_families = get_generated_instance_families()
    kconfig += "\n# Include instance-specific configurations\n"
    for family in sorted(families):
        # Only add source statement if we generate a file for this family
        if family in generated_families:
            safe_name = sanitize_kconfig_name(family)
            kconfig += f"""if TERRAFORM_AWS_INSTANCE_TYPE_{safe_name}
source "terraform/aws/kconfigs/instance-types/Kconfig.{family}.generated"
endif

"""

    # Add the TERRAFORM_AWS_INSTANCE_TYPE configuration that maps to the actual instance type
    kconfig += """# Final instance type configuration
config TERRAFORM_AWS_INSTANCE_TYPE
	string
	output yaml
"""

    # Add default for each family that maps to its size variable
    for family in sorted(families):
        safe_name = sanitize_kconfig_name(family)
        kconfig += f"\tdefault TERRAFORM_AWS_{safe_name}_SIZE if TERRAFORM_AWS_INSTANCE_TYPE_{safe_name}\n"

    # Add a final fallback default
    kconfig += '\tdefault "t3.micro"\n\n'

    return kconfig


def generate_family_config(family: str, info: Dict) -> str:
    """Generate Kconfig entry for an instance family."""
    safe_name = sanitize_kconfig_name(family)

    # Determine architecture dependencies
    architectures = info.get("architectures", set())
    depends_line = ""
    if architectures:
        if "x86_64" in architectures and "arm64" not in architectures:
            depends_line = "\n\tdepends on TARGET_ARCH_X86_64"
        elif "arm64" in architectures and "x86_64" not in architectures:
            depends_line = "\n\tdepends on TARGET_ARCH_ARM64"

    # Family descriptions
    descriptions = {
        "t3": "Burstable performance instances powered by Intel processors",
        "t3a": "Burstable performance instances powered by AMD processors",
        "m5": "General purpose instances powered by Intel Xeon Platinum processors",
        "m7a": "Latest generation general purpose instances powered by AMD EPYC processors",
        "c5": "Compute optimized instances powered by Intel Xeon Platinum processors",
        "c7a": "Latest generation compute optimized instances powered by AMD EPYC processors",
        "i4i": "Storage optimized instances with NVMe SSD storage",
        "is4gen": "Storage optimized ARM instances powered by AWS Graviton2",
        "im4gn": "Storage optimized ARM instances with NVMe storage",
        "r5": "Memory optimized instances powered by Intel Xeon Platinum processors",
        "p3": "GPU instances for machine learning and HPC",
        "g4dn": "GPU instances for graphics-intensive applications",
    }

    description = descriptions.get(family, f"AWS {family.upper()} instance family")
    count = info.get("count", 0)

    config = f"""config TERRAFORM_AWS_INSTANCE_TYPE_{safe_name}
\tbool "{family.upper()}"
{depends_line}
\thelp
\t  {description}
\t  Available instance types: {count}

"""
    return config


def generate_default_instance_families_kconfig() -> str:
    """Generate default Kconfig content when AWS CLI is not available."""
    return """# AWS instance families (default - AWS CLI not available)

choice
	prompt "AWS instance family"
	default TERRAFORM_AWS_INSTANCE_TYPE_M5
	help
	  Select the AWS instance family for your deployment.
	  Note: AWS CLI is not available, showing default options.

config TERRAFORM_AWS_INSTANCE_TYPE_M5
	bool "M5"
	depends on TARGET_ARCH_X86_64
	help
	  General purpose instances powered by Intel Xeon Platinum processors.

config TERRAFORM_AWS_INSTANCE_TYPE_M7A
	bool "M7a"
	depends on TARGET_ARCH_X86_64
	help
	  Latest generation general purpose instances powered by AMD EPYC processors.

config TERRAFORM_AWS_INSTANCE_TYPE_T3
	bool "T3"
	depends on TARGET_ARCH_X86_64
	help
	  Burstable performance instances powered by Intel processors.

config TERRAFORM_AWS_INSTANCE_TYPE_C5
	bool "C5"
	depends on TARGET_ARCH_X86_64
	help
	  Compute optimized instances powered by Intel Xeon Platinum processors.

config TERRAFORM_AWS_INSTANCE_TYPE_I4I
	bool "I4i"
	depends on TARGET_ARCH_X86_64
	help
	  Storage optimized instances with NVMe SSD storage.

endchoice

# Include instance-specific configurations
if TERRAFORM_AWS_INSTANCE_TYPE_M5
source "terraform/aws/kconfigs/instance-types/Kconfig.m5"
endif

if TERRAFORM_AWS_INSTANCE_TYPE_M7A
source "terraform/aws/kconfigs/instance-types/Kconfig.m7a"
endif

if TERRAFORM_AWS_INSTANCE_TYPE_T3
source "terraform/aws/kconfigs/instance-types/Kconfig.t3.generated"
endif

if TERRAFORM_AWS_INSTANCE_TYPE_C5
source "terraform/aws/kconfigs/instance-types/Kconfig.c5.generated"
endif

if TERRAFORM_AWS_INSTANCE_TYPE_I4I
source "terraform/aws/kconfigs/instance-types/Kconfig.i4i"
endif

# Final instance type configuration
config TERRAFORM_AWS_INSTANCE_TYPE
	string
	output yaml
	default TERRAFORM_AWS_M5_SIZE if TERRAFORM_AWS_INSTANCE_TYPE_M5
	default TERRAFORM_AWS_M7A_SIZE if TERRAFORM_AWS_INSTANCE_TYPE_M7A
	default TERRAFORM_AWS_T3_SIZE if TERRAFORM_AWS_INSTANCE_TYPE_T3
	default TERRAFORM_AWS_C5_SIZE if TERRAFORM_AWS_INSTANCE_TYPE_C5
	default TERRAFORM_AWS_I4I_SIZE if TERRAFORM_AWS_INSTANCE_TYPE_I4I
	default "t3.micro"

"""


def generate_instance_types_kconfig(family: str) -> str:
    """Generate Kconfig content for specific instance types within a family."""
    if not check_aws_cli():
        return ""

    instance_types = get_instance_types(family=family, fetch_all=True)
    if not instance_types:
        return ""

    # Filter to only exact family matches (e.g., c5a but not c5ad)
    filtered_instances = []
    for instance in instance_types:
        instance_type = instance.get("InstanceType", "")
        if "." in instance_type:
            inst_family = instance_type.split(".")[0]
            if inst_family == family:
                filtered_instances.append(instance)

    instance_types = filtered_instances
    if not instance_types:
        return ""

    pricing = get_pricing_info()

    # Sort by vCPU count and memory
    instance_types.sort(
        key=lambda x: (
            x.get("VCpuInfo", {}).get("DefaultVCpus", 0),
            x.get("MemoryInfo", {}).get("SizeInMiB", 0),
        )
    )

    safe_family = sanitize_kconfig_name(family)

    # Get the first instance type to use as default
    default_instance_name = f"{safe_family}_LARGE"  # Fallback
    if instance_types:
        first_instance_type = instance_types[0].get("InstanceType", "")
        if "." in first_instance_type:
            first_full_name = first_instance_type.replace(".", "_")
            default_instance_name = sanitize_kconfig_name(first_full_name)

    kconfig = f"""# AWS {family.upper()} instance sizes (dynamically generated)

choice
\tprompt "Instance size for {family.upper()} family"
\tdefault TERRAFORM_AWS_INSTANCE_{default_instance_name}
\thelp
\t  Select the specific instance size within the {family.upper()} family.

"""

    seen_configs = set()
    for instance in instance_types:
        instance_type = instance.get("InstanceType", "")
        if "." not in instance_type:
            continue

        # Get the full instance type name to make unique config names
        full_name = instance_type.replace(".", "_")
        safe_full_name = sanitize_kconfig_name(full_name)

        # Skip if we've already seen this config name
        if safe_full_name in seen_configs:
            continue
        seen_configs.add(safe_full_name)

        size = instance_type.split(".")[1]

        vcpus = instance.get("VCpuInfo", {}).get("DefaultVCpus", 0)
        memory_mib = instance.get("MemoryInfo", {}).get("SizeInMiB", 0)
        memory_gb = memory_mib / 1024

        # Get pricing
        price = pricing.get(instance_type, {}).get("on_demand", 0.0)
        price_str = f"${price:.3f}/hour" if price > 0 else "pricing varies"

        # Network performance
        network = instance.get("NetworkInfo", {}).get("NetworkPerformance", "varies")

        # Storage
        storage_info = ""
        if instance.get("InstanceStorageSupported"):
            storage = instance.get("InstanceStorageInfo", {})
            total_size = storage.get("TotalSizeInGB", 0)
            if total_size > 0:
                storage_info = f"\n\t  Instance storage: {total_size} GB"

        kconfig += f"""config TERRAFORM_AWS_INSTANCE_{safe_full_name}
\tbool "{instance_type}"
\thelp
\t  vCPUs: {vcpus}
\t  Memory: {memory_gb:.1f} GB
\t  Network: {network}
\t  Price: {price_str}{storage_info}

"""

    kconfig += "endchoice\n"

    # Add the actual instance type string config with full instance names
    kconfig += f"""
config TERRAFORM_AWS_{safe_family}_SIZE
\tstring
"""

    # Generate default mappings for each seen instance type
    for instance in instance_types:
        instance_type = instance.get("InstanceType", "")
        if "." not in instance_type:
            continue

        full_name = instance_type.replace(".", "_")
        safe_full_name = sanitize_kconfig_name(full_name)

        kconfig += (
            f'\tdefault "{instance_type}" if TERRAFORM_AWS_INSTANCE_{safe_full_name}\n'
        )

    # Use the first instance type as the final fallback default
    final_default = f"{family}.large"
    if instance_types:
        first_instance_type = instance_types[0].get("InstanceType", "")
        if first_instance_type:
            final_default = first_instance_type

    kconfig += f'\tdefault "{final_default}"\n\n'

    return kconfig


def generate_regions_kconfig() -> str:
    """Generate Kconfig content for AWS regions."""
    if not check_aws_cli():
        return generate_default_regions_kconfig()

    regions = get_regions()
    if not regions:
        return generate_default_regions_kconfig()

    kconfig = """# AWS regions (dynamically generated)

choice
	prompt "AWS region"
	default TERRAFORM_AWS_REGION_USEAST1
	help
	  Select the AWS region for your deployment.
	  Note: Not all instance types are available in all regions.

"""

    # Group regions by geographic area
    us_regions = []
    eu_regions = []
    ap_regions = []
    other_regions = []

    for region in regions:
        region_name = region.get("RegionName", "")
        if region_name.startswith("us-"):
            us_regions.append(region)
        elif region_name.startswith("eu-"):
            eu_regions.append(region)
        elif region_name.startswith("ap-"):
            ap_regions.append(region)
        else:
            other_regions.append(region)

    # Add US regions
    if us_regions:
        kconfig += "# US Regions\n"
        for region in sorted(us_regions, key=lambda x: x.get("RegionName", "")):
            kconfig += generate_region_config(region)
        kconfig += "\n"

    # Add EU regions
    if eu_regions:
        kconfig += "# Europe Regions\n"
        for region in sorted(eu_regions, key=lambda x: x.get("RegionName", "")):
            kconfig += generate_region_config(region)
        kconfig += "\n"

    # Add Asia Pacific regions
    if ap_regions:
        kconfig += "# Asia Pacific Regions\n"
        for region in sorted(ap_regions, key=lambda x: x.get("RegionName", "")):
            kconfig += generate_region_config(region)
        kconfig += "\n"

    # Add other regions
    if other_regions:
        kconfig += "# Other Regions\n"
        for region in sorted(other_regions, key=lambda x: x.get("RegionName", "")):
            kconfig += generate_region_config(region)

    kconfig += "\nendchoice\n"

    # Add the actual region string config
    kconfig += """
config TERRAFORM_AWS_REGION
	string
"""

    for region in regions:
        region_name = region.get("RegionName", "")
        safe_name = sanitize_kconfig_name(region_name)
        kconfig += f'\tdefault "{region_name}" if TERRAFORM_AWS_REGION_{safe_name}\n'

    kconfig += '\tdefault "us-east-1"\n'

    return kconfig


def generate_region_config(region: Dict) -> str:
    """Generate Kconfig entry for a region."""
    region_name = region.get("RegionName", "")
    safe_name = sanitize_kconfig_name(region_name)
    opt_in_status = region.get("OptInStatus", "")

    # Region display names
    display_names = {
        "us-east-1": "US East (N. Virginia)",
        "us-east-2": "US East (Ohio)",
        "us-west-1": "US West (N. California)",
        "us-west-2": "US West (Oregon)",
        "eu-west-1": "Europe (Ireland)",
        "eu-west-2": "Europe (London)",
        "eu-west-3": "Europe (Paris)",
        "eu-central-1": "Europe (Frankfurt)",
        "eu-north-1": "Europe (Stockholm)",
        "ap-southeast-1": "Asia Pacific (Singapore)",
        "ap-southeast-2": "Asia Pacific (Sydney)",
        "ap-northeast-1": "Asia Pacific (Tokyo)",
        "ap-northeast-2": "Asia Pacific (Seoul)",
        "ap-south-1": "Asia Pacific (Mumbai)",
        "ca-central-1": "Canada (Central)",
        "sa-east-1": "South America (São Paulo)",
    }

    display_name = display_names.get(region_name, region_name.replace("-", " ").title())

    help_text = f"\t  Region: {display_name}"
    if opt_in_status and opt_in_status != "opt-in-not-required":
        help_text += f"\n\t  Status: {opt_in_status}"

    config = f"""config TERRAFORM_AWS_REGION_{safe_name}
\tbool "{display_name}"
\thelp
{help_text}

"""
    return config


def get_gpu_amis(region: str = None) -> List[Dict[str, Any]]:
    """
    Get available GPU-optimized AMIs including Deep Learning AMIs.

    Args:
        region: AWS region

    Returns:
        List of AMI information
    """
    # Query for Deep Learning AMIs from AWS
    cmd = ["ec2", "describe-images"]
    filters = [
        "Name=owner-alias,Values=amazon",
        "Name=name,Values=Deep Learning AMI GPU*",
        "Name=state,Values=available",
        "Name=architecture,Values=x86_64",
    ]
    cmd.append("--filters")
    cmd.extend(filters)
    cmd.extend(["--query", "Images[?contains(Name, '2024') || contains(Name, '2025')]"])

    response = run_aws_command(cmd, region=region)

    if response:
        # Sort by creation date to get the most recent
        response.sort(key=lambda x: x.get("CreationDate", ""), reverse=True)
        return response[:10]  # Return top 10 most recent
    return []


def generate_gpu_amis_kconfig() -> str:
    """Generate Kconfig content for GPU AMIs."""
    # Check if AWS CLI is available
    if not check_aws_cli():
        return generate_default_gpu_amis_kconfig()

    # Get available GPU AMIs
    amis = get_gpu_amis()

    if not amis:
        return generate_default_gpu_amis_kconfig()

    kconfig = """# GPU-optimized AMIs (dynamically generated)

# GPU AMI Override - only shown for GPU instances
config TERRAFORM_AWS_USE_GPU_AMI
	bool "Use GPU-optimized AMI instead of standard distribution"
	depends on TERRAFORM_AWS_IS_GPU_INSTANCE
	output yaml
	default n
	help
	  Enable this to use a GPU-optimized AMI with pre-installed NVIDIA drivers,
	  CUDA, and ML frameworks instead of the standard distribution AMI.

	  When disabled, the standard distribution AMI will be used and you'll need
	  to install GPU drivers manually.

if TERRAFORM_AWS_USE_GPU_AMI

choice
	prompt "GPU-optimized AMI selection"
	default TERRAFORM_AWS_GPU_AMI_DEEP_LEARNING
	depends on TERRAFORM_AWS_IS_GPU_INSTANCE
	help
	  Select which GPU-optimized AMI to use for your GPU instance.

config TERRAFORM_AWS_GPU_AMI_DEEP_LEARNING
	bool "AWS Deep Learning AMI (Ubuntu 22.04)"
	help
	  AWS Deep Learning AMI with NVIDIA drivers, CUDA, cuDNN, and popular ML frameworks.
	  Optimized for machine learning workloads on GPU instances.
	  Includes: TensorFlow, PyTorch, MXNet, and Jupyter.

config TERRAFORM_AWS_GPU_AMI_DEEP_LEARNING_NVIDIA
	bool "NVIDIA Deep Learning AMI"
	help
	  NVIDIA optimized Deep Learning AMI with latest GPU drivers.
	  Includes NVIDIA GPU Cloud (NGC) containers and frameworks.

config TERRAFORM_AWS_GPU_AMI_CUSTOM
	bool "Custom GPU AMI"
	help
	  Specify a custom AMI ID for GPU instances.

endchoice

if TERRAFORM_AWS_GPU_AMI_DEEP_LEARNING

config TERRAFORM_AWS_GPU_AMI_NAME
	string
	output yaml
	default "Deep Learning OSS Nvidia Driver AMI GPU PyTorch*Ubuntu 22.04*"
	help
	  AMI name pattern for AWS Deep Learning AMI.

config TERRAFORM_AWS_GPU_AMI_OWNER
	string
	output yaml
	default "amazon"

endif # TERRAFORM_AWS_GPU_AMI_DEEP_LEARNING

if TERRAFORM_AWS_GPU_AMI_DEEP_LEARNING_NVIDIA

config TERRAFORM_AWS_GPU_AMI_NAME
	string
	output yaml
	default "NVIDIA Deep Learning AMI*"
	help
	  AMI name pattern for NVIDIA Deep Learning AMI.

config TERRAFORM_AWS_GPU_AMI_OWNER
	string
	output yaml
	default "amazon"

endif # TERRAFORM_AWS_GPU_AMI_DEEP_LEARNING_NVIDIA

if TERRAFORM_AWS_GPU_AMI_CUSTOM

config TERRAFORM_AWS_GPU_AMI_ID
	string "Custom GPU AMI ID"
	output yaml
	help
	  Specify the AMI ID for your custom GPU image.
	  Example: ami-0123456789abcdef0

endif # TERRAFORM_AWS_GPU_AMI_CUSTOM

endif # TERRAFORM_AWS_USE_GPU_AMI

# GPU instance detection
config TERRAFORM_AWS_IS_GPU_INSTANCE
	bool
	output yaml
	default y if TERRAFORM_AWS_INSTANCE_TYPE_G6E
	default y if TERRAFORM_AWS_INSTANCE_TYPE_G6
	default y if TERRAFORM_AWS_INSTANCE_TYPE_G5
	default y if TERRAFORM_AWS_INSTANCE_TYPE_G5G
	default y if TERRAFORM_AWS_INSTANCE_TYPE_G4DN
	default y if TERRAFORM_AWS_INSTANCE_TYPE_G4AD
	default y if TERRAFORM_AWS_INSTANCE_TYPE_P5
	default y if TERRAFORM_AWS_INSTANCE_TYPE_P5EN
	default y if TERRAFORM_AWS_INSTANCE_TYPE_P4D
	default y if TERRAFORM_AWS_INSTANCE_TYPE_P4DE
	default y if TERRAFORM_AWS_INSTANCE_TYPE_P3
	default y if TERRAFORM_AWS_INSTANCE_TYPE_P3DN
	default n
	help
	  Automatically detected based on selected instance type.
	  This indicates whether the selected instance has GPU support.

"""

    return kconfig


def generate_default_gpu_amis_kconfig() -> str:
    """Generate default GPU AMI Kconfig when AWS CLI is not available."""
    return """# GPU-optimized AMIs (default - AWS CLI not available)

# GPU AMI Override - only shown for GPU instances
config TERRAFORM_AWS_USE_GPU_AMI
	bool "Use GPU-optimized AMI instead of standard distribution"
	depends on TERRAFORM_AWS_IS_GPU_INSTANCE
	output yaml
	default n
	help
	  Enable this to use a GPU-optimized AMI with pre-installed NVIDIA drivers,
	  CUDA, and ML frameworks instead of the standard distribution AMI.
	  Note: AWS CLI is not available, showing default options.

if TERRAFORM_AWS_USE_GPU_AMI

choice
	prompt "GPU-optimized AMI selection"
	default TERRAFORM_AWS_GPU_AMI_DEEP_LEARNING
	depends on TERRAFORM_AWS_IS_GPU_INSTANCE
	help
	  Select which GPU-optimized AMI to use for your GPU instance.

config TERRAFORM_AWS_GPU_AMI_DEEP_LEARNING
	bool "AWS Deep Learning AMI (Ubuntu 22.04)"
	help
	  Pre-configured with NVIDIA drivers, CUDA, and ML frameworks.

config TERRAFORM_AWS_GPU_AMI_CUSTOM
	bool "Custom GPU AMI"

endchoice

if TERRAFORM_AWS_GPU_AMI_DEEP_LEARNING

config TERRAFORM_AWS_GPU_AMI_NAME
	string
	output yaml
	default "Deep Learning OSS Nvidia Driver AMI GPU PyTorch*Ubuntu 22.04*"

config TERRAFORM_AWS_GPU_AMI_OWNER
	string
	output yaml
	default "amazon"

endif # TERRAFORM_AWS_GPU_AMI_DEEP_LEARNING

if TERRAFORM_AWS_GPU_AMI_CUSTOM

config TERRAFORM_AWS_GPU_AMI_ID
	string "Custom GPU AMI ID"
	output yaml
	help
	  Specify the AMI ID for your custom GPU image.

endif # TERRAFORM_AWS_GPU_AMI_CUSTOM

endif # TERRAFORM_AWS_USE_GPU_AMI

# GPU instance detection (static)
config TERRAFORM_AWS_IS_GPU_INSTANCE
	bool
	output yaml
	default y if TERRAFORM_AWS_INSTANCE_TYPE_G6E
	default y if TERRAFORM_AWS_INSTANCE_TYPE_G6
	default y if TERRAFORM_AWS_INSTANCE_TYPE_G5
	default y if TERRAFORM_AWS_INSTANCE_TYPE_G5G
	default y if TERRAFORM_AWS_INSTANCE_TYPE_G4DN
	default y if TERRAFORM_AWS_INSTANCE_TYPE_G4AD
	default y if TERRAFORM_AWS_INSTANCE_TYPE_P5
	default y if TERRAFORM_AWS_INSTANCE_TYPE_P5EN
	default y if TERRAFORM_AWS_INSTANCE_TYPE_P4D
	default y if TERRAFORM_AWS_INSTANCE_TYPE_P4DE
	default y if TERRAFORM_AWS_INSTANCE_TYPE_P3
	default y if TERRAFORM_AWS_INSTANCE_TYPE_P3DN
	default n
	help
	  Automatically detected based on selected instance type.
	  This indicates whether the selected instance has GPU support.

"""


def generate_default_regions_kconfig() -> str:
    """Generate default Kconfig content when AWS CLI is not available."""
    return """# AWS regions (default - AWS CLI not available)

choice
	prompt "AWS region"
	default TERRAFORM_AWS_REGION_USEAST1
	help
	  Select the AWS region for your deployment.
	  Note: AWS CLI is not available, showing default options.

# US Regions
config TERRAFORM_AWS_REGION_USEAST1
	bool "US East (N. Virginia)"

config TERRAFORM_AWS_REGION_USEAST2
	bool "US East (Ohio)"

config TERRAFORM_AWS_REGION_USWEST1
	bool "US West (N. California)"

config TERRAFORM_AWS_REGION_USWEST2
	bool "US West (Oregon)"

# Europe Regions
config TERRAFORM_AWS_REGION_EUWEST1
	bool "Europe (Ireland)"

config TERRAFORM_AWS_REGION_EUCENTRAL1
	bool "Europe (Frankfurt)"

# Asia Pacific Regions
config TERRAFORM_AWS_REGION_APSOUTHEAST1
	bool "Asia Pacific (Singapore)"

config TERRAFORM_AWS_REGION_APNORTHEAST1
	bool "Asia Pacific (Tokyo)"

endchoice

config TERRAFORM_AWS_REGION
	string
	default "us-east-1" if TERRAFORM_AWS_REGION_USEAST1
	default "us-east-2" if TERRAFORM_AWS_REGION_USEAST2
	default "us-west-1" if TERRAFORM_AWS_REGION_USWEST1
	default "us-west-2" if TERRAFORM_AWS_REGION_USWEST2
	default "eu-west-1" if TERRAFORM_AWS_REGION_EUWEST1
	default "eu-central-1" if TERRAFORM_AWS_REGION_EUCENTRAL1
	default "ap-southeast-1" if TERRAFORM_AWS_REGION_APSOUTHEAST1
	default "ap-northeast-1" if TERRAFORM_AWS_REGION_APNORTHEAST1
	default "us-east-1"

"""

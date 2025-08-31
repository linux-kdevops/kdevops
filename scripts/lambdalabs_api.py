#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

"""
Lambda Labs API library for kdevops.

Provides low-level API access for Lambda Labs cloud services.
Used by lambda-cli and other kdevops components.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple

# Import our credentials module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lambdalabs_credentials import get_api_key as get_api_key_from_credentials

LAMBDALABS_API_BASE = "https://cloud.lambdalabs.com/api/v1"


def get_api_key() -> Optional[str]:
    """Get Lambda Labs API key from credentials file or environment variable."""
    return get_api_key_from_credentials()


def make_api_request(endpoint: str, api_key: str) -> Optional[Dict]:
    """Make a request to Lambda Labs API."""
    url = f"{LAMBDALABS_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "kdevops/1.0",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error making API request: {e}", file=sys.stderr)
        return None


def get_instance_types_with_capacity(api_key: str) -> Tuple[Dict, Dict[str, List[str]]]:
    """
    Get available instance types from Lambda Labs with capacity information.

    Returns:
        Tuple of (instance_types_data, capacity_map)
        where capacity_map is {instance_type: [list of regions with capacity]}
    """
    response = make_api_request("/instance-types", api_key)
    if not response or "data" not in response:
        return {}, {}

    instance_data = response["data"]
    capacity_map = {}

    # Build capacity map
    for instance_type, info in instance_data.items():
        regions_with_capacity = info.get("regions_with_capacity_available", [])
        if regions_with_capacity:
            capacity_map[instance_type] = [r["name"] for r in regions_with_capacity]
        else:
            capacity_map[instance_type] = []

    return instance_data, capacity_map


def get_regions(api_key: str) -> List[Dict]:
    """Get available regions from Lambda Labs by extracting from instance data."""
    # Lambda Labs doesn't have a dedicated regions endpoint
    # Extract regions from instance-types data
    response = make_api_request("/instance-types", api_key)
    if response and "data" in response:
        regions_set = set()
        region_descriptions = {
            "us-tx-1": "US Texas",
            "us-midwest-1": "US Midwest",
            "us-west-1": "US West (California)",
            "us-west-2": "US West 2",
            "us-west-3": "US West 3",
            "us-south-1": "US South",
            "europe-central-1": "Europe Central",
            "asia-northeast-1": "Asia Northeast",
            "asia-south-1": "Asia South",
            "me-west-1": "Middle East West",
            "us-east-1": "US East (Virginia)",
        }

        # Extract all regions from instance data
        for instance_name, instance_info in response["data"].items():
            regions_available = instance_info.get("regions_with_capacity_available", [])
            for region in regions_available:
                # Handle both string and dict formats
                if isinstance(region, dict):
                    region_name = region.get("name", region.get("region", str(region)))
                else:
                    region_name = str(region)
                regions_set.add(region_name)

        # Return as list of dicts to match expected format
        return [
            {
                "name": region,
                "description": region_descriptions.get(
                    region, region.replace("-", " ").title()
                ),
            }
            for region in sorted(regions_set)
        ]
    return []


def get_images(api_key: str) -> List[Dict]:
    """Get available OS images from Lambda Labs."""
    response = make_api_request("/images", api_key)
    if response and "data" in response:
        return response["data"]
    return []


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


def get_instance_pricing() -> Dict[str, float]:
    """Get hardcoded instance pricing data (per hour in USD).

    Prices are based on Lambda Labs public pricing as of 2025.
    These are on-demand prices; reserved instances may be cheaper.
    """
    return {
        # 1x GPU instances
        "gpu_1x_gh200": 1.49,
        "gpu_1x_h100_sxm": 3.29,
        "gpu_1x_h100_pcie": 2.49,
        "gpu_1x_a100": 1.29,
        "gpu_1x_a100_sxm": 1.29,
        "gpu_1x_a100_pcie": 1.29,
        "gpu_1x_a10": 0.75,
        "gpu_1x_a6000": 0.80,
        "gpu_1x_rtx6000": 0.50,
        "gpu_1x_quadro_rtx_6000": 0.50,
        # 2x GPU instances
        "gpu_2x_h100_sxm": 6.38,  # 2 * 3.19
        "gpu_2x_a100": 2.58,  # 2 * 1.29
        "gpu_2x_a100_pcie": 2.58,  # 2 * 1.29
        "gpu_2x_a6000": 1.60,  # 2 * 0.80
        # 4x GPU instances
        "gpu_4x_h100_sxm": 12.36,  # 4 * 3.09
        "gpu_4x_a100": 5.16,  # 4 * 1.29
        "gpu_4x_a100_pcie": 5.16,  # 4 * 1.29
        "gpu_4x_a6000": 3.20,  # 4 * 0.80
        # 8x GPU instances
        "gpu_8x_b200_sxm": 39.92,  # 8 * 4.99
        "gpu_8x_h100_sxm": 23.92,  # 8 * 2.99
        "gpu_8x_a100_80gb": 14.32,  # 8 * 1.79
        "gpu_8x_a100_80gb_sxm": 14.32,  # 8 * 1.79
        "gpu_8x_a100": 10.32,  # 8 * 1.29
        "gpu_8x_a100_40gb": 10.32,  # 8 * 1.29
        "gpu_8x_v100": 4.40,  # 8 * 0.55
    }


def generate_instance_types_kconfig(api_key: str) -> str:
    """Generate Kconfig content for Lambda Labs instance types with capacity info."""
    instance_types, capacity_map = get_instance_types_with_capacity(api_key)
    pricing = get_instance_pricing()

    if not instance_types:
        # Fallback to some default instance types if API is unavailable
        return """# Lambda Labs instance types (API unavailable - using defaults)

choice
    prompt "Lambda Labs instance type"
    default TERRAFORM_LAMBDALABS_INSTANCE_TYPE_GPU_1X_A10
    help
      Select the Lambda Labs instance type for your deployment.
      Note: API is currently unavailable, showing default options.
      Prices shown are on-demand hourly rates in USD.

config TERRAFORM_LAMBDALABS_INSTANCE_TYPE_GPU_1X_A10
    bool "gpu_1x_a10 - 1x NVIDIA A10 GPU ($0.75/hr)"
    help
      Single NVIDIA A10 GPU instance with 24GB VRAM.
      Price: $0.75 per hour (on-demand)

config TERRAFORM_LAMBDALABS_INSTANCE_TYPE_GPU_1X_A100
    bool "gpu_1x_a100 - 1x NVIDIA A100 GPU ($1.29/hr)"
    help
      Single NVIDIA A100 GPU instance with 40GB VRAM.
      Price: $1.29 per hour (on-demand)

config TERRAFORM_LAMBDALABS_INSTANCE_TYPE_GPU_8X_A100_80GB
    bool "gpu_8x_a100_80gb - 8x NVIDIA A100 GPU ($14.32/hr)"
    help
      Eight NVIDIA A100 GPUs with 80GB VRAM each.
      Price: $14.32 per hour (on-demand)

endchoice
"""

    # Separate instance types by availability
    available_types = []
    unavailable_types = []

    for name, info in instance_types.items():
        if name in capacity_map and capacity_map[name]:
            available_types.append((name, info))
        else:
            unavailable_types.append((name, info))

    # Sort by name for consistency
    available_types.sort(key=lambda x: x[0])
    unavailable_types.sort(key=lambda x: x[0])

    # Generate dynamic Kconfig from API data
    kconfig = (
        "# Lambda Labs instance types (dynamically generated with capacity info)\n\n"
    )
    kconfig += "choice\n"
    kconfig += '\tprompt "Lambda Labs instance type"\n'

    # Use the first available instance type as default
    if available_types:
        default_type = sanitize_kconfig_name(available_types[0][0])
        kconfig += f"\tdefault TERRAFORM_LAMBDALABS_INSTANCE_TYPE_{default_type}\n"

    kconfig += "\thelp\n"
    kconfig += "\t  Select the Lambda Labs instance type for your deployment.\n"
    kconfig += "\t  These options are dynamically generated from the Lambda Labs API.\n"
    kconfig += "\t  [Available] = Has capacity in at least one region\n"
    kconfig += "\t  [No Capacity] = Currently no capacity available\n"
    kconfig += "\t  Prices shown are on-demand hourly rates in USD.\n\n"

    # First add available instance types
    if available_types:
        kconfig += "# Instance types WITH available capacity:\n"
        for name, info in available_types:
            kconfig_name = sanitize_kconfig_name(name)

            # Get instance details
            instance_info = info.get("instance_type", {})
            description = instance_info.get("description", name)

            # Get pricing for this instance type
            price = pricing.get(name, 0)
            price_str = f"${price:.2f}/hr" if price > 0 else "Price N/A"

            # Get capacity regions
            regions = capacity_map.get(name, [])
            regions_str = ", ".join(regions[:3])  # Show first 3 regions
            if len(regions) > 3:
                regions_str += f" +{len(regions)-3} more"

            # Get instance specifications
            specs = instance_info.get("specs", {})
            vcpus = specs.get("vcpus", "N/A")
            memory_gib = specs.get("memory_gib", "N/A")
            storage_gib = specs.get("storage_gib", "N/A")

            kconfig += f"config TERRAFORM_LAMBDALABS_INSTANCE_TYPE_{kconfig_name}\n"
            kconfig += f'\tbool "{name} ({price_str}) - {description} [AVAILABLE]"\n'
            kconfig += "\thelp\n"
            kconfig += f"\t  {description}\n"
            kconfig += f"\t  AVAILABLE in: {regions_str}\n"
            kconfig += f"\t  Price: {price_str} (on-demand)\n"
            kconfig += f"\t  vCPUs: {vcpus}, Memory: {memory_gib} GiB, Storage: {storage_gib} GiB\n\n"

    # Then add unavailable instance types (commented out or with warning)
    if unavailable_types:
        kconfig += "# Instance types WITHOUT capacity (not recommended):\n"
        for name, info in unavailable_types:
            kconfig_name = sanitize_kconfig_name(name)

            # Get instance details
            instance_info = info.get("instance_type", {})
            description = instance_info.get("description", name)

            # Get pricing for this instance type
            price = pricing.get(name, 0)
            price_str = f"${price:.2f}/hr" if price > 0 else "Price N/A"

            kconfig += f"config TERRAFORM_LAMBDALABS_INSTANCE_TYPE_{kconfig_name}\n"
            kconfig += f'\tbool "{name} ({price_str}) - [NO CAPACITY]"\n'
            kconfig += "\thelp\n"
            kconfig += f"\t  {description}\n"
            kconfig += f"\t  WARNING: Currently NO CAPACITY in any region!\n"
            kconfig += f"\t  This option will fail during provisioning.\n"
            kconfig += f"\t  Price: {price_str} (on-demand) when available\n\n"

    kconfig += "endchoice\n"

    # Don't generate the TERRAFORM_LAMBDALABS_INSTANCE_TYPE config here
    # It's already defined in Kconfig.compute with proper defaults

    return kconfig


def generate_instance_type_mappings(api_key: str) -> str:
    """Generate Kconfig mappings for all instance types."""
    instance_types, _ = get_instance_types_with_capacity(api_key)

    # Generate mappings for TERRAFORM_LAMBDALABS_INSTANCE_TYPE config
    mappings = []
    for name in sorted(instance_types.keys()):
        kconfig_name = sanitize_kconfig_name(name)
        mappings.append(
            f'\tdefault "{name}" if TERRAFORM_LAMBDALABS_INSTANCE_TYPE_{kconfig_name}'
        )

    return "\n".join(mappings)


def generate_regions_kconfig(api_key: str) -> str:
    """Generate Kconfig content for Lambda Labs regions with capacity indicators."""
    regions = get_regions(api_key)

    # Get capacity information
    _, capacity_map = get_instance_types_with_capacity(api_key)

    # Count how many instance types have capacity in each region
    region_capacity_count = {}
    for instance_type, available_regions in capacity_map.items():
        for region in available_regions:
            region_capacity_count[region] = region_capacity_count.get(region, 0) + 1

    if not regions:
        # Fallback to default regions if API is unavailable
        return """# Lambda Labs regions (API unavailable - using defaults)

choice
    prompt "Lambda Labs region"
    default TERRAFORM_LAMBDALABS_REGION_US_TX_1
    help
      Select the Lambda Labs region for deployment.
      Note: API is currently unavailable, showing default options.

config TERRAFORM_LAMBDALABS_REGION_US_TX_1
    bool "us-tx-1 - Texas, USA"

config TERRAFORM_LAMBDALABS_REGION_US_MIDWEST_1
    bool "us-midwest-1 - Midwest, USA"

config TERRAFORM_LAMBDALABS_REGION_US_WEST_1
    bool "us-west-1 - West Coast, USA"

endchoice
"""

    # Sort regions by capacity count (most capacity first)
    regions_sorted = sorted(
        regions,
        key=lambda r: region_capacity_count.get(r.get("name", ""), 0),
        reverse=True,
    )

    # Generate dynamic Kconfig from API data
    kconfig = "# Lambda Labs regions (dynamically generated with capacity info)\n\n"
    kconfig += "choice\n"
    kconfig += '\tprompt "Lambda Labs region"\n'

    # Use region with most capacity as default
    if regions_sorted:
        default_region = sanitize_kconfig_name(regions_sorted[0].get("name", "us_tx_1"))
        kconfig += f"\tdefault TERRAFORM_LAMBDALABS_REGION_{default_region}\n"

    kconfig += "\thelp\n"
    kconfig += "\t  Select the Lambda Labs region for deployment.\n"
    kconfig += (
        "\t  Number shows how many instance types have capacity in that region.\n"
    )
    kconfig += "\t  Choose regions with higher numbers for better availability.\n\n"

    for region in regions_sorted:
        name = region.get("name", "")
        if not name:
            continue

        kconfig_name = sanitize_kconfig_name(name)
        description = region.get("description", name)

        # Get capacity count for this region
        capacity_count = region_capacity_count.get(name, 0)

        if capacity_count > 0:
            capacity_str = f"[{capacity_count} types available]"
        else:
            capacity_str = "[NO CAPACITY]"

        kconfig += f"config TERRAFORM_LAMBDALABS_REGION_{kconfig_name}\n"
        kconfig += f'\tbool "{name} - {description} {capacity_str}"\n'
        kconfig += "\thelp\n"
        kconfig += f"\t  Region: {description}\n"
        if capacity_count > 0:
            kconfig += (
                f"\t  {capacity_count} instance types have capacity in this region.\n\n"
            )
        else:
            kconfig += "\t  WARNING: No instance types currently have capacity in this region!\n\n"

    kconfig += "endchoice\n"

    # Don't generate the TERRAFORM_LAMBDALABS_REGION config here
    # It's already defined in Kconfig.location with proper defaults

    return kconfig


def generate_images_kconfig(api_key: str) -> str:
    """Generate Kconfig content for Lambda Labs OS images."""
    images = get_images(api_key)

    if not images:
        # Note: Lambda Labs doesn't support OS selection via terraform
        return """# Lambda Labs OS images configuration

# NOTE: The Lambda Labs terraform provider (elct9620/lambdalabs v0.3.0) does NOT support
# OS image selection. Lambda Labs automatically deploys Ubuntu 22.04 LTS by default.
#
# The provider only supports these attributes for instances:
# - name (instance name)
# - region_name (deployment region)
# - instance_type_name (GPU type)
# - ssh_key_names (SSH keys)
#
# What's NOT supported:
# - OS/distribution selection
# - Custom user creation
# - User data/cloud-init scripts
# - Storage configuration
#
# SSH User: Always "ubuntu" (the OS default user)
#
# This file is kept as a placeholder for future provider updates.

# No configuration options available - provider doesn't support OS selection
"""

    # If we somehow get images from API (future), generate the config
    # but add a warning that it's not supported by terraform provider
    kconfig = (
        "# Lambda Labs OS images (from API but NOT SUPPORTED by terraform provider)\n\n"
    )
    kconfig += "# WARNING: The terraform provider does NOT support OS selection!\n"
    kconfig += "# These options are shown for reference only.\n\n"

    kconfig += "choice\n"
    kconfig += '\tprompt "Lambda Labs OS image (NOT SUPPORTED)"\n'

    # Use first available image as default
    if images:
        default_image = sanitize_kconfig_name(images[0].get("name", "ubuntu_22_04"))
        kconfig += f"\tdefault TERRAFORM_LAMBDALABS_IMAGE_{default_image}\n"

    kconfig += "\thelp\n"
    kconfig += "\t  WARNING: OS selection is NOT supported by the terraform provider.\n"
    kconfig += "\t  Lambda Labs will always deploy Ubuntu 22.04 regardless of this setting.\n\n"

    for image in images:
        name = image.get("name", "")
        if not name:
            continue

        kconfig_name = sanitize_kconfig_name(name)
        description = image.get("description", name)

        kconfig += f"config TERRAFORM_LAMBDALABS_IMAGE_{kconfig_name}\n"
        kconfig += f'\tbool "{description} (NOT SUPPORTED)"\n\n'

    kconfig += "endchoice\n\n"

    # Generate the string config that maps choices to actual values
    kconfig += "config TERRAFORM_LAMBDALABS_IMAGE\n"
    kconfig += "\tstring\n"
    kconfig += "\toutput yaml\n"

    for image in images:
        name = image.get("name", "")
        if not name:
            continue
        kconfig_name = sanitize_kconfig_name(name)
        kconfig += f'\tdefault "{name}" if TERRAFORM_LAMBDALABS_IMAGE_{kconfig_name}\n'

    return kconfig


def main():
    """Main entry point for generating Lambda Labs Kconfig files."""
    if len(sys.argv) < 2:
        print("Usage: lambdalabs_api.py <command> [args...]")
        print("Commands:")
        print("  instance-types - Generate instance types Kconfig")
        print("  regions       - Generate regions Kconfig")
        print("  images        - Generate OS images Kconfig")
        print("  all           - Generate all Kconfig files")
        sys.exit(1)

    command = sys.argv[1]
    api_key = get_api_key()

    if not api_key:
        print(
            "Warning: Lambda Labs API key not found, using default values",
            file=sys.stderr,
        )
        api_key = ""  # Will trigger fallback behavior

    if command == "instance-types":
        print(generate_instance_types_kconfig(api_key))
    elif command == "regions":
        print(generate_regions_kconfig(api_key))
    elif command == "images":
        print(generate_images_kconfig(api_key))
    elif command == "all":
        # Generate all Kconfig files
        output_dir = (
            sys.argv[2] if len(sys.argv) > 2 else "terraform/lambdalabs/kconfigs"
        )

        os.makedirs(output_dir, exist_ok=True)

        # Generate instance types
        with open(os.path.join(output_dir, "Kconfig.compute.generated"), "w") as f:
            f.write(generate_instance_types_kconfig(api_key))

        # Generate regions
        with open(os.path.join(output_dir, "Kconfig.location.generated"), "w") as f:
            f.write(generate_regions_kconfig(api_key))

        # Generate images
        with open(os.path.join(output_dir, "Kconfig.images.generated"), "w") as f:
            f.write(generate_images_kconfig(api_key))

        print(f"Generated Kconfig files in {output_dir}")
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

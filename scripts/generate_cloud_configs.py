#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Generate dynamic cloud configurations for all supported providers.
Provides a summary of available options and pricing.
"""

import os
import sys
import subprocess
import json
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple

# Import our credentials module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lambdalabs_credentials import get_api_key as get_api_key_from_credentials


def get_lambdalabs_summary() -> Tuple[bool, str]:
    """
    Get a summary of Lambda Labs configurations.
    Returns (success, summary_string)
    """
    api_key = get_api_key_from_credentials()
    if not api_key:
        return False, "Lambda Labs: API key not set - using defaults"

    try:
        # Get instance types with capacity
        headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "kdevops/1.0"}
        req = urllib.request.Request(
            "https://cloud.lambdalabs.com/api/v1/instance-types", headers=headers
        )

        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

            if "data" not in data:
                return False, "Lambda Labs: Invalid API response"

            # Get pricing data
            pricing = {
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
                "gpu_2x_h100_sxm": 6.38,
                "gpu_2x_a100": 2.58,
                "gpu_2x_a100_pcie": 2.58,
                "gpu_2x_a6000": 1.60,
                "gpu_4x_h100_sxm": 12.36,
                "gpu_4x_a100": 5.16,
                "gpu_4x_a100_pcie": 5.16,
                "gpu_4x_a6000": 3.20,
                "gpu_8x_b200_sxm": 39.92,
                "gpu_8x_h100_sxm": 23.92,
                "gpu_8x_a100_80gb": 14.32,
                "gpu_8x_a100_80gb_sxm": 14.32,
                "gpu_8x_a100": 10.32,
                "gpu_8x_a100_40gb": 10.32,
                "gpu_8x_v100": 4.40,
            }

            # Count available instances and get price range
            available_count = 0
            total_count = len(data["data"])
            available_prices = []
            all_regions = set()

            for instance_type, info in data["data"].items():
                regions = info.get("regions_with_capacity_available", [])
                if regions:
                    available_count += 1
                    if instance_type in pricing:
                        available_prices.append(pricing[instance_type])
                    for r in regions:
                        all_regions.add(r["name"])

            # Format summary
            if available_prices:
                min_price = min(available_prices)
                max_price = max(available_prices)
                price_range = f"${min_price:.2f}-${max_price:.2f}/hr"
            else:
                price_range = "pricing varies"

            region_count = len(all_regions)

            return (
                True,
                f"Lambda Labs: {available_count}/{total_count} GPU types available, {region_count} regions, {price_range}",
            )

    except urllib.error.HTTPError as e:
        if e.code == 403:
            return False, "Lambda Labs: API key invalid - using defaults"
        else:
            return False, f"Lambda Labs: API error {e.code}"
    except Exception as e:
        return False, f"Lambda Labs: Error - {str(e)}"


def generate_lambdalabs_configs(output_dir: str) -> bool:
    """Generate Lambda Labs Kconfig files."""
    try:
        # Run the lambdalabs_api.py script
        result = subprocess.run(
            [sys.executable, "scripts/lambdalabs_api.py", "all", output_dir],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(
                f"  ⚠ Error generating Lambda Labs configs: {result.stderr}",
                file=sys.stderr,
            )
            return False

        return True
    except Exception as e:
        print(f"  ⚠ Error: {e}", file=sys.stderr)
        return False


def generate_aws_configs(output_dir: str) -> bool:
    """
    Generate AWS Kconfig files (placeholder for future implementation).
    """
    # For now, just return True as AWS uses static configs
    return True


def generate_azure_configs(output_dir: str) -> bool:
    """
    Generate Azure Kconfig files (placeholder for future implementation).
    """
    # For now, just return True as Azure uses static configs
    return True


def generate_gce_configs(output_dir: str) -> bool:
    """
    Generate GCE Kconfig files (placeholder for future implementation).
    """
    # For now, just return True as GCE uses static configs
    return True


def main():
    """Main function to generate all cloud configurations."""
    print("Generating dynamic cloud configurations based on latest data...")
    print()

    # Create .cloud.initialized marker file to signal cloud support is configured
    # This will be used by Kconfig to set intelligent defaults
    try:
        with open(".cloud.initialized", "w") as f:
            f.write("# This file indicates cloud support has been initialized\n")
            f.write("# Created by 'make cloud-config'\n")
            f.write("# Kconfig will use this to set cloud-related defaults\n")
    except Exception as e:
        print(f"  ⚠ Warning: Could not create .cloud.initialized: {e}", file=sys.stderr)

    # Get summaries for each provider
    providers = []

    # Lambda Labs
    success, summary = get_lambdalabs_summary()
    providers.append(("Lambda Labs", success, summary))

    # Future providers (placeholders for when we add dynamic support)
    # When these providers get dynamic config support, they would show:
    # providers.append(("AWS", True, "AWS: 100+ instance types, 26 regions, $0.01-$40.00/hr"))
    # providers.append(("Azure", True, "Azure: 200+ VM sizes, 60+ regions, $0.01-$50.00/hr"))
    # providers.append(("GCE", True, "GCE: 50+ machine types, 35 regions, $0.01-$30.00/hr"))

    # Print summaries
    for provider, success, summary in providers:
        if success:
            print(f"  ✓ {summary}")
        else:
            print(f"  ⚠ {summary}")

    print()

    # Generate configurations for each provider
    configs_generated = []

    # Lambda Labs
    print("  • Generating Lambda Labs configurations...")
    if generate_lambdalabs_configs("terraform/lambdalabs/kconfigs"):
        configs_generated.append("Lambda Labs")
        print("    ✓ Instance types, regions, and capacity information updated")
    else:
        print("    ⚠ Using default configurations")

    # Future providers would go here
    # print("  • AWS configurations (static)...")
    # configs_generated.append("AWS")

    print()

    if configs_generated:
        print(f"✓ Cloud configurations ready for: {', '.join(configs_generated)}")
        print("  Run 'make menuconfig' to select your cloud provider and options")
    else:
        print("⚠ No dynamic configurations were generated, using defaults")

    return 0


if __name__ == "__main__":
    sys.exit(main())

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


def generate_lambdalabs_kconfig() -> bool:
    """
    Generate Lambda Labs Kconfig files.
    Returns True on success, False on failure.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cli_path = os.path.join(script_dir, "lambda-cli")

    # Generate the Kconfig files
    result = subprocess.run(
        [cli_path, "generate-kconfig"],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode == 0


def get_lambdalabs_summary() -> tuple[bool, str]:
    """
    Get a summary of Lambda Labs configurations using lambda-cli.
    Returns (success, summary_string)
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cli_path = os.path.join(script_dir, "lambda-cli")

    try:
        # Get instance availability
        result = subprocess.run(
            [cli_path, "--output", "json", "instance-types", "list"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return False, "Lambda Labs: API key not set - using defaults"

        instances = json.loads(result.stdout)

        # Count available instances
        available = [i for i in instances if i.get("available_regions", 0) > 0]
        total_count = len(instances)
        available_count = len(available)

        # Get price range
        prices = []
        regions = set()
        for instance in available:
            price_str = instance.get("price_per_hour", "$0.00")
            price = float(price_str.replace("$", ""))
            if price > 0:
                prices.append(price)
            # Note: available_regions is a count, not a list

        # Get regions separately
        regions_result = subprocess.run(
            [cli_path, "--output", "json", "regions", "list"],
            capture_output=True,
            text=True,
            check=False,
        )

        if regions_result.returncode == 0:
            regions_data = json.loads(regions_result.stdout)
            region_count = len(regions_data)
        else:
            region_count = 0

        # Format summary
        if prices:
            min_price = min(prices)
            max_price = max(prices)
            price_range = f"${min_price:.2f}-${max_price:.2f}/hr"
        else:
            price_range = "pricing varies"

        return (
            True,
            f"Lambda Labs: {available_count}/{total_count} instances available, "
            f"{region_count} regions, {price_range}",
        )

    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
        return False, "Lambda Labs: Error querying API - using defaults"


def main():
    """Main function to generate cloud configurations."""
    print("Cloud Provider Configuration Summary")
    print("=" * 60)
    print()

    # Lambda Labs - Generate Kconfig files first
    kconfig_generated = generate_lambdalabs_kconfig()

    # Lambda Labs - Get summary
    success, summary = get_lambdalabs_summary()
    if success:
        print(f"✓ {summary}")
        if kconfig_generated:
            print("  Kconfig files generated successfully")
        else:
            print("  Warning: Failed to generate Kconfig files")
    else:
        print(f"⚠ {summary}")
    print()

    # AWS (placeholder - not implemented)
    print("⚠ AWS: Dynamic configuration not yet implemented")

    # Azure (placeholder - not implemented)
    print("⚠ Azure: Dynamic configuration not yet implemented")

    # GCE (placeholder - not implemented)
    print("⚠ GCE: Dynamic configuration not yet implemented")

    print()
    print("Note: Dynamic configurations query real-time availability")
    print("Run 'make menuconfig' to configure your cloud provider")


if __name__ == "__main__":
    main()

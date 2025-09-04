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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Tuple


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


def generate_aws_kconfig() -> bool:
    """
    Generate AWS Kconfig files.
    Returns True on success, False on failure.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cli_path = os.path.join(script_dir, "aws-cli")

    # Generate the Kconfig files
    result = subprocess.run(
        [cli_path, "generate-kconfig"],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode == 0


def get_aws_summary() -> tuple[bool, str]:
    """
    Get a summary of AWS configurations using aws-cli.
    Returns (success, summary_string)
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cli_path = os.path.join(script_dir, "aws-cli")

    try:
        # Check if AWS CLI is available
        result = subprocess.run(
            ["aws", "--version"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return False, "AWS: AWS CLI not installed - using defaults"

        # Check if credentials are configured
        result = subprocess.run(
            ["aws", "sts", "get-caller-identity"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return False, "AWS: Credentials not configured - using defaults"

        # Get instance types count
        result = subprocess.run(
            [
                cli_path,
                "--output",
                "json",
                "instance-types",
                "list",
                "--max-results",
                "100",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return False, "AWS: Error querying API - using defaults"

        instances = json.loads(result.stdout)
        instance_count = len(instances)

        # Get regions
        result = subprocess.run(
            [cli_path, "--output", "json", "regions", "list"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            regions = json.loads(result.stdout)
            region_count = len(regions)
        else:
            region_count = 0

        # Get price range from a sample of instances
        prices = []
        for instance in instances[:20]:  # Sample first 20 for speed
            if "error" not in instance:
                # Extract price if available (would need pricing API)
                # For now, we'll use placeholder
                vcpus = instance.get("vcpu", 0)
                if vcpus > 0:
                    # Rough estimate: $0.05 per vCPU/hour
                    estimated_price = vcpus * 0.05
                    prices.append(estimated_price)

        # Format summary
        if prices:
            min_price = min(prices)
            max_price = max(prices)
            price_range = f"~${min_price:.2f}-${max_price:.2f}/hr"
        else:
            price_range = "pricing varies by region"

        return (
            True,
            f"AWS: {instance_count} instance types available, "
            f"{region_count} regions, {price_range}",
        )

    except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
        return False, "AWS: Error querying API - using defaults"


def process_lambdalabs() -> Tuple[bool, bool, str]:
    """Process Lambda Labs configuration generation and summary.
    Returns (kconfig_generated, summary_success, summary_text)
    """
    kconfig_generated = generate_lambdalabs_kconfig()
    success, summary = get_lambdalabs_summary()
    return kconfig_generated, success, summary


def process_aws() -> Tuple[bool, bool, str]:
    """Process AWS configuration generation and summary.
    Returns (kconfig_generated, summary_success, summary_text)
    """
    kconfig_generated = generate_aws_kconfig()
    success, summary = get_aws_summary()

    return kconfig_generated, success, summary


def main():
    """Main function to generate cloud configurations."""
    print("Cloud Provider Configuration Summary")
    print("=" * 60)
    print()

    # Run cloud provider operations in parallel
    results = {}
    any_success = False

    with ThreadPoolExecutor(max_workers=4) as executor:
        # Submit all tasks
        futures = {
            executor.submit(process_lambdalabs): "lambdalabs",
            executor.submit(process_aws): "aws",
        }

        # Process results as they complete
        for future in as_completed(futures):
            provider = futures[future]
            try:
                results[provider] = future.result()
            except Exception as e:
                results[provider] = (
                    False,
                    False,
                    f"{provider.upper()}: Error - {str(e)}",
                )

    # Display results in consistent order
    for provider in ["lambdalabs", "aws"]:
        if provider in results:
            kconfig_gen, success, summary = results[provider]
            if success and kconfig_gen:
                any_success = True
            if success:
                print(f"✓ {summary}")
                if kconfig_gen:
                    print("  Kconfig files generated successfully")
                else:
                    print("  Warning: Failed to generate Kconfig files")
            else:
                print(f"⚠ {summary}")
            print()

    # Create .cloud.initialized if any provider succeeded
    if any_success:
        Path(".cloud.initialized").touch()

    # Azure (placeholder - not implemented)
    print("⚠ Azure: Dynamic configuration not yet implemented")

    # GCE (placeholder - not implemented)
    print("⚠ GCE: Dynamic configuration not yet implemented")

    print()
    print("Note: Dynamic configurations query real-time availability")
    print("Run 'make menuconfig' to configure your cloud provider")


if __name__ == "__main__":
    main()

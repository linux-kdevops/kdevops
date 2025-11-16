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
import argparse


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
    project_root = os.path.dirname(script_dir)
    aws_scripts_dir = os.path.join(project_root, "terraform", "aws", "scripts")
    aws_kconfigs_dir = os.path.join(project_root, "terraform", "aws", "kconfigs")

    # Define the script-to-output mapping
    scripts_to_run = [
        ("gen_kconfig_ami", "Kconfig.ami.generated"),
        ("gen_kconfig_instance", "Kconfig.instance.generated"),
        ("gen_kconfig_location", "Kconfig.location.generated"),
    ]

    all_success = True

    for script_name, kconfig_file in scripts_to_run:
        script_path = os.path.join(aws_scripts_dir, script_name)
        output_path = os.path.join(aws_kconfigs_dir, kconfig_file)

        # Run the script and capture its output
        result = subprocess.run(
            [script_path],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            # Write the output to the corresponding Kconfig file
            try:
                with open(output_path, "w") as f:
                    f.write(result.stdout)
            except IOError as e:
                print(f"Error writing {kconfig_file}: {e}", file=sys.stderr)
                all_success = False
        else:
            print(f"Error running {script_name}: {result.stderr}", file=sys.stderr)
            all_success = False

    return all_success


def generate_azure_kconfig() -> bool:
    """
    Generate Azure Kconfig files.
    Returns True on success, False on failure.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    azure_scripts_dir = os.path.join(project_root, "terraform", "azure", "scripts")
    azure_kconfigs_dir = os.path.join(project_root, "terraform", "azure", "kconfigs")

    # Define the script-to-output mapping
    scripts_to_run = [
        ("gen_kconfig_image", "Kconfig.image.generated"),
        ("gen_kconfig_location", "Kconfig.location.generated"),
        ("gen_kconfig_size", "Kconfig.size.generated"),
    ]

    all_success = True

    for script_name, kconfig_file in scripts_to_run:
        script_path = os.path.join(azure_scripts_dir, script_name)
        output_path = os.path.join(azure_kconfigs_dir, kconfig_file)

        # Run the script and capture its output
        result = subprocess.run(
            [script_path],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            # Write the output to the corresponding Kconfig file
            try:
                with open(output_path, "w") as f:
                    f.write(result.stdout)
            except IOError as e:
                print(f"Error writing {kconfig_file}: {e}", file=sys.stderr)
                all_success = False
        else:
            print(f"Error running {script_name}: {result.stderr}", file=sys.stderr)
            all_success = False

    return all_success


def generate_oci_kconfig() -> bool:
    """
    Generate OCI Kconfig files.
    Returns True on success, False on failure.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    oci_scripts_dir = os.path.join(project_root, "terraform", "oci", "scripts")
    oci_kconfigs_dir = os.path.join(project_root, "terraform", "oci", "kconfigs")

    # Define the script-to-output mapping
    scripts_to_run = [
        ("gen_kconfig_image", "Kconfig.image.generated"),
        ("gen_kconfig_location", "Kconfig.location.generated"),
        ("gen_kconfig_shape", "Kconfig.shape.generated"),
    ]

    all_success = True

    for script_name, kconfig_file in scripts_to_run:
        script_path = os.path.join(oci_scripts_dir, script_name)
        output_path = os.path.join(oci_kconfigs_dir, kconfig_file)

        # Run the script and capture its output
        result = subprocess.run(
            [script_path],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0:
            # Write the output to the corresponding Kconfig file
            try:
                with open(output_path, "w") as f:
                    f.write(result.stdout)
            except IOError as e:
                print(f"Error writing {kconfig_file}: {e}", file=sys.stderr)
                all_success = False
        else:
            print(f"Error running {script_name}: {result.stderr}", file=sys.stderr)
            all_success = False

    return all_success


def process_lambdalabs():
    """Process Lambda Labs configuration."""
    # Generate Kconfig files first
    kconfig_generated = generate_lambdalabs_kconfig()

    # Get summary
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


def process_aws():
    """Process AWS configuration."""
    kconfig_generated = generate_aws_kconfig()
    if kconfig_generated:
        print("✓ AWS: Kconfig files generated successfully")
    else:
        print("⚠ AWS: Failed to generate Kconfig files - using defaults")
    print()


def process_azure():
    """Process Azure configuration."""
    kconfig_generated = generate_azure_kconfig()
    if kconfig_generated:
        print("✓ Azure: Kconfig files generated successfully")
    else:
        print("⚠ Azure: Failed to generate Kconfig files - using defaults")
    print()


def process_gce():
    """Process GCE configuration (placeholder)."""
    print("⚠ GCE: Dynamic configuration not yet implemented")


def process_oci():
    """Process OCI configuration."""
    kconfig_generated = generate_oci_kconfig()
    if kconfig_generated:
        print("✓ OCI: Kconfig files generated successfully")
    else:
        print("⚠ OCI: Failed to generate Kconfig files - using defaults")
    print()


def generate_datacrunch_kconfig() -> bool:
    """
    Generate DataCrunch Kconfig files.
    Returns True on success, False on failure.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    generator_path = os.path.join(script_dir, "generate_datacrunch_kconfig.py")

    # Generate the Kconfig files
    result = subprocess.run(
        [generator_path],
        capture_output=True,
        text=True,
        check=False,
    )

    return result.returncode == 0


def process_datacrunch():
    """Process DataCrunch configuration."""
    kconfig_generated = generate_datacrunch_kconfig()
    if kconfig_generated:
        print("✓ DataCrunch: Kconfig files generated successfully")
    else:
        print("⚠ DataCrunch: Failed to generate Kconfig files - using defaults")
    print()


def main():
    """Main function to generate cloud configurations."""
    parser = argparse.ArgumentParser(
        description="Generate dynamic cloud configurations for supported providers",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                      # Generate configs for all providers
  %(prog)s --provider lambdalabs    # Generate configs for Lambda Labs only
  %(prog)s --provider datacrunch    # Generate configs for DataCrunch only
  %(prog)s --provider aws           # Generate configs for AWS only
  %(prog)s --provider azure         # Generate configs for Azure only

Supported providers: lambdalabs, datacrunch, aws, azure, gce, oci
        """,
    )

    parser.add_argument(
        "--provider",
        choices=["lambdalabs", "datacrunch", "aws", "azure", "gce", "oci"],
        help="Generate configuration for a specific cloud provider only",
    )

    args = parser.parse_args()

    # Provider dispatch table
    providers = {
        "lambdalabs": process_lambdalabs,
        "datacrunch": process_datacrunch,
        "aws": process_aws,
        "azure": process_azure,
        "gce": process_gce,
        "oci": process_oci,
    }

    print("Cloud Provider Configuration Summary")
    print("=" * 60)
    print()

    # If a specific provider is requested, only process that one
    if args.provider:
        if args.provider in providers:
            providers[args.provider]()
        else:
            print(f"Error: Unknown provider '{args.provider}'", file=sys.stderr)
            sys.exit(1)
    else:
        # Process all providers
        process_lambdalabs()
        process_datacrunch()
        process_aws()
        process_azure()
        process_gce()
        process_oci()

    print()
    print("Note: Dynamic configurations query real-time availability")
    print("Run 'make menuconfig' to configure your cloud provider")


if __name__ == "__main__":
    main()

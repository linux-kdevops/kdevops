#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

import boto3
import json
import sys
import argparse
import os
from configparser import ConfigParser
from botocore.exceptions import ClientError, NoCredentialsError


def get_aws_default_region():
    """
    Get the default AWS region from ~/.aws/config file.

    Returns:
        str: Default region or 'us-east-1' if not found
    """
    config_path = os.path.expanduser("~/.aws/config")

    if os.path.exists(config_path):
        try:
            config = ConfigParser()
            config.read(config_path)

            # Check for default profile region
            if "default" in config:
                return config["default"].get("region", "us-east-1")

            # Check for profile default section
            if "profile default" in config:
                return config["profile default"].get("region", "us-east-1")

        except Exception as e:
            print(f"Warning: Error reading AWS config file: {e}", file=sys.stderr)

    return "us-east-1"


def get_available_families(region="us-east-1"):
    """
    Get all available instance families in the specified region.

    Args:
        region (str): AWS region to query

    Returns:
        dict: Dictionary with family info including count of instances per family
    """
    try:
        ec2_client = boto3.client("ec2", region_name=region)
        response = ec2_client.describe_instance_types()

        families = {}
        for instance_type in response["InstanceTypes"]:
            instance_name = instance_type["InstanceType"]
            family = instance_name.split(".")[0]

            if family not in families:
                families[family] = {
                    "family_name": family,
                    "instance_count": 0,
                    "has_gpu": False,
                    "architectures": set(),
                }

            families[family]["instance_count"] += 1

            # Check for GPU
            if "GpuInfo" in instance_type:
                families[family]["has_gpu"] = True

            # Get architectures
            cpu_architectures = instance_type.get("ProcessorInfo", {}).get(
                "SupportedArchitectures", []
            )
            families[family]["architectures"].update(cpu_architectures)

        # Convert architecture sets to sorted lists for JSON serialization
        for family in families.values():
            family["architectures"] = sorted(list(family["architectures"]))

        return families

    except Exception as e:
        print(f"Error retrieving instance families: {e}", file=sys.stderr)
        return {}


def get_gpu_info(instance_type):
    """
    Extract GPU information from instance type data.

    Args:
        instance_type (dict): Instance type data from AWS API

    Returns:
        str: Formatted GPU information string
    """
    if "GpuInfo" not in instance_type:
        return "None"

    gpu_info = instance_type["GpuInfo"]
    total_gpu_memory = gpu_info.get("TotalGpuMemoryInMiB", 0)
    gpus = gpu_info.get("Gpus", [])

    if not gpus:
        return "GPU present (details unavailable)"

    gpu_details = []
    for gpu in gpus:
        gpu_name = gpu.get("Name", "Unknown GPU")
        gpu_count = gpu.get("Count", 1)
        gpu_memory = gpu.get("MemoryInfo", {}).get("SizeInMiB", 0)

        if gpu_count > 1:
            detail = f"{gpu_count}x {gpu_name}"
        else:
            detail = gpu_name

        if gpu_memory > 0:
            detail += f" ({gpu_memory // 1024}GB)"

        gpu_details.append(detail)

    return ", ".join(gpu_details)


def get_instance_family_info(family_name, region="us-east-1", quiet=False):
    """
    Get instance types, pricing, and hardware info for an AWS instance family.

    Args:
        family_name (str): Instance family name (e.g., 'm5', 't3', 'c5')
        region (str): AWS region to query (default: us-east-1)
        quiet (bool): Suppress debug messages

    Returns:
        list: List of dictionaries containing instance information
    """
    try:
        # Initialize AWS clients
        ec2_client = boto3.client("ec2", region_name=region)
        pricing_client = boto3.client(
            "pricing", region_name="us-east-1"
        )  # Pricing API only in us-east-1

        if not quiet:
            print(
                f"Querying EC2 API for instances starting with '{family_name}'...",
                file=sys.stderr,
            )

        # Get ALL instance types first, then filter
        response = ec2_client.describe_instance_types()

        # Filter instances that belong to the specified family
        family_instances = []
        for instance_type in response["InstanceTypes"]:
            instance_name = instance_type["InstanceType"]
            # More flexible matching - check if instance name starts with family name
            if instance_name.startswith(family_name + ".") or instance_name.startswith(
                family_name
            ):
                family_instances.append(instance_type)

        if not family_instances:
            if not quiet:
                print(
                    f"No instances found starting with '{family_name}'. Trying broader search...",
                    file=sys.stderr,
                )

            # Try a broader search - maybe the family name is part of the instance type
            family_instances = []
            for instance_type in response["InstanceTypes"]:
                instance_name = instance_type["InstanceType"]
                if family_name.lower() in instance_name.lower():
                    family_instances.append(instance_type)

        if not family_instances:
            if not quiet:
                # Show available families to help debug
                families = get_available_families(region)
                family_names = sorted([f["family_name"] for f in families.values()])
                print(f"Available instance families: {family_names}", file=sys.stderr)
            return []

        if not quiet:
            print(
                f"Found {len(family_instances)} instances in family '{family_name}'",
                file=sys.stderr,
            )

        instance_info = []

        for instance_type in family_instances:
            instance_name = instance_type["InstanceType"]

            if not quiet:
                print(f"Processing {instance_name}...", file=sys.stderr)

            # Extract CPU architecture information
            cpu_architectures = instance_type.get("ProcessorInfo", {}).get(
                "SupportedArchitectures", ["Unknown"]
            )
            cpu_isa = ", ".join(cpu_architectures) if cpu_architectures else "Unknown"

            # Extract GPU information
            gpu_info = get_gpu_info(instance_type)

            # Extract hardware specifications
            hardware_info = {
                "instance_type": instance_name,
                "vcpus": instance_type["VCpuInfo"]["DefaultVCpus"],
                "memory_gb": instance_type["MemoryInfo"]["SizeInMiB"] / 1024,
                "cpu_isa": cpu_isa,
                "gpu": gpu_info,
                "network_performance": instance_type.get("NetworkInfo", {}).get(
                    "NetworkPerformance", "Not specified"
                ),
                "storage": "EBS-only",
            }

            # Check for instance storage
            if "InstanceStorageInfo" in instance_type:
                storage_info = instance_type["InstanceStorageInfo"]
                total_storage = storage_info.get("TotalSizeInGB", 0)
                storage_type = storage_info.get("Disks", [{}])[0].get("Type", "Unknown")
                hardware_info["storage"] = f"{total_storage} GB {storage_type}"

            # Get pricing information (note: this often fails due to AWS Pricing API limitations)
            try:
                pricing_response = pricing_client.get_products(
                    ServiceCode="AmazonEC2",
                    Filters=[
                        {
                            "Type": "TERM_MATCH",
                            "Field": "instanceType",
                            "Value": instance_name,
                        },
                        {
                            "Type": "TERM_MATCH",
                            "Field": "location",
                            "Value": get_location_name(region),
                        },
                        {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
                        {
                            "Type": "TERM_MATCH",
                            "Field": "operating-system",
                            "Value": "Linux",
                        },
                        {
                            "Type": "TERM_MATCH",
                            "Field": "preInstalledSw",
                            "Value": "NA",
                        },
                        {
                            "Type": "TERM_MATCH",
                            "Field": "capacitystatus",
                            "Value": "Used",
                        },
                    ],
                )

                if pricing_response["PriceList"]:
                    price_data = json.loads(pricing_response["PriceList"][0])
                    terms = price_data["terms"]["OnDemand"]

                    # Extract the hourly price
                    for term_key in terms:
                        price_dimensions = terms[term_key]["priceDimensions"]
                        for price_key in price_dimensions:
                            price_per_hour = price_dimensions[price_key][
                                "pricePerUnit"
                            ]["USD"]
                            hardware_info["price_per_hour_usd"] = f"${price_per_hour}"
                            break
                        break
                else:
                    hardware_info["price_per_hour_usd"] = "Not available"

            except Exception as e:
                if not quiet:
                    print(
                        f"Warning: Could not fetch pricing for {instance_name}: {str(e)}",
                        file=sys.stderr,
                    )
                hardware_info["price_per_hour_usd"] = "Not available"

            instance_info.append(hardware_info)

        return sorted(instance_info, key=lambda x: x["instance_type"])

    except NoCredentialsError:
        print(
            "Error: AWS credentials not found. Please configure your credentials.",
            file=sys.stderr,
        )
        return []
    except ClientError as e:
        print(f"AWS API Error: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return []


def get_location_name(region):
    """Convert AWS region to location name for pricing API."""
    region_mapping = {
        "us-east-1": "US East (N. Virginia)",
        "us-east-2": "US East (Ohio)",
        "us-west-1": "US West (N. California)",
        "us-west-2": "US West (Oregon)",
        "us-west-2-lax-1": "US West (Los Angeles)",
        "ca-central-1": "Canada (Central)",
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
        "sa-east-1": "South America (Sao Paulo)",
    }
    return region_mapping.get(region, "US East (N. Virginia)")


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Get AWS EC2 instance family information including pricing and hardware specs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python %(prog)s m5
  python %(prog)s t3 --region us-west-2
  python %(prog)s c5 --format json
  python %(prog)s r5 --quiet
  python %(prog)s --families
  python %(prog)s --families --format json
        """,
    )

    parser.add_argument(
        "family_name",
        nargs="?",  # Make family_name optional when using --families
        help="Instance family name (e.g., m5, t3, c5, r5)",
    )

    parser.add_argument(
        "--region", "-r", help="AWS region (default: from ~/.aws/config or us-east-1)"
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (default: table)",
    )

    parser.add_argument(
        "--quiet", "-q", action="store_true", help="Suppress informational messages"
    )

    parser.add_argument(
        "--debug", "-d", action="store_true", help="Enable debug output"
    )

    parser.add_argument(
        "--families",
        action="store_true",
        help="List all available instance families in the region",
    )

    return parser.parse_args()


def output_families_table(families, region, quiet=False):
    """Output available instance families in table format."""
    if not quiet:
        print(f"Available instance families in {region}:\n")

    # Print header
    print(f"{'Family':<10} {'Count':<6} {'GPU':<5} {'Architectures':<20}")
    print("-" * 45)

    # Sort families by name
    sorted_families = sorted(families.values(), key=lambda x: x["family_name"])

    for family in sorted_families:
        gpu_indicator = "Yes" if family["has_gpu"] else "No"
        architectures = ", ".join(family["architectures"])

        print(
            f"{family['family_name']:<10} "
            f"{family['instance_count']:<6} "
            f"{gpu_indicator:<5} "
            f"{architectures:<20}"
        )


def output_families_json(families):
    """Output families in JSON format."""
    # Convert to list for JSON output
    families_list = sorted(families.values(), key=lambda x: x["family_name"])
    print(json.dumps(families_list, indent=2))


def output_families_csv(families):
    """Output families in CSV format."""
    if families:
        # Print header
        print("family_name,instance_count,has_gpu,architectures")

        # Sort families by name
        sorted_families = sorted(families.values(), key=lambda x: x["family_name"])

        # Print data
        for family in sorted_families:
            architectures = ";".join(
                family["architectures"]
            )  # Use semicolon to avoid CSV issues
            print(
                f"{family['family_name']},{family['instance_count']},{family['has_gpu']},{architectures}"
            )


def output_table(instances, quiet=False):
    """Output results in table format."""
    if not quiet:
        print(f"Found {len(instances)} instance types:\n")

    # Print header - adjusted for GPU column
    print(
        f"{'Instance Type':<15} {'vCPUs':<6} {'Memory (GB)':<12} {'CPU ISA':<10} {'GPU':<25} {'Storage':<20} {'Network':<15} {'Price/Hour':<12}"
    )
    print("-" * 130)

    # Print instance details
    for instance in instances:
        print(
            f"{instance['instance_type']:<15} "
            f"{instance['vcpus']:<6} "
            f"{instance['memory_gb']:<12.1f} "
            f"{instance['cpu_isa']:<10} "
            f"{instance['gpu']:<25} "
            f"{instance['storage']:<20} "
            f"{instance['network_performance']:<15} "
            f"{instance['price_per_hour_usd']:<12}"
        )


def output_json(instances):
    """Output results in JSON format."""
    print(json.dumps(instances, indent=2))


def output_csv(instances):
    """Output results in CSV format."""
    if instances:
        # Print header
        headers = instances[0].keys()
        print(",".join(headers))

        # Print data
        for instance in instances:
            values = [str(instance[header]).replace(",", ";") for header in headers]
            print(",".join(values))


def main():
    """Main function to run the program."""
    args = parse_arguments()

    # Determine region
    if args.region:
        region = args.region
    else:
        region = get_aws_default_region()

    # Handle --families option
    if args.families:
        families = get_available_families(region)
        if families:
            if args.format == "json":
                output_families_json(families)
            elif args.format == "csv":
                output_families_csv(families)
            else:  # table format
                output_families_table(families, region, args.quiet)
        else:
            print("Could not retrieve instance families.", file=sys.stderr)
            sys.exit(1)
        return

    # Require family_name if not using --families
    if not args.family_name:
        print(
            "Error: family_name is required unless using --families option",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.quiet:
        print(
            f"Fetching information for {args.family_name} family in {region}...",
            file=sys.stderr,
        )

    # Get instance information
    instances = get_instance_family_info(
        args.family_name, region, args.quiet or not args.debug
    )

    if not instances:
        print(f"No instances found for family '{args.family_name}'.", file=sys.stderr)
        print(
            f"Try running with --families to see available instance families.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Output results in specified format
    if args.format == "json":
        output_json(instances)
    elif args.format == "csv":
        output_csv(instances)
    else:  # table format
        output_table(instances, args.quiet)


if __name__ == "__main__":
    main()

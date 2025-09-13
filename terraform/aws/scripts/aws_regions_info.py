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


def get_all_regions():
    """
    Get all available AWS regions with their descriptions.

    Returns:
        dict: Dictionary of region information
    """
    try:
        # Use a default region to get the list of all regions
        ec2_client = boto3.client("ec2", region_name="us-east-1")
        response = ec2_client.describe_regions(AllRegions=True)

        regions = {}
        for region in response["Regions"]:
            region_name = region["RegionName"]
            regions[region_name] = {
                "region_name": region_name,
                "region_description": region.get("RegionName", region_name),
                "opt_in_status": region.get("OptInStatus", "Unknown"),
                "availability_zones": [],
            }

        return regions

    except Exception as e:
        print(f"Error retrieving AWS regions: {e}", file=sys.stderr)
        return {}


def get_region_info(region_name, quiet=False):
    """
    Get detailed information about a specific region including availability zones.

    Args:
        region_name (str): AWS region name (e.g., 'us-east-1', 'eu-west-1')
        quiet (bool): Suppress debug messages

    Returns:
        dict: Dictionary containing region information and availability zones
    """
    try:
        if not quiet:
            print(f"Querying information for region {region_name}...", file=sys.stderr)

        # Initialize EC2 client for the specific region
        ec2_client = boto3.client("ec2", region_name=region_name)

        # Get region information
        regions_response = ec2_client.describe_regions(
            Filters=[{"Name": "region-name", "Values": [region_name]}]
        )

        if not regions_response["Regions"]:
            if not quiet:
                print(f"Region {region_name} not found", file=sys.stderr)
            return None

        region_info = regions_response["Regions"][0]

        # Get availability zones for the region
        az_response = ec2_client.describe_availability_zones()

        availability_zones = []
        for az in az_response["AvailabilityZones"]:
            zone_info = {
                "zone_id": az["ZoneId"],
                "zone_name": az["ZoneName"],
                "zone_type": az.get("ZoneType", "availability-zone"),
                "parent_zone_id": az.get("ParentZoneId", ""),
                "parent_zone_name": az.get("ParentZoneName", ""),
                "state": az["State"],
                "messages": [],
            }

            # Add any messages about the zone
            if "Messages" in az:
                zone_info["messages"] = [
                    msg.get("Message", "") for msg in az["Messages"]
                ]

            availability_zones.append(zone_info)

        # Get network border group information if available
        try:
            zone_details = {}
            for az in az_response["AvailabilityZones"]:
                if "NetworkBorderGroup" in az:
                    zone_details[az["ZoneName"]] = az["NetworkBorderGroup"]
        except:
            zone_details = {}

        result = {
            "region_name": region_info["RegionName"],
            "endpoint": region_info.get("Endpoint", f"ec2.{region_name}.amazonaws.com"),
            "opt_in_status": region_info.get("OptInStatus", "opt-in-not-required"),
            "availability_zone_count": len(availability_zones),
            "availability_zones": sorted(
                availability_zones, key=lambda x: x["zone_name"]
            ),
        }

        if not quiet:
            print(
                f"Found {len(availability_zones)} availability zones in {region_name}",
                file=sys.stderr,
            )

        return result

    except NoCredentialsError:
        print(
            "Error: AWS credentials not found. Please configure your credentials.",
            file=sys.stderr,
        )
        return None
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        if error_code in ["UnauthorizedOperation", "InvalidRegion"]:
            print(
                f"Error: Cannot access region {region_name}. Check region name and permissions.",
                file=sys.stderr,
            )
        else:
            print(f"AWS API Error: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return None


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Get AWS region and availability zone information",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python %(prog)s --regions
  python %(prog)s us-east-1
  python %(prog)s eu-west-1 --format json
  python %(prog)s --regions --format csv
  python %(prog)s ap-southeast-1 --quiet
        """,
    )

    parser.add_argument(
        "region_name",
        nargs="?",  # Make region_name optional when using --regions
        help="AWS region name (e.g., us-east-1, eu-west-1, ap-southeast-1)",
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
        "--regions", action="store_true", help="List all available AWS regions"
    )

    return parser.parse_args()


def output_regions_table(regions, quiet=False):
    """Output available regions in table format."""
    if not quiet:
        print(f"Available AWS regions ({len(regions)}):\n")

    # Print header
    print(f"{'Region Name':<20} {'Opt-in Status':<20}")
    print("-" * 42)

    # Sort regions by name
    sorted_regions = sorted(regions.values(), key=lambda x: x["region_name"])

    for region in sorted_regions:
        opt_in_status = region.get("opt_in_status", "Unknown")
        print(f"{region['region_name']:<20} {opt_in_status:<20}")


def output_regions_json(regions):
    """Output regions in JSON format."""
    # Convert to list for JSON output
    regions_list = sorted(regions.values(), key=lambda x: x["region_name"])
    print(json.dumps(regions_list, indent=2))


def output_regions_csv(regions):
    """Output regions in CSV format."""
    if regions:
        # Print header
        print("region_name,opt_in_status")

        # Sort regions by name
        sorted_regions = sorted(regions.values(), key=lambda x: x["region_name"])

        # Print data
        for region in sorted_regions:
            opt_in_status = region.get("opt_in_status", "Unknown")
            print(f"{region['region_name']},{opt_in_status}")


def output_region_table(region_info, quiet=False):
    """Output region information in table format."""
    if not quiet:
        print(f"Region: {region_info['region_name']}\n")
        print(f"Endpoint: {region_info['endpoint']}")
        print(f"Opt-in Status: {region_info['opt_in_status']}")
        print(f"Availability Zones: {region_info['availability_zone_count']}\n")

    # Print availability zones table
    print(
        f"{'Zone Name':<15} {'Zone ID':<15} {'Zone Type':<18} {'State':<12} {'Parent Zone':<15}"
    )
    print("-" * 80)

    for az in region_info["availability_zones"]:
        parent_zone = az.get("parent_zone_name", "") or az.get("parent_zone_id", "")
        zone_type = az.get("zone_type", "availability-zone")

        print(
            f"{az['zone_name']:<15} "
            f"{az['zone_id']:<15} "
            f"{zone_type:<18} "
            f"{az['state']:<12} "
            f"{parent_zone:<15}"
        )

    # Show messages if any zones have them
    zones_with_messages = [
        az for az in region_info["availability_zones"] if az.get("messages")
    ]
    if zones_with_messages and not quiet:
        print("\nZone Messages:")
        for az in zones_with_messages:
            for message in az["messages"]:
                print(f"  {az['zone_name']}: {message}")


def output_region_json(region_info):
    """Output region information in JSON format."""
    print(json.dumps(region_info, indent=2))


def output_region_csv(region_info):
    """Output region information in CSV format."""
    # First output region info
    print("type,region_name,endpoint,opt_in_status,availability_zone_count")
    print(
        f"region,{region_info['region_name']},{region_info['endpoint']},{region_info['opt_in_status']},{region_info['availability_zone_count']}"
    )

    # Then output availability zones
    print("\ntype,zone_name,zone_id,zone_type,state,parent_zone_name,parent_zone_id")
    for az in region_info["availability_zones"]:
        parent_zone_name = az.get("parent_zone_name", "")
        parent_zone_id = az.get("parent_zone_id", "")
        zone_type = az.get("zone_type", "availability-zone")

        print(
            f"availability_zone,{az['zone_name']},{az['zone_id']},{zone_type},{az['state']},{parent_zone_name},{parent_zone_id}"
        )


def main():
    """Main function to run the program."""
    args = parse_arguments()

    # Handle --regions option
    if args.regions:
        if not args.quiet:
            print("Fetching list of all AWS regions...", file=sys.stderr)

        regions = get_all_regions()
        if regions:
            if args.format == "json":
                output_regions_json(regions)
            elif args.format == "csv":
                output_regions_csv(regions)
            else:  # table format
                output_regions_table(regions, args.quiet)
        else:
            print("Could not retrieve AWS regions.", file=sys.stderr)
            sys.exit(1)
        return

    # Require region_name if not using --regions
    if not args.region_name:
        print(
            "Error: region_name is required unless using --regions option",
            file=sys.stderr,
        )
        print("Use --regions to list all available regions", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        print(f"Fetching information for region {args.region_name}...", file=sys.stderr)

    # Get region information
    region_info = get_region_info(args.region_name, args.quiet or not args.debug)

    if not region_info:
        print(
            f"Could not retrieve information for region '{args.region_name}'.",
            file=sys.stderr,
        )
        print(f"Try running with --regions to see available regions.", file=sys.stderr)
        sys.exit(1)

    # Output results in specified format
    if args.format == "json":
        output_region_json(region_info)
    elif args.format == "csv":
        output_region_csv(region_info)
    else:  # table format
        output_region_table(region_info, args.quiet)


if __name__ == "__main__":
    main()

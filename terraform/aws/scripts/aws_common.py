#!/usr/bin/env python3
# ex: set filetype=python:

"""
Common utilities for AWS Kconfig generation scripts.

This module provides shared functionality used by gen_kconfig_location,
gen_kconfig_instance, and gen_kconfig_ami scripts to avoid code duplication.
"""

import os
import sys
from configparser import ConfigParser

from jinja2 import Environment, FileSystemLoader

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class AwsNotConfiguredError(Exception):
    """Raised when AWS credentials are not available."""

    pass


def get_default_region():
    """
    Get the default AWS region from the ~/.aws/config file.

    Returns:
        str: Default region, or 'us-east-1' if no default is found.
    """
    config_path = os.path.expanduser("~/.aws/config")
    if os.path.exists(config_path):
        try:
            config = ConfigParser()
            config.read(config_path)
            if "default" in config:
                return config["default"].get("region", "us-east-1")
            if "profile default" in config:
                return config["profile default"].get("region", "us-east-1")
        except Exception as e:
            print(f"Warning: Error reading AWS config file: {e}", file=sys.stderr)
    return "us-east-1"


def get_jinja2_environment(template_path=None):
    """
    Create a standardized Jinja2 environment for template rendering.

    Args:
        template_path (str): Path to template directory. If None, uses caller's directory.

    Returns:
        Environment: Configured Jinja2 Environment object
    """
    if template_path is None:
        template_path = sys.path[0]

    return Environment(
        loader=FileSystemLoader(template_path),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def create_ec2_client(region=None):
    """
    Create a boto3 EC2 client with optional region override.

    Args:
        region (str): Optional region to use instead of default

    Returns:
        boto3.client: Configured EC2 client

    Raises:
        NoCredentialsError: If AWS credentials are not found
        ClientError: For AWS API errors
    """
    if region is None:
        region = get_default_region()

    return boto3.client("ec2", region_name=region)


def handle_aws_client_error(e, context="AWS operation", quiet=False):
    """
    Handle AWS ClientError exceptions with consistent error messaging.

    Args:
        e (ClientError): The boto3 ClientError exception
        context (str): Description of what operation failed
        quiet (bool): Suppress error messages

    Returns:
        bool: False (operation failed)
    """
    if not quiet:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_message = e.response.get("Error", {}).get("Message", str(e))

        if error_code in ["UnauthorizedOperation", "InvalidRegion"]:
            print(
                f"Error: Cannot perform {context}. Check region name and permissions.",
                file=sys.stderr,
            )
            print(f"  Details: {error_message}", file=sys.stderr)
        else:
            print(f"AWS API Error during {context}: {error_message}", file=sys.stderr)
            print(f"  Error Code: {error_code}", file=sys.stderr)

    return False


def handle_aws_credentials_error(quiet=False):
    """
    Handle AWS credentials not found error with consistent messaging.

    Args:
        quiet (bool): Suppress error messages

    Returns:
        bool: False (operation failed)
    """
    if not quiet:
        print(
            "Error: AWS credentials not found. Please configure your credentials.",
            file=sys.stderr,
        )
        print("  Run: aws configure", file=sys.stderr)

    return False


def require_aws_credentials():
    """
    Require AWS credentials, raising an exception if not configured.

    This function should be called early in main() to validate AWS
    credentials. If AWS is not configured, it raises AwsNotConfiguredError
    to let the caller decide how to handle it.

    This centralizes the handling of missing AWS credentials and avoids
    TOCTOU race conditions from manual file existence checks.

    Returns:
        dict: Caller identity information if credentials are valid

    Raises:
        AwsNotConfiguredError: If AWS credentials are not found
    """
    try:
        sts = boto3.client("sts")
        return sts.get_caller_identity()
    except NoCredentialsError as e:
        raise AwsNotConfiguredError("AWS credentials not found") from e


def get_all_regions(quiet=False):
    """
    Retrieve the list of all AWS regions.

    Args:
        quiet (bool): Suppress debug messages

    Returns:
        list: Sorted list of dictionaries each containing region information,
              or empty list on error
    """
    try:
        ec2 = create_ec2_client()
        response = ec2.describe_regions(AllRegions=True)

        regions = {}
        for region in response["Regions"]:
            region_name = region["RegionName"]
            regions[region_name] = {
                "region_name": region_name,
                "opt_in_status": region.get("OptInStatus", "Unknown"),
                "end_point": region.get("Endpoint"),
            }

        region_list = sorted(regions.values(), key=lambda x: x["region_name"])

        if not quiet:
            print(f"Found {len(region_list)} AWS regions", file=sys.stderr)

        return region_list

    except NoCredentialsError:
        handle_aws_credentials_error(quiet)
        return []
    except ClientError as e:
        handle_aws_client_error(e, "retrieving AWS regions", quiet)
        return []
    except Exception as e:
        if not quiet:
            print(f"Error retrieving AWS regions: {e}", file=sys.stderr)
        return []


def get_region_availability_zones(region_name, quiet=False):
    """
    Get availability zones for a specific region.

    Args:
        region_name (str): AWS region name (e.g., 'us-east-1')
        quiet (bool): Suppress debug messages

    Returns:
        list: List of availability zone dictionaries, or None on error
    """
    try:
        if not quiet:
            print(
                f"Querying availability zones for region {region_name}...",
                file=sys.stderr,
            )

        ec2 = create_ec2_client(region=region_name)
        response = ec2.describe_availability_zones(
            AllAvailabilityZones=True,
            Filters=[
                {"Name": "region-name", "Values": [region_name]},
                {"Name": "zone-type", "Values": ["availability-zone"]},
            ],
        )

        availability_zones = []
        for zone in response["AvailabilityZones"]:
            zone_info = {
                "zone_id": zone["ZoneId"],
                "zone_name": zone["ZoneName"],
                "zone_type": zone.get("ZoneType", "availability-zone"),
                "state": zone["State"],
            }
            availability_zones.append(zone_info)

        if not quiet:
            print(
                f"Found {len(availability_zones)} availability zones in {region_name}",
                file=sys.stderr,
            )

        return sorted(availability_zones, key=lambda x: x["zone_name"])

    except NoCredentialsError:
        handle_aws_credentials_error(quiet)
        return None
    except ClientError as e:
        handle_aws_client_error(e, f"querying region {region_name}", quiet)
        return None
    except Exception as e:
        if not quiet:
            print(f"Unexpected error: {e}", file=sys.stderr)
        return None


def get_all_instance_types(region, quiet=False):
    """
    Get all available instance types in the specified region.

    Args:
        region (str): AWS region to query
        quiet (bool): Suppress debug messages

    Returns:
        list: List of dictionaries, each containing an instance type,
              or empty list on error
    """
    if not quiet:
        print(f"Fetching list of instance types in region {region}...", file=sys.stderr)

    try:
        ec2 = create_ec2_client(region=region)
        paginator = ec2.get_paginator("describe_instance_types")

        instance_types = []
        for page in paginator.paginate():
            instance_types.extend(page["InstanceTypes"])

        if not quiet:
            print(f"Found {len(instance_types)} instance types", file=sys.stderr)

        return instance_types

    except NoCredentialsError:
        handle_aws_credentials_error(quiet)
        return []
    except ClientError as e:
        handle_aws_client_error(e, "retrieving instance types", quiet)
        return []
    except Exception as e:
        if not quiet:
            print(f"Error retrieving instance types: {e}", file=sys.stderr)
        return []


def get_region_kconfig_name(region_name):
    """
    Convert AWS region name to Kconfig region constant name.

    Args:
        region_name (str): AWS region name (e.g., 'us-east-1', 'eu-west-2')

    Returns:
        str: Kconfig constant name (e.g., 'US_EAST_1', 'EU_WEST_2')
    """
    return region_name.upper().replace("-", "_")

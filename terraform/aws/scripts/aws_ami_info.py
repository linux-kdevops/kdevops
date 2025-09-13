#!/usr/bin/env python3
# SPDX-License-Identifier: MIT

import boto3
import json
import sys
import argparse
import os
import re
from collections import defaultdict
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


def get_known_ami_owners():
    """
    Get dictionary of well-known AMI owners that provide Linux images.

    Returns:
        dict: Dictionary of owner information
    """
    return {
        "amazon": {
            "owner_id": "137112412989",
            "owner_name": "Amazon",
            "description": "Amazon Linux AMIs",
            "search_patterns": [
                r"al2023-ami-.*",  # Amazon Linux 2023
                r"amzn2-ami-.*",  # Amazon Linux 2
                r"amzn-ami-.*",  # Amazon Linux 1
            ],
        },
        "ubuntu": {
            "owner_id": "099720109477",
            "owner_name": "Canonical",
            "description": "Ubuntu AMIs",
            "search_patterns": [
                r"ubuntu/images/.*ubuntu-.*",  # All Ubuntu images
            ],
        },
        "redhat": {
            "owner_id": "309956199498",
            "owner_name": "Red Hat",
            "description": "Red Hat Enterprise Linux AMIs",
            "search_patterns": [
                r"RHEL-.*",  # All RHEL versions
            ],
        },
        "suse": {
            "owner_id": "013907871322",
            "owner_name": "SUSE",
            "description": "SUSE Linux Enterprise AMIs",
            "search_patterns": [
                r"suse-sles-.*",
                r"suse-sle-.*",
            ],
        },
        "debian": {
            "owner_id": "136693071363",
            "owner_name": "Debian",
            "description": "Debian GNU/Linux AMIs",
            "search_patterns": [
                r"debian-.*",
            ],
        },
        "centos": {
            "owner_id": "125523088429",
            "owner_name": "CentOS",
            "description": "CentOS Linux AMIs (Legacy)",
            "search_patterns": [
                r"CentOS.*",
            ],
        },
        "rocky": {
            "owner_id": "792107900819",
            "owner_name": "Rocky Linux",
            "description": "Rocky Linux AMIs",
            "search_patterns": [
                r"Rocky-.*",
            ],
        },
        "almalinux": {
            "owner_id": "764336703387",
            "owner_name": "AlmaLinux",
            "description": "AlmaLinux AMIs",
            "search_patterns": [
                r"AlmaLinux.*",
            ],
        },
        "fedora": {
            "owner_id": "125523088429",
            "owner_name": "Fedora Project",
            "description": "Fedora Linux Cloud AMIs",
            "search_patterns": [
                r"Fedora-Cloud-.*",
                r"Fedora-.*",
            ],
        },
        "oracle": {
            "owner_id": "131827586825",
            "owner_name": "Oracle",
            "description": "Oracle Linux AMIs",
            "search_patterns": [
                r"OL.*-.*",
            ],
        },
    }


def discover_ami_patterns(
    owner_id,
    owner_name,
    search_patterns,
    region="us-east-1",
    quiet=False,
    max_results=1000,
):
    """
    Dynamically discover AMI patterns by scanning available AMIs for an owner.

    Args:
        owner_id (str): AWS owner account ID
        owner_name (str): Human readable owner name
        search_patterns (list): Regex patterns to filter AMI names
        region (str): AWS region to query
        quiet (bool): Suppress debug messages
        max_results (int): Maximum AMIs to scan

    Returns:
        dict: Dictionary of discovered AMI patterns and examples
    """
    try:
        if not quiet:
            print(
                f"Discovering AMI patterns for {owner_name} in {region}...",
                file=sys.stderr,
            )

        ec2_client = boto3.client("ec2", region_name=region)

        # Get all AMIs from this owner
        all_amis = []
        paginator = ec2_client.get_paginator("describe_images")

        for page in paginator.paginate(
            Owners=[owner_id],
            Filters=[
                {"Name": "state", "Values": ["available"]},
                {"Name": "image-type", "Values": ["machine"]},
            ],
        ):
            all_amis.extend(page["Images"])
            if len(all_amis) >= max_results:
                all_amis = all_amis[:max_results]
                break

        if not quiet:
            print(f"Found {len(all_amis)} total AMIs for {owner_name}", file=sys.stderr)

        # Filter AMIs by search patterns
        matching_amis = []
        for ami in all_amis:
            ami_name = ami.get("Name", "")
            for pattern in search_patterns:
                if re.match(pattern, ami_name, re.IGNORECASE):
                    matching_amis.append(ami)
                    break

        if not quiet:
            print(
                f"Found {len(matching_amis)} matching AMIs after pattern filtering",
                file=sys.stderr,
            )

        # Group AMIs by detected patterns
        pattern_groups = defaultdict(list)

        for ami in matching_amis:
            ami_name = ami.get("Name", "")
            group_key = classify_ami_name(ami_name, owner_name)

            ami_info = {
                "ami_id": ami["ImageId"],
                "name": ami_name,
                "description": ami.get("Description", ""),
                "creation_date": ami["CreationDate"],
                "architecture": ami.get("Architecture", "Unknown"),
                "virtualization_type": ami.get("VirtualizationType", "Unknown"),
                "root_device_type": ami.get("RootDeviceType", "Unknown"),
                "platform_details": ami.get("PlatformDetails", "Unknown"),
            }

            pattern_groups[group_key].append(ami_info)

        # Sort each group by creation date (newest first) and generate patterns
        discovered_patterns = {}
        for group_key, amis in pattern_groups.items():
            # Sort by creation date, newest first
            sorted_amis = sorted(amis, key=lambda x: x["creation_date"], reverse=True)

            # Generate Terraform-compatible filter pattern
            terraform_pattern = generate_terraform_pattern(
                group_key, sorted_amis[:5]
            )  # Use top 5 for pattern analysis

            discovered_patterns[group_key] = {
                "display_name": group_key,
                "ami_count": len(sorted_amis),
                "latest_ami": sorted_amis[0] if sorted_amis else None,
                "sample_amis": sorted_amis[:3],  # Show 3 most recent
                "terraform_filter": terraform_pattern,
                "terraform_example": generate_terraform_example(
                    group_key, terraform_pattern, owner_id
                ),
            }

        return discovered_patterns

    except NoCredentialsError:
        print(
            "Error: AWS credentials not found. Please configure your credentials.",
            file=sys.stderr,
        )
        return {}
    except ClientError as e:
        print(f"AWS API Error: {e}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return {}


def classify_ami_name(ami_name, owner_name):
    """
    Classify an AMI name into a logical group for pattern generation.

    Args:
        ami_name (str): AMI name
        owner_name (str): Owner name for context

    Returns:
        str: Classification key
    """
    ami_lower = ami_name.lower()

    # Amazon Linux patterns
    if "al2023" in ami_lower:
        return "Amazon Linux 2023"
    elif "amzn2" in ami_lower:
        return "Amazon Linux 2"
    elif "amzn-ami" in ami_lower:
        return "Amazon Linux 1"

    # Ubuntu patterns
    elif "ubuntu" in ami_lower:
        if "noble" in ami_lower or "24.04" in ami_lower:
            return "Ubuntu 24.04 LTS (Noble)"
        elif "jammy" in ami_lower or "22.04" in ami_lower:
            return "Ubuntu 22.04 LTS (Jammy)"
        elif "focal" in ami_lower or "20.04" in ami_lower:
            return "Ubuntu 20.04 LTS (Focal)"
        elif "bionic" in ami_lower or "18.04" in ami_lower:
            return "Ubuntu 18.04 LTS (Bionic)"
        else:
            # Extract version number if available
            version_match = re.search(r"(\d+\.\d+)", ami_name)
            if version_match:
                return f"Ubuntu {version_match.group(1)}"
            return "Ubuntu (Other)"

    # RHEL patterns
    elif "rhel" in ami_lower:
        if re.search(r"rhel-?10", ami_lower):
            return "RHEL 10"
        elif re.search(r"rhel-?9", ami_lower):
            return "RHEL 9"
        elif re.search(r"rhel-?8", ami_lower):
            return "RHEL 8"
        elif re.search(r"rhel-?7", ami_lower):
            return "RHEL 7"
        else:
            version_match = re.search(r"rhel-?(\d+)", ami_lower)
            if version_match:
                return f"RHEL {version_match.group(1)}"
            return "RHEL (Other)"

    # Rocky Linux patterns
    elif "rocky" in ami_lower:
        version_match = re.search(r"rocky-(\d+)", ami_lower)
        if version_match:
            return f"Rocky Linux {version_match.group(1)}"
        return "Rocky Linux"

    # AlmaLinux patterns
    elif "almalinux" in ami_lower:
        version_match = re.search(r"(\d+)", ami_name)
        if version_match:
            return f"AlmaLinux {version_match.group(1)}"
        return "AlmaLinux"

    # Debian patterns
    elif "debian" in ami_lower:
        if re.search(r"debian-?12", ami_lower) or "bookworm" in ami_lower:
            return "Debian 12 (Bookworm)"
        elif re.search(r"debian-?11", ami_lower) or "bullseye" in ami_lower:
            return "Debian 11 (Bullseye)"
        elif re.search(r"debian-?10", ami_lower) or "buster" in ami_lower:
            return "Debian 10 (Buster)"
        else:
            version_match = re.search(r"debian-?(\d+)", ami_lower)
            if version_match:
                return f"Debian {version_match.group(1)}"
            return "Debian (Other)"

    # SUSE patterns
    elif "suse" in ami_lower or "sles" in ami_lower:
        version_match = re.search(r"(\d+)", ami_name)
        if version_match:
            return f"SUSE Linux Enterprise {version_match.group(1)}"
        return "SUSE Linux Enterprise"

    # CentOS patterns
    elif "centos" in ami_lower:
        version_match = re.search(r"(\d+)", ami_name)
        if version_match:
            return f"CentOS {version_match.group(1)}"
        return "CentOS"

    # Fedora patterns
    elif "fedora" in ami_lower:
        version_match = re.search(r"fedora-.*?(\d+)", ami_lower)
        if version_match:
            return f"Fedora {version_match.group(1)}"
        return "Fedora"

    # Oracle Linux patterns
    elif ami_lower.startswith("ol"):
        version_match = re.search(r"ol(\d+)", ami_lower)
        if version_match:
            return f"Oracle Linux {version_match.group(1)}"
        return "Oracle Linux"

    # Default: use the owner name
    return f"{owner_name} (Other)"


def generate_terraform_pattern(group_key, sample_amis):
    """
    Generate a Terraform-compatible filter pattern from sample AMIs.

    Args:
        group_key (str): Classification key
        sample_amis (list): List of sample AMI info

    Returns:
        str: Terraform filter pattern
    """
    if not sample_amis:
        return ""

    # Analyze common patterns in AMI names
    names = [ami["name"] for ami in sample_amis]

    # Find the longest common prefix and suffix patterns
    if len(names) == 1:
        # Single AMI - create a pattern that matches similar names
        name = names[0]
        # Replace specific dates/versions with wildcards
        pattern = re.sub(r"\d{4}-\d{2}-\d{2}", "*", name)  # Replace dates
        pattern = re.sub(r"-\d+\.\d+\.\d+", "-*", pattern)  # Replace version numbers
        pattern = re.sub(
            r"_\d+\.\d+\.\d+", "_*", pattern
        )  # Replace version numbers with underscores
        return pattern

    # Multiple AMIs - find common pattern
    common_parts = []
    min_len = min(len(name) for name in names)

    # Find common prefix
    prefix_len = 0
    for i in range(min_len):
        chars = set(name[i] for name in names)
        if len(chars) == 1:
            prefix_len = i + 1
        else:
            break

    if prefix_len > 0:
        prefix = names[0][:prefix_len]
        return f"{prefix}*"

    # If no common prefix, try to extract the base pattern
    first_name = names[0]
    # Replace numbers and dates with wildcards
    pattern = re.sub(r"\d{8}", "*", first_name)  # Replace 8-digit dates
    pattern = re.sub(r"\d{4}-\d{2}-\d{2}", "*", pattern)  # Replace ISO dates
    pattern = re.sub(r"-\d+\.\d+\.\d+", "-*", pattern)  # Replace version numbers
    pattern = re.sub(
        r"_\d+\.\d+\.\d+", "_*", pattern
    )  # Replace version numbers with underscores

    return pattern


def generate_terraform_example(group_key, filter_pattern, owner_id):
    """
    Generate a complete Terraform example.

    Args:
        group_key (str): Classification key
        filter_pattern (str): Filter pattern
        owner_id (str): AWS owner account ID

    Returns:
        str: Complete Terraform data source example
    """
    # Create a safe resource name
    resource_name = re.sub(r"[^a-zA-Z0-9_]", "_", group_key.lower())
    resource_name = re.sub(r"_+", "_", resource_name)  # Remove multiple underscores
    resource_name = resource_name.strip("_")  # Remove leading/trailing underscores

    if not filter_pattern:
        filter_pattern = "*"

    terraform_code = f"""data "aws_ami" "{resource_name}" {{
  most_recent = true
  owners      = ["{owner_id}"]
  filter {{
    name   = "name"
    values = ["{filter_pattern}"]
  }}
  filter {{
    name   = "architecture"
    values = ["x86_64"]
  }}
  filter {{
    name   = "virtualization-type"
    values = ["hvm"]
  }}
  filter {{
    name   = "state"
    values = ["available"]
  }}
}}"""

    return terraform_code


def get_owner_ami_info(owner_key, region="us-east-1", quiet=False):
    """
    Get comprehensive AMI information for a specific owner.

    Args:
        owner_key (str): Owner key (e.g., 'amazon', 'ubuntu')
        region (str): AWS region to query
        quiet (bool): Suppress debug messages

    Returns:
        dict: Owner information with discovered AMI patterns
    """
    known_owners = get_known_ami_owners()

    if owner_key not in known_owners:
        return None

    owner_info = known_owners[owner_key].copy()

    # Discover actual AMI patterns
    discovered_patterns = discover_ami_patterns(
        owner_info["owner_id"],
        owner_info["owner_name"],
        owner_info["search_patterns"],
        region,
        quiet,
    )

    owner_info["discovered_patterns"] = discovered_patterns
    owner_info["total_pattern_count"] = len(discovered_patterns)

    return owner_info


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Get AWS AMI owner information and Terraform filter examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python %(prog)s --owners
  python %(prog)s amazon
  python %(prog)s ubuntu --format json
  python %(prog)s --owners --format csv
  python %(prog)s redhat --region eu-west-1
        """,
    )

    parser.add_argument(
        "owner_key",
        nargs="?",  # Make owner_key optional when using --owners
        help="AMI owner key (e.g., amazon, ubuntu, redhat, debian, suse, centos, rocky, almalinux)",
    )

    parser.add_argument(
        "--region", "-r", help="AWS region (default: from ~/.aws/config or us-east-1)"
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=["table", "json", "csv", "terraform"],
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
        "--owners", action="store_true", help="List all known AMI owners"
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=1000,
        help="Maximum number of AMIs to scan per owner (default: 1000)",
    )

    return parser.parse_args()


def output_owners_table(owners, quiet=False):
    """Output AMI owners in table format."""
    if not quiet:
        print(f"Known Linux AMI owners ({len(owners)}):\n")

    # Print header
    print(f"{'Owner Key':<12} {'Owner Name':<15} {'Owner ID':<15} {'Description':<30}")
    print("-" * 75)

    # Sort owners by key
    for owner_key in sorted(owners.keys()):
        owner = owners[owner_key]
        print(
            f"{owner_key:<12} "
            f"{owner['owner_name']:<15} "
            f"{owner['owner_id']:<15} "
            f"{owner['description']:<30}"
        )


def output_owners_json(owners):
    """Output owners in JSON format."""
    print(json.dumps(owners, indent=2))


def output_owners_csv(owners):
    """Output owners in CSV format."""
    print("owner_key,owner_name,owner_id,description")

    for owner_key in sorted(owners.keys()):
        owner = owners[owner_key]
        description = owner["description"].replace(",", ";")  # Avoid CSV issues
        print(f"{owner_key},{owner['owner_name']},{owner['owner_id']},{description}")


def output_owner_table(owner_info, quiet=False):
    """Output owner AMI information in table format."""
    if not quiet:
        print(
            f"AMI Information for {owner_info['owner_name']} (Owner ID: {owner_info['owner_id']})"
        )
        print(f"Description: {owner_info['description']}")
        print(f"Found {owner_info['total_pattern_count']} AMI pattern groups\n")

    if not owner_info["discovered_patterns"]:
        print("No AMI patterns discovered for this owner in the specified region.")
        return

    for pattern_name, pattern_info in sorted(owner_info["discovered_patterns"].items()):
        print(f"Pattern: {pattern_name}")
        print(f"  AMI Count: {pattern_info['ami_count']}")
        print(f"  Filter Pattern: {pattern_info['terraform_filter']}")

        # Show latest AMI
        if pattern_info["latest_ami"]:
            latest = pattern_info["latest_ami"]
            print(f"  Latest AMI: {latest['ami_id']} ({latest['creation_date'][:10]})")
            print(f"  Architecture: {latest['architecture']}")

        # Show sample AMIs
        if pattern_info["sample_amis"]:
            print(f"  Sample AMIs:")
            for ami in pattern_info["sample_amis"]:
                print(
                    f"    {ami['ami_id']} - {ami['name'][:60]}{'...' if len(ami['name']) > 60 else ''}"
                )
                print(
                    f"      Created: {ami['creation_date'][:10]} | Arch: {ami['architecture']} | Virt: {ami['virtualization_type']}"
                )

        print()  # Empty line between patterns


def output_owner_json(owner_info):
    """Output owner information in JSON format."""

    # Convert datetime objects to strings for JSON serialization
    def json_serializer(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        return str(obj)

    print(json.dumps(owner_info, indent=2, default=json_serializer))


def output_owner_csv(owner_info):
    """Output owner information in CSV format."""
    print(
        "pattern_name,ami_count,filter_pattern,latest_ami_id,latest_ami_name,creation_date,architecture"
    )

    for pattern_name, pattern_info in sorted(owner_info["discovered_patterns"].items()):
        latest = pattern_info.get("latest_ami", {})
        ami_id = latest.get("ami_id", "")
        ami_name = latest.get("name", "").replace(",", ";")  # Avoid CSV issues
        creation_date = (
            latest.get("creation_date", "")[:10] if latest.get("creation_date") else ""
        )
        architecture = latest.get("architecture", "")

        print(
            f"{pattern_name},{pattern_info['ami_count']},{pattern_info['terraform_filter']},{ami_id},{ami_name},{creation_date},{architecture}"
        )


def output_owner_terraform(owner_info):
    """Output owner information as Terraform examples."""
    print(f"# Terraform aws_ami data source examples for {owner_info['owner_name']}")
    print(f"# Owner ID: {owner_info['owner_id']}")
    print(f"# {owner_info['description']}")
    print(f"# Found {owner_info['total_pattern_count']} AMI pattern groups")
    print()

    for pattern_name, pattern_info in sorted(owner_info["discovered_patterns"].items()):
        print(f"# {pattern_name} ({pattern_info['ami_count']} AMIs available)")
        if pattern_info["latest_ami"]:
            print(
                f"# Latest: {pattern_info['latest_ami']['ami_id']} ({pattern_info['latest_ami']['creation_date'][:10]})"
            )
        print(pattern_info["terraform_example"])
        print()


def main():
    """Main function to run the program."""
    args = parse_arguments()

    # Determine region
    if args.region:
        region = args.region
    else:
        region = get_aws_default_region()

    # Handle --owners option
    if args.owners:
        owners = get_known_ami_owners()
        if args.format == "json":
            output_owners_json(owners)
        elif args.format == "csv":
            output_owners_csv(owners)
        else:  # table format (terraform not applicable for owners list)
            output_owners_table(owners, args.quiet)
        return

    # Require owner_key if not using --owners
    if not args.owner_key:
        print(
            "Error: owner_key is required unless using --owners option", file=sys.stderr
        )
        print("Use --owners to list all available AMI owners", file=sys.stderr)
        sys.exit(1)

    # Validate owner key
    known_owners = get_known_ami_owners()
    if args.owner_key not in known_owners:
        print(f"Error: Unknown owner key '{args.owner_key}'", file=sys.stderr)
        print(
            f"Available owners: {', '.join(sorted(known_owners.keys()))}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not args.quiet:
        print(
            f"Discovering AMI patterns for {args.owner_key} in {region}...",
            file=sys.stderr,
        )
        print(f"This may take a moment as we scan available AMIs...", file=sys.stderr)

    # Get owner information with dynamic discovery
    owner_info = get_owner_ami_info(
        args.owner_key, region, args.quiet or not args.debug
    )

    if not owner_info:
        print(
            f"Could not retrieve AMI information for owner '{args.owner_key}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    if not owner_info.get("discovered_patterns"):
        print(
            f"No AMI patterns discovered for owner '{args.owner_key}' in region {region}.",
            file=sys.stderr,
        )
        print(
            "This may be because the owner has no AMIs in this region or the search patterns need adjustment.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Output results in specified format
    if args.format == "json":
        output_owner_json(owner_info)
    elif args.format == "csv":
        output_owner_csv(owner_info)
    elif args.format == "terraform":
        output_owner_terraform(owner_info)
    else:  # table format
        output_owner_table(owner_info, args.quiet)


if __name__ == "__main__":
    main()

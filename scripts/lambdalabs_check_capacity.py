#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
"""
Check Lambda Labs instance availability across all regions.

This script queries the Lambda Labs API to find where specific instance types
are available, helping users avoid provisioning failures.
"""

import argparse
import json
import os
import sys

# Import our Lambda Labs API module
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from lambdalabs_api import get_api_key, get_instance_types_with_capacity


def _build_region_map(gpu_instances):
    """Build a mapping from regions to available instance types."""
    region_map = {}
    for inst_type, regions in gpu_instances.items():
        for region in regions:
            if region not in region_map:
                region_map[region] = []
            region_map[region].append(inst_type)
    return region_map


def check_availability(instance_type=None, json_output=False, pick_first=False):
    """Check instance availability across all regions."""
    api_key = get_api_key()
    if not api_key:
        sys.stderr.write("Error: Lambda Labs API key not found\n")
        sys.stderr.write("Set LAMBDALABS_API_KEY or create ~/.lambdalabs/credentials\n")
        return 1

    try:
        _, capacity_map = get_instance_types_with_capacity(api_key)
    except Exception as e:
        sys.stderr.write(f"Error: Failed to fetch instance availability: {e}\n")
        return 1

    if not capacity_map:
        sys.stderr.write("Error: Could not fetch instance availability\n")
        return 1

    if instance_type:
        # Check specific instance type
        regions = capacity_map.get(instance_type, [])
        if pick_first:
            if regions:
                print(regions[0])
                return 0
            return 1

        if json_output:
            result = [{"instance_type": instance_type, "regions": regions}]
            print(json.dumps(result, indent=2))
        else:
            if regions:
                print(f"{instance_type}:")
                for region in regions:
                    print(f"  • {region}")
            else:
                print(f"{instance_type}: No capacity available")
        return 0 if regions else 1
    else:
        # Show all GPU instances with capacity
        results = []
        gpu_instances = {
            k: v for k, v in capacity_map.items() if k.startswith("gpu_") and v
        }

        if json_output:
            # Format for tier selection script compatibility
            # Group by region for consistency with DataCrunch format
            region_map = _build_region_map(gpu_instances)

            results = [
                {"location": region, "instances": instances}
                for region, instances in sorted(region_map.items())
            ]
            print(json.dumps(results, indent=2))
        else:
            print("GPU Instance Availability:\n")

            # Group by region
            region_map = _build_region_map(gpu_instances)

            for region in sorted(region_map.keys()):
                print(f"📍 {region}:")
                for inst in sorted(region_map[region]):
                    print(f"  • {inst}")
                print()

            if not region_map:
                print("No GPU instances currently available")

        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Check Lambda Labs instance availability"
    )
    parser.add_argument(
        "--instance-type",
        "-i",
        help="Check specific instance type (e.g., gpu_1x_h100_sxm5)",
    )
    parser.add_argument(
        "--json", "-j", action="store_true", help="Output in JSON format"
    )
    parser.add_argument(
        "--pick-first",
        action="store_true",
        help="Return first available region (for scripts)",
    )

    args = parser.parse_args()
    sys.exit(check_availability(args.instance_type, args.json, args.pick_first))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
DataCrunch GPU tier-based instance selection.

This script implements a tiered fallback system for selecting GPU instances
based on availability. Users can specify a maximum tier (e.g., "h100" or "b300")
and the script will try to provision the highest tier available, falling back
to lower tiers if necessary.
"""

import argparse
import json
import os
import subprocess
import sys
from typing import List, Dict, Optional

# Get the directory containing this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAPACITY_CHECKER = os.path.join(SCRIPT_DIR, "datacrunch_check_capacity.py")


# GPU tier definitions from highest to lowest performance
GPU_TIERS = {
    "b300": [
        "1B300.30V",  # Single NVIDIA Blackwell B300
    ],
    "b200": [
        "1B200.30V",  # Single NVIDIA Blackwell B200
    ],
    "h100": [
        "1H100.80S.30V",  # Single H100 80GB - 30 vCPU variant
        "1H100.80S.32V",  # Single H100 80GB - 32 vCPU variant
    ],
    "a100-80": [
        "1A100.80S.22V",  # Single A100 80GB SXM
    ],
    "a100-40": [
        "1A100.40S.22V",  # Single A100 40GB SXM
    ],
    "rtx-pro-6000": [
        "1RTXPRO6000.30V",  # NVIDIA RTX PRO 6000 Ada
    ],
    "rtx-6000-ada": [
        "1RTX6000ADA.10V",  # NVIDIA RTX 6000 Ada Generation
    ],
    "l40s": [
        "1L40S.20V",  # NVIDIA L40S
    ],
    "a6000": [
        "1A6000.10V",  # NVIDIA RTX A6000
    ],
    "v100": [
        "1V100.6V",  # Tesla V100 (cheapest fallback)
    ],
}

# Tier ordering from highest to lowest
TIER_ORDER = [
    "b300",
    "b200",
    "h100",
    "a100-80",
    "a100-40",
    "rtx-pro-6000",
    "rtx-6000-ada",
    "l40s",
    "a6000",
    "v100",
]

# Pre-defined tier groups for common use cases
TIER_GROUPS = {
    "b300-or-less": TIER_ORDER[TIER_ORDER.index("b300") :],
    "b200-or-less": TIER_ORDER[TIER_ORDER.index("b200") :],
    "h100-or-less": TIER_ORDER[TIER_ORDER.index("h100") :],
    "a100-80-or-less": TIER_ORDER[TIER_ORDER.index("a100-80") :],
    "a100-40-or-less": TIER_ORDER[TIER_ORDER.index("a100-40") :],
}


def get_all_available_capacity(on_demand: bool = False) -> Dict[str, List[str]]:
    """
    Get all available GPU capacity across all regions.

    Args:
        on_demand: If True, check on-demand/dynamic pricing availability instead of spot

    Returns:
        Dictionary mapping location to list of available instance types
        Example: {"FIN-02": ["1H100.80S.30V", "1H100.80S.32V"], "ICE-01": ["1H100.80S.32V"]}
    """
    try:
        cmd = [CAPACITY_CHECKER, "--json"]
        if on_demand:
            cmd.append("--on-demand")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            return {}

        data = json.loads(result.stdout)

        # Convert from list of dicts to location -> instance types mapping
        capacity_map = {}
        for location_data in data:
            location = location_data.get("location")
            instances = location_data.get("instances", [])
            if location and instances:
                capacity_map[location] = instances

        return capacity_map

    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
        return {}


def check_instance_availability(
    instance_type: str, capacity_map: Dict[str, List[str]]
) -> Optional[str]:
    """
    Check if a specific instance type has available capacity in any region.

    Args:
        instance_type: The instance type to check (e.g., "1H100.80S.30V")
        capacity_map: Dictionary mapping locations to available instance types

    Returns:
        The location where the instance is available, or None if not available
    """
    for location, instances in capacity_map.items():
        if instance_type in instances:
            return location
    return None


def check_instance_on_demand(instance_type: str) -> Optional[str]:
    """
    Check if a specific instance type is available for on-demand deployment.

    Args:
        instance_type: The instance type to check (e.g., "1A100.40S.22V")

    Returns:
        The location where the instance can be deployed, or None if not available
    """
    try:
        result = subprocess.run(
            [
                CAPACITY_CHECKER,
                "--instance-type",
                instance_type,
                "--on-demand",
                "--pick-first",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def select_instance_from_tiers(
    tier_group: str, verbose: bool = False, on_demand: bool = False
) -> Optional[Dict[str, str]]:
    """
    Select the highest-tier available instance from a tier group.

    Args:
        tier_group: The tier group name (e.g., "h100-or-less")
        verbose: If True, print detailed selection process
        on_demand: If True, check on-demand/dynamic pricing availability instead of spot

    Returns:
        Dictionary with 'instance_type' and 'location' keys, or None if no instances are available
        Example: {"instance_type": "1H100.80S.30V", "location": "FIN-02"}
    """
    if tier_group not in TIER_GROUPS:
        if verbose:
            print(f"Error: Unknown tier group '{tier_group}'", file=sys.stderr)
            print(
                f"Available tier groups: {', '.join(TIER_GROUPS.keys())}",
                file=sys.stderr,
            )
        return None

    # Get all available spot capacity across all regions once
    capacity_map = get_all_available_capacity(on_demand)

    if verbose and capacity_map:
        print("Available capacity across all regions:", file=sys.stderr)
        for location, instances in sorted(capacity_map.items()):
            print(f"  {location}: {', '.join(sorted(instances))}", file=sys.stderr)
        print("", file=sys.stderr)

    tiers_to_check = TIER_GROUPS[tier_group]

    if verbose:
        print(f"Checking tier group: {tier_group}", file=sys.stderr)
        print(
            f"Tiers to check (highest to lowest): {', '.join(tiers_to_check)}",
            file=sys.stderr,
        )
        print("", file=sys.stderr)

    for tier in tiers_to_check:
        if tier not in GPU_TIERS:
            continue

        instance_types = GPU_TIERS[tier]

        if verbose:
            print(
                f"Checking tier '{tier}': {', '.join(instance_types)}", file=sys.stderr
            )

        for instance_type in instance_types:
            if verbose:
                print(f"  Checking {instance_type}...", end=" ", file=sys.stderr)

            # First check spot availability
            location = check_instance_availability(instance_type, capacity_map)
            if location:
                if verbose:
                    print(f"✓ AVAILABLE (spot) in {location}", file=sys.stderr)
                    print("", file=sys.stderr)
                    print(
                        f"Selected: {instance_type} in {location} (tier: {tier}, spot)",
                        file=sys.stderr,
                    )
                return {"instance_type": instance_type, "location": location}

            # If not available as spot, check on-demand
            if (
                not on_demand
            ):  # Only check on-demand if not already explicitly checking it
                location = check_instance_on_demand(instance_type)
                if location:
                    if verbose:
                        print(f"✓ AVAILABLE (on-demand) in {location}", file=sys.stderr)
                        print("", file=sys.stderr)
                        print(
                            f"Selected: {instance_type} in {location} (tier: {tier}, on-demand)",
                            file=sys.stderr,
                        )
                    return {"instance_type": instance_type, "location": location}

            if verbose:
                print("✗ not available in any region", file=sys.stderr)

        if verbose:
            print("", file=sys.stderr)

    if verbose:
        print(
            "Error: No instances available in any tier across all regions",
            file=sys.stderr,
        )

    return None


def list_tier_groups():
    """Print available tier groups and their contents."""
    print("Available tier groups:")
    print("")

    for group_name, tiers in TIER_GROUPS.items():
        print(f"{group_name}:")
        for tier in tiers:
            instance_types = GPU_TIERS.get(tier, [])
            print(f"  - {tier}: {', '.join(instance_types)}")
        print("")


def main():
    parser = argparse.ArgumentParser(
        description="Select DataCrunch GPU instance using tier-based fallback",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Select best available up to H100
  %(prog)s h100-or-less

  # Select best available up to B300
  %(prog)s b300-or-less

  # List all tier groups
  %(prog)s --list-tiers

  # Verbose mode to see selection process
  %(prog)s h100-or-less --verbose
""",
    )

    parser.add_argument(
        "tier_group",
        nargs="?",
        help="Tier group to select from (e.g., h100-or-less, b300-or-less)",
    )

    parser.add_argument(
        "--list-tiers",
        action="store_true",
        help="List all available tier groups and exit",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Print detailed selection process"
    )

    parser.add_argument(
        "--on-demand",
        "-d",
        action="store_true",
        help="Check on-demand/dynamic pricing availability instead of spot instances",
    )

    args = parser.parse_args()

    if args.list_tiers:
        list_tier_groups()
        return 0

    if not args.tier_group:
        parser.print_help()
        return 1

    result = select_instance_from_tiers(args.tier_group, args.verbose, args.on_demand)

    if result:
        # Output format: instance_type location
        print(f"{result['instance_type']} {result['location']}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())

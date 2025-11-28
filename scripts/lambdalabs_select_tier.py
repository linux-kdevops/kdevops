#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
"""
Lambda Labs GPU tier-based instance selection.

This script implements a tiered fallback system for selecting GPU instances
based on availability. Users can specify a maximum tier (e.g., "h100" or "gh200")
and the script will try to provision the highest tier available, falling back
to lower tiers if necessary.
"""

import argparse
import json
import os
import sys
from typing import Dict, List, Optional

# Import our Lambda Labs API module
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from lambdalabs_api import get_api_key, get_instance_types_with_capacity


# GPU tier definitions for single GPU instances (highest to lowest performance)
GPU_TIERS_1X = {
    "gh200": [
        "gpu_1x_gh200",  # NVIDIA GH200 Grace Hopper Superchip
    ],
    "h100-sxm": [
        "gpu_1x_h100_sxm5",  # H100 SXM5 (highest bandwidth)
    ],
    "h100-pcie": [
        "gpu_1x_h100_pcie",  # H100 PCIe
    ],
    "a100-sxm": [
        "gpu_1x_a100_sxm4",  # A100 SXM4
    ],
    "a100": [
        "gpu_1x_a100",  # A100 (PCIe variant)
    ],
    "a6000": [
        "gpu_1x_a6000",  # RTX A6000
    ],
    "rtx6000": [
        "gpu_1x_rtx6000",  # RTX 6000
    ],
    "a10": [
        "gpu_1x_a10",  # A10 (budget option)
    ],
}

# Tier ordering for single GPU (highest to lowest)
TIER_ORDER_1X = [
    "gh200",
    "h100-sxm",
    "h100-pcie",
    "a100-sxm",
    "a100",
    "a6000",
    "rtx6000",
    "a10",
]

# GPU tier definitions for 8x GPU instances
GPU_TIERS_8X = {
    "b200": [
        "gpu_8x_b200_sxm6",  # 8x B200 (Blackwell)
    ],
    "h100": [
        "gpu_8x_h100_sxm5",  # 8x H100 SXM5
    ],
    "a100-80": [
        "gpu_8x_a100_80gb_sxm4",  # 8x A100 80GB
    ],
    "a100": [
        "gpu_8x_a100",  # 8x A100
    ],
    "v100": [
        "gpu_8x_v100",  # 8x V100 (legacy)
    ],
}

TIER_ORDER_8X = [
    "b200",
    "h100",
    "a100-80",
    "a100",
    "v100",
]

# Pre-defined tier groups for single GPU
TIER_GROUPS_1X = {
    "gh200-or-less": TIER_ORDER_1X[TIER_ORDER_1X.index("gh200") :],
    "h100-or-less": TIER_ORDER_1X[TIER_ORDER_1X.index("h100-sxm") :],
    "a100-or-less": TIER_ORDER_1X[TIER_ORDER_1X.index("a100-sxm") :],
    "a6000-or-less": TIER_ORDER_1X[TIER_ORDER_1X.index("a6000") :],
}

# Pre-defined tier groups for 8x GPU
TIER_GROUPS_8X = {
    "8x-b200-or-less": TIER_ORDER_8X[TIER_ORDER_8X.index("b200") :],
    "8x-h100-or-less": TIER_ORDER_8X[TIER_ORDER_8X.index("h100") :],
    "8x-a100-or-less": TIER_ORDER_8X[TIER_ORDER_8X.index("a100-80") :],
}

# Combined tier groups
TIER_GROUPS = {**TIER_GROUPS_1X, **TIER_GROUPS_8X}


def get_capacity_map(api_key: str) -> Dict[str, List[str]]:
    """
    Get GPU instance capacity map.

    Returns:
        Dictionary mapping instance_type to list of available regions
        Example: {"gpu_1x_h100_sxm5": ["us-west-1", "us-east-1"]}
    """
    _, capacity_map = get_instance_types_with_capacity(api_key)
    return capacity_map


def check_instance_availability(
    instance_type: str, capacity_map: Dict[str, List[str]]
) -> Optional[str]:
    """
    Check if a specific instance type has available capacity in any region.

    Returns:
        The region where the instance is available, or None if not available
    """
    regions = capacity_map.get(instance_type, [])
    return regions[0] if regions else None


def select_instance_from_tiers(
    tier_group: str, verbose: bool = False
) -> Optional[Dict[str, str]]:
    """
    Select the highest-tier available instance from a tier group.

    Returns:
        Dictionary with 'instance_type' and 'region' keys, or None if unavailable
        Example: {"instance_type": "gpu_1x_h100_sxm5", "region": "us-west-1"}
    """
    if tier_group not in TIER_GROUPS:
        if verbose:
            print(f"Error: Unknown tier group '{tier_group}'", file=sys.stderr)
            print(
                f"Available tier groups: {', '.join(sorted(TIER_GROUPS.keys()))}",
                file=sys.stderr,
            )
        return None

    api_key = get_api_key()
    if not api_key:
        if verbose:
            print("Error: Lambda Labs API key not found", file=sys.stderr)
        return None

    capacity_map = get_capacity_map(api_key)

    if verbose and capacity_map:
        gpu_capacity = {
            k: v for k, v in capacity_map.items() if v and k.startswith("gpu_")
        }
        if gpu_capacity:
            print("Available GPU capacity:", file=sys.stderr)
            for inst_type, regions in sorted(gpu_capacity.items()):
                print(f"  {inst_type}: {', '.join(regions)}", file=sys.stderr)
            print("", file=sys.stderr)

    tiers_to_check = TIER_GROUPS[tier_group]

    # Determine which GPU_TIERS dict to use
    is_8x = tier_group.startswith("8x-")
    gpu_tiers = GPU_TIERS_8X if is_8x else GPU_TIERS_1X

    if verbose:
        print(f"Checking tier group: {tier_group}", file=sys.stderr)
        print(
            f"Tiers to check (highest to lowest): {', '.join(tiers_to_check)}",
            file=sys.stderr,
        )
        print("", file=sys.stderr)

    for tier in tiers_to_check:
        if tier not in gpu_tiers:
            continue

        instance_types = gpu_tiers[tier]

        if verbose:
            print(
                f"Checking tier '{tier}': {', '.join(instance_types)}", file=sys.stderr
            )

        for instance_type in instance_types:
            if verbose:
                print(f"  Checking {instance_type}...", end=" ", file=sys.stderr)

            region = check_instance_availability(instance_type, capacity_map)
            if region:
                if verbose:
                    print(f"✓ AVAILABLE in {region}", file=sys.stderr)
                    print("", file=sys.stderr)
                    print(
                        f"Selected: {instance_type} in {region} (tier: {tier})",
                        file=sys.stderr,
                    )
                return {"instance_type": instance_type, "region": region}

            if verbose:
                print("✗ not available", file=sys.stderr)

        if verbose:
            print("", file=sys.stderr)

    if verbose:
        print(
            "Error: No instances available in any tier",
            file=sys.stderr,
        )

    return None


def list_tier_groups():
    """Print available tier groups and their contents."""
    print("Available tier groups:\n")

    print("Single GPU (1x) tiers:")
    for group_name in sorted(TIER_GROUPS_1X.keys()):
        tiers = TIER_GROUPS_1X[group_name]
        print(f"  {group_name}:")
        for tier in tiers:
            instance_types = GPU_TIERS_1X.get(tier, [])
            print(f"    - {tier}: {', '.join(instance_types)}")
    print("")

    print("Multi-GPU (8x) tiers:")
    for group_name in sorted(TIER_GROUPS_8X.keys()):
        tiers = TIER_GROUPS_8X[group_name]
        print(f"  {group_name}:")
        for tier in tiers:
            instance_types = GPU_TIERS_8X.get(tier, [])
            print(f"    - {tier}: {', '.join(instance_types)}")


def main():
    parser = argparse.ArgumentParser(
        description="Select Lambda Labs GPU instance using tier-based fallback",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Select best available single GPU up to H100
  %(prog)s h100-or-less

  # Select best available single GPU up to GH200
  %(prog)s gh200-or-less

  # Select best available 8x GPU up to H100
  %(prog)s 8x-h100-or-less

  # List all tier groups
  %(prog)s --list-tiers

  # Verbose mode to see selection process
  %(prog)s h100-or-less --verbose
""",
    )

    parser.add_argument(
        "tier_group",
        nargs="?",
        help="Tier group to select from (e.g., h100-or-less, gh200-or-less)",
    )

    parser.add_argument(
        "--list-tiers",
        action="store_true",
        help="List all available tier groups and exit",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print detailed selection process",
    )

    args = parser.parse_args()

    if args.list_tiers:
        list_tier_groups()
        return 0

    if not args.tier_group:
        parser.print_help()
        return 1

    result = select_instance_from_tiers(args.tier_group, args.verbose)

    if result:
        # Output format: instance_type region
        print(f"{result['instance_type']} {result['region']}")
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())

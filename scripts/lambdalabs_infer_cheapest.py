#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Find the cheapest available Lambda Labs instance type.
"""

import json
import sys
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Tuple

# Import our credentials module
sys.path.insert(0, sys.path[0])
from lambdalabs_credentials import get_api_key

LAMBDALABS_API_BASE = "https://cloud.lambdalabs.com/api/v1"

# Known pricing for Lambda Labs instances (per hour)
INSTANCE_PRICING = {
    "gpu_1x_rtx6000": 0.50,
    "gpu_1x_a10": 0.75,
    "gpu_1x_a6000": 0.80,
    "gpu_1x_a100": 1.29,
    "gpu_1x_a100_sxm4": 1.29,
    "gpu_1x_a100_pcie": 1.29,
    "gpu_1x_gh200": 1.49,
    "gpu_1x_h100_pcie": 2.49,
    "gpu_1x_h100_sxm5": 3.29,
    "gpu_2x_a100": 2.58,
    "gpu_2x_a100_pcie": 2.58,
    "gpu_2x_a6000": 1.60,
    "gpu_2x_h100_sxm5": 6.38,
    "gpu_4x_a100": 5.16,
    "gpu_4x_a100_pcie": 5.16,
    "gpu_4x_a6000": 3.20,
    "gpu_4x_h100_sxm5": 12.36,
    "gpu_8x_v100": 4.40,
    "gpu_8x_a100": 10.32,
    "gpu_8x_a100_40gb": 10.32,
    "gpu_8x_a100_80gb": 14.32,
    "gpu_8x_a100_80gb_sxm4": 14.32,
    "gpu_8x_h100_sxm5": 23.92,
    "gpu_8x_b200_sxm6": 39.92,
}


def get_cheapest_available_instance() -> Optional[str]:
    """
    Find the cheapest instance type with available capacity.

    Returns:
        Instance type name of cheapest available option
    """
    api_key = get_api_key()
    if not api_key:
        # Return a reasonable default if no API key
        return "gpu_1x_a10"

    headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "kdevops/1.0"}
    url = f"{LAMBDALABS_API_BASE}/instance-types"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

            if "data" not in data:
                return "gpu_1x_a10"

            # Find all instance types with available capacity
            available_instances = []

            for instance_type, info in data["data"].items():
                regions_with_capacity = info.get("regions_with_capacity_available", [])
                if regions_with_capacity:
                    # This instance has capacity somewhere
                    price = INSTANCE_PRICING.get(instance_type, 999.99)
                    available_instances.append((instance_type, price))

            if not available_instances:
                # No capacity anywhere, return cheapest known instance
                return "gpu_1x_a10"

            # Sort by price (lowest first)
            available_instances.sort(key=lambda x: x[1])

            # Return the cheapest available instance type
            return available_instances[0][0]

    except Exception as e:
        # On any error, return default
        return "gpu_1x_a10"


def main():
    """Main function for command-line usage."""
    instance = get_cheapest_available_instance()
    if instance:
        print(instance)
    else:
        print("gpu_1x_a10")


if __name__ == "__main__":
    main()

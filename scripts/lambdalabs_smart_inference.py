#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Smart inference for Lambda Labs - finds cheapest instance preferring closer regions.
Algorithm:
1. Determine user's location from public IP
2. Find all available instance/region combinations
3. Group by price tier (instances with same price)
4. For each price tier, select the closest region
5. Return the cheapest tier's best region/instance combo
"""

import json
import sys
import urllib.request
import urllib.error
from typing import Optional, List, Dict, Tuple
import math

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

# Approximate region locations (latitude, longitude)
REGION_LOCATIONS = {
    "us-east-1": (39.0458, -77.6413),  # Virginia
    "us-west-1": (37.3541, -121.9552),  # California (San Jose)
    "us-west-2": (45.5152, -122.6784),  # Oregon
    "us-west-3": (33.4484, -112.0740),  # Arizona
    "us-tx-1": (30.2672, -97.7431),  # Texas (Austin)
    "us-midwest-1": (41.8781, -87.6298),  # Illinois (Chicago)
    "us-south-1": (33.7490, -84.3880),  # Georgia (Atlanta)
    "us-south-2": (29.7604, -95.3698),  # Texas (Houston)
    "us-south-3": (25.7617, -80.1918),  # Florida (Miami)
    "europe-central-1": (50.1109, 8.6821),  # Frankfurt
    "asia-northeast-1": (35.6762, 139.6503),  # Tokyo
    "asia-south-1": (19.0760, 72.8777),  # Mumbai
    "me-west-1": (25.2048, 55.2708),  # Dubai
    "australia-east-1": (-33.8688, 151.2093),  # Sydney
}


def get_user_location() -> Tuple[float, float]:
    """
    Get user's approximate location from public IP.
    Returns (latitude, longitude) tuple.
    """
    try:
        # Try to get location from IP
        with urllib.request.urlopen("http://ip-api.com/json/", timeout=2) as response:
            data = json.loads(response.read().decode())
            if data.get("status") == "success":
                return (data.get("lat", 39.0458), data.get("lon", -77.6413))
    except:
        pass

    # Default to US East Coast if can't determine
    return (39.0458, -77.6413)


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate approximate distance between two points using Haversine formula.
    Returns distance in kilometers.
    """
    R = 6371  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def get_best_instance_and_region() -> Tuple[str, str]:
    """
    Find the cheapest available instance, preferring closer regions when same price.

    Returns:
        (instance_type, region) tuple
    """
    api_key = get_api_key()
    if not api_key:
        # Return defaults if no API key
        return ("gpu_1x_a10", "us-west-1")

    # Get user's location
    user_lat, user_lon = get_user_location()

    headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "kdevops/1.0"}
    url = f"{LAMBDALABS_API_BASE}/instance-types"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

            if "data" not in data:
                return ("gpu_1x_a10", "us-west-1")

            # Build a map of price -> list of (instance, region, distance) tuples
            price_tiers = {}

            for instance_type, info in data["data"].items():
                regions_with_capacity = info.get("regions_with_capacity_available", [])
                if regions_with_capacity:
                    price = INSTANCE_PRICING.get(instance_type, 999.99)

                    for region_info in regions_with_capacity:
                        region = region_info.get("name")
                        if region and region in REGION_LOCATIONS:
                            region_lat, region_lon = REGION_LOCATIONS[region]
                            distance = calculate_distance(
                                user_lat, user_lon, region_lat, region_lon
                            )

                            if price not in price_tiers:
                                price_tiers[price] = []
                            price_tiers[price].append((instance_type, region, distance))

            if not price_tiers:
                # No capacity anywhere
                return ("gpu_1x_a10", "us-west-1")

            # Sort price tiers by price
            sorted_prices = sorted(price_tiers.keys())

            # For the cheapest price tier, find the closest region
            cheapest_price = sorted_prices[0]
            options = price_tiers[cheapest_price]

            # Sort by distance to find closest
            options.sort(key=lambda x: x[2])
            best_instance, best_region, best_distance = options[0]

            return (best_instance, best_region)

    except Exception as e:
        # On any error, return defaults (west for SF user)
        return ("gpu_1x_a10", "us-west-1")


def main():
    """Main function for command-line usage."""
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"

    instance, region = get_best_instance_and_region()

    if mode == "instance":
        print(instance)
    elif mode == "region":
        print(region)
    else:  # both
        print(f"{instance},{region}")


if __name__ == "__main__":
    main()

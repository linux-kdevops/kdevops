#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Check Lambda Labs capacity for a given instance type and region.
Provides clear error messages when capacity is not available.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from typing import Dict, List, Optional

# Import our credentials module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lambdalabs_credentials import get_api_key as get_api_key_from_credentials

LAMBDALABS_API_BASE = "https://cloud.lambdalabs.com/api/v1"


def get_api_key() -> Optional[str]:
    """Get Lambda Labs API key from credentials file or environment variable."""
    return get_api_key_from_credentials()


def check_capacity(instance_type: str, region: str) -> Dict:
    """
    Check if capacity is available for the given instance type and region.

    Returns:
        Dictionary with:
        - available: bool - whether capacity is available
        - message: str - human-readable message
        - alternatives: list - alternative regions with capacity
    """
    api_key = get_api_key()
    if not api_key:
        return {
            "available": False,
            "message": "ERROR: Lambda Labs API key not configured.\n"
            "Please configure your API key using:\n"
            "  python3 scripts/lambdalabs_credentials.py set 'your-api-key'",
            "alternatives": [],
        }

    headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "kdevops/1.0"}
    url = f"{LAMBDALABS_API_BASE}/instance-types"

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

            if "data" not in data:
                return {
                    "available": False,
                    "message": "ERROR: Invalid API response format",
                    "alternatives": [],
                }

            # Check if instance type exists
            if instance_type not in data["data"]:
                available_types = list(data["data"].keys())[:10]
                return {
                    "available": False,
                    "message": f"ERROR: Instance type '{instance_type}' does not exist.\n"
                    f"Available instance types include: {', '.join(available_types)}",
                    "alternatives": [],
                }

            gpu_info = data["data"][instance_type]

            # Check if instance type is generally available
            # Note: is_available can be None, True, or False
            is_available = gpu_info.get("instance_type", {}).get("is_available")
            if is_available is False:  # Only fail if explicitly False, not None
                return {
                    "available": False,
                    "message": f"ERROR: Instance type '{instance_type}' is not currently available from Lambda Labs",
                    "alternatives": [],
                }

            # Get regions with capacity
            regions_with_capacity = gpu_info.get("regions_with_capacity_available", [])
            region_names = [r["name"] for r in regions_with_capacity]

            # Check if requested region has capacity
            if region in region_names:
                return {
                    "available": True,
                    "message": f"✓ Capacity is available for {instance_type} in {region}",
                    "alternatives": region_names,
                }
            else:
                # No capacity in requested region
                if regions_with_capacity:
                    alt_regions = [f"{r['name']}" for r in regions_with_capacity]
                    return {
                        "available": False,
                        "message": f"ERROR: No capacity available for '{instance_type}' in region '{region}'.\n"
                        f"\nRegions with available capacity:\n"
                        + "\n".join([f"  • {r}" for r in alt_regions])
                        + f"\n\nTo fix this issue, either:\n"
                        f"1. Wait for capacity to become available in {region}\n"
                        f"2. Change your region in menuconfig to one of the available regions\n"
                        f"3. Choose a different instance type",
                        "alternatives": region_names,
                    }
                else:
                    return {
                        "available": False,
                        "message": f"ERROR: No capacity available for '{instance_type}' in ANY region.\n"
                        f"This instance type is currently sold out across all Lambda Labs regions.\n"
                        f"Please try:\n"
                        f"  • A different instance type\n"
                        f"  • Checking back later when capacity becomes available",
                        "alternatives": [],
                    }

    except urllib.error.HTTPError as e:
        if e.code == 403:
            return {
                "available": False,
                "message": "ERROR: Lambda Labs API returned 403 Forbidden.\n"
                "This usually means your API key is invalid, expired, or lacks permissions.\n"
                "\n"
                "To fix this:\n"
                "1. Log into https://cloud.lambdalabs.com\n"
                "2. Go to API Keys section\n"
                "3. Create a new API key with full permissions\n"
                "4. Update your credentials:\n"
                '   python3 scripts/lambdalabs_credentials.py set "your-new-api-key"\n'
                "\n"
                "Current API key source: ~/.lambdalabs/credentials",
                "alternatives": [],
            }
        else:
            return {
                "available": False,
                "message": f"ERROR: API request failed with HTTP {e.code}: {e.reason}",
                "alternatives": [],
            }
    except Exception as e:
        return {
            "available": False,
            "message": f"ERROR: Failed to check capacity: {str(e)}",
            "alternatives": [],
        }


def main():
    """Main function for command-line usage."""
    if len(sys.argv) != 3:
        print("Usage: check_lambdalabs_capacity.py <instance_type> <region>")
        print("Example: check_lambdalabs_capacity.py gpu_1x_a10 us-tx-1")
        sys.exit(1)

    instance_type = sys.argv[1]
    region = sys.argv[2]

    result = check_capacity(instance_type, region)

    print(result["message"])

    # Exit with appropriate code
    sys.exit(0 if result["available"] else 1)


if __name__ == "__main__":
    main()

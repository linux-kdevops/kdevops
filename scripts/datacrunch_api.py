#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
DataCrunch API library for kdevops.

Provides low-level API access for DataCrunch cloud services.
Used by datacrunch-cli and other kdevops components.
"""

import json
import os
import socket
import sys
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, List, Optional, Tuple

# Default timeout for API requests in seconds
DEFAULT_TIMEOUT = 30

# Import our credentials module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datacrunch_credentials import (
    get_credentials,
    get_api_key as get_api_key_from_credentials,
)

DATACRUNCH_API_BASE = "https://api.datacrunch.io/v1"

# Cache for OAuth2 access token
_access_token_cache = None


def get_api_key() -> Optional[str]:
    """Get DataCrunch API key (client secret) from credentials file."""
    return get_api_key_from_credentials()


def get_access_token(
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    force_refresh: bool = False,
) -> Optional[str]:
    """
    Get OAuth2 access token for DataCrunch API.

    DataCrunch uses OAuth2 client credentials flow.

    Args:
        client_id: OAuth2 client ID (if None, reads from credentials)
        client_secret: OAuth2 client secret (if None, reads from credentials)
        force_refresh: Force refresh even if cached token exists

    Returns:
        Access token if successful, None otherwise
    """
    global _access_token_cache

    if _access_token_cache and not force_refresh:
        return _access_token_cache

    if client_id is None or client_secret is None:
        client_id, client_secret = get_credentials()

    if not client_id or not client_secret:
        print("Error: No credentials found", file=sys.stderr)
        return None

    # OAuth2 client credentials request
    token_url = f"{DATACRUNCH_API_BASE}/oauth2/token"
    data = urllib.parse.urlencode(
        {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        }
    ).encode()

    try:
        req = urllib.request.Request(
            token_url,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "kdevops/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as response:
            token_data = json.loads(response.read().decode())
            access_token = token_data.get("access_token")
            if access_token:
                _access_token_cache = access_token
                return access_token
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        if e.code == 401:
            print("Invalid API key (client secret)", file=sys.stderr)
    except (socket.timeout, urllib.error.URLError) as e:
        print(f"Connection error getting access token: {e}", file=sys.stderr)
    except Exception as e:
        print(f"Error getting access token: {e}", file=sys.stderr)

    return None


def make_api_request(
    endpoint: str, access_token: Optional[str] = None
) -> Optional[Dict]:
    """
    Make a GET request to DataCrunch API.

    Args:
        endpoint: API endpoint (e.g., "/instances")
        access_token: OAuth2 access token (if None, will get one)

    Returns:
        JSON response as dict, or None on error
    """
    if access_token is None:
        access_token = get_access_token()

    if not access_token:
        return None

    url = f"{DATACRUNCH_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "kdevops/1.0",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        # If 401, token might be expired, retry once with fresh token
        if e.code == 401:
            access_token = get_access_token(force_refresh=True)
            if access_token:
                try:
                    req = urllib.request.Request(
                        url,
                        headers={**headers, "Authorization": f"Bearer {access_token}"},
                    )
                    with urllib.request.urlopen(
                        req, timeout=DEFAULT_TIMEOUT
                    ) as response:
                        return json.loads(response.read().decode())
                except Exception:
                    pass
        return None
    except (socket.timeout, urllib.error.URLError) as e:
        print(f"Connection error making API request: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error making API request: {e}", file=sys.stderr)
        return None


def make_api_post(
    endpoint: str, data: Dict, access_token: Optional[str] = None
) -> Optional[Dict]:
    """
    Make a POST request to DataCrunch API.

    Args:
        endpoint: API endpoint
        data: Request body as dict
        access_token: OAuth2 access token (if None, will get one)

    Returns:
        JSON response as dict, or None on error
    """
    if access_token is None:
        access_token = get_access_token()

    if not access_token:
        return None

    url = f"{DATACRUNCH_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "kdevops/1.0",
    }

    try:
        json_data = json.dumps(data).encode()
        req = urllib.request.Request(
            url, data=json_data, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        try:
            error_body = e.read().decode()
            print(f"Error body: {error_body}", file=sys.stderr)
        except Exception:
            pass
        return None
    except (socket.timeout, urllib.error.URLError) as e:
        print(f"Connection error making API POST request: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error making API request: {e}", file=sys.stderr)
        return None


# High-level API functions


def list_instance_types() -> Optional[List[Dict]]:
    """Get list of available instance types."""
    result = make_api_request("/instance-types")
    if result:
        if isinstance(result, list):
            return result
        return result.get("instance_types", [])
    return None


def list_images() -> Optional[List[Dict]]:
    """Get list of available OS images."""
    result = make_api_request("/images")
    if result:
        if isinstance(result, list):
            return result
        return result.get("images", [])
    return None


def list_locations() -> Optional[List[Dict]]:
    """Get list of available datacenter locations."""
    result = make_api_request("/locations")
    if result:
        if isinstance(result, list):
            return result
        return result.get("locations", [])
    return None


def list_instances() -> Optional[List[Dict]]:
    """Get list of currently provisioned instances."""
    result = make_api_request("/instances")
    if result:
        if isinstance(result, list):
            return result
        return result.get("instances", [])
    return None


def list_ssh_keys() -> Optional[List[Dict]]:
    """Get list of SSH keys."""
    result = make_api_request("/ssh-keys")
    if result:
        if isinstance(result, list):
            return result
        return result.get("items", [])
    return None


def get_instance_availability() -> Optional[Dict]:
    """Get instance availability by location and type."""
    return make_api_request("/instance-availability")


def main():
    """Test the API library."""
    print("DataCrunch API Library Test")
    print("=" * 50)

    client_id, client_secret = get_credentials()
    if not client_id or not client_secret:
        print("Error: No credentials configured")
        print(
            "Run: python3 scripts/datacrunch_credentials.py set <client_id> <client_secret>"
        )
        sys.exit(1)

    print("✓ Credentials found")
    print(f"  client_id: {client_id}")

    # Get access token
    access_token = get_access_token()
    if not access_token:
        print("✗ Failed to get access token")
        sys.exit(1)

    print("✓ Access token obtained")

    # Test API calls
    print("\nTesting API endpoints...")

    instance_types = list_instance_types()
    if instance_types:
        print(f"✓ Instance types: {len(instance_types)} available")
        # Show H100 instances
        h100_types = [
            it for it in instance_types if "H100" in it.get("instance_type", "")
        ]
        if h100_types:
            print(f"  H100 instances: {len(h100_types)}")
            for it in h100_types:
                print(
                    f"    - {it.get('instance_type')}: ${it.get('price_per_hour', 'N/A')}/hr"
                )
    else:
        print("✗ Failed to get instance types")

    images = list_images()
    if images:
        print(f"✓ Images: {len(images)} available")
        # Show PyTorch images
        pytorch_images = [
            img for img in images if "pytorch" in img.get("name", "").lower()
        ]
        if pytorch_images:
            print(f"  PyTorch images: {len(pytorch_images)}")
            for img in pytorch_images[:3]:
                print(f"    - {img.get('name')}")
    else:
        print("✗ Failed to get images")

    locations = list_locations()
    if locations:
        print(f"✓ Locations: {len(locations)} available")
        for loc in locations[:5]:
            print(f"    - {loc.get('code')}: {loc.get('name')}")
    else:
        print("✗ Failed to get locations")

    instances = list_instances()
    if instances is not None:
        print(f"✓ Current instances: {len(instances)}")
    else:
        print("✗ Failed to get instances")

    ssh_keys = list_ssh_keys()
    if ssh_keys is not None:
        print(f"✓ SSH keys: {len(ssh_keys)}")
    else:
        print("✗ Failed to get SSH keys")

    print("\n" + "=" * 50)
    print("API library test complete!")


if __name__ == "__main__":
    main()

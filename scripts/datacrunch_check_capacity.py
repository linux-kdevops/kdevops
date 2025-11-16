#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
"""
Check DataCrunch instance availability across all locations.

This script queries the DataCrunch API to find where a specific instance type
is available, helping users avoid 503 errors when provisioning.
"""

import argparse
import configparser
import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.stderr.write("Error: requests module not installed\n")
    sys.stderr.write("Install with: pip install requests\n")
    sys.exit(1)


def load_credentials(creds_file="~/.datacrunch/credentials"):
    """Load DataCrunch API credentials from file."""
    try:
        path = Path(creds_file).expanduser()
        if not path.exists():
            sys.stderr.write(f"Credentials file not found: {path}\n")
            sys.stderr.write(
                "Run: python3 scripts/datacrunch_credentials.py set <your_client_secret>\n"
            )
            sys.exit(1)

        config = configparser.ConfigParser()
        config.read(path)

        section = (
            "default"
            if "default" in config
            else "DEFAULT" if "DEFAULT" in config else None
        )
        if section is None:
            sys.stderr.write("No default section found in credentials file\n")
            sys.exit(1)

        # Extract client_id and client_secret
        client_id = config[section].get("client_id")
        client_secret = None
        for key in ["client_secret", "datacrunch_api_key", "api_key"]:
            if key in config[section]:
                client_secret = config[section][key].strip()
                break

        if not client_id or not client_secret:
            sys.stderr.write(
                "client_id and client_secret not found in credentials file\n"
            )
            sys.exit(1)

        return client_id, client_secret

    except Exception as e:
        sys.stderr.write(f"Error loading credentials: {e}\n")
        sys.exit(1)


def get_oauth_token(client_id, client_secret):
    """Get OAuth2 access token from DataCrunch API."""
    try:
        response = requests.post(
            "https://api.datacrunch.io/v1/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=30,
        )
        response.raise_for_status()
        return response.json()["access_token"]
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"Error getting OAuth token: {e}\n")
        sys.exit(1)


def check_availability(token, instance_type=None, location=None):
    """Check instance availability across all or specific locations."""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        params = {}
        if location:
            params["locationCode"] = location

        response = requests.get(
            "https://api.datacrunch.io/v1/instance-availability",
            headers=headers,
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        results = []
        for loc_data in data:
            location_code = loc_data.get("location_code", "UNKNOWN")
            availabilities = loc_data.get("availabilities", [])

            # If specific instance type requested, filter to that
            if instance_type:
                if instance_type in availabilities:
                    results.append(
                        {
                            "location": location_code,
                            "instance_type": instance_type,
                            "available": True,
                        }
                    )
            else:
                # Show all H100 instances (default)
                h100_instances = [a for a in availabilities if "H100" in a]
                if h100_instances:
                    results.append(
                        {
                            "location": location_code,
                            "instances": h100_instances,
                        }
                    )

        return results

    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"Error checking availability: {e}\n")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Check DataCrunch instance availability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check where 4H100.80S.176V is available
  %(prog)s --instance-type 4H100.80S.176V

  # Check all H100 instances across all locations
  %(prog)s

  # Check specific location
  %(prog)s --location FIN-01

  # JSON output for scripting
  %(prog)s --instance-type 4H100.80S.176V --json
        """,
    )
    parser.add_argument(
        "--instance-type",
        "-i",
        help="Specific instance type to check (e.g., 4H100.80S.176V)",
    )
    parser.add_argument(
        "--location",
        "-l",
        help="Check specific location only (e.g., FIN-01, FIN-02, FIN-03, ICE-01)",
    )
    parser.add_argument(
        "--json",
        "-j",
        action="store_true",
        help="Output results in JSON format",
    )
    parser.add_argument(
        "--pick-first",
        "-p",
        action="store_true",
        help="Just pick the first available location (useful for automation)",
    )
    parser.add_argument(
        "--credentials",
        "-c",
        default="~/.datacrunch/credentials",
        help="Path to credentials file (default: ~/.datacrunch/credentials)",
    )

    args = parser.parse_args()

    # Load credentials and get OAuth token
    client_id, client_secret = load_credentials(args.credentials)
    token = get_oauth_token(client_id, client_secret)

    # Check availability
    results = check_availability(token, args.instance_type, args.location)

    # Handle --pick-first mode: just output first available location
    if args.pick_first:
        if results and len(results) > 0:
            print(results[0]["location"])
            sys.exit(0)
        else:
            sys.stderr.write(
                f"Error: No locations found for {args.instance_type or 'any instance'}\n"
            )
            sys.exit(1)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Human-readable output
        if args.instance_type:
            print(f"Checking availability for: {args.instance_type}\n")
            if not results:
                print(f"❌ {args.instance_type} is NOT available in any location")
                sys.exit(1)
            else:
                print(f"✓ {args.instance_type} is available in:")
                for r in results:
                    print(f"  • {r['location']}")
        else:
            print("H100 GPU Instance Availability:\n")
            if not results:
                print("❌ No H100 instances available")
                sys.exit(1)
            for loc in results:
                print(f"📍 {loc['location']}:")
                for inst in loc["instances"]:
                    print(f"  • {inst}")
                print()


if __name__ == "__main__":
    main()

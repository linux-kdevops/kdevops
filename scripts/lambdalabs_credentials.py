#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Lambda Labs credentials management.
Reads API keys from credentials file (~/.lambdalabs/credentials).
"""

import os
import configparser
from pathlib import Path
from typing import Optional


def get_credentials_file_path() -> Path:
    """Get the default Lambda Labs credentials file path."""
    return Path.home() / ".lambdalabs" / "credentials"


def read_credentials_file(
    path: Optional[Path] = None, profile: str = "default"
) -> Optional[str]:
    """
    Read Lambda Labs API key from credentials file.

    Args:
        path: Path to credentials file (defaults to ~/.lambdalabs/credentials)
        profile: Profile name to use (defaults to "default")

    Returns:
        API key if found, None otherwise
    """
    if path is None:
        path = get_credentials_file_path()

    if not path.exists():
        return None

    try:
        config = configparser.ConfigParser()
        config.read(path)

        if profile in config:
            # Try different possible key names
            for key_name in ["lambdalabs_api_key", "api_key"]:
                if key_name in config[profile]:
                    return config[profile][key_name].strip()

        # Also check if it's in DEFAULT section
        if "DEFAULT" in config:
            for key_name in ["lambdalabs_api_key", "api_key"]:
                if key_name in config["DEFAULT"]:
                    return config["DEFAULT"][key_name].strip()

    except Exception:
        # Silently fail if file can't be parsed
        pass

    return None


def get_api_key(profile: str = "default") -> Optional[str]:
    """
    Get Lambda Labs API key from credentials file.

    Args:
        profile: Profile name to use from credentials file

    Returns:
        API key if found, None otherwise
    """
    # Try default credentials file
    api_key = read_credentials_file(profile=profile)
    if api_key:
        return api_key

    # Try custom credentials file path from environment
    custom_path = os.environ.get("LAMBDALABS_CREDENTIALS_FILE")
    if custom_path:
        api_key = read_credentials_file(Path(custom_path), profile=profile)
        if api_key:
            return api_key

    return None


def create_credentials_file(
    api_key: str, path: Optional[Path] = None, profile: str = "default"
) -> bool:
    """
    Create or update Lambda Labs credentials file.

    Args:
        api_key: The API key to save
        path: Path to credentials file (defaults to ~/.lambdalabs/credentials)
        profile: Profile name to use (defaults to "default")

    Returns:
        True if successful, False otherwise
    """
    if path is None:
        path = get_credentials_file_path()

    try:
        # Create directory if it doesn't exist
        path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing config or create new one
        config = configparser.ConfigParser()
        if path.exists():
            config.read(path)

        # Add or update the profile
        if profile not in config:
            config[profile] = {}

        config[profile]["lambdalabs_api_key"] = api_key

        # Write the config file with restricted permissions
        with open(path, "w") as f:
            config.write(f)

        # Set restrictive permissions (owner read/write only)
        path.chmod(0o600)

        return True

    except Exception as e:
        print(f"Error creating credentials file: {e}")
        return False


def main():
    """Command-line utility for managing Lambda Labs credentials."""
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  lambdalabs_credentials.py get [profile]     - Get API key")
        print("  lambdalabs_credentials.py set <api_key> [profile] - Set API key")
        print(
            "  lambdalabs_credentials.py check [profile]   - Check if API key is configured"
        )
        print("  lambdalabs_credentials.py test [profile]    - Test API key validity")
        print(
            "  lambdalabs_credentials.py path              - Show credentials file path"
        )
        sys.exit(1)

    command = sys.argv[1]

    if command == "get":
        profile = sys.argv[2] if len(sys.argv) > 2 else "default"
        api_key = get_api_key(profile)
        if api_key:
            print(api_key)
            sys.exit(0)
        else:
            print("No API key found", file=sys.stderr)
            sys.exit(1)

    elif command == "set":
        if len(sys.argv) < 3:
            print("Error: API key required", file=sys.stderr)
            sys.exit(1)
        api_key = sys.argv[2]
        profile = sys.argv[3] if len(sys.argv) > 3 else "default"

        if create_credentials_file(api_key, profile=profile):
            print(
                f"API key saved to {get_credentials_file_path()} (profile: {profile})"
            )
            sys.exit(0)
        else:
            print("Failed to save API key", file=sys.stderr)
            sys.exit(1)

    elif command == "check":
        profile = sys.argv[2] if len(sys.argv) > 2 else "default"
        api_key = get_api_key(profile)
        if api_key:
            print(f"✓ API key configured (profile: {profile})")
            # Show sources checked
            if read_credentials_file(profile=profile):
                print(f"  Source: {get_credentials_file_path()}")
            elif os.environ.get("LAMBDALABS_CREDENTIALS_FILE"):
                print(f"  Source: {os.environ.get('LAMBDALABS_CREDENTIALS_FILE')}")
            sys.exit(0)
        else:
            print("✗ No API key found")
            print(f"  Checked: {get_credentials_file_path()}")
            if os.environ.get("LAMBDALABS_CREDENTIALS_FILE"):
                print(f"  Checked: {os.environ.get('LAMBDALABS_CREDENTIALS_FILE')}")
            sys.exit(1)

    elif command == "test":
        profile = sys.argv[2] if len(sys.argv) > 2 else "default"
        api_key = get_api_key(profile)
        if not api_key:
            print("✗ No API key found")
            sys.exit(1)

        # Test the API key
        import urllib.request
        import urllib.error
        import json

        print(f"Testing API key (profile: {profile})...")
        headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "kdevops/1.0"}

        try:
            req = urllib.request.Request(
                "https://cloud.lambdalabs.com/api/v1/instances", headers=headers
            )
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                print(f"✓ API key is VALID")
                print(f"  Current instances: {len(data.get('data', []))}")
                sys.exit(0)
        except urllib.error.HTTPError as e:
            if e.code == 403:
                print(f"✗ API key is INVALID (HTTP 403 Forbidden)")
                print("  The key exists but Lambda Labs rejected it.")
                print("  Please get a new API key from https://cloud.lambdalabs.com")
            else:
                print(f"✗ API test failed: HTTP {e.code}")
            sys.exit(1)
        except Exception as e:
            print(f"✗ API test failed: {e}")
            sys.exit(1)

    elif command == "path":
        print(get_credentials_file_path())
        sys.exit(0)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

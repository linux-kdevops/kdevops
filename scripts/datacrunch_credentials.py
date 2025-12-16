#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
DataCrunch credentials management.
Reads API keys from credentials file (~/.datacrunch/credentials).
"""

import os
import configparser
from pathlib import Path
from typing import Optional


def get_credentials_file_path() -> Path:
    """Get the default DataCrunch credentials file path."""
    return Path.home() / ".datacrunch" / "credentials"


def read_credentials_file(
    path: Optional[Path] = None, profile: str = "default"
) -> tuple[Optional[str], Optional[str]]:
    """
    Read DataCrunch API credentials from credentials file.

    Args:
        path: Path to credentials file (defaults to ~/.datacrunch/credentials)
        profile: Profile name to use (defaults to "default")

    Returns:
        Tuple of (client_id, client_secret) if found, (None, None) otherwise
    """
    if path is None:
        path = get_credentials_file_path()

    if not path.exists():
        return None, None

    try:
        config = configparser.ConfigParser()
        config.read(path)

        client_id = None
        client_secret = None

        if profile in config:
            # Get client_id
            if "client_id" in config[profile]:
                client_id = config[profile]["client_id"].strip()

            # Get client_secret (try multiple names)
            for key_name in ["client_secret", "datacrunch_api_key", "api_key"]:
                if key_name in config[profile]:
                    client_secret = config[profile][key_name].strip()
                    break

        # Also check if it's in DEFAULT section
        if not client_id and "DEFAULT" in config:
            if "client_id" in config["DEFAULT"]:
                client_id = config["DEFAULT"]["client_id"].strip()

        if not client_secret and "DEFAULT" in config:
            for key_name in ["client_secret", "datacrunch_api_key", "api_key"]:
                if key_name in config["DEFAULT"]:
                    client_secret = config["DEFAULT"][key_name].strip()
                    break

        return client_id, client_secret

    except Exception:
        # Silently fail if file can't be parsed
        pass

    return None, None


def get_credentials(profile: str = "default") -> tuple[Optional[str], Optional[str]]:
    """
    Get DataCrunch credentials from credentials file.

    Args:
        profile: Profile name to use from credentials file

    Returns:
        Tuple of (client_id, client_secret) if found, (None, None) otherwise
    """
    # Try default credentials file
    client_id, client_secret = read_credentials_file(profile=profile)
    if client_id and client_secret:
        return client_id, client_secret

    # Try custom credentials file path from environment
    custom_path = os.environ.get("DATACRUNCH_CREDENTIALS_FILE")
    if custom_path:
        client_id, client_secret = read_credentials_file(
            Path(custom_path), profile=profile
        )
        if client_id and client_secret:
            return client_id, client_secret

    return None, None


def get_api_key(profile: str = "default") -> Optional[str]:
    """
    Get DataCrunch API key (client_secret) from credentials file.

    DEPRECATED: Use get_credentials() instead to get both client_id and client_secret.

    Args:
        profile: Profile name to use from credentials file

    Returns:
        Client secret if found, None otherwise
    """
    _, client_secret = get_credentials(profile)
    return client_secret


def create_credentials_file(
    client_id: str,
    client_secret: str,
    path: Optional[Path] = None,
    profile: str = "default",
) -> bool:
    """
    Create or update DataCrunch credentials file.

    Args:
        client_id: The OAuth2 client ID
        client_secret: The OAuth2 client secret
        path: Path to credentials file (defaults to ~/.datacrunch/credentials)
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

        config[profile]["client_id"] = client_id
        config[profile]["client_secret"] = client_secret

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
    """Command-line utility for managing DataCrunch credentials."""
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print(
            "  datacrunch_credentials.py set [profile]   - Set credentials (interactive)"
        )
        print(
            "  datacrunch_credentials.py check [profile] - Check if credentials configured"
        )
        print("  datacrunch_credentials.py test [profile]  - Test API connectivity")
        print("  datacrunch_credentials.py get [profile]   - Get credentials")
        print(
            "  datacrunch_credentials.py path            - Show credentials file path"
        )
        print()
        print("Get your credentials from: https://cloud.datacrunch.io/dashboard/api")
        sys.exit(1)

    command = sys.argv[1]

    if command == "get":
        profile = sys.argv[2] if len(sys.argv) > 2 else "default"
        client_id, client_secret = get_credentials(profile)
        if client_id and client_secret:
            print(f"client_id={client_id}")
            print(f"client_secret={client_secret}")
            sys.exit(0)
        else:
            print("No credentials found", file=sys.stderr)
            sys.exit(1)

    elif command == "set":
        profile = sys.argv[2] if len(sys.argv) > 2 else "default"

        print(f"Setting up DataCrunch credentials (profile: {profile})")
        print()
        print("Get your credentials from: https://cloud.datacrunch.io/dashboard/api")
        print()

        # Prompt for client_id
        client_id = input("Enter your client_id: ").strip()
        if not client_id:
            print("Error: client_id cannot be empty", file=sys.stderr)
            sys.exit(1)

        # Prompt for client_secret
        try:
            import getpass

            client_secret = getpass.getpass(
                "Enter your client_secret (hidden): "
            ).strip()
        except (ImportError, Exception):
            # Fallback if getpass not available
            client_secret = input("Enter your client_secret: ").strip()

        if not client_secret:
            print("Error: client_secret cannot be empty", file=sys.stderr)
            sys.exit(1)

        print()
        if create_credentials_file(client_id, client_secret, profile=profile):
            print(
                f"✓ Credentials saved to {get_credentials_file_path()} (profile: {profile})"
            )
            print()
            print("Test your credentials with:")
            print("  python3 scripts/datacrunch_credentials.py test")
            sys.exit(0)
        else:
            print("Failed to save credentials", file=sys.stderr)
            sys.exit(1)

    elif command == "check":
        profile = sys.argv[2] if len(sys.argv) > 2 else "default"
        client_id, client_secret = get_credentials(profile)
        if client_id and client_secret:
            print(f"[OK] Credentials configured (profile: {profile})")
            print(f"  client_id: {client_id}")
            print(
                f"  client_secret: {'*' * (len(client_secret) - 4)}{client_secret[-4:]}"
            )
            # Show sources checked
            cid, csec = read_credentials_file(profile=profile)
            if cid and csec:
                print(f"  Source: {get_credentials_file_path()}")
            elif os.environ.get("DATACRUNCH_CREDENTIALS_FILE"):
                print(f"  Source: {os.environ.get('DATACRUNCH_CREDENTIALS_FILE')}")
            sys.exit(0)
        else:
            print("[ERROR] No credentials found")
            print(f"  Checked: {get_credentials_file_path()}")
            if os.environ.get("DATACRUNCH_CREDENTIALS_FILE"):
                print(f"  Checked: {os.environ.get('DATACRUNCH_CREDENTIALS_FILE')}")
            print("\nPlease set credentials with:")
            print(
                "  python3 scripts/datacrunch_credentials.py set <client_id> <client_secret>"
            )
            sys.exit(1)

    elif command == "test":
        profile = sys.argv[2] if len(sys.argv) > 2 else "default"
        client_id, client_secret = get_credentials(profile)
        if not client_id or not client_secret:
            print("[ERROR] No credentials found")
            print("Please set credentials with:")
            print(
                "  python3 scripts/datacrunch_credentials.py set <client_id> <client_secret>"
            )
            sys.exit(1)

        # Test the credentials using OAuth2 token endpoint
        import urllib.request
        import urllib.error
        import json

        print(f"Testing credentials (profile: {profile})...")
        print(f"  client_id: {client_id}")

        # DataCrunch uses OAuth2 client credentials flow
        # Try to get instances to test credentials validity
        try:
            # First get access token
            token_url = "https://api.datacrunch.io/v1/oauth2/token"
            token_data = urllib.parse.urlencode(
                {
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                }
            ).encode()

            token_req = urllib.request.Request(
                token_url,
                data=token_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "kdevops/1.0",
                },
            )

            with urllib.request.urlopen(token_req) as response:
                token_resp = json.loads(response.read().decode())
                access_token = token_resp.get("access_token")

            if not access_token:
                print("[ERROR] Failed to get access token")
                print("  Response did not contain access_token")
                sys.exit(1)

            print("  ✓ OAuth2 token obtained successfully")

            # Now test with instances endpoint
            headers = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "kdevops/1.0",
            }

            req = urllib.request.Request(
                "https://api.datacrunch.io/v1/instances", headers=headers
            )
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                print(f"[OK] Credentials are VALID")
                instances = (
                    data if isinstance(data, list) else data.get("instances", [])
                )
                print(f"  Current instances: {len(instances)}")
                sys.exit(0)
        except urllib.error.HTTPError as e:
            if e.code == 401 or e.code == 403:
                print(f"[ERROR] Credentials are INVALID (HTTP {e.code})")
                print("  DataCrunch rejected the client_id/client_secret combination.")
                print(
                    "  Please verify your credentials at: https://cloud.datacrunch.io/dashboard/api"
                )
            else:
                print(f"[ERROR] API test failed: HTTP {e.code}")
                try:
                    error_body = e.read().decode()
                    print(f"  Error: {error_body}")
                except Exception:
                    pass
            sys.exit(1)
        except Exception as e:
            print(f"[ERROR] API test failed: {e}")
            sys.exit(1)

    elif command == "path":
        print(get_credentials_file_path())
        sys.exit(0)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

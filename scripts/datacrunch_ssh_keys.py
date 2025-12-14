#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
DataCrunch SSH Key Management via API.
Provides functions to list, add, and delete SSH keys through the DataCrunch API.
"""

import json
import os
import socket
import sys
import subprocess
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

# Default timeout for API requests in seconds
DEFAULT_TIMEOUT = 30

# Import our API module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from datacrunch_api import (
    get_credentials,
    get_access_token,
    make_api_request,
    make_api_post,
)


def list_ssh_keys() -> Optional[List[Dict]]:
    """
    List all SSH keys associated with the DataCrunch account.

    Returns:
        List of SSH key dictionaries
    """
    result = make_api_request("/ssh-keys")
    if result:
        return result.get("items", result if isinstance(result, list) else [])
    return None


def add_ssh_key(name: str, public_key: str) -> bool:
    """
    Add a new SSH key to the DataCrunch account.

    Args:
        name: Name for the SSH key
        public_key: The public key content

    Returns:
        True if successful, False otherwise
    """
    data = {"name": name, "key": public_key.strip()}

    print(f"Adding SSH key '{name}' to DataCrunch...", file=sys.stderr)
    response = make_api_post("/ssh-keys", data)
    if response:
        print(f"✓ Successfully added SSH key '{name}'", file=sys.stderr)
        return True

    return False


def delete_ssh_key(key_name_or_id: str) -> bool:
    """
    Delete an SSH key from the DataCrunch account.

    Args:
        key_name_or_id: Name or ID of the SSH key to delete

    Returns:
        True if successful, False otherwise
    """
    # If we have a name, find the ID
    keys = list_ssh_keys()
    if not keys:
        print("Failed to list SSH keys", file=sys.stderr)
        return False

    key_id = None
    for key in keys:
        if key.get("name") == key_name_or_id or key.get("id") == key_name_or_id:
            key_id = key.get("id")
            break

    if not key_id:
        print(f"SSH key '{key_name_or_id}' not found", file=sys.stderr)
        return False

    # DataCrunch API doesn't document DELETE for single key, but let's try
    # Fallback: the API might require DELETE to /ssh-keys with body containing key IDs
    print(f"Deleting SSH key '{key_name_or_id}' (ID: {key_id})...", file=sys.stderr)

    # Try direct DELETE
    import urllib.request
    import urllib.error

    client_id, client_secret = get_credentials()
    if not client_id or not client_secret:
        print("Error: No credentials found", file=sys.stderr)
        return False

    access_token = get_access_token(client_id, client_secret)
    if not access_token:
        return False

    url = f"https://api.datacrunch.io/v1/ssh-keys/{key_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "kdevops/1.0",
    }

    try:
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        with urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT) as response:
            print(f"✓ Successfully deleted SSH key '{key_name_or_id}'", file=sys.stderr)
            return True
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        try:
            error_body = e.read().decode()
            print(f"Error details: {error_body}", file=sys.stderr)
        except Exception:
            pass
        return False
    except (socket.timeout, urllib.error.URLError) as e:
        print(f"Connection error deleting SSH key: {e}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error deleting SSH key: {e}", file=sys.stderr)
        return False


def generate_unique_key_name() -> str:
    """
    Generate a unique SSH key name based on current directory.
    Format: kdevops-datacrunch-<hash>
    """
    # Get current directory path
    cwd = os.getcwd()
    # Create hash of directory path
    dir_hash = hashlib.md5(cwd.encode()).hexdigest()[:8]
    return f"kdevops-datacrunch-{dir_hash}"


def generate_ssh_key_pair(key_path: Path, passphrase: str = "") -> bool:
    """
    Generate a new ed25519 SSH key pair.

    Args:
        key_path: Path where to save the private key
        passphrase: Passphrase for the key (empty for no passphrase)

    Returns:
        True if successful, False otherwise
    """
    # Ensure parent directory exists
    key_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate key using ssh-keygen
    cmd = [
        "ssh-keygen",
        "-t",
        "ed25519",
        "-f",
        str(key_path),
        "-N",
        passphrase,
        "-C",
        f"kdevops@datacrunch-{key_path.stem}",
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✓ Generated SSH key pair: {key_path}", file=sys.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to generate SSH key: {e}", file=sys.stderr)
        return False


def setup_ssh_key(
    key_name: Optional[str] = None, key_file: Optional[str] = None
) -> bool:
    """
    Setup SSH key for DataCrunch - generate if needed and upload.

    Args:
        key_name: Name for the SSH key (default: auto-generated unique name)
        key_file: Path to private key file (default: ~/.ssh/kdevops_terraform)

    Returns:
        True if successful, False otherwise
    """
    if key_name is None:
        key_name = generate_unique_key_name()

    if key_file is None:
        key_file = str(Path.home() / ".ssh" / "kdevops_terraform")

    key_path = Path(key_file)
    pub_key_path = Path(str(key_file) + ".pub")

    print(f"Setting up SSH key: {key_name}")
    print(f"  Key file: {key_path}")

    # Check if key already exists in DataCrunch
    keys = list_ssh_keys()
    if keys:
        for key in keys:
            if key.get("name") == key_name:
                print(f"✓ SSH key '{key_name}' already exists in DataCrunch")
                return True

    # Generate key if it doesn't exist
    if not key_path.exists():
        print(f"Generating new SSH key pair...")
        if not generate_ssh_key_pair(key_path):
            return False
    else:
        print(f"✓ Using existing SSH key: {key_path}")

    # Read public key
    if not pub_key_path.exists():
        print(f"Error: Public key not found: {pub_key_path}", file=sys.stderr)
        return False

    with open(pub_key_path, "r") as f:
        public_key = f.read().strip()

    # Upload to DataCrunch
    return add_ssh_key(key_name, public_key)


def cleanup_ssh_key(key_name: Optional[str] = None) -> bool:
    """
    Remove SSH key from DataCrunch (does not delete local key files).

    Args:
        key_name: Name of the SSH key (default: auto-generated unique name)

    Returns:
        True if successful, False otherwise
    """
    if key_name is None:
        key_name = generate_unique_key_name()

    print(f"Cleaning up SSH key: {key_name}")
    return delete_ssh_key(key_name)


def main():
    """Command-line interface for SSH key management."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage DataCrunch SSH keys")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # List command
    subparsers.add_parser("list", help="List all SSH keys")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add an SSH key")
    add_parser.add_argument("name", help="Name for the SSH key")
    add_parser.add_argument("keyfile", help="Path to public key file")

    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete an SSH key")
    delete_parser.add_argument("name", help="Name or ID of the SSH key to delete")

    # Setup command (generate + upload)
    setup_parser = subparsers.add_parser(
        "setup", help="Setup SSH key (generate if needed and upload)"
    )
    setup_parser.add_argument(
        "--name", help="Name for the SSH key (default: auto-generated)"
    )
    setup_parser.add_argument(
        "--keyfile", help="Path to private key file (default: ~/.ssh/kdevops_terraform)"
    )

    # Cleanup command
    cleanup_parser = subparsers.add_parser(
        "cleanup", help="Remove SSH key from DataCrunch"
    )
    cleanup_parser.add_argument(
        "--name", help="Name of the SSH key (default: auto-generated)"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Check credentials
    client_id, client_secret = get_credentials()
    if not client_id or not client_secret:
        print("Error: No DataCrunch credentials configured", file=sys.stderr)
        print("Run: python3 scripts/datacrunch_credentials.py set", file=sys.stderr)
        sys.exit(1)

    if args.command == "list":
        keys = list_ssh_keys()
        if keys:
            print(f"SSH keys in DataCrunch account ({len(keys)}):")
            print()
            for key in keys:
                name = key.get("name", "N/A")
                key_id = key.get("id", "N/A")
                print(f"  {name}")
                print(f"    ID: {key_id}")
                print()
        else:
            print("No SSH keys found or failed to retrieve")
        sys.exit(0 if keys is not None else 1)

    elif args.command == "add":
        keyfile = Path(args.keyfile)
        if not keyfile.exists():
            print(f"Error: Key file not found: {keyfile}", file=sys.stderr)
            sys.exit(1)

        with open(keyfile, "r") as f:
            public_key = f.read().strip()

        success = add_ssh_key(args.name, public_key)
        sys.exit(0 if success else 1)

    elif args.command == "delete":
        success = delete_ssh_key(args.name)
        sys.exit(0 if success else 1)

    elif args.command == "setup":
        success = setup_ssh_key(args.name, args.keyfile)
        if success:
            key_name = args.name or generate_unique_key_name()
            print()
            print(f"✓ SSH key '{key_name}' is ready to use")
            print()
            print("You can now provision instances with:")
            print("  make bringup")
        sys.exit(0 if success else 1)

    elif args.command == "cleanup":
        success = cleanup_ssh_key(args.name)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

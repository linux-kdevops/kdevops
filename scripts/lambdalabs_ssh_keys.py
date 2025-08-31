#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Lambda Labs SSH Key Management via API.
Provides functions to list, add, and delete SSH keys through the Lambda Labs API.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from typing import Dict, List, Optional, Tuple

# Import our credentials module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lambdalabs_credentials import get_api_key as get_api_key_from_credentials

LAMBDALABS_API_BASE = "https://cloud.lambdalabs.com/api/v1"


def get_api_key() -> Optional[str]:
    """Get Lambda Labs API key from credentials file or environment variable."""
    return get_api_key_from_credentials()


def make_api_request(
    endpoint: str, api_key: str, method: str = "GET", data: Optional[Dict] = None
) -> Optional[Dict]:
    """Make a request to Lambda Labs API."""
    url = f"{LAMBDALABS_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "kdevops/1.0",
    }

    try:
        req_data = None
        if data and method in ["POST", "PUT", "PATCH"]:
            req_data = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, headers=headers, data=req_data, method=method)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        if e.code == 404:
            print(f"Endpoint not found: {endpoint}", file=sys.stderr)
        try:
            error_body = e.read().decode()
            print(f"Error details: {error_body}", file=sys.stderr)
        except:
            pass
        return None
    except Exception as e:
        print(f"Error making API request: {e}", file=sys.stderr)
        return None


def list_ssh_keys(api_key: str) -> Optional[List[Dict]]:
    """
    List all SSH keys associated with the Lambda Labs account.

    Returns:
        List of SSH key dictionaries with 'name', 'id', and 'public_key' fields
    """
    response = make_api_request("/ssh-keys", api_key)
    if response:
        # The API returns {"data": [{name, id, public_key}, ...]}
        if "data" in response:
            return response["data"]
        # Fallback for other response formats
        elif isinstance(response, list):
            return response
    return None


def add_ssh_key(api_key: str, name: str, public_key: str) -> bool:
    """
    Add a new SSH key to the Lambda Labs account.

    Args:
        api_key: Lambda Labs API key
        name: Name for the SSH key
        public_key: The public key content

    Returns:
        True if successful, False otherwise
    """
    # Based on the API response structure, the endpoint is /ssh-keys
    # and the format is likely {"name": name, "public_key": public_key}
    endpoint = "/ssh-keys"
    data = {"name": name, "public_key": public_key.strip()}

    print(f"Adding SSH key '{name}' via POST {endpoint}", file=sys.stderr)
    response = make_api_request(endpoint, api_key, method="POST", data=data)
    if response:
        print(f"Successfully added SSH key '{name}'", file=sys.stderr)
        return True

    # Try alternative format if the first one fails
    data = {"name": name, "key": public_key.strip()}
    print(f"Trying alternative format with 'key' field", file=sys.stderr)
    response = make_api_request(endpoint, api_key, method="POST", data=data)
    if response:
        print(f"Successfully added SSH key '{name}'", file=sys.stderr)
        return True

    return False


def delete_ssh_key(api_key: str, key_name_or_id: str) -> bool:
    """
    Delete an SSH key from the Lambda Labs account.

    Args:
        api_key: Lambda Labs API key
        key_name_or_id: Name or ID of the SSH key to delete

    Returns:
        True if successful, False otherwise
    """
    # Check if input looks like an ID (32 character hex string)
    is_id = len(key_name_or_id) == 32 and all(
        c in "0123456789abcdef" for c in key_name_or_id.lower()
    )

    if not is_id:
        # If we have a name, we need to find the ID
        keys = list_ssh_keys(api_key)
        if keys:
            for key in keys:
                if key.get("name") == key_name_or_id:
                    key_id = key.get("id")
                    if key_id:
                        print(
                            f"Found ID {key_id} for key '{key_name_or_id}'",
                            file=sys.stderr,
                        )
                        key_name_or_id = key_id
                        break
            else:
                print(f"SSH key '{key_name_or_id}' not found", file=sys.stderr)
                return False

    # Delete using the ID
    endpoint = f"/ssh-keys/{key_name_or_id}"
    print(f"Deleting SSH key via DELETE {endpoint}", file=sys.stderr)
    response = make_api_request(endpoint, api_key, method="DELETE")
    if response is not None:
        print(f"Successfully deleted SSH key", file=sys.stderr)
        return True

    return False


def read_public_key_file(filepath: str) -> Optional[str]:
    """Read SSH public key from file."""
    expanded_path = os.path.expanduser(filepath)
    if not os.path.exists(expanded_path):
        print(f"SSH public key file not found: {expanded_path}", file=sys.stderr)
        return None

    try:
        with open(expanded_path, "r") as f:
            return f.read().strip()
    except Exception as e:
        print(f"Error reading SSH public key: {e}", file=sys.stderr)
        return None


def check_ssh_key_exists(api_key: str, key_name: str) -> bool:
    """
    Check if an SSH key with the given name exists.

    Args:
        api_key: Lambda Labs API key
        key_name: Name of the SSH key to check

    Returns:
        True if key exists, False otherwise
    """
    keys = list_ssh_keys(api_key)
    if not keys:
        return False

    for key in keys:
        # Try different possible field names
        if key.get("name") == key_name or key.get("key_name") == key_name:
            return True

    return False


def validate_ssh_setup(
    api_key: str, expected_key_name: str = "kdevops-lambdalabs"
) -> Tuple[bool, str]:
    """
    Validate that SSH keys are properly configured for Lambda Labs.

    Args:
        api_key: Lambda Labs API key
        expected_key_name: The SSH key name we expect to use

    Returns:
        Tuple of (success, message)
    """
    # First, try to list SSH keys
    keys = list_ssh_keys(api_key)

    if keys is None:
        # API doesn't support SSH key management
        return (
            False,
            "Lambda Labs API does not appear to support SSH key management.\n"
            "You must manually add your SSH key through the Lambda Labs web console:\n"
            "1. Go to https://cloud.lambdalabs.com/ssh-keys\n"
            "2. Click 'Add SSH key'\n"
            f"3. Name it '{expected_key_name}'\n"
            "4. Paste your public key from ~/.ssh/kdevops_terraform.pub",
        )

    if not keys:
        # No keys found
        return (
            False,
            "No SSH keys found in your Lambda Labs account.\n"
            "Please add an SSH key through the web console or API before proceeding.",
        )

    # Check if expected key exists
    key_names = []
    for key in keys:
        name = key.get("name") or key.get("key_name")
        if name:
            key_names.append(name)
            if name == expected_key_name:
                return (True, f"SSH key '{expected_key_name}' found and ready to use.")

    # Key not found but other keys exist
    key_list = "\n  - ".join(key_names)
    return (
        False,
        f"SSH key '{expected_key_name}' not found in your Lambda Labs account.\n"
        f"Available SSH keys:\n  - {key_list}\n"
        f"Either:\n"
        f"1. Add a key named '{expected_key_name}' through the web console\n"
        f"2. Or update terraform/lambdalabs/kconfigs/Kconfig.identity to use one of the existing keys",
    )


def main():
    """Main entry point for SSH key management."""
    if len(sys.argv) < 2:
        print("Usage: lambdalabs_ssh_keys.py <command> [args...]")
        print("Commands:")
        print("  list          - List all SSH keys")
        print("  check <name>  - Check if a specific key exists")
        print("  add <name> <public_key_file> - Add a new SSH key")
        print("  delete <name> - Delete an SSH key")
        print("  validate [key_name] - Validate SSH setup for kdevops")
        sys.exit(1)

    command = sys.argv[1]
    api_key = get_api_key()

    if not api_key:
        print("Error: Lambda Labs API key not found", file=sys.stderr)
        print("Please configure your API key:", file=sys.stderr)
        print(
            "  python3 scripts/lambdalabs_credentials.py set 'your-api-key'",
            file=sys.stderr,
        )
        sys.exit(1)

    if command == "list":
        keys = list_ssh_keys(api_key)
        if keys is None:
            print("Failed to list SSH keys - API may not support this feature")
            sys.exit(1)
        elif not keys:
            print("No SSH keys found")
        else:
            print("SSH Keys:")
            for key in keys:
                if isinstance(key, dict):
                    name = key.get("name") or key.get("key_name") or "Unknown"
                    key_id = key.get("id", "")
                    fingerprint = key.get("fingerprint", "")
                    print(f"  - Name: {name}")
                    if key_id and key_id != name:
                        print(f"    ID: {key_id}")
                    if fingerprint:
                        print(f"    Fingerprint: {fingerprint}")
                    # Show all fields for debugging
                    for k, v in key.items():
                        if k not in ["name", "id", "fingerprint", "key_name"]:
                            print(f"    {k}: {v}")
                else:
                    # Key is just a string (name)
                    print(f"  - {key}")

    elif command == "check":
        if len(sys.argv) < 3:
            print("Usage: lambdalabs_ssh_keys.py check <key_name>")
            sys.exit(1)
        key_name = sys.argv[2]
        if check_ssh_key_exists(api_key, key_name):
            print(f"SSH key '{key_name}' exists")
        else:
            print(f"SSH key '{key_name}' not found")
            sys.exit(1)

    elif command == "add":
        if len(sys.argv) < 4:
            print("Usage: lambdalabs_ssh_keys.py add <name> <public_key_file>")
            sys.exit(1)
        name = sys.argv[2]
        key_file = sys.argv[3]

        public_key = read_public_key_file(key_file)
        if not public_key:
            sys.exit(1)

        if add_ssh_key(api_key, name, public_key):
            print(f"Successfully added SSH key '{name}'")
        else:
            print(f"Failed to add SSH key '{name}'")
            sys.exit(1)

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: lambdalabs_ssh_keys.py delete <key_name>")
            sys.exit(1)
        key_name = sys.argv[2]

        if delete_ssh_key(api_key, key_name):
            print(f"Successfully deleted SSH key '{key_name}'")
        else:
            print(f"Failed to delete SSH key '{key_name}'")
            sys.exit(1)

    elif command == "validate":
        key_name = sys.argv[2] if len(sys.argv) > 2 else "kdevops-lambdalabs"
        success, message = validate_ssh_setup(api_key, key_name)
        print(message)
        if not success:
            sys.exit(1)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

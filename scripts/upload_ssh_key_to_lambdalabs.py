#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Upload SSH key to Lambda Labs via API.
This script helps upload your local SSH public key to Lambda Labs.
"""

import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
import lambdalabs_credentials

LAMBDALABS_API_BASE = "https://cloud.lambdalabs.com/api/v1"


def get_api_key():
    """Get Lambda Labs API key from credentials file."""
    # Get API key from credentials
    api_key = lambdalabs_credentials.get_api_key()
    if not api_key:
        print("Error: Lambda Labs API key not found in credentials file", file=sys.stderr)
        print("Please configure it with: python3 scripts/lambdalabs_credentials.py set 'your-api-key'", file=sys.stderr)
        sys.exit(1)
    return api_key


def make_api_request(endpoint, api_key, method="GET", data=None):
    """Make a request to Lambda Labs API."""
    url = f"{LAMBDALABS_API_BASE}{endpoint}"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        if data:
            data = json.dumps(data).encode("utf-8")

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode() if e.read() else "No error body"
        print(f"HTTP Error {e.code}: {e.reason}", file=sys.stderr)
        print(f"Error details: {error_body}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error making API request: {e}", file=sys.stderr)
        return None


def list_ssh_keys(api_key):
    """List existing SSH keys."""
    response = make_api_request("/ssh-keys", api_key)
    if response and "data" in response:
        return response["data"]
    return []


def create_ssh_key(api_key, name, public_key):
    """Create a new SSH key."""
    data = {"name": name, "public_key": public_key.strip()}
    response = make_api_request("/ssh-keys", api_key, method="POST", data=data)
    return response


def delete_ssh_key(api_key, key_id):
    """Delete an SSH key by ID."""
    response = make_api_request(f"/ssh-keys/{key_id}", api_key, method="DELETE")
    return response


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 upload_ssh_key_to_lambdalabs.py <command> [args]")
        print("Commands:")
        print("  list                              - List all SSH keys")
        print("  upload <name> <public_key_file>   - Upload a new SSH key")
        print("  delete <key_id>                   - Delete an SSH key by ID")
        print("  check <name>                      - Check if key with name exists")
        sys.exit(1)

    command = sys.argv[1]
    api_key = get_api_key()

    if command == "list":
        keys = list_ssh_keys(api_key)
        if keys:
            print("Existing SSH keys:")
            for key in keys:
                print(f"  - ID: {key.get('id')}, Name: {key.get('name')}")
        else:
            print("No SSH keys found or unable to retrieve keys")

    elif command == "upload":
        if len(sys.argv) < 4:
            print(
                "Error: upload requires <name> and <public_key_file> arguments",
                file=sys.stderr,
            )
            sys.exit(1)

        name = sys.argv[2]
        key_file = sys.argv[3]

        # Check if key already exists
        existing_keys = list_ssh_keys(api_key)
        for key in existing_keys:
            if key.get("name") == name:
                print(
                    f"SSH key with name '{name}' already exists (ID: {key.get('id')})"
                )
                print("Use 'delete' command first if you want to replace it")
                sys.exit(1)

        # Read the public key
        try:
            with open(os.path.expanduser(key_file), "r") as f:
                public_key = f.read().strip()
        except FileNotFoundError:
            print(f"Error: File {key_file} not found", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

        # Upload the key
        result = create_ssh_key(api_key, name, public_key)
        if result:
            print(f"Successfully uploaded SSH key '{name}'")
            if "data" in result:
                print(f"Key ID: {result['data'].get('id')}")
        else:
            print("Failed to upload SSH key")
            sys.exit(1)

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Error: delete requires <key_id> argument", file=sys.stderr)
            sys.exit(1)

        key_id = sys.argv[2]
        result = delete_ssh_key(api_key, key_id)
        if result is not None:
            print(f"Successfully deleted SSH key with ID: {key_id}")
        else:
            print("Failed to delete SSH key")
            sys.exit(1)

    elif command == "check":
        if len(sys.argv) < 3:
            print("Error: check requires <name> argument", file=sys.stderr)
            sys.exit(1)

        name = sys.argv[2]
        existing_keys = list_ssh_keys(api_key)
        for key in existing_keys:
            if key.get("name") == name:
                print(f"SSH key '{name}' exists (ID: {key.get('id')})")
                sys.exit(0)
        print(f"SSH key '{name}' does not exist")
        sys.exit(1)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

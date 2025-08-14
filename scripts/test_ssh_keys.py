#!/usr/bin/env python3

import json
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lambdalabs_credentials import get_api_key


def list_ssh_keys():
    api_key = get_api_key()
    if not api_key:
        print("No API key found")
        return None

    url = "https://cloud.lambdalabs.com/api/v1/ssh-keys"
    headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "kdevops/1.0"}

    print(f"Attempting to list SSH keys...")
    print(f"URL: {url}")
    print(f"API Key prefix: {api_key[:15]}...")

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            return data
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        try:
            error_body = json.loads(e.read().decode())
            print(f"Error details: {json.dumps(error_body, indent=2)}")
        except:
            pass
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def delete_ssh_key(key_name):
    api_key = get_api_key()
    if not api_key:
        print("No API key found")
        return False

    url = f"https://cloud.lambdalabs.com/api/v1/ssh-keys/{key_name}"
    headers = {"Authorization": f"Bearer {api_key}", "User-Agent": "kdevops/1.0"}

    print(f"Attempting to delete SSH key: {key_name}")

    try:
        req = urllib.request.Request(url, headers=headers, method="DELETE")
        with urllib.request.urlopen(req) as response:
            print(f"Successfully deleted key: {key_name}")
            return True
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        try:
            error_body = json.loads(e.read().decode())
            print(f"Error details: {json.dumps(error_body, indent=2)}")
        except:
            pass
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    # First try to list keys
    keys_data = list_ssh_keys()

    if keys_data:
        print("\nSSH Keys found:")
        print(json.dumps(keys_data, indent=2))

        # Extract key names
        if "data" in keys_data:
            keys = keys_data["data"]
        else:
            keys = keys_data if isinstance(keys_data, list) else []

        if keys:
            print("\nAttempting to delete all keys...")
            for key in keys:
                if isinstance(key, dict):
                    key_name = key.get("name") or key.get("id")
                    if key_name:
                        delete_ssh_key(key_name)
                elif isinstance(key, str):
                    delete_ssh_key(key)
    else:
        print("\nCould not retrieve SSH keys")

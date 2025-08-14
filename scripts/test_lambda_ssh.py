#!/usr/bin/env python3

import os
import json
import urllib.request
import urllib.error
import lambdalabs_credentials

# Get API key from credentials file
# Get API key from credentials
api_key = lambdalabs_credentials.get_api_key()
if not api_key:
    print("No Lambda Labs API key found in credentials file")
    print("Please configure it with: python3 scripts/lambdalabs_credentials.py set 'your-api-key'")
    exit(1)

print(f"API Key length: {len(api_key)}")
print(f"API Key prefix: {api_key[:30]}...")


def make_request(endpoint, method="GET", data=None):
    """Make API request to Lambda Labs"""
    url = f"https://cloud.lambdalabs.com/api/v1{endpoint}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "kdevops/1.0",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    req_data = None
    if data and method in ["POST", "PUT", "PATCH", "DELETE"]:
        req_data = json.dumps(data).encode("utf-8")

    try:
        req = urllib.request.Request(url, headers=headers, data=req_data, method=method)
        with urllib.request.urlopen(req) as response:
            content = response.read().decode()
            if content:
                return json.loads(content)
            return {"status": "success"}
    except urllib.error.HTTPError as e:
        print(f"\nHTTP Error {e.code} for {method} {endpoint}")
        try:
            error_content = e.read().decode()
            error_data = json.loads(error_content)
            print(f"Error: {json.dumps(error_data, indent=2)}")
        except:
            print(f"Error response: {error_content[:500]}")
        return None
    except Exception as e:
        print(f"\nException for {method} {endpoint}: {e}")
        return None


# Test different endpoints
print("\n1. Testing /instances endpoint...")
result = make_request("/instances")
if result and "data" in result:
    print(f"   ✓ Instances: Found {len(result['data'])} instances")
else:
    print("   ✗ Instances endpoint failed")

print("\n2. Testing /instance-types endpoint...")
result = make_request("/instance-types")
if result and "data" in result:
    print(f"   ✓ Instance types: Found {len(result['data'])} types")
else:
    print("   ✗ Instance types endpoint failed")

print("\n3. Testing /ssh-keys endpoint...")
result = make_request("/ssh-keys")
if result:
    print(f"   ✓ SSH Keys endpoint works!")
    if "data" in result:
        keys = result["data"]
        print(f"   Found {len(keys)} SSH keys:")
        for key in keys:
            if isinstance(key, dict):
                name = key.get("name", key.get("id", "unknown"))
                print(f"     - {name}")
            else:
                print(f"     - {key}")

        # Try to delete keys
        print("\n4. Attempting to delete SSH keys...")
        for key in keys:
            if isinstance(key, dict):
                key_name = key.get("name", key.get("id"))
            else:
                key_name = key

            if key_name:
                print(f"   Deleting key: {key_name}")
                delete_result = make_request(f"/ssh-keys/{key_name}", method="DELETE")
                if delete_result is not None:
                    print(f"     ✓ Deleted {key_name}")
                else:
                    print(f"     ✗ Failed to delete {key_name}")
    else:
        print("   Response:", json.dumps(result, indent=2))
else:
    print("   ✗ SSH Keys endpoint failed")

print("\n5. Testing if keys were deleted...")
result = make_request("/ssh-keys")
if result and "data" in result:
    print(f"   Remaining keys: {len(result['data'])}")

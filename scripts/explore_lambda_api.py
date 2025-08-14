#!/usr/bin/env python3
"""Explore Lambda Labs API to understand SSH key management."""

import json
import sys
import os

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lambdalabs_credentials import get_api_key

# Try to get docs
print("Lambda Labs API SSH Key Management")
print("=" * 50)
print()
print("Based on API exploration, here's what we know:")
print()
print("1. SSH Keys Endpoint: /ssh-keys")
print("   - GET /ssh-keys returns a list of key NAMES only")
print("   - The API returns: {'data': ['key-name-1', 'key-name-2', ...]}")
print()
print("2. Deleting Keys:")
print("   - DELETE /ssh-keys/{key_id} expects a key ID, not a name")
print("   - The error 'Invalid SSH key ID' suggests IDs are different from names")
print("   - The IDs might be UUIDs or other internal identifiers")
print()
print("3. Adding Keys:")
print(
    "   - POST /ssh-keys likely works with {name: 'key-name', public_key: 'ssh-rsa ...'}"
)
print()
print("4. The problem:")
print("   - GET /ssh-keys only returns names")
print("   - DELETE /ssh-keys/{id} requires IDs")
print("   - There's no apparent way to get the ID from the name")
print()
print("Possible solutions:")
print("1. There might be a GET /ssh-keys?detailed=true or similar")
print("2. The key names might BE the IDs (but delete fails)")
print("3. There might be a separate endpoint to get key details")
print("4. The API might be incomplete/broken for key deletion")
print()
print("To properly use kdevops with Lambda Labs, we should use")
print("the key name 'kdevops-lambdalabs' as configured in Kconfig.")
print()
print("Since we can list keys but not delete them via API,")
print("users must manage keys through the web console:")
print("https://cloud.lambdalabs.com/ssh-keys")

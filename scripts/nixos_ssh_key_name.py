#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""Generate SSH key name for NixOS VMs based on directory location."""

import os
import sys
import hashlib


def get_ssh_key_name():
    """Generate SSH key name based on kdevops project directory."""
    # Find the kdevops root directory
    # Start from the script's location
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # The script is in kdevops/scripts/, so go up one level
    kdevops_root = os.path.dirname(script_dir)

    # Use the kdevops root directory for consistent key naming
    # This ensures the same key is used regardless of where the script is called from
    cwd = kdevops_root

    # Get the last two directory components for the key name
    path_parts = cwd.split("/")
    if len(path_parts) >= 2:
        # Use last two directories
        key_suffix = "-".join(path_parts[-2:])
    else:
        # Use just the last directory
        key_suffix = path_parts[-1] if path_parts else "kdevops"

    # Create a short hash to ensure uniqueness
    path_hash = hashlib.sha256(cwd.encode()).hexdigest()[:8]

    # Construct the key name
    key_name = f"kdevops-nixos-{key_suffix}-{path_hash}"

    return key_name


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--path":
        # Return full path to key
        key_name = get_ssh_key_name()
        key_path = os.path.expanduser(f"~/.ssh/{key_name}")
        print(key_path)
    else:
        # Return just the key name
        print(get_ssh_key_name())


if __name__ == "__main__":
    main()

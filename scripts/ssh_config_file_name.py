#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Generate a unique SSH config file name based on the current directory.
This ensures each kdevops instance uses its own SSH config file.
"""

import hashlib
import os
import sys


def get_directory_hash(path: str, length: int = 8) -> str:
    """
    Generate a short hash of the directory path.

    Args:
        path: Directory path to hash
        length: Number of hex characters to use (default 8)

    Returns:
        Hex string of specified length
    """
    # Get the absolute path to ensure consistency
    abs_path = os.path.abspath(path)

    # Create SHA256 hash of the path
    hash_obj = hashlib.sha256(abs_path.encode("utf-8"))

    # Return first N characters of the hex digest
    return hash_obj.hexdigest()[:length]


def generate_ssh_config_filename(base_path: str = "~/.ssh/config_kdevops") -> str:
    """
    Generate a unique SSH config filename for the current directory.

    Args:
        base_path: Base path for the SSH config file (default ~/.ssh/config_kdevops)

    Returns:
        Unique SSH config filename like "~/.ssh/config_kdevops_a1b2c3d4"
    """
    cwd = os.getcwd()
    dir_hash = get_directory_hash(cwd)

    # Create the unique filename
    config_file = f"{base_path}_{dir_hash}"

    return config_file


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Usage: ssh_config_file_name.py [base_path]")
            print()
            print("Generate a unique SSH config filename based on current directory.")
            print()
            print("Options:")
            print(
                "  base_path   Base path for SSH config (default: ~/.ssh/config_kdevops)"
            )
            print()
            print("Examples:")
            print("  Default:    ~/.ssh/config_kdevops_a1b2c3d4")
            print("  Custom:     /tmp/ssh_config_a1b2c3d4")
            sys.exit(0)
        else:
            # Use provided base path
            print(generate_ssh_config_filename(sys.argv[1]))
    else:
        print(generate_ssh_config_filename())


if __name__ == "__main__":
    main()

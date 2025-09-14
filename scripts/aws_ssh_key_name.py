#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Generate a unique SSH key name for AWS based on the current directory.
This ensures each kdevops instance uses its own SSH key to prevent conflicts.
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


def get_project_name(path: str) -> str:
    """
    Extract a meaningful project name from the path.

    Args:
        path: Directory path

    Returns:
        Project name derived from directory
    """
    abs_path = os.path.abspath(path)

    # Get the last two directory components for context
    # e.g., /home/user/projects/kdevops -> projects-kdevops
    parts = abs_path.rstrip("/").split("/")

    if len(parts) >= 2:
        # Use last two directories
        project_parts = parts[-2:]
        # Filter out generic names
        filtered = [
            p
            for p in project_parts
            if p not in ["data", "home", "root", "usr", "var", "tmp", "cloud", "opt"]
        ]
        if filtered:
            return "-".join(filtered)

    # Fallback to just the last directory
    return parts[-1] if parts else "kdevops"


def generate_ssh_key_name(
    prefix: str = "kdevops-aws", include_project: bool = True
) -> str:
    """
    Generate a unique SSH key name for the current directory.

    Args:
        prefix: Prefix for the key name (default "kdevops-aws")
        include_project: Include project name in the key (default True)

    Returns:
        Unique SSH key name like "kdevops-aws-projectname-a1b2c3d4"
    """
    # Find the kdevops root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    kdevops_root = os.path.dirname(script_dir)

    # Use the kdevops root directory for consistent key naming
    dir_hash = get_directory_hash(kdevops_root)

    parts = [prefix]

    if include_project:
        project = get_project_name(kdevops_root)
        # Limit project name length and sanitize
        project = project.replace("_", "-").replace(".", "-")[:20]
        parts.append(project)

    parts.append(dir_hash)

    # Create the key name
    key_name = "-".join(parts)

    # Ensure it's a valid AWS key name (alphanumeric, hyphens, underscores)
    key_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in key_name)

    # Remove multiple consecutive hyphens
    while "--" in key_name:
        key_name = key_name.replace("--", "-")

    # AWS key pair names have a 255 character limit, but let's be reasonable
    if len(key_name) > 60:
        # Keep prefix and full hash for uniqueness
        key_name = f"{prefix}-{dir_hash}"

    return key_name.strip("-")


def get_ssh_key_path(key_type: str = "") -> str:
    """
    Generate the local SSH key file path based on directory.

    Args:
        key_type: Either "" for private key, ".pub" for public key

    Returns:
        Path to SSH key file
    """
    key_name = generate_ssh_key_name()
    return os.path.expanduser(f"~/.ssh/{key_name}{key_type}")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h":
            print("Usage: aws_ssh_key_name.py [--simple|--path|--pubkey-path]")
            print()
            print("Generate a unique SSH key name based on current directory.")
            print()
            print("Options:")
            print("  --simple       Generate simple name without project context")
            print("  --path         Output full path to private key file")
            print("  --pubkey-path  Output full path to public key file")
            print("  --help         Show this help message")
            print()
            print("Examples:")
            print("  Default:       kdevops-aws-projectname-a1b2c3d4")
            print("  Simple:        kdevops-aws-a1b2c3d4")
            print("  Path:          /home/user/.ssh/kdevops-aws-projectname-a1b2c3d4")
            print(
                "  Pubkey Path:   /home/user/.ssh/kdevops-aws-projectname-a1b2c3d4.pub"
            )
            sys.exit(0)
        elif sys.argv[1] == "--simple":
            print(generate_ssh_key_name(include_project=False))
        elif sys.argv[1] == "--path":
            print(get_ssh_key_path())
        elif sys.argv[1] == "--pubkey-path":
            print(get_ssh_key_path(".pub"))
        else:
            print(f"Unknown option: {sys.argv[1]}", file=sys.stderr)
            sys.exit(1)
    else:
        print(generate_ssh_key_name())


if __name__ == "__main__":
    main()

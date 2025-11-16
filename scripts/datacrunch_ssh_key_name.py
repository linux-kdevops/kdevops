#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Generate unique SSH key name for DataCrunch based on project directory.
This ensures each kdevops project uses its own SSH key for security isolation.
"""

import os
import sys
import hashlib


def get_unique_key_name() -> str:
    """
    Generate a unique SSH key name based on current directory.

    The name format is: kdevops-datacrunch-<hash>
    where hash is an 8-character MD5 hash of the directory path.

    This ensures:
    - Different projects get different keys
    - Same project always gets the same key name
    - Keys are easy to identify as kdevops-related
    """
    # Get current directory path
    cwd = os.getcwd()

    # Create hash of directory path
    dir_hash = hashlib.md5(cwd.encode()).hexdigest()[:8]

    # Format: kdevops-datacrunch-<hash>
    return f"kdevops-datacrunch-{dir_hash}"


def main():
    """Output the unique key name for the current directory."""
    print(get_unique_key_name())
    return 0


if __name__ == "__main__":
    sys.exit(main())

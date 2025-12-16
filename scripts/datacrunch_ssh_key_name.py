#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Generate unique SSH key name for DataCrunch based on git repository root.
This ensures each kdevops project uses its own SSH key for security isolation.
"""

import os
import sys
import hashlib
import subprocess


def get_unique_key_name() -> str:
    """
    Generate a unique SSH key name based on the git repository root.

    The name format is: kdevops-datacrunch-<hash>
    where hash is an 8-character MD5 hash of the repository root path.

    This ensures:
    - Different projects get different keys
    - Same project always gets the same key name
    - Keys are easy to identify as kdevops-related

    Uses the git repository root to ensure consistent key names regardless
    of which subdirectory the script is invoked from. Falls back to the
    current working directory if not in a git repository.
    """
    # Get git repository root, or fall back to current directory
    try:
        project_path = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        project_path = os.getcwd()

    # Create hash of project path
    dir_hash = hashlib.md5(project_path.encode()).hexdigest()[:8]

    # Format: kdevops-datacrunch-<hash>
    return f"kdevops-datacrunch-{dir_hash}"


def main():
    """Output the unique key name for the current directory."""
    print(get_unique_key_name())
    return 0


if __name__ == "__main__":
    sys.exit(main())

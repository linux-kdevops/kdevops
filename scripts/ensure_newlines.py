#!/usr/bin/env python3
"""
Ensure all text files end with a newline
"""

import os
import sys
from pathlib import Path


def needs_newline(file_path):
    """Check if file needs a newline at the end"""
    try:
        with open(file_path, "rb") as f:
            content = f.read()
            if not content:
                return False
            # Skip binary files
            if b"\0" in content:
                return False
            return not content.endswith(b"\n")
    except:
        return False


def add_newline(file_path):
    """Add newline to end of file"""
    try:
        with open(file_path, "a") as f:
            f.write("\n")
        return True
    except:
        return False


def main():
    """Main function"""
    extensions = [".py", ".yml", ".yaml", ".sh", ".md", ".txt", ".j2", ".cfg"]
    filenames = ["Makefile", "Kconfig", "hosts", ".gitignore", "LICENSE"]

    fixed_count = 0

    for root, dirs, files in os.walk("."):
        # Skip hidden directories and common non-source directories
        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") and d not in ["__pycache__", "node_modules"]
        ]

        for file in files:
            file_path = os.path.join(root, file)

            # Check if file should be processed
            should_process = False
            if any(file.endswith(ext) for ext in extensions):
                should_process = True
            elif (
                file in filenames
                or file.startswith("Makefile")
                or file.endswith("Kconfig")
            ):
                should_process = True

            if should_process and needs_newline(file_path):
                if add_newline(file_path):
                    print(f"Added newline to: {file_path}")
                    fixed_count += 1

    print(f"\nFixed {fixed_count} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())

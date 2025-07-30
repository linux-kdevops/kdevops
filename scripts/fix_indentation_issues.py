#!/usr/bin/env python3
"""
Fix indentation issues in files - convert between tabs and spaces as appropriate
"""

import os
import sys
from pathlib import Path


def fix_file_indentation(file_path, dry_run=False):
    """Fix indentation in a single file"""
    fixed = False

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        # Skip binary files
        if b"\0" in content:
            return False

        original_content = content
        lines = content.decode("utf-8", errors="ignore").splitlines(keepends=True)

        # Determine file type
        file_ext = Path(file_path).suffix.lower()
        is_yaml = file_ext in [".yml", ".yaml"]
        is_makefile = "Makefile" in Path(file_path).name or file_ext == ".mk"
        is_python = file_ext == ".py"

        new_lines = []

        for line_num, line in enumerate(lines, 1):
            if not line.strip():  # Keep empty lines as-is
                new_lines.append(line)
                continue

            # Get leading whitespace
            leading_ws = line[: len(line) - len(line.lstrip())]
            rest_of_line = line[len(leading_ws) :]

            if is_yaml or is_python:
                # Convert any tabs to spaces (4 spaces per tab)
                if "\t" in leading_ws:
                    new_leading = leading_ws.replace("\t", "    ")
                    new_line = new_leading + rest_of_line
                    new_lines.append(new_line)
                    if not dry_run:
                        print(f"  ✅ Line {line_num}: Converted tabs to spaces")
                    fixed = True
                else:
                    new_lines.append(line)
            elif is_makefile:
                # Check if this is a recipe line
                if line_num > 1 and lines[line_num - 2].strip().endswith(":"):
                    # Recipe line should start with tab
                    if leading_ws and not leading_ws.startswith("\t"):
                        # Convert leading spaces to tab
                        space_count = len(leading_ws)
                        tab_count = (space_count + 3) // 4  # Round up
                        new_leading = "\t" * tab_count
                        new_line = new_leading + rest_of_line
                        new_lines.append(new_line)
                        if not dry_run:
                            print(
                                f"  ✅ Line {line_num}: Converted spaces to tabs (Makefile recipe)"
                            )
                        fixed = True
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)

        if fixed and not dry_run:
            new_content = "".join(new_lines).encode("utf-8")
            with open(file_path, "wb") as f:
                f.write(new_content)

    except Exception as e:
        print(f"  ❌ Error processing file: {e}")
        return False

    return fixed


def main():
    """Main function to fix indentation issues"""
    import argparse

    parser = argparse.ArgumentParser(description="Fix indentation issues in files")
    parser.add_argument(
        "paths", nargs="*", help="Files to check (default: all git tracked files)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fixed without changing files",
    )

    args = parser.parse_args()

    if args.paths:
        paths = args.paths
    else:
        # Default to git tracked files
        import subprocess

        try:
            result = subprocess.run(
                ["git", "ls-files"], capture_output=True, text=True, check=True
            )
            paths = result.stdout.strip().split("\n") if result.stdout.strip() else []
        except subprocess.CalledProcessError:
            print("Error: Not in a git repository")
            return 1

    total_fixed = 0

    for path_str in paths:
        if not path_str:
            continue

        path = Path(path_str)
        if not path.exists() or not path.is_file():
            continue

        # Skip binary files and certain extensions
        if path.suffix in [".pyc", ".so", ".o", ".bin", ".jpg", ".png", ".gif", ".ico"]:
            continue

        if fix_file_indentation(path, args.dry_run):
            total_fixed += 1
            if not args.dry_run:
                print(f"{path}:")

    if total_fixed > 0:
        if args.dry_run:
            print(f"\nWould fix indentation in {total_fixed} files")
            print("Run without --dry-run to apply fixes")
        else:
            print(f"\n✅ Fixed indentation in {total_fixed} files")
    else:
        print("✅ No indentation issues found!")

    return 0


if __name__ == "__main__":
    sys.exit(main())

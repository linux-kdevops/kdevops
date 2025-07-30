#!/usr/bin/env python3
"""
Detect indentation issues in files - mixed tabs/spaces or incorrect indentation
"""

import os
import sys
from pathlib import Path


def check_file_indentation(file_path):
    """Check a single file for indentation issues"""
    issues = []

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        # Skip binary files
        if b"\0" in content:
            return issues

        lines = content.decode("utf-8", errors="ignore").splitlines()

        # Determine expected indentation style
        uses_tabs = False
        uses_spaces = False

        for line in lines[:100]:  # Check first 100 lines to determine style
            if line.startswith("\t"):
                uses_tabs = True
            elif line.startswith(" "):
                uses_spaces = True

        # Special rules for certain file types
        file_ext = Path(file_path).suffix.lower()
        is_yaml = file_ext in [".yml", ".yaml"]
        is_makefile = "Makefile" in Path(file_path).name or file_ext == ".mk"
        is_python = file_ext == ".py"

        # Check each line for issues
        for line_num, line in enumerate(lines, 1):
            if not line.strip():  # Skip empty lines
                continue

            # Get leading whitespace
            leading_ws = line[: len(line) - len(line.lstrip())]

            if is_yaml:
                # YAML should use spaces only
                if "\t" in leading_ws:
                    issues.append(
                        f"Line {line_num}: Tab character in YAML file (should use spaces)"
                    )
            elif is_makefile:
                # Makefiles need tabs for recipe lines
                # But can use spaces for variable definitions
                stripped = line.lstrip()
                if stripped and not stripped.startswith("#"):
                    # Check if this looks like a recipe line (follows a target)
                    if line_num > 1 and lines[line_num - 2].strip().endswith(":"):
                        if leading_ws and not leading_ws.startswith("\t"):
                            issues.append(
                                f"Line {line_num}: Recipe line should start with tab"
                            )
            elif is_python:
                # Python should use spaces only
                if "\t" in leading_ws:
                    issues.append(
                        f"Line {line_num}: Tab character in Python file (PEP 8 recommends spaces)"
                    )
            else:
                # For other files, check for mixed indentation
                if leading_ws:
                    has_tabs = "\t" in leading_ws
                    has_spaces = " " in leading_ws

                    if has_tabs and has_spaces:
                        issues.append(
                            f"Line {line_num}: Mixed tabs and spaces in indentation"
                        )
                    elif uses_tabs and uses_spaces:
                        # File uses both styles
                        if has_tabs and not uses_tabs:
                            issues.append(
                                f"Line {line_num}: Tab indentation (file mostly uses spaces)"
                            )
                        elif has_spaces and not uses_spaces:
                            issues.append(
                                f"Line {line_num}: Space indentation (file mostly uses tabs)"
                            )

    except Exception as e:
        issues.append(f"Error reading file: {e}")

    return issues


def main():
    """Main function to scan for indentation issues"""
    if len(sys.argv) > 1:
        paths = sys.argv[1:]
    else:
        # Default to git tracked files with modifications
        import subprocess

        try:
            result = subprocess.run(
                ["git", "diff", "--name-only"],
                capture_output=True,
                text=True,
                check=True,
            )
            paths = result.stdout.strip().split("\n") if result.stdout.strip() else []
            if not paths:
                print("No modified files found in git")
                return 0
        except subprocess.CalledProcessError:
            print("Error: Not in a git repository or git command failed")
            return 1
        except FileNotFoundError:
            print("Error: git command not found")
            return 1

    total_issues = 0
    files_with_issues = 0

    for path_str in paths:
        if not path_str:
            continue

        path = Path(path_str)
        if not path.exists() or not path.is_file():
            continue

        # Skip binary files and certain extensions
        if path.suffix in [".pyc", ".so", ".o", ".bin", ".jpg", ".png", ".gif", ".ico"]:
            continue

        issues = check_file_indentation(path)
        if issues:
            files_with_issues += 1
            total_issues += len(issues)
            print(f"\n{path}:")
            for issue in issues:
                print(f"  ⚠️  {issue}")

    if total_issues > 0:
        print(
            f"\nSummary: {total_issues} indentation issues found in {files_with_issues} files"
        )
        print("\nTo fix these issues:")
        print("- Use spaces only in YAML and Python files")
        print("- Use tabs for Makefile recipe lines")
        print("- Be consistent with indentation style within each file")
        return 1
    else:
        print("✅ No indentation issues found!")
        return 0


if __name__ == "__main__":
    sys.exit(main())

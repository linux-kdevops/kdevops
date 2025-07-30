#!/usr/bin/env python3
"""
Whitespace Issue Detector for kdevops

This script detects common whitespace issues that Claude AI tends to introduce:
- Trailing whitespace at end of lines
- Missing newline at end of file
- Excessive blank lines
"""

import os
import sys
from pathlib import Path


def check_file_whitespace(file_path):
    """Check a single file for whitespace issues"""
    issues = []

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        # Skip binary files
        if b"\0" in content:
            return issues

        lines = content.decode("utf-8", errors="ignore").splitlines(keepends=True)

        # Check trailing whitespace
        for line_num, line in enumerate(lines, 1):
            if line.rstrip("\n\r").endswith(" ") or line.rstrip("\n\r").endswith("\t"):
                issues.append(f"Line {line_num}: Trailing whitespace")

        # Check missing newline at end of file
        if content and not content.endswith(b"\n"):
            issues.append("Missing newline at end of file")

        # Check for excessive blank lines (more than 2 consecutive)
        blank_count = 0
        for line_num, line in enumerate(lines, 1):
            if line.strip() == "":
                blank_count += 1
            else:
                if blank_count > 2:
                    issues.append(
                        f"Line {line_num - blank_count}: {blank_count} consecutive blank lines"
                    )
                blank_count = 0

    except Exception as e:
        issues.append(f"Error reading file: {e}")

    return issues


def main():
    """Main function to scan for whitespace issues"""
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
                return
        except subprocess.CalledProcessError:
            print("Error: Not in a git repository or git command failed")
            return
        except FileNotFoundError:
            print("Error: git command not found")
            return

    total_issues = 0
    files_with_issues = 0

    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            print(f"Warning: {path} does not exist")
            continue

        if path.is_file():
            # Skip certain file types
            if path.suffix in [".pyc", ".so", ".o", ".bin", ".jpg", ".png", ".gif"]:
                continue

            issues = check_file_whitespace(path)
            if issues:
                files_with_issues += 1
                total_issues += len(issues)
                print(f"\n{path}:")
                for issue in issues:
                    print(f"  ⚠️  {issue}")

    print(
        f"\nSummary: {total_issues} whitespace issues found in {files_with_issues} files"
    )

    if total_issues > 0:
        print("\nTo fix these issues:")
        print("- Remove trailing spaces/tabs from lines")
        print("- Add newline at end of files")
        print("- Reduce excessive blank lines to 1-2 maximum")
        return 1
    else:
        print("✅ No whitespace issues found!")
        return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Whitespace Issue Fixer for kdevops

This script fixes common whitespace issues that Claude AI tends to introduce:
- Trailing whitespace at end of lines
- Missing newline at end of file
- Excessive blank lines (reduces to maximum 2 consecutive)
"""

import os
import sys
from pathlib import Path


def fix_file_whitespace(file_path):
    """Fix whitespace issues in a single file"""
    issues_fixed = []

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        # Skip binary files
        if b"\0" in content:
            return issues_fixed

        original_content = content.decode("utf-8", errors="ignore")
        lines = original_content.splitlines(keepends=True)
        modified = False

        # Fix trailing whitespace
        new_lines = []
        for line_num, line in enumerate(lines, 1):
            original_line = line
            # Remove trailing whitespace but preserve line endings
            if line.endswith("\r\n"):
                cleaned_line = line.rstrip(" \t\r\n") + "\r\n"
            elif line.endswith("\n"):
                cleaned_line = line.rstrip(" \t\n") + "\n"
            else:
                cleaned_line = line.rstrip(" \t")

            if original_line != cleaned_line:
                issues_fixed.append(f"Line {line_num}: Removed trailing whitespace")
                modified = True

            new_lines.append(cleaned_line)

        # Fix excessive blank lines (reduce to maximum 2 consecutive)
        final_lines = []
        blank_count = 0
        i = 0
        while i < len(new_lines):
            line = new_lines[i]
            if line.strip() == "":
                blank_count += 1
                if blank_count <= 2:
                    final_lines.append(line)
                else:
                    issues_fixed.append(f"Line {i+1}: Removed excessive blank line")
                    modified = True
            else:
                blank_count = 0
                final_lines.append(line)
            i += 1

        # Fix missing newline at end of file
        new_content = "".join(final_lines)
        if new_content and not new_content.endswith("\n"):
            new_content += "\n"
            issues_fixed.append("Added missing newline at end of file")
            modified = True

        # Write back if modified
        if modified:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

    except Exception as e:
        issues_fixed.append(f"Error processing file: {e}")

    return issues_fixed


def main():
    """Main function to fix whitespace issues"""
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

    total_fixes = 0
    files_fixed = 0

    for path_str in paths:
        path = Path(path_str)
        if not path.exists():
            print(f"Warning: {path} does not exist")
            continue

        if path.is_file():
            # Skip certain file types
            if path.suffix in [".pyc", ".so", ".o", ".bin", ".jpg", ".png", ".gif"]:
                continue

            fixes = fix_file_whitespace(path)
            if fixes:
                files_fixed += 1
                total_fixes += len(fixes)
                print(f"\n{path}:")
                for fix in fixes:
                    print(f"  ✅ {fix}")

    print(f"\nSummary: {total_fixes} whitespace issues fixed in {files_fixed} files")

    if total_fixes > 0:
        print("✅ Whitespace issues have been automatically fixed!")
        return 0
    else:
        print("✅ No whitespace issues found to fix!")
        return 0


if __name__ == "__main__":
    sys.exit(main())

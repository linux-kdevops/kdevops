#!/usr/bin/env python3
"""
Commit Message Format Checker for kdevops

This script checks the most recent commit message for proper formatting:
- If "Generated-by: Claude AI" is present, it must be immediately followed by
  "Signed-off-by:" with no blank lines in between
"""

import subprocess
import sys
import re


def get_latest_commit_message():
    """Get the latest commit message"""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--pretty=format:%B"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        print("Error: Failed to get commit message")
        return None
    except FileNotFoundError:
        print("Error: git command not found")
        return None


def check_commit_format(commit_msg):
    """Check commit message formatting"""
    issues = []
    if not commit_msg:
        return ["No commit message found"]
    lines = commit_msg.strip().split("\n")
    # Find Generated-by line
    generated_by_idx = None
    signed_off_by_idx = None
    for i, line in enumerate(lines):
        if line.startswith("Generated-by: Claude AI"):
            generated_by_idx = i
        elif line.startswith("Signed-off-by:"):
            signed_off_by_idx = i
    # If Generated-by is present, check formatting
    if generated_by_idx is not None:
        if signed_off_by_idx is None:
            issues.append(
                "Generated-by: Claude AI found but no Signed-off-by tag present"
            )
        else:
            # Check if Generated-by is immediately followed by Signed-off-by (no lines in between)
            if signed_off_by_idx != generated_by_idx + 1:
                lines_between = signed_off_by_idx - generated_by_idx - 1
                if lines_between > 0:
                    issues.append(
                        f"Generated-by: Claude AI must be immediately followed by Signed-off-by (found {lines_between} lines between them)"
                    )
                    for i in range(generated_by_idx + 1, signed_off_by_idx):
                        if lines[i].strip():
                            issues.append(f"  - Non-empty line at {i+1}: '{lines[i]}'")
                        else:
                            issues.append(f"  - Empty line at {i+1}")
    return issues


def main():
    """Main function to check commit message format"""
    commit_msg = get_latest_commit_message()
    if commit_msg is None:
        return 1
    issues = check_commit_format(commit_msg)
    if issues:
        print("❌ Commit message formatting issues found:")
        for issue in issues:
            print(f"  ⚠️  {issue}")
        print("\nLatest commit message:")
        print("=" * 50)
        print(commit_msg)
        print("=" * 50)
        print("\nCorrect format when using Generated-by:")
        print("Subject line")
        print("")
        print("Detailed description...")
        print("")
        print("Generated-by: Claude AI")
        print("Signed-off-by: Your Name <email@example.com>")
        return 1
    else:
        print("✅ Commit message formatting is correct!")
        return 0


if __name__ == "__main__":
    sys.exit(main())

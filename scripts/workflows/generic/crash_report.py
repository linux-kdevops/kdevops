#!/usr/bin/env python3
import os
import re
from pathlib import Path

CRASH_DIR = Path("crashes")
ANSI_ESCAPE_RE = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


def clean_lines(text):
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        line = ANSI_ESCAPE_RE.sub("", line)
        line = re.sub(r"[^\x20-\x7E\t]", "", line)
        if line.strip():
            cleaned.append(line)
    return "\n".join(cleaned)


def collect_host_logs(host_path):
    entries = []
    files = sorted(host_path.iterdir())
    seen_base = set()

    # First pass: collect decoded crash files
    for file in files:
        if not file.is_file():
            continue
        fname = file.name

        # Look for decoded crash variants first
        for suffix in [".crash", ".crash_and_corruption"]:
            if fname.endswith(".decoded" + suffix):
                # Store the original filename (without .decoded) in seen_base
                base = fname.replace(".decoded" + suffix, suffix)
                seen_base.add(base)
                entries.append(
                    {
                        "type": "crash",
                        "file": fname,
                        "content": clean_lines(file.read_text(errors="replace")),
                    }
                )

    # Second pass: collect remaining files (non-decoded crashes and other types)
    for file in files:
        if not file.is_file():
            continue
        fname = file.name

        # Handle undecoded crash files only if we didn't already see their decoded version
        for suffix in [".crash", ".crash_and_corruption"]:
            if fname.endswith(suffix) and not fname.endswith(".decoded" + suffix):
                if fname in seen_base:
                    continue  # decoded version already handled

                seen_base.add(fname)
                entries.append(
                    {
                        "type": "crash",
                        "file": fname,
                        "content": clean_lines(file.read_text(errors="replace")),
                    }
                )

        # Warnings or corruption always go in
        if fname.endswith(".warning"):
            entries.append(
                {
                    "type": "warning",
                    "file": fname,
                    "content": clean_lines(file.read_text(errors="replace")),
                }
            )
        elif fname.endswith(".corruption"):
            entries.append(
                {
                    "type": "corruption",
                    "file": fname,
                    "content": clean_lines(file.read_text(errors="replace")),
                }
            )

    return entries


def generate_commit_log():
    print("# Kernel crash report summary\n")
    for host_dir in sorted(CRASH_DIR.iterdir()):
        if not host_dir.is_dir():
            continue
        logs = collect_host_logs(host_dir)
        if not logs:
            continue
        print(f"## Host: {host_dir.name}\n")
        for entry in logs:
            tag = entry["type"].upper()
            print(f"### [{tag}] {entry['file']}")
            print("```")
            print(entry["content"])
            print("```\n")


if __name__ == "__main__":
    if not CRASH_DIR.exists():
        print(
            f"No crashes, filesystem corruption isues, or kernel warnings were detected on this run."
        )
        exit(0)
    generate_commit_log()

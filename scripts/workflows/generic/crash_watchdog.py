#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
This script is intended to run as a kernel-ci agent. Monitoring for crashes
and kernel warnings and reseting host after capturing essential information.
It can also be invoked as 'get_console.py' to retrieve the entire kernel log.
"""

import os
import sys
import subprocess
import re
import logging
import argparse
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from lib.crash import KernelCrashWatchdog

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("crash_watchdog")


def get_active_hosts():
    """Get the list of active hosts from kdevops configuration."""
    try:
        # First try to get the hosts from the ansible inventory
        result = subprocess.run(
            ["ansible-inventory", "-i", "hosts", "--list"],
            capture_output=True,
            text=True,
            check=True,
        )
        inventory = yaml.safe_load(result.stdout)
        hosts = inventory.get("baseline", {}).get("hosts", [])
        return sorted(set(hosts))
    except Exception as e:
        logger.error(f"Error getting active hosts: {e}")
        return []


def run_crash_watchdog_on_host(args, this_host_name):
    watchdog = KernelCrashWatchdog(
        host_name=this_host_name,
        output_dir=args.output_dir,
        full_log=args.full_log,
        decode_crash=not args.no_decode,
        reset_host=not args.no_reset,
        save_warnings=args.save_warnings,
    )

    crashed = False
    warnings_found = False

    crash_file, warning_file = watchdog.check_and_reset_host(
        method=args.method, get_fstests_log=args.fstests_log
    )

    if warning_file:
        logger.warning(f"Kernel warning and logged to {warning_file}")
        warnings_found = True
    elif args.save_warnings:
        logger.debug(f"No kernel warnings detected for host {this_host_name}")
    if crash_file:
        crashed = True
        logger.warning(f"Crash detected and logged to {crash_file}")
    else:
        logger.debug(f"No crash detected for host {this_host_name}")
    return crashed, [crash_file], warnings_found, warning_file


def run_crash_watchdog_all_hosts(args):
    """Check all active hosts for kernel crashes."""
    hosts = get_active_hosts()
    crash_detected = False
    crash_files = []
    warnings_detected = False
    warning_files = []

    logger.info(f"Checking {len(hosts)} hosts for kernel crashes: {', '.join(hosts)}")

    for host in hosts:
        host_crash_detected, crash_file, host_warnings_detected, warnings_file = (
            run_crash_watchdog_on_host(args, host)
        )
        if host_crash_detected and crash_file:
            crash_detected = True
            crash_files.append(crash_file)
            logger.warning(f"Crash detected in host {host}, logs saved to {crash_file}")
        if host_warnings_detected and warnings_file:
            warnings_detected = True
            warning_files.append(warning_file)
            logger.warning(
                f"Kernel warning found on host {host}, logs saved to {warning_file}"
            )

    return crash_detected, crash_files, warnings_detected, warning_files


def write_log_section(f, title, files, label):
    f.write(f"# {title}\n\n")
    for path in files:
        f.write(f"- {label} detected: {path}\n")
        try:
            with open(path, "r") as content_file:
                snippet = "".join(content_file.readlines()[:10]) + "\n...(truncated)..."
                f.write("\n```\n" + snippet + "\n```\n\n")
        except Exception as e:
            f.write(f"\nError reading {label.lower()} file: {e}\n\n")


def main():
    parser = argparse.ArgumentParser(
        description="Detect and handle kernel crashes or kernel warnings in hosts.",
        epilog="""
Examples:
  Detect and reset all hosts a crash was found (default):
    ./crash_watchdog.py

  Detect and reset host crash only on e3-ext4-2k guest:
    ./crash_watchdog.py --host-name e3-ext4-2k

  Detect using systemd-remote journal and show full kernel log:
    ./crash_watchdog.py e3-ext4-2k --method remote --full-log

  Skip decoding and skip reset:
    ./crash_watchdog.py e3-ext4-2k --no-decode --no-reset

  Just fetch the full kernel log using symlinked name:
    ln -s crash_watchdog.py get_console.py
    ./get_console.py e3-ext4-2k

  Use guestfs console log and do not decode:
    ./crash_watchdog.py e3-ext4-2k --method console --no-decode

  Use SSH to query the live journalctl output:
    ./crash_watchdog.py e3-ext4-2k --method ssh

  Disable guest reset when using libvirt:
    ./crash_watchdog.py e3-ext4-2k --no-reset

  Print full kernel logs for a specific fstest (all tests run with it):
    ./crash_watchdog.py e3-ext4-2k --fstests-log generic/750

  Get all kernel warnings only:
    ./crash_watchdog.py e3-ext4-2k --method remote --save-warnings sad.warn
        """,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "--host-name", help="Optional name of the host to check", default="all"
    )
    parser.add_argument(
        "--output-dir", help="Directory to store crash logs", default="crashes"
    )
    parser.add_argument(
        "--method",
        choices=["auto", "remote", "console", "ssh"],
        default="auto",
        help="Choose method to collect logs: auto, remote, console, or ssh",
    )
    parser.add_argument(
        "--full-log",
        action="store_true",
        help="Get full kernel log instead of only crash context",
    )
    parser.add_argument(
        "--no-decode",
        action="store_true",
        help="Disable decoding crash logs with decode_stacktrace.sh",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Do not reset the guest even if a crash is detected",
    )
    parser.add_argument(
        "--fstests-log",
        help="Show all kernel log lines for a specific fstests test ID (e.g., generic/750)",
    )
    parser.add_argument(
        "--save-warnings",
        help="Do you want detected and save kernel warnings",
        default=True,
    )
    args = parser.parse_args()
    crash_files = []
    warnings_files = []

    invoked_name = os.path.basename(sys.argv[0])
    if invoked_name == "get_console.py":
        args.no_reset = True
        args.save_warnings = False
        args.full_log_mode = True

    if args.host_name != "all":
        crash_detected, crash_files, warnings_detected, warnings_files = (
            run_crash_watchdog_on_host(args, args.host_name)
        )
    else:
        crash_detected, crash_files, warnings_detected, warnings_files = (
            run_crash_watchdog_all_hosts(args)
        )

    if warnings_detected:
        logger.warning("Kernel warnings detected in one or more hosts")

    if crash_detected:
        logger.warning("Kernel crashes detected in one or more hosts")
        sys.exit(1)
    else:
        logger.info("No kernel crashes detected")
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
"""
DataCrunch OS-NVMe Volume Cache Management

This script manages the volume mapping cache for DataCrunch instances, enabling
persistent volume reuse to speed up reprovisioning and reduce costs.

Volume mappings are stored in:
~/.cache/kdevops/datacrunch/<prefix>.yml

Usage:
    volume_cache.py save <prefix> <hostname> <volume_id>
    volume_cache.py load <prefix> <hostname>
    volume_cache.py delete <prefix> <hostname>
    volume_cache.py list <prefix>
    volume_cache.py clear <prefix>
"""

import argparse
import os
import sys
import yaml
from pathlib import Path


def get_cache_dir():
    """Get the cache directory path, creating it if needed."""
    cache_dir = Path.home() / ".cache" / "kdevops" / "datacrunch"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cache_file(prefix):
    """Get the cache file path for a given prefix."""
    return get_cache_dir() / f"{prefix}.yml"


def load_cache(prefix):
    """Load volume mappings from cache file."""
    cache_file = get_cache_file(prefix)
    if not cache_file.exists():
        return {}

    try:
        with open(cache_file, "r") as f:
            data = yaml.safe_load(f)
            return data if data else {}
    except Exception as e:
        print(f"Error loading cache: {e}", file=sys.stderr)
        return {}


def save_cache(prefix, mappings):
    """Save volume mappings to cache file."""
    cache_file = get_cache_file(prefix)
    try:
        with open(cache_file, "w") as f:
            yaml.dump(mappings, f, default_flow_style=False)
        return True
    except Exception as e:
        print(f"Error saving cache: {e}", file=sys.stderr)
        return False


def cmd_save(args):
    """Save a volume mapping to the cache."""
    mappings = load_cache(args.prefix)
    mappings[args.hostname] = args.volume_id
    if save_cache(args.prefix, mappings):
        print(f"Saved: {args.hostname} -> {args.volume_id}")
        return 0
    return 1


def cmd_load(args):
    """Load a volume mapping from the cache."""
    mappings = load_cache(args.prefix)
    volume_id = mappings.get(args.hostname)
    if volume_id:
        print(volume_id)
        return 0
    else:
        print(f"No volume mapping found for {args.hostname}", file=sys.stderr)
        return 1


def cmd_delete(args):
    """Delete a volume mapping from the cache."""
    mappings = load_cache(args.prefix)
    if args.hostname in mappings:
        del mappings[args.hostname]
        if save_cache(args.prefix, mappings):
            print(f"Deleted mapping for {args.hostname}")
            return 0
    else:
        print(f"No mapping found for {args.hostname}", file=sys.stderr)
        return 1


def cmd_list(args):
    """List all volume mappings for a prefix."""
    mappings = load_cache(args.prefix)
    if not mappings:
        print(f"No volume mappings for prefix '{args.prefix}'")
        return 0

    print(f"Volume mappings for prefix '{args.prefix}':")
    for hostname, volume_id in sorted(mappings.items()):
        print(f"  {hostname}: {volume_id}")
    return 0


def cmd_clear(args):
    """Clear all volume mappings for a prefix."""
    cache_file = get_cache_file(args.prefix)
    if cache_file.exists():
        cache_file.unlink()
        print(f"Cleared all mappings for prefix '{args.prefix}'")
    else:
        print(f"No cache file found for prefix '{args.prefix}'")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Manage DataCrunch OS-NVMe volume cache"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # save command
    save_parser = subparsers.add_parser("save", help="Save volume mapping")
    save_parser.add_argument("prefix", help="KDEVOPS_HOSTS_PREFIX")
    save_parser.add_argument("hostname", help="Instance hostname")
    save_parser.add_argument("volume_id", help="OS volume ID")
    save_parser.set_defaults(func=cmd_save)

    # load command
    load_parser = subparsers.add_parser("load", help="Load volume mapping")
    load_parser.add_argument("prefix", help="KDEVOPS_HOSTS_PREFIX")
    load_parser.add_argument("hostname", help="Instance hostname")
    load_parser.set_defaults(func=cmd_load)

    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete volume mapping")
    delete_parser.add_argument("prefix", help="KDEVOPS_HOSTS_PREFIX")
    delete_parser.add_argument("hostname", help="Instance hostname")
    delete_parser.set_defaults(func=cmd_delete)

    # list command
    list_parser = subparsers.add_parser("list", help="List all volume mappings")
    list_parser.add_argument("prefix", help="KDEVOPS_HOSTS_PREFIX")
    list_parser.set_defaults(func=cmd_list)

    # clear command
    clear_parser = subparsers.add_parser("clear", help="Clear all volume mappings")
    clear_parser.add_argument("prefix", help="KDEVOPS_HOSTS_PREFIX")
    clear_parser.set_defaults(func=cmd_clear)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

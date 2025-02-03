#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

import argparse


def get_ansible_verbosity(av: str, max_level: int = 6) -> str:
    """Return Ansible verbosity flag (e.g. -vv or emtpy)."""
    try:
        av = int(av)
    except ValueError:
        return ""
    av = max(0, min(av, max_level))
    return "-" + "v" * av if av > 0 else ""


def main():
    parser = argparse.ArgumentParser(
        description="Validate and return Ansible verbosity level."
    )
    parser.add_argument("--av", type=str, default="0", help="Verbosity level (0-6)")

    args = parser.parse_args()
    print(get_ansible_verbosity(args.av))


if __name__ == "__main__":
    main()

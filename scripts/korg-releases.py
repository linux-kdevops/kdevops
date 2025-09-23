#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
import sys
import logging
import argparse
import json
import urllib.request
import socket
import re


def parser():
    parser = argparse.ArgumentParser(description="kernel.org/releases.json checker")
    parser.add_argument("--debug", action="store_true", help="debug")
    parser.add_argument(
        "--moniker",
        help="moniker (mainline, stable, longterm or linux-next)",
        required=True,
    )
    parser.add_argument(
        "--pname",
        help="project name for User-Agent request",
        default="kdevops",
    )
    parser.add_argument(
        "--pversion",
        help="project version for User-Agent request",
        default="5.0.2",
    )
    return parser


def _check_connection(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout):
            logging.debug(f"Connection to {host} on port {port} succeeded!")
            return True
    except (socket.timeout, socket.error) as e:
        logging.debug(f"Connection to {host} on port {port} failed: {e}")
        return False


def kreleases(args) -> None:
    """Get the latest kernel releases from kernel.org/releases.json"""

    reflist = []
    if _check_connection("kernel.org", 80):
        _url = "https://www.kernel.org/releases.json"
        req = urllib.request.Request(
            _url,
            headers={
                "User-Agent": f"{args.pname}/{args.pversion} (kdevops@lists.linux.dev)"
            },
        )
        with urllib.request.urlopen(req) as url:
            data = json.load(url)

            for release in data["releases"]:
                if release["moniker"] == args.moniker:
                    # Check if release.json is aa.bb.cc type
                    if re.compile(r"^\d+\.\d+(\.\d+|-rc\d+)?$").match(
                        release["version"]
                    ):
                        reflist.append("v" + release["version"])
                    else:
                        reflist.append(release["version"])

    logging.debug(f"{reflist}")
    for r in reflist:
        print(r)


def main() -> None:
    """Kconfig choice generator for git refereces"""
    log = logging.getLogger()
    log.setLevel(logging.INFO)
    p = parser()
    args, _ = p.parse_known_args()
    if args.debug:
        log.setLevel(logging.DEBUG)

    kreleases(args)


if __name__ == "__main__":
    ret = 0
    try:
        main()
    except Exception:
        ret = 1
        import traceback

        traceback.print_exc()
    sys.exit(ret)

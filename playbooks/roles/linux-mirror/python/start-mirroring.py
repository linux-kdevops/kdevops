#!/usr/bin/python3
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Start mirroring based on mirrors.yaml file

import argparse
import yaml
import json
import sys
import pprint
import subprocess
import time
import os
from pathlib import Path
import subprocess

topdir = os.environ.get("TOPDIR", ".")
yaml_dir = topdir + "/playbooks/roles/linux-mirror/linux-mirror-systemd/"
default_mirrors_yaml = yaml_dir + "mirrors.yaml"

mirror_path = "/mirror/"


def mirror_entry(mirror, args):
    short_name = mirror["short_name"]
    url = mirror["url"]
    target = mirror["target"]
    reference = None
    reference_args = []

    if mirror.get("reference"):
        reference = mirror_path + mirror.get("reference")
        reference_args = ["--reference", reference]

    if args.verbose:
        sys.stdout.write("\tshort_name: %s\n" % (short_name))
        sys.stdout.write("\turl: %s\n" % (url))
        sys.stdout.write("\ttarget: %s\n" % (url))
        if reference is None:
            sys.stdout.write("\treference: %s\n" % ("None"))
        else:
            sys.stdout.write("\treference: %s\n" % (reference))
    cmd = [
        "git",
        "-C",
        mirror_path,
        "clone",
        "--verbose",
        "--progress",
        "--mirror",
        url,
        target,
    ]
    cmd = cmd + reference_args
    mirror_target = mirror_path + target
    if os.path.isdir(mirror_target):
        return
    sys.stdout.write("Mirroring: %s onto %s\n" % (short_name, mirror_target))
    if args.verbose:
        sys.stdout.write("%s\n" % (cmd))
        sys.stdout.write("%s\n" % (" ".join(cmd)))
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        universal_newlines=True,
    )
    try:
        data = process.communicate(timeout=12000)
    except subprocess.TimeoutExpired:
        return "Timeout"
    else:
        process.wait()
        if process.returncode != 0:
            raise Exception(f"Failed clone with:\n%s" % (" ".join(cmd)))


def main():
    parser = argparse.ArgumentParser(description="start-mirroring")
    parser.add_argument(
        "--yaml-mirror",
        metavar="<yaml_mirror>",
        type=str,
        default=default_mirrors_yaml,
        help="The yaml mirror input file.",
    )
    parser.add_argument(
        "--verbose",
        const=True,
        default=False,
        action="store_const",
        help="Be verbose on otput.",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.yaml_mirror):
        sys.stdout.write("%s does not exist\n" % (yaml_mirror))
        sys.exit(1)

    # load the yaml input file
    with open(f"{args.yaml_mirror}") as stream:
        yaml_vars = yaml.safe_load(stream)

    if yaml_vars.get("mirrors") is None:
        raise Exception(f"Missing mirrors descriptions on %s" % (args.yaml_mirror))

    if args.verbose:
        sys.stdout.write("Yaml mirror input: %s\n\n" % args.yaml_mirror)

    # We do 3 passes, first to check the file has all requirements
    # properly defined, and we bail if any of them have something missing.
    # This avoids cloning if *any* mirror is not configured correctly.
    #
    # The second pass is for mirrors which do not have a reference, the
    # third and final pass is for mirrors which do have a reference.
    total = 0
    for mirror in yaml_vars["mirrors"]:
        total = total + 1

        if mirror.get("short_name") is None:
            raise Exception(
                f"Missing required short_name on mirror item #%d on file: %s"
                % (total, args.yaml_mirror)
            )
        if mirror.get("url") is None:
            raise Exception(
                f"Missing required url on mirror item #%d on file: %s"
                % (total, args.yaml_mirror)
            )
        if mirror.get("target") is None:
            raise Exception(
                f"Missing required target for mirror %s on yaml file %s on item #%d"
                % (mirror.get("short_name"), args.yaml_mirror, total)
            )

    # Mirror trees without a reference first
    for mirror in yaml_vars["mirrors"]:
        if not mirror.get("reference"):
            mirror_entry(mirror, args)

    # Mirror trees which need a reference last
    for mirror in yaml_vars["mirrors"]:
        if mirror.get("reference"):
            mirror_entry(mirror, args)


if __name__ == "__main__":
    main()

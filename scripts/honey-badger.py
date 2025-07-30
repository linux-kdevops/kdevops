#!/usr/bin/python3
# SPDX-License-Identifier: copyleft-next-0.3.1

# Ever need to just tons of stable kernels fast and you just want to build
# them? The Ubuntu stable kernels on their PPA list have existed for decades.
# Let's just use that even if you don't have debian based distros we can just
# extract the debian files using ar for you. Just honey badge them.

import argparse
import requests
import re
import subprocess
from bs4 import BeautifulSoup
from itertools import groupby
import os
import tarfile
import tempfile
import shutil

KERNEL_PPA_URL = "https://kernel.ubuntu.com/mainline/"
ARCH = "amd64"
KERNEL_DIR = "/tmp/kernels"


def is_dpkg_installed():
    return shutil.which("dpkg") is not None


def extract_deb(deb_file, tempdir, verbose=False, dest="/"):
    try:
        if verbose:
            print(f"Extracting {deb_file} onto {tempdir}")
        # Extract the ar archive
        subprocess.run(["ar", "x", deb_file], check=True, cwd=tempdir)
        data_tarball = next(f for f in os.listdir(tempdir) if f.startswith("data.tar"))
        # Extract the data tarball to the correct locations
        with tarfile.open(os.path.join(tempdir, data_tarball)) as tar:
            tar.extractall(path=dest)

        print(f"Installed {deb_file} manually using ar x to directory {dest}")
    except Exception as e:
        print(f"Failed to install {deb_file}: {str(e)}")
    finally:
        # Cleanup the work directory
        if os.path.exists(tempdir):
            if verbose:
                print(f"Removing temporary directory {tempdir}")
            subprocess.run(["rm", "-rf", tempdir])


def install_kernel_packages(package_files, verbose=False, use_ar=False, dest="/"):
    if use_ar:
        for package in package_files:
            if verbose:
                print("Using ar x on %s" % package)
            with tempfile.TemporaryDirectory() as tempdir:
                extract_deb(package, tempdir, verbose, dest)
    else:
        for package in package_files:
            if verbose:
                print("Running: dpkg %s" % package)
            subprocess.run(["sudo", "dpkg", "-i", package], check=True)


def parse_version(version):
    match = re.match(r"v(\d+)\.(\d+)(?:\.(\d+))?(?:-(rc\d+))?", version)
    if match:
        major, minor, patch, rc = match.groups()
        return (int(major), int(minor), int(patch) if patch else 0, rc if rc else "")
    return (0, 0, 0, "")


def get_kernel_versions():
    response = requests.get(KERNEL_PPA_URL)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    versions = [
        href.strip("/")
        for link in soup.find_all("a")
        if (href := link.get("href")).startswith("v") and href.endswith("/")
    ]

    versions = sorted(versions, key=parse_version, reverse=True)
    return group_versions(versions)


def group_versions(versions):
    grouped = []
    for key, group in groupby(
        versions, lambda x: (parse_version(x)[0], parse_version(x)[1])
    ):
        group = sorted(group, key=parse_version, reverse=True)
        grouped.append(list(group))
    return grouped


def verify_kernel_files(version):
    url = f"{KERNEL_PPA_URL}{version}/{ARCH}/"
    response = requests.get(url)
    if response.status_code != 200:
        return False
    soup = BeautifulSoup(response.text, "html.parser")
    files = [a["href"] for a in soup.find_all("a") if a["href"].endswith(".deb")]
    if any("linux-image-unsigned" in f for f in files) and any(
        "linux-modules" in f for f in files
    ):
        return True
    return False


def download_and_install(file_type, version, verbose=False, use_ar=False, dest="/"):
    url = f"{KERNEL_PPA_URL}{version}/{ARCH}/"
    response = requests.get(url)
    response.raise_for_status()  # Ensure we raise an exception for failed requests
    soup = BeautifulSoup(response.text, "html.parser")

    deb_files = [
        a["href"]
        for a in soup.find_all("a")
        if a["href"].endswith(".deb") and file_type in a["href"]
    ]
    local_deb_files = []

    if not os.path.exists(KERNEL_DIR):
        os.makedirs(KERNEL_DIR)

    for deb_file in deb_files:
        full_url = url + deb_file
        local_file = f"{KERNEL_DIR}/{deb_file}"
        if verbose:
            print(f"Attempting to download from {full_url}...")
        r = requests.get(full_url, stream=True)
        if r.status_code == 200:
            with open(local_file, "wb") as f:
                f.write(r.content)
            if verbose:
                print(f"Downloaded {local_file}.")
            local_deb_files.append(local_file)
        else:
            if verbose:
                print(f"URL not found: {full_url}")

    install_kernel_packages(local_deb_files, verbose, use_ar, dest)


def main():
    dpkg_installed = is_dpkg_installed()
    parser = argparse.ArgumentParser(description="Linux stable kernel honey badger")
    parser.add_argument("--list", action="store_true", help="List available kernels")
    parser.add_argument(
        "--install",
        action="store_true",
        help="Install specified number of latest kernels",
    )
    parser.add_argument(
        "--dest", type=str, help="Install the packages into the specified directory"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument(
        "--use-ar",
        action="store_true",
        default=dpkg_installed,
        help="Do not use dpkg even if present",
    )
    parser.add_argument(
        "--use-file",
        type=str,
        help="Skip download and just install this debian package file",
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=1,
        help="Number of kernels to list or install",
    )
    args = parser.parse_args()

    kernel_versions_grouped = get_kernel_versions()
    if args.verbose:
        print(f"Found {sum(len(group) for group in kernel_versions_grouped)} versions.")
        print("Grouping and sorting versions...")

    valid_versions = []
    for group in kernel_versions_grouped:
        if len(valid_versions) >= args.count:
            break
        version = group[0]  # Pick the latest version in the group
        if args.verbose:
            print(
                f"Verifying files for {version} at {KERNEL_PPA_URL}{version}/{ARCH}/..."
            )
        if verify_kernel_files(version):
            valid_versions.append(version)
        else:
            if args.verbose:
                print(f"Failed to access {KERNEL_PPA_URL}{version}/{ARCH}/.")

    if args.list:
        print(valid_versions)
        return

    if args.use_file and args.install:
        pkgs = [args.use_file]
        install_kernel_packages(pkgs, args.verbose, args.use_ar, args.dest)
        return

    if args.install:
        for version in valid_versions:
            if args.verbose:
                print(f"Installing kernel version {version}...")
            files = ["linux-modules", "linux-image-unsigned", "linux-headers"]
            for file_type in files:
                download_and_install(
                    file_type, version, args.verbose, args.use_ar, args.dest
                )


if __name__ == "__main__":
    main()

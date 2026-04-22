# SPDX-License-Identifier: copyleft-next-0.3.1
#
# pynfs workflow: Python-based NFSv4 protocol conformance tests.
#
# Upstream: https://git.linux-nfs.org/?p=bfields/pynfs.git
#
# pynfs is cloned and driven by the consumer's own tooling
# (kdevops checks out the upstream tree). This module supplies
# only the Python runtime and ply parser-generator the harness
# imports, plus the NFS userland the scripts shell out to for
# server-side fixtures. A pre-built pynfs binary is available as
# a custom package in this flake (pkgs/pynfs.nix) but is not
# installed by default to avoid duplicating the consumer's own
# checkout.
{ pkgs, ... }: {
  environment.systemPackages = with pkgs; [
    python3
    python3Packages.ply

    nfs-utils
  ];
}

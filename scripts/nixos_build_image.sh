#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Build a per-node NixOS disk image from a generated kdevops flake.
# Invoked from playbooks/nixos.yml's build-vms play with a single
# argument: the per-node flake directory.
#
# Resolves the flake with a path: URL so nix does not filter the
# flake directory through git. The per-node directory lives under
# scripts/nixos-qemu/configurations/ which the nixos-qemu subtree's
# own .gitignore excludes; a plain "." or "./" flake-ref would be
# treated as git+file: and come back empty.
#
# Optional: if NIXOS_MIRROR_URL is set in the environment, the nix
# build invocation routes through that substituter in addition to
# cache.nixos.org.
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 <per-node-flake-directory>" >&2
    exit 1
fi

NODE_DIR="$1"

if [ -f /nix/var/nix/profiles/default/etc/profile.d/nix.sh ]; then
    . /nix/var/nix/profiles/default/etc/profile.d/nix.sh
fi
export PATH="/nix/var/nix/profiles/default/bin:${PATH:-/usr/local/bin:/usr/bin:/bin}"

if [ -n "${NIXOS_MIRROR_URL:-}" ]; then
    export NIX_CONFIG="substituters = ${NIXOS_MIRROR_URL} https://cache.nixos.org"
fi

cd "$NODE_DIR"
rm -f result
nix build "path:$PWD#image" -o result
readlink -f result/nixos.qcow2

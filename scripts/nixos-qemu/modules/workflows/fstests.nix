# SPDX-License-Identifier: copyleft-next-0.3.1
#
# fstests (xfstests-dev) workflow: filesystem regression tests.
#
# Upstream: https://git.kernel.org/pub/scm/fs/xfs/xfstests-dev.git
#
# Provides the userland filesystem tools, load generators, and NFS
# and SMB clients that the local and network fstests variants
# invoke on the target host. Services are enabled with mkDefault so
# consumers can turn them off for test subsets that do not exercise
# them.
{ pkgs, lib, ... }: {
  environment.systemPackages = with pkgs; [
    # Filesystem userland tools for the filesystems fstests covers
    xfsprogs
    xfsdump
    btrfs-progs
    e2fsprogs
    f2fs-tools

    # Load generators and stressors fstests scripts invoke.
    # (dbench used to be in nixpkgs; upstream removed it in late
    # 2025 as unmaintained for 14 years and broken, so fstests
    # subsets that need dbench currently fall back to the consumer's
    # own checkout.)
    fio
    stress-ng

    # POSIX attribute, ACL, and quota userland
    attr
    acl
    quota

    # NFS and SMB clients for the network filesystem fstests variants
    nfs-utils
    cifs-utils

    # The xfstests-dev test harness. The overlay in overlays/xfstests.nix
    # bumps the nixpkgs version (2023.05.14 broken with modern GCC) to
    # a current upstream snapshot. Installing it here puts `check` on
    # the guest's PATH via /run/current-system/sw/bin, so consumers
    # that skip the in-guest clone-and-build path (e.g. kdevops qsu
    # bringup) can drive the same binary kdevops otherwise builds from
    # source.
    xfstests
  ];

  services.nfs.server.enable = lib.mkDefault true;
  services.rpcbind.enable = lib.mkDefault true;

  # xfstests ./check and the kdevops wrapper scripts that drive
  # it (oscheck.sh, gendisks.sh, naggy-check.sh) all start with
  # `#!/bin/bash`, and ld-version.sh uses `#!/usr/bin/awk -f`.
  # NixOS only ships /bin/sh (pointing at bash) and /usr/bin/env
  # out of the box, so the kernel's shebang resolver fails with
  # ENOENT on those interpreters and the scripts refuse to exec
  # with a misleading "No such file or directory" on the script
  # itself. Patching every shebang in the xfstests tree is
  # intractable, and redirecting through `env` in a wrapper only
  # shifts the problem. Declare the two additional compat
  # symlinks here so the unmodified upstream scripts run
  # on qsu guests. Scoped to this module so consumers that opt
  # out of the fstests workflow don't carry the FHS bits they
  # don't need.
  systemd.tmpfiles.rules = [
    "L+ /bin/bash     - - - - ${pkgs.bash}/bin/bash"
    "L+ /usr/bin/awk  - - - - ${pkgs.gawk}/bin/awk"
  ];
}

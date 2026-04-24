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
}

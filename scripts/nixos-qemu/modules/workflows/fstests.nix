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

    # Runtime deps xfstests ./check (and the individual test scripts
    # under tests/*) invoke. nixpkgs' xfstests-check wrapper embeds
    # an explicit PATH with these store paths before exec'ing ./check;
    # when downstream consumers drive ./check directly (e.g. via
    # kdevops' oscheck.sh), we need the same tools reachable via
    # /run/current-system/sw/bin. Keeping the list here alongside
    # xfstests mirrors the wrapper's intent and keeps the dependency
    # relationship explicit rather than relying on nixpkgs'
    # propagatedBuildInputs (which only affect build-time closure).
    perl
    bc
    keyutils
    libcap
    lvm2
    psmisc
    which
    util-linux

    # Build toolchain that xfstests' ./check and the kdevops
    # oscheck.sh wrapper expect. oscheck.sh's check_reqs() bails
    # early on `which {gcc,make,git,automake}` coming up empty,
    # and several tests rebuild helper binaries (e.g. src/*.c)
    # on the fly via a plain `make` in the xfstests tree. The
    # nixpkgs xfstests derivation ships its helpers pre-built,
    # but check_reqs() still insists the toolchain is present so
    # the test scripts can invoke make/gcc themselves when they
    # regenerate fixtures. Ship gcc + gnumake + git + automake
    # so both paths work.
    gcc
    gnumake
    git
    automake
  ];

  # xfstests convention: most tests run as an unprivileged user
  # named `fsgqa` in group `fsgqa`, and a few tests (xfs/106 in
  # particular) explicitly check that fsgqa's primary group is
  # fsgqa. oscheck.sh's check_reqs() fails the whole run if the
  # user or group is missing, and NixOS' default user database
  # ships neither. Declare both here, scoped to the fstests
  # module so consumers that opt out don't carry an extra user.
  # The `sys` group is a second xfstests convention (some tests
  # set group ownership to `sys`); nixpkgs' default `sys` is only
  # created if a service declares it, so declare it explicitly.
  users.groups.fsgqa = {};
  users.groups.sys = {};
  users.users.fsgqa = {
    isSystemUser = true;
    group = "fsgqa";
    description = "xfstests unprivileged test user";
  };

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

    # Expose the xfstests tree at a stable, FHS-standard path so
    # driver scripts and external tools can cd into it without
    # resolving the nixpkgs store hash at runtime. Matches what
    # distribution packages of xfstests conventionally install
    # under /usr/lib/xfstests (Debian, Fedora, nixpkgs via the
    # libexec→/usr/lib translation) and gives the consumer a
    # predictable path the kdevops oscheck.sh flow can use as CWD.
    "L+ /usr/lib/xfstests - - - - ${pkgs.xfstests}/lib/xfstests"
  ];
}

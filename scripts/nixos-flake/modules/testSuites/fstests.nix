# SPDX-License-Identifier: copyleft-next-0.3.1
#
# fstests (xfstests-dev): filesystem regression tests.
#
# Upstream: https://git.kernel.org/pub/scm/fs/xfs/xfstests-dev.git
#
# Provides the userland filesystem tools, load generators, and NFS
# and SMB clients that the local and network fstests variants
# invoke on the target host. Services are enabled with mkDefault so
# consumers can turn them off for test subsets that do not exercise
# them.
{ pkgs, lib, ... }:
{
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
    # the guest's PATH via /run/current-system/sw/bin so consumers
    # that skip the in-guest clone-and-build path can drive the same
    # binary the package builds from source.
    xfstests

    # Runtime deps xfstests ./check (and the individual test scripts
    # under tests/*) invoke. nixpkgs' xfstests-check wrapper embeds
    # an explicit PATH with these store paths before exec'ing ./check;
    # when consumers drive ./check directly we need the same tools
    # reachable via /run/current-system/sw/bin. Keeping the list here
    # alongside xfstests mirrors the wrapper's intent and keeps the
    # dependency relationship explicit rather than relying on
    # nixpkgs' propagatedBuildInputs (which only affect build-time
    # closure).
    perl
    bc
    keyutils
    libcap
    lvm2
    psmisc
    which
    util-linux

    # Userland utilities individual tests reach for. Each one
    # corresponds to a _require_command guard in xfstests'
    # common/* helpers; absent the binary, the affected tests
    # skip with "X utility required, skipped this test". Keeping
    # the list scoped to this module so consumers that opt out of
    # fstests don't pay closure size for them.
    duperemove
    indent
    acct
    fsverity-utils
    man-db
    thin-provisioning-tools

    # checkbashisms flags /bin/sh portability slips against the
    # xfsprogs source tree. xfstests' auto-bashisms tests skip
    # with "checkbashisms utility required, skipped this test"
    # absent the binary. nixpkgs splits this out from the full
    # debian-devscripts suite as a standalone package, so pull
    # that and skip the rest of the suite.
    checkbashisms

    # python3 with dbus-python importable, so xfs/802 can talk to
    # the xfs_scrub@ family of systemd units via D-Bus. The test's
    # gate is literally `python3 -c 'import dbus'` (xfs/802:45) —
    # absent the import succeeding, the test skips with
    #   "test requires python3-dbus".
    # Build a per-closure python3 wrapper that has dbus-python on
    # its PYTHONPATH and place that wrapper on PATH; xfsprogs'
    # xfs_scrub_all.py uses the same `python3` from /run/current-
    # system/sw/bin so it picks up the same import surface
    # automatically.
    (python3.withPackages (ps: [ ps.dbus-python ]))

    # Build toolchain that xfstests' ./check (and the common
    # wrapper scripts that drive it) expect. The wrappers bail
    # early when `which {gcc,make,git,automake}` comes up empty,
    # and several tests rebuild helper binaries (e.g. src/*.c) on
    # the fly via a plain `make` in the xfstests tree. The nixpkgs
    # xfstests derivation ships its helpers pre-built, but the
    # request-side checks still insist the toolchain is present so
    # the test scripts can invoke make/gcc themselves when they
    # regenerate fixtures. Ship gcc + gnumake + git + automake so
    # both paths work.
    gcc
    gnumake
    git
    automake
  ];

  # xfstests convention: most tests run as an unprivileged user
  # named `fsgqa` in group `fsgqa`, and a few tests (xfs/106 in
  # particular) explicitly check that fsgqa's primary group is
  # fsgqa. Test wrappers fail the whole run if the user or group
  # is missing, and NixOS' default user database ships neither.
  # Declare both here, scoped to the fstests module so consumers
  # that opt out don't carry an extra user.
  # The `sys` group is a second xfstests convention (some tests
  # set group ownership to `sys`); nixpkgs' default `sys` is only
  # created if a service declares it, so declare it explicitly.
  # Explicit gids for the test-framework groups. Without an
  # explicit `gid =`, NixOS' auto-allocator can land on a slot
  # already reserved by the closure (e.g. gid 2 = kmem in
  # nixos/modules/misc/ids.nix), which fails module evaluation
  # with "Failed assertions: UIDs and GIDs must be unique!".
  # NixOS' system gid reservations top out around 327; pinning
  # to 500+ stays clear of every reserved slot in ids.nix and
  # safely below the 1000 boundary that separates system from
  # regular-user gids. xfstests checks group existence by name
  # (not by numeric gid), so the specific values are arbitrary
  # as long as they are stable and non-conflicting.
  users.groups.fsgqa = {
    gid = 500;
  };
  users.groups.sys = {
    gid = 501;
  };
  users.groups.daemon = {
    gid = 502;
  };
  # fsgqa2 group is required by ~6 xfstests per section that gate
  # on `_require_group fsgqa2` — generic/097, generic/132 and
  # similar tests that swap effective gid to "the second user's
  # primary group". The user already exists below. Conventional
  # distro `useradd -U fsgqa2` creates the matching group
  # implicitly; this module declares users individually so the
  # group has to be declared too. Without this, the tests skip
  # with "fsgqa2 group not defined."
  users.groups.fsgqa2 = {
    gid = 504;
  };
  # Same convention applies to the high-uid 123456-fsgqa user
  # used by generic/381 and a handful of xattr/quota tests:
  # `_require_group 123456-fsgqa` checks the same-name group
  # exists. Distro `useradd -U` would create it implicitly;
  # declare it here for the closure path.
  users.groups."123456-fsgqa" = {
    gid = 505;
  };

  # Each test-framework user gets a real shell via
  # `useDefaultShell = true`. xfstests' `_require_user` helper at
  # common/rc:2861 runs `echo /bin/true | _su <user>`, which in
  # turn invokes `su - <user> -c /bin/true`. NixOS' default for
  # isSystemUser=true is shell=nologin, which makes su fail and
  # the test skips with "<user> cannot execute commands." That
  # pattern can account for dozens of unexpected skips per section
  # even after the users themselves are declared. Conventional
  # distro `useradd` leaves the shell at the system default
  # (/bin/bash); this restores parity.
  users.users.fsgqa = {
    isSystemUser = true;
    group = "fsgqa";
    useDefaultShell = true;
    description = "xfstests unprivileged test user";
  };

  # Additional accounts xfstests reaches for. fsgqa2 is the
  # convention for the "second unprivileged user" that group
  # ownership tests need (generic/596 and friends). 123456-fsgqa
  # exercises the high-uid path in tools that don't truncate to
  # 16 bits (generic/381 hardcodes the 123456 numeric uid in its
  # check). daemon is the canonical "system service user" that
  # quota and accounting tests target (generic/079 calls daemon
  # explicitly). Declaring all three matches the conventional
  # distro useradd loop so the test framework sees the user
  # database it expects.
  users.users.fsgqa2 = {
    isSystemUser = true;
    # fsgqa2's primary group must be fsgqa2 (not fsgqa). The
    # xfstests pattern is "two unprivileged users with their own
    # primary groups so tests that swap egid get a distinct
    # ownership context"; mapping fsgqa2 onto fsgqa breaks that
    # split and confuses tests like generic/097 that compare egid
    # before/after a setegid(fsgqa2's gid) call.
    group = "fsgqa2";
    useDefaultShell = true;
    description = "xfstests secondary unprivileged test user";
  };
  users.users."123456-fsgqa" = {
    isSystemUser = true;
    uid = 123456;
    # Primary group must match the user's own name so
    # `_require_group 123456-fsgqa` resolves and the per-user
    # gid the test sets up via setegid is distinct from
    # fsgqa's gid.
    group = "123456-fsgqa";
    useDefaultShell = true;
    description = "xfstests numeric-uid test user (generic/381)";
  };
  users.users.daemon = {
    isSystemUser = true;
    group = "daemon";
    useDefaultShell = true;
    description = "xfstests system-service test user";
  };

  # `bin` is the traditional Unix system account for binary-owned
  # files. Conventional distros add it via useradd, and a subset
  # of xfstests (~28 tests, including some generic/* and xfs/*
  # tests that chown to bin during setup) skip with "bin user not
  # defined" when it is absent. NixOS does not ship a bin user by
  # default, so declare it here.
  #
  # Note: do NOT pin uid/gid to 2. NixOS' default user database
  # already declares the historical uid 2 / gid 2 slot for kmem
  # (config.ids.uids.bin / config.ids.gids.bin map elsewhere on
  # NixOS), so an explicit gid = 2 here triggers
  # "Failed assertions: UIDs and GIDs must be unique!" at module
  # evaluation time. But leaving gid unpinned is also wrong:
  # NixOS' auto-allocator scans from a low base and can land on
  # gid 2 itself, hitting the same assertion. Pin to a safe slot
  # in the same 500+ band as the other test-framework groups
  # (well clear of NixOS' system gid reservations that top out
  # around 327, and below the 1000 boundary that separates system
  # from regular-user gids). xfstests' bin-using tests check user
  # existence (_require_user_exists), not the numeric uid, so
  # the specific value is arbitrary as long as it is stable and
  # non-conflicting.
  users.groups.bin = {
    gid = 503;
  };
  users.users.bin = {
    isSystemUser = true;
    group = "bin";
    useDefaultShell = true;
    description = "xfstests bin test user (system binaries owner)";
  };

  services.nfs.server.enable = lib.mkDefault true;
  services.rpcbind.enable = lib.mkDefault true;

  # The imageless backend imports profiles/minimal.nix, which sets
  # documentation.enable = mkDefault false; that propagates into
  # documentation.man.enable and skips aggregating each package's
  # share/man/ into system-path. xfs/293, xfs/294 and similar
  # tests gate on `man -P cat xfs_io` returning a manpage and fail
  # outright (not notrun) when no manual entry resolves. Force the
  # man infrastructure on so xfsprogs' man8 pages are reachable
  # via the standard /run/current-system/sw/share/man/ hierarchy.
  documentation.enable = lib.mkForce true;
  documentation.man.enable = lib.mkForce true;

  # Expose xfsprogs' bundled systemd units (xfs_scrub@.service,
  # xfs_scrub_all.service+.timer, xfs_scrub_media@.service, plus
  # the matching _fail siblings, and xfs_healer@.service /
  # xfs_healer_start.service / system-xfs_healer.slice when the
  # source carries them) so xfstests can resolve them via
  # `_require_systemd_unit_defined`. xfsprogs installs these to
  # $out/lib/systemd/system/ — note the path is in the `out`
  # output, not `bin`. NixOS only forwards units from packages
  # explicitly listed in systemd.packages, and the path it walks
  # is "<package>/lib/systemd/system/" against whichever output
  # the user passes. `systemd.packages = [ pkgs.xfsprogs ]`
  # resolves to the package's *default* output (bin), which has
  # no lib/systemd/system/ — units silently never get forwarded
  # and tests skip with `systemd unit "xfs_scrub@.service" not
  # found`. Pass pkgs.xfsprogs.out explicitly to point the
  # forwarder at the output that actually carries the units.
  systemd.packages = [ pkgs.xfsprogs.out ];

  # Force-load the xfs module early so /sys/fs/xfs/debug/bug_on_assert
  # exists by the time the systemd-tmpfiles rule below fires. The
  # imageless module restores the standard
  # `boot.kernelModules → /etc/modules-load.d/nixos.conf` wiring that
  # NixOS' kernel.nix gates off when boot.kernel.enable=false, so the
  # natural option Just Works here.
  boot.kernelModules = [ "xfs" ];

  # dm-flakey, dm-delay, dm-log-writes etc. (used by xfstests under
  # generic/, and exercised heavily once CONFIG_DM_* are enabled) drive
  # device-mapper through libdevmapper, which serializes operations via
  # an SysV semaphore "udev cookie": dmsetup increments the semaphore
  # before the ioctl and udevd is expected to decrement it once it has
  # processed the resulting uevent. The decrement is performed by lvm2's
  # /lib/udev/rules.d/{10-dm,13-dm-disk,95-dm-notify}.rules. Putting
  # lvm2 on PATH (above) is not enough — the rules also need to land
  # in the active udev ruleset, and on NixOS that is wired up by the
  # upstream services.lvm module (which knows to grab lvm2's `out`
  # output containing the rules and to ship its tmpfiles + systemd
  # units). The imageless module disables services.lvm by default to
  # keep the minimal closure small, so use mkForce here to override
  # that default and opt the fstests test suite back in. Without this,
  # dm-* tests like generic/034 hang indefinitely with dmsetup blocked
  # in __do_semtimedop because the cookie semaphore is never released.
  services.lvm.enable = lib.mkForce true;

  # xfstests ./check and the wrapper scripts that drive it all
  # start with `#!/bin/bash`, and ld-version.sh uses
  # `#!/usr/bin/awk -f`. NixOS only ships /bin/sh (pointing at
  # bash) and /usr/bin/env out of the box, so the kernel's
  # shebang resolver fails with ENOENT on those interpreters and
  # the scripts refuse to exec with a misleading "No such file or
  # directory" on the script itself. Patching every shebang in
  # the xfstests tree is intractable, and redirecting through
  # `env` in a wrapper only shifts the problem. Declare the two
  # additional compat symlinks here so the unmodified upstream
  # scripts run unmodified. Scoped to this module so consumers
  # that opt out of the fstests test suite don't carry the FHS bits
  # they don't need.
  systemd.tmpfiles.rules = [
    "L+ /bin/bash     - - - - ${pkgs.bash}/bin/bash"
    "L+ /usr/bin/awk  - - - - ${pkgs.gawk}/bin/awk"

    # Expose the xfstests tree at a stable, FHS-standard path so
    # driver scripts and external tools can cd into it without
    # resolving the nixpkgs store hash at runtime. Matches what
    # distribution packages of xfstests conventionally install
    # under /usr/lib/xfstests (Debian, Fedora, nixpkgs via the
    # libexec→/usr/lib translation) and gives consumers a
    # predictable path to use as CWD.
    "L+ /usr/lib/xfstests - - - - ${pkgs.xfstests}/lib/xfstests"

    # Same FHS-symlink pattern for xfsprogs' libexec dir.
    # xfstests' common/config probes
    #   if [ ! -x "$XFS_HEALER_PROG" ] && \
    #      [ -e /usr/libexec/xfsprogs/xfs_healer ]; then ...
    # to find xfs_healer when `type -P` returns empty. xfsprogs
    # installs xfs_healer + xfs_healer_start to
    # <xfsprogs.out>/libexec/xfsprogs/ — outside PATH, since the
    # `bin` and `out` outputs are split. Without this symlink,
    # the fallback branch never resolves and ~9 tests
    # (xfs/657-664, 667) skip with "xfs_healer utility required".
    "L+ /usr/libexec/xfsprogs - - - - ${pkgs.xfsprogs.out}/libexec/xfsprogs"

    # Override the runtime default of XFS bug_on_assert from 1
    # to 0 when the running kernel was built with
    # CONFIG_XFS_ASSERT_FATAL=y. CONFIG_XFS_ASSERT_FATAL=y makes
    # ASSERT() call BUG() — instantly panicing the guest the
    # moment any XFS internal invariant is violated. That is the
    # right default for a developer's working kernel (catch bugs
    # immediately, see the stack), but on a test-framework guest
    # it bails xfstests mid-run on the first assertion and every
    # test that runs after the first ASSERT site is touched is
    # lost. xfstests itself flags this with the
    # `_require_no_xfs_bug_on_assert` helper (~2 .notruns per
    # section). Override to 0 so ASSERT() downgrades to WARN();
    # the assertion still fires into dmesg and the test
    # continues, which is the exact policy xfstests assumes for
    # its bug_on_assert-gated tests.
    # Persistence: w+ writes the value, follows symlinks, and
    # tolerates the file being missing (xfs may be unloaded).
    # The setting reapplies on every boot via systemd-tmpfiles,
    # which on NixOS runs as part of the activation phase.
    "w+ /sys/fs/xfs/debug/bug_on_assert - - - - 0"
  ];
}

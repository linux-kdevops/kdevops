# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Override xfstests to a current version. The nixpkgs version
# (2023.05.14) fails to build with modern GCC due to
# -Werror=implicit-function-declaration in ltp/fsx.c.
#
# The nixpkgs recipe handles all the packaging quirks (path
# patching, wrapper script, libtool workaround). We only need
# to bump the version and hash.
final: prev:
let
  version = "2026.03.20";
in {
  xfstests = prev.xfstests.overrideAttrs (old: {
    inherit version;
    src = prev.fetchzip {
      url = "https://git.kernel.org/pub/scm/fs/xfs/xfstests-dev.git/snapshot/xfstests-dev-v${version}.tar.gz";
      hash = "sha256-f82TsOEikGo9uQyM0hQmgy6A6R/2U4Ot/eINq34kohM=";
    };
    # Newer xfstests needs pkg-config for autoconf macros.
    nativeBuildInputs = (old.nativeBuildInputs or []) ++ [ prev.pkg-config ];
    # gdbm.dev provides gdbm-ndbm.h which xfstests' configure
    # probes for to enable HAVE_DB; without it src/dbtest is not
    # built and tests like generic/010 are skipped with the
    # "src/dbtest not built" .notrun reason.
    #
    # liburing unlocks the io_uring probe in src/feature.c.
    # Without HAVE_LIBURING defined at compile time,
    # check_uring_support() returns 1 unconditionally and every
    # _require_io_uring callsite skips with
    # "kernel does not support IO_URING" — even when
    # CONFIG_IO_URING=y and the syscall is fully functional.
    # The nixpkgs xfstests recipe omits liburing from
    # buildInputs, so xfstests winds up never probing the kernel
    # regardless of the runtime configuration. Adding it here
    # lets autoconf detect liburing.h, sets HAVE_LIBURING, and
    # check_uring_support() actually calls io_uring_queue_init
    # against the running kernel.
    buildInputs = (old.buildInputs or []) ++ [ prev.gdbm prev.liburing ];
    # Force-build src/file_attr even when configure decides
    # HAVE_FILE_GETATTR=no.
    #
    # xfstests' src/file_attr.c is the userspace driver for the
    # file_getattr / file_setattr syscalls (kernel commits landed
    # 2024-2025; syscall numbers 468/469 in asm-generic/unistd.h
    # 6.18+). The configure check at m4/package_libcdev.m4:93
    # uses AC_LINK_IFELSE to compile a tiny program calling
    # `syscall(__NR_file_getattr, ...)`, which fails on stdenv
    # toolchains whose linux-headers / glibc predate 6.18 — that
    # is the case for nixpkgs-25.11 (linux-headers 6.16.7, glibc
    # 2.40-218 — neither defines __NR_file_getattr). configure
    # then sets HAVE_FILE_GETATTR=no, src/Makefile:65 skips
    # file_attr, and ~2 tests per fstests section notrun with
    #   "/.../xfstests/src/file_attr not built".
    #
    # The C source itself is robust to old headers — it defines
    # `__NR_file_getattr 468` and `__NR_file_setattr 469`
    # internally inside `#ifndef HAVE_FILE_GETATTR`, so the
    # binary builds and links against any glibc whose
    # syscall(2) is the generic wrapper (true for all modern
    # glibcs). The gate at the Makefile layer is the only
    # blocker, and its purpose was to skip build on toolchains
    # genuinely too old to even produce a working binary —
    # not relevant on current nixpkgs.
    #
    # Force HAVE_FILE_GETATTR=yes at configure time AND inject
    # the syscall numbers via NIX_CFLAGS_COMPILE.
    #
    # Three pieces had to align:
    #
    #   1. src/Makefile gate (line 65: `ifeq ($(HAVE_FILE_GETATTR),
    #      yes)`) governs whether file_attr is built at all and
    #      whether `-DHAVE_FILE_GETATTR` is added to LCFLAGS.
    #
    #   2. file_attr.c uses `#ifndef HAVE_FILE_GETATTR` to
    #      conditionally provide both the __NR_file_getattr/
    #      __NR_file_setattr macros AND a `struct file_attr`
    #      fallback definition.
    #
    #   3. xfsprogs (we bumped to djwong's for-next under
    #      WORKFLOW_XFSPROGS_GIT) ships `struct file_attr` in
    #      <xfs/linux.h>. file_attr.c includes it transitively
    #      via "global.h" → <xfs/xfs.h> → <xfs/linux.h>.
    #
    # Combinations:
    #
    #   HAVE_FILE_GETATTR unset, system headers have __NR macros:
    #     fallback supplies its own __NR macros (redundant but
    #     harmless) AND its own struct file_attr (CONFLICTS with
    #     xfsprogs for-next's struct). Build error: redefinition.
    #
    #   HAVE_FILE_GETATTR set, system headers have __NR macros:
    #     fallback skipped, headers provide both. Builds cleanly.
    #     This is the path we want.
    #
    #   HAVE_FILE_GETATTR set, system headers DO NOT have __NR
    #   macros (our case: linux-headers 6.16.7 < 6.18 where
    #   file_getattr was added):
    #     fallback skipped, headers don't provide __NR macros.
    #     Build error: __NR_file_getattr undeclared.
    #
    # Fix: force HAVE_FILE_GETATTR=yes (skip fallback to dodge
    # the struct conflict with xfsprogs for-next), and inject
    # the syscall numbers via NIX_CFLAGS_COMPILE so the headers
    # appear to define them. The configure substitution lands
    # in include/builddefs which the Makefile reads at make
    # time. Drop this whole stanza once nixpkgs bumps
    # linux-headers past 6.18 AND the toolchain glibc is
    # rebuilt against those headers.
    NIX_CFLAGS_COMPILE = (old.NIX_CFLAGS_COMPILE or "") + " "
      + "-D__NR_file_getattr=468 -D__NR_file_setattr=469";
    patchPhase = (old.patchPhase or "") + ''
      sed -i include/builddefs.in \
        -e 's/^HAVE_FILE_GETATTR\s*=.*/HAVE_FILE_GETATTR = yes/'
    '';
  });
}

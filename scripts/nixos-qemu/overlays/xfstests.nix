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
  });
}

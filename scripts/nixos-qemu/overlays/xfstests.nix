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
  });
}

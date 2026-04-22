# SPDX-License-Identifier: copyleft-next-0.3.1
#
# xNVMe: cross-platform NVMe user space library and tools.
#
# Built with libaio and liburing backends. SPDK, libvfn, and ISA-L
# are disabled (not needed for kernel development workflows).
#
# Source: https://github.com/xnvme/xnvme
{
  lib,
  stdenv,
  fetchurl,
  meson,
  ninja,
  pkg-config,
  libaio,
  liburing,
}:

stdenv.mkDerivation rec {
  pname = "xnvme";
  version = "0.7.5";

  src = fetchurl {
    url = "https://github.com/xnvme/xnvme/releases/download/v${version}/xnvme-${version}.tar.gz";
    hash = "sha256-2VGjEV9oaVb1xrg5s5D/tQu0Q/dxH+NfV6B/TQZnJ38=";
  };

  nativeBuildInputs = [ meson ninja pkg-config ];

  buildInputs = [ libaio liburing ];

  mesonFlags = [
    "-Dwith-spdk=disabled"
    "-Dwith-libvfn=disabled"
    "-Dwith-isal=disabled"
    "-Dexamples=false"
    "-Dtests=false"
    "-Dbuild_subprojects=false"
  ];

  meta = {
    description = "Cross-platform NVMe user space library and tools";
    homepage = "https://xnvme.io";
    license = lib.licenses.bsd3;
    mainProgram = "xnvme";
    platforms = lib.platforms.linux;
  };
}

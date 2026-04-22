# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Standalone cpupower built from a kernel source tree.
#
# nixpkgs cpupower is tied to linuxPackages and requires a
# NixOS-built kernel. This package builds from any kernel source,
# defaulting to linux_latest when no override is provided.
{
  lib,
  stdenv,
  buildPackages,
  linux_latest,
  pciutils,
  gettext,
  which,
}:

stdenv.mkDerivation {
  pname = "cpupower";
  inherit (linux_latest) version src;

  nativeBuildInputs = [
    gettext
    which
  ];
  buildInputs = [ pciutils ];

  postPatch = ''
    cd tools/power/cpupower
    substituteInPlace Makefile \
      --replace-fail /bin/true ${buildPackages.coreutils}/bin/true \
      --replace-fail /usr/bin/install ${buildPackages.coreutils}/bin/install
  '';

  makeFlags = [
    "CROSS=${stdenv.cc.targetPrefix}"
    "CC=${stdenv.cc.targetPrefix}cc"
    "LD=${stdenv.cc.targetPrefix}cc"
  ];

  installFlags = lib.mapAttrsToList (n: v: "${n}dir=${placeholder "out"}/${v}") {
    bin = "bin";
    sbin = "sbin";
    man = "share/man";
    include = "include";
    lib = "lib";
    libexec = "libexec";
    locale = "share/locale";
    doc = "share/doc/cpupower";
    conf = "etc";
    bash_completion_ = "share/bash-completion/completions";
    unit = "lib/systemd/system";
  };

  enableParallelBuilding = true;

  meta = {
    description = "Tool to examine and tune power saving features";
    homepage = "https://www.kernel.org/";
    license = lib.licenses.gpl2Only;
    mainProgram = "cpupower";
    platforms = lib.platforms.linux;
  };
}

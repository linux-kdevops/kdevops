# SPDX-License-Identifier: copyleft-next-0.3.1
#
# libbpf-tools: standalone CO-RE BPF tracing tools from the BCC project.
#
# These are lightweight alternatives to the Python-based BCC tools.
# Each tool is a statically-linked binary (against vendored libbpf)
# that embeds its BPF program via a skeleton header. No BCC runtime,
# no Python, no LLVM needed at runtime.
#
# The build requires the full BCC source tree with submodules because
# libbpf-tools/ references ../src/cc/libbpf/src (vendored libbpf) and
# ./bpftool/src (vendored bpftool) via relative paths.
#
# Source: https://github.com/iovisor/bcc/tree/master/libbpf-tools
# Debian: https://packages.debian.org/trixie/libbpf-tools
{
  lib,
  stdenv,
  fetchFromGitHub,
  clang,
  llvmPackages,
  elfutils,
  zlib,
  openssl,
  pkg-config,
  gnumake,
}:

stdenv.mkDerivation rec {
  pname = "libbpf-tools";
  version = "0.36.1";

  src = fetchFromGitHub {
    owner = "iovisor";
    repo = "bcc";
    tag = "v${version}";
    hash = "sha256-yfIyV+NKaSYMNjqFpxPwCgetPacC8OrBBGxRG3P2z0o=";
    fetchSubmodules = true;
  };

  sourceRoot = "${src.name}/libbpf-tools";

  nativeBuildInputs = [
    # clang compiles the BPF programs with -target bpf. The BPF target
    # is freestanding, so any clang wrapper works; the plain wrapper
    # keeps the build closure small. The host-side loader uses
    # stdenv.cc via $(CC), not this clang.
    llvmPackages.clang
    llvmPackages.llvm  # llvm-strip
    pkg-config
    gnumake
  ];

  buildInputs = [
    elfutils             # libelf (dynamic)
    zlib                 # libz (dynamic)
    openssl              # for bpftool build
  ];

  # Nix's hardening flags (-fzero-call-used-regs, -fstack-protector)
  # are not valid for the BPF target. Disable them since the BPF
  # programs are compiled with clang --target=bpf.
  hardeningDisable = [ "zerocallusedregs" "stackprotector" ];

  makeFlags = [
    "prefix=${placeholder "out"}"
    "USE_BLAZESYM=0"
  ];

  enableParallelBuilding = true;

  installPhase = ''
    runHook preInstall

    make install prefix=$out

    # Add -libbpf suffix to avoid collisions with BCC's Python
    # wrappers that share the same names (biolatency, execsnoop,
    # etc.). Follows the Debian libbpf-tools package convention
    # (e.g., /usr/sbin/biolatency-libbpf).
    for bin in $out/bin/*; do
      name=$(basename "$bin")
      # Skip if already suffixed (symlink aliases like btrfsdist).
      if [[ "$name" != *-libbpf ]]; then
        mv "$bin" "''${bin}-libbpf"
      fi
    done

    # Recreate filesystem aliases with the suffix.
    for link in $out/bin/*-libbpf; do
      if [ -L "$link" ]; then
        target=$(readlink "$link")
        ln --symbolic --force "$(basename "$target")-libbpf" "$link"
      fi
    done

    # Install man pages from the BCC man/man8/ directory for tools
    # that have matching names.
    mkdir --parents $out/share/man/man8
    for bin in $out/bin/*-libbpf; do
      tool=$(basename "$bin" -libbpf)
      manpage="../man/man8/''${tool}.8"
      if [ -f "$manpage" ]; then
        install --mode=644 "$manpage" $out/share/man/man8/
      fi
    done

    runHook postInstall
  '';

  meta = {
    description = "Standalone libbpf-based BPF tracing tools from BCC";
    homepage = "https://github.com/iovisor/bcc/tree/master/libbpf-tools";
    license = with lib.licenses; [ lgpl21Only bsd2 ];
    platforms = lib.platforms.linux;
  };
}

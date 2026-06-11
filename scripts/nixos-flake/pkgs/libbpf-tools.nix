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
  cargo,
  rustc,
  rustPlatform,
  clang,
  llvmPackages,
  elfutils,
  zlib,
  openssl,
  json_c,
  pkg-config,
  gnumake,
}:

stdenv.mkDerivation (finalAttrs: {
  pname = "libbpf-tools";
  version = "0.36.1";

  src = fetchFromGitHub {
    owner = "iovisor";
    repo = "bcc";
    tag = "v${finalAttrs.version}";
    hash = "sha256-yfIyV+NKaSYMNjqFpxPwCgetPacC8OrBBGxRG3P2z0o=";
    fetchSubmodules = true;
  };

  # Let stdenv auto-detect the unpacked top-level dir (its name varies
  # by src — fetchFromGitHub gives "source", a flake-input override
  # gives "${shortRev}-source") and just navigate into the
  # libbpf-tools subdir from there. Avoids hardcoding src.name, which
  # is not present on every src form (notably flake-input overrides
  # that point src at a bcc fork).
  postUnpack = "sourceRoot=$sourceRoot/libbpf-tools";

  # USE_BLAZESYM=1 pulls in the blazesym Rust crate that ships as a
  # bcc submodule under libbpf-tools/blazesym. blkalgn (and a few
  # other tools — futexctn, memleak, opensnoop) #include
  # blazesym.h unconditionally and link against libblazesym_c.a,
  # which the Makefile builds via `cargo build --release` inside
  # libbpf-tools/blazesym. The cargo invocation runs in the nix
  # sandbox with no network, so its dependencies must be vendored
  # ahead of time.
  #
  # importCargoLock + finalAttrs.src reads the lockfile that
  # determines the dependency closure from whatever src is
  # currently in play. When the per-VM flake overlay overrides src
  # (via overrideAttrs pointing at a bcc fork), finalAttrs.src
  # updates and cargoDeps re-derives from that fork's pinned
  # blazesym submodule SHA — no separate cargoHash to chase when
  # the bcc tag (or fork branch) bumps the blazesym submodule.
  #
  # outputHashes pins blazesym's one git-only dependency (vmlinux,
  # not on crates.io). The pinned rev is stable across recent BCC
  # tags and the forks that carry blkalgn, so a single hash covers
  # both src cases. Update this hash if a future blazesym bump
  # moves to a different vmlinux.h rev — nix prints the expected
  # hash on mismatch.
  #
  # cargoRoot is relative to the source root the build cd's into
  # (sourceRoot above), which is .../libbpf-tools, so cargoRoot is
  # just "blazesym". The lockFile path used by importCargoLock is
  # rooted at finalAttrs.src and walks the fully-laid-out source
  # tree, so it carries the full prefix.
  cargoRoot = "blazesym";
  cargoDeps = rustPlatform.importCargoLock {
    lockFile = "${finalAttrs.src}/libbpf-tools/blazesym/Cargo.lock";
    outputHashes = {
      "vmlinux-0.0.0" = "sha256-a2q2AuTpqCU7gD0oZmjA+UbGwh4kVazaK6xKgK2L/Nk=";
    };
  };

  nativeBuildInputs = [
    # clang compiles the BPF programs with -target bpf. The BPF target
    # is freestanding, so any clang wrapper works; the plain wrapper
    # keeps the build closure small. The host-side loader uses
    # stdenv.cc via $(CC), not this clang.
    llvmPackages.clang
    llvmPackages.llvm # llvm-strip
    pkg-config
    gnumake
    # Rust toolchain is needed only because libbpf-tools/Makefile
    # does `cd blazesym && cargo build` to produce libblazesym_c.a.
    # cargoSetupHook reads cargoDeps and writes the .cargo/config.toml
    # that points cargo at the vendored crate copies.
    cargo
    rustc
    rustPlatform.cargoSetupHook
  ];

  buildInputs = [
    elfutils # libelf (dynamic)
    zlib # libz (dynamic)
    openssl # for bpftool build
    json_c # blkalgn (lbs branch) writes JSON via json-c
  ];

  # Nix's hardening flags (-fzero-call-used-regs, -fstack-protector)
  # are not valid for the BPF target. Disable them since the BPF
  # programs are compiled with clang --target=bpf.
  hardeningDisable = [
    "zerocallusedregs"
    "stackprotector"
  ];

  makeFlags = [
    "prefix=${placeholder "out"}"
    "USE_BLAZESYM=1"
    # The bcc Makefile detects cargo via `CARGO ?= $(shell which cargo)`.
    # The nix build sandbox has cargo on PATH (nativeBuildInputs above)
    # but ships no `which` binary, so the shell call returns empty and
    # the blazesym build recipe collapses to `cd ... && build ...`,
    # failing with "build: command not found". Pin CARGO=cargo on the
    # make line; ?= treats it as already-set and skips the shell call.
    "CARGO=cargo"
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
    license = with lib.licenses; [
      lgpl21Only
      bsd2
    ];
    platforms = lib.platforms.linux;
    maintainers = [ ];
  };
})

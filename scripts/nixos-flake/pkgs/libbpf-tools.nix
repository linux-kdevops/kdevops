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
  stdenvNoCC,
  fetchFromGitHub,
  cacert,
  cargo,
  rustc,
  rustPlatform,
  gitMinimal,
  clang,
  llvmPackages,
  elfutils,
  zlib,
  openssl,
  json_c,
  pkg-config,
  gnumake,
}:

let
  # crates.io's WAF 403s both per-crate `curl` fetches (importCargoLock)
  # and `python-requests` fetches (rustPlatform.fetchCargoVendor) when a
  # crate is missing from cache.nixos.org. `cargo` itself sends a UA the
  # WAF accepts, so vendor through cargo in one FOD. cargoSetupHook reads
  # the produced layout (a directory of <crate>-<version>/ subdirs) and
  # writes the default .cargo/config.toml that points at it.
  cargoVendorViaCargo =
    {
      src,
      cargoRoot,
      name,
      hash,
    }:
    stdenvNoCC.mkDerivation {
      inherit src;
      name = "${name}-vendor";
      nativeBuildInputs = [
        cacert
        cargo
        gitMinimal
      ];
      impureEnvVars = lib.fetchers.proxyImpureEnvVars;
      dontConfigure = true;
      dontInstall = true;
      dontFixup = true;
      buildPhase = ''
        runHook preBuild
        cd "${cargoRoot}"
        export HOME="$NIX_BUILD_TOP/.home"
        mkdir -p "$HOME"
        config_tmp=$(mktemp)
        cargo vendor --locked "$out" > "$config_tmp"
        mkdir -p "$out/.cargo"
        # cargo vendor emits source redirections for crates-io plus any
        # git sources, pinned at the absolute $out path. Replace it with
        # @vendor@ so cargoSetupHook can substitute the build-time copy
        # path; the hook's default config only redirects crates-io, so
        # without ours the git source stays unconfigured and cargo falls
        # back to /homeless-shelter/.cargo which is read-only.
        sed "s|$out|@vendor@|g" "$config_tmp" > "$out/.cargo/config.toml"
        cp Cargo.lock "$out/Cargo.lock"
        runHook postBuild
      '';
      outputHash = hash;
      outputHashAlgo = if hash == "" then "sha256" else null;
      outputHashMode = "recursive";
    };
in

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

  cargoRoot = "blazesym";
  cargoDeps = cargoVendorViaCargo {
    inherit (finalAttrs) src;
    cargoRoot = "libbpf-tools/blazesym";
    name = "libbpf-tools-blazesym";
    hash = "sha256-0jnrwSQODRWFBSdCULMYi/BFq3npPKDA+CZKEU627L4=";
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

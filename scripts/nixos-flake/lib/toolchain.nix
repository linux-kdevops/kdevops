# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Build toolchain package sets, shared by the controller NixOS module and the
# build devShells so a control node and an any-host shell agree on versions.
{ pkgs }:
{
  # Kernel + Kconfig toolchain a kernel tree's make / `make *config` needs
  # beyond stdenv.
  kernel = with pkgs; [
    ncurses
    pkg-config
    gcc
    gnumake
    bison
    flex
    bc
    perl
    openssl
    elfutils
    pahole
    cpio
    kmod
    zstd
    rsync
    hostname
  ];

  # Controller orchestration / provisioning tools.
  orchestration = with pkgs; [
    ansible
    git
    qemu-utils
    virtiofsd
    python3
    python3Packages.pyyaml
    python3Packages.jinja2
  ];

  # Multi-toolchain build matrix (gcc AND clang AND rust AND sparse),
  # selected per build via make flags (LLVM=1, C=1) / CONFIG_RUST.
  matrixExtras = with pkgs; [
    clang
    lld
    llvm # llvm-objcopy/ar/nm/... so an LLVM=1 build is self-contained
    rustc
    rust-bindgen
    rustfmt
    sparse
  ];
}

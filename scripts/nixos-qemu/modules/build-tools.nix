# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Common build toolchain: GNU Autotools plus a handful of headers
# and libraries that kernel-style compile jobs and several in-tree
# test frameworks routinely expect on a target host.
#
# Kept deliberately narrow. This module does not pick a C compiler
# (nixpkgs' stdenv already provides one) and does not pull in
# language-specific build systems; consumers that need more compose
# the additional packages themselves.
{ pkgs, ... }: {
  environment.systemPackages = with pkgs; [
    autoconf
    automake
    libtool
    pkg-config
    flex
    bison
    bc
    openssl
    elfutils
  ];
}

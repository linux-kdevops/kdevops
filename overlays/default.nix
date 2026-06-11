# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Package overlays and custom packages. Each file in this directory
# modifies one nixpkgs package. Custom packages not in nixpkgs are
# defined in pkgs/ using callPackage and merged here.
#
# Usage in a NixOS module:
#   { nixpkgs.overlays = [ (import ./overlays) ]; }
#
# Reference: https://nixos.org/manual/nixpkgs/stable/#chap-overlays
final: prev:
prev.lib.composeManyExtensions [
  (import ./fio.nix)
  (import ./xfstests.nix)
  (overlayFinal: _: import ../pkgs overlayFinal)
] final prev

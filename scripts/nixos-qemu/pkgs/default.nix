# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Custom packages not available in nixpkgs.
#
# Each package is a file declaring a function whose arguments are its
# dependencies. Use callPackage to compose them:
#
#   xnvme = pkgs.callPackage ./xnvme.nix { };
#
# The overlay at overlays/default.nix imports this file and merges
# the packages into the nixpkgs set.
#
# Reference: https://nix.dev/tutorials/callpackage
pkgs: {
  cpupower = pkgs.callPackage ./cpupower.nix { };
  damo = pkgs.callPackage ./damo.nix { };
  libbpf-tools = pkgs.callPackage ./libbpf-tools.nix { };
  nfstest = pkgs.callPackage ./nfstest.nix { };
  pynfs = pkgs.callPackage ./pynfs.nix { };
  xnvme = pkgs.callPackage ./xnvme.nix { };
}

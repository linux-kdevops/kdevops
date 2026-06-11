# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Per-VM overrides for the libvirt template.
#
# The flake passes nixos-flake and the flake inputs via specialArgs
# so this module can pull in test-suite modules (LTP, fstests, and so
# on) and reference local source checkouts without having to edit
# flake.nix again.
{
  config,
  lib,
  pkgs,
  nixos-flake,
  inputs,
  ...
}:
{
  imports = [
    # Development tools (editors, tracing, kernel dev comfort). Drop
    # this import for a minimal VM that only runs a specific test suite.
    nixos-flake.nixosModules.profiles.devel

    # Pick the test-suite modules that match what you intend to
    # run, for example:
    #   nixos-flake.nixosModules.profiles.build-tools
    #   nixos-flake.nixosModules.testSuites.fstests
    #   nixos-flake.nixosModules.testSuites.blktests
  ];

  networking.hostName = "vm";

  # Build a package from a local source checkout. The matching
  # fio-src input must be declared in flake.nix.
  # nixpkgs.overlays = [
  #   (final: prev: { fio = prev.fio.overrideAttrs { src = inputs.fio-src; patches = []; }; })
  # ];

  # SSH keys for the root and unprivileged accounts.
  # users.users.root.openssh.authorizedKeys.keys = [ "ssh-ed25519 ..." ];
  # users.users.${config.nixos-flake.user.name}.openssh.authorizedKeys.keys = [ "ssh-ed25519 ..." ];
}

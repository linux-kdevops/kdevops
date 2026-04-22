# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Per-VM overrides for the libvirt template.
#
# The flake passes nixos-qemu and the flake inputs via specialArgs
# so this module can pull in workflow modules (LTP, fstests, and so
# on) and reference local source checkouts without having to edit
# flake.nix again.
{ config, lib, pkgs, nixos-qemu, inputs, ... }: {
  imports = [
    # Development tools (editors, tracing, kernel dev comfort). Drop
    # this import for a minimal VM that only runs a specific workflow.
    nixos-qemu.nixosModules.devel

    # Pick the workflow modules that match what you intend to run,
    # for example:
    #   nixos-qemu.nixosModules.build-tools
    #   nixos-qemu.nixosModules.workflows.fstests
    #   nixos-qemu.nixosModules.workflows.blktests
  ];

  networking.hostName = "vm";

  # Build a package from a local source checkout. The matching
  # fio-src input must be declared in flake.nix.
  # nixpkgs.overlays = [
  #   (final: prev: { fio = prev.fio.overrideAttrs { src = inputs.fio-src; patches = []; }; })
  # ];

  # SSH keys for the root and workflow user accounts.
  # users.users.root.openssh.authorizedKeys.keys = [ "ssh-ed25519 ..." ];
  # users.users.${config.nixos-qemu.user.name}.openssh.authorizedKeys.keys = [ "ssh-ed25519 ..." ];
}

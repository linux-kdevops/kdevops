# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Controller profile: turns a NixOS host into a control node that
# drives the provisioning and test execution itself — building
# kernels, running Kconfig and `make menuconfig`, executing
# Ansible, and provisioning libvirt/QEMU guests.
#
# Enable it on top of a backend on a real machine (typically the
# libvirt backend, which is disk-booted with its own kernel). The
# same host can also import a test-suite module and run the
# suite directly, which is the baremetal case.
{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.nixos-flake.controller;
  tc = import ../../lib/toolchain.nix { inherit pkgs; };
in
{
  options.nixos-flake.controller.enable = lib.mkEnableOption "the control-node environment";

  config = lib.mkIf cfg.enable {
    # Kernel/Kconfig toolchain + orchestration tools, shared with the build
    # devShells through lib/toolchain.nix.
    environment.systemPackages = tc.kernel ++ tc.orchestration;

    # System libvirt with the QEMU/KVM stack so the controller can
    # define, run, and tear down guest VMs. runAsRoot stays off and
    # virtiofsd is registered as a vhost-user backend so guests can
    # share the host store without the daemon running as root.
    virtualisation.libvirtd = {
      enable = true;
      qemu = {
        runAsRoot = false;
        vhostUserPackages = [ pkgs.virtiofsd ];
      };
    };

    # Flakes so the controller can build system closures and disk
    # images locally.
    nix.settings.experimental-features = [
      "nix-command"
      "flakes"
    ];
  };
}

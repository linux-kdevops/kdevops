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
in
{
  options.nixos-flake.controller.enable = lib.mkEnableOption "the control-node environment";

  config = lib.mkIf cfg.enable {
    environment.systemPackages = with pkgs; [
      # Kconfig and `make menuconfig`: ncurses backs the menuconfig
      # frontend, pkg-config resolves its build-time probes.
      ncurses
      pkg-config

      # Kernel build toolchain. This is what a modern kernel tree's
      # `make` and `make *config` invoke directly beyond stdenv:
      # bison/flex for the parser generators, bc for kernel/timeconst,
      # openssl for module signing, elfutils and pahole for objtool
      # and BTF, cpio for the initramfs, kmod for depmod, zstd for
      # module compression, rsync and hostname for the build scripts.
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

      # Provisioning and orchestration: Ansible drives the playbooks,
      # git checks out the trees under test, qemu-img manipulates
      # guest disk images, virtiofsd shares host directories into
      # guests.
      ansible
      git
      qemu-utils
      virtiofsd

      # Python runtime the Ansible playbooks and helper scripts
      # import.
      python3
      python3Packages.pyyaml
      python3Packages.jinja2
    ];

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

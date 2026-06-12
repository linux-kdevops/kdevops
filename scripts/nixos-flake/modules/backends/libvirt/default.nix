# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Disk-image NixOS boot for libvirt-managed VMs. Expects a qcow2
# virtio-blk disk at /dev/vda.
#
# Per-node content (hostname, keys, virtiofs shares, mounts) is
# the consumer's responsibility and composes as additional
# modules.
{
  config,
  pkgs,
  lib,
  modulesPath,
  ...
}:
{

  imports = [
    # qemu-guest wires up virtio drivers, the QEMU guest agent, and
    # the small set of host-facing services that every NixOS VM
    # under QEMU needs. Brings the hardware setup into the module
    # so downstream consumers do not have to hand-write a matching
    # hardware-configuration.nix.
    (modulesPath + "/profiles/qemu-guest.nix")
    # Libvirt-specific defaults for the unprivileged account.
    # The user module itself is opt-in: importing this backend
    # alone does not create the account. Importing the user
    # module alongside picks up these backend-shaped defaults.
    ./user.nix
  ];

  # Built fresh, never upgraded in place, so this tracks the release each
  # build is made from (the option's default). Pin a literal only if you
  # persist a disk across nixpkgs upgrades:
  # https://wiki.nixos.org/wiki/FAQ/When_do_I_update_stateVersion
  system.stateVersion = lib.mkDefault config.system.nixos.release;

  # Key-only SSH. Password below is serial-console break-glass.
  services.openssh = {
    enable = true;
    settings = {
      PermitRootLogin = lib.mkDefault "yes";
      PubkeyAuthentication = true;
      PasswordAuthentication = lib.mkDefault false;
    };
  };

  boot.loader.grub = {
    enable = true;
    device = "/dev/vda";
  };
  boot.loader.timeout = lib.mkDefault 1;
  boot.kernelPackages = lib.mkDefault pkgs.linuxPackages_latest;

  fileSystems."/" = {
    device = "/dev/vda1";
    fsType = "ext4";
  };

  # libvirt's default network hands out 192.168.122.0/24 via DHCP.
  networking.useDHCP = lib.mkDefault true;

  virtualisation.libvirtd.enable = lib.mkDefault false;

  time.timeZone = lib.mkDefault "UTC";
  i18n.defaultLocale = lib.mkDefault "en_US.UTF-8";

  nix.settings.experimental-features = [
    "nix-command"
    "flakes"
  ];
  nix.gc = {
    automatic = lib.mkDefault true;
    dates = lib.mkDefault "weekly";
    options = lib.mkDefault "--delete-older-than 7d";
  };
}

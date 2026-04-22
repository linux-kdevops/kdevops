# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Opt-in workflow account with passwordless sudo. Name is
# configurable via options.nixos-qemu.user.name (default "user");
# downstream consumers like kdevops override it.
#
# Also sets a break-glass root password ("root") for serial-console
# recovery when SSH is unreachable. Safe because the backend modules
# disable password authentication at the sshd layer.
{ config, lib, ... }:
let
  cfg = config.nixos-qemu.user;
in {
  options.nixos-qemu.user = {
    name = lib.mkOption {
      type = lib.types.str;
      default = "user";
      description = "Unprivileged workflow account name.";
    };

    extraGroups = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ "wheel" "libvirt" "kvm" ];
      description = "Groups the workflow account belongs to.";
    };
  };

  config = {
    users.users.${cfg.name} = {
      isNormalUser = true;
      extraGroups = cfg.extraGroups;
      openssh.authorizedKeys.keys = [];
    };

    # Unattended tests would deadlock on a sudo prompt.
    security.sudo.wheelNeedsPassword = false;

    # Serial-console break-glass. See header for rationale.
    users.mutableUsers = false;
    users.users.root.initialPassword = "root";
  };
}

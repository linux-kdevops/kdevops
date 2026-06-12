# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Opt-in unprivileged account with passwordless sudo. The
# option schema lives in modules/user-options.nix, shared with
# the per-backend user.nix files so the backends can set
# extraGroups defaults without forcing user.nix to be imported.
# This module imports the same schema and adds the config block
# that actually creates the account.
#
# Also sets a break-glass root password ("root") for serial-
# console recovery when SSH is unreachable. Safe because the
# backend modules disable password authentication at the sshd
# layer.
{ config, lib, ... }:
let
  cfg = config.nixos-flake.user;
in
{
  imports = [ ./user-options.nix ];

  config = {
    users.users.${cfg.name} = {
      isNormalUser = true;
      extraGroups = cfg.extraGroups;
    };

    # Unattended tests would deadlock on a sudo prompt.
    security.sudo.wheelNeedsPassword = false;

    # Serial-console break-glass. mkDefault so a consumer who
    # wants mutable users or a different break-glass password
    # can override without lib.mkForce; the imageless backend
    # hardcodes the same values at normal priority and wins on
    # imageless+user.
    users.mutableUsers = lib.mkDefault false;
    users.users.root.initialPassword = lib.mkDefault "root";
  };
}

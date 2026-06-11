# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Shared option schema for the unprivileged account.
# Imported by modules/user.nix (which creates the account) and
# by each backend's user.nix (which sets backend-specific
# defaults). NixOS deduplicates same-path imports, so the
# option is declared exactly once at evaluation time regardless
# of how many modules pull this in.
{ lib, ... }:
{
  options.nixos-flake.user = {
    name = lib.mkOption {
      type = lib.types.str;
      default = "user";
      description = "Unprivileged account name.";
    };

    extraGroups = lib.mkOption {
      type = lib.types.listOf lib.types.str;
      default = [ ];
      example = [
        "wheel"
        "kvm"
      ];
      description = ''
        Supplementary groups for the unprivileged account. The
        option default is empty; backends set per-backend
        defaults at mkDefault priority via their bundled
        user.nix file (modules/backends/<backend>/user.nix).
        Consumers that want to add groups without replacing
        the backend's default set them via
        users.users.<name>.extraGroups, which NixOS list-
        merges with the value this module assigns from
        cfg.extraGroups.
      '';
    };
  };
}

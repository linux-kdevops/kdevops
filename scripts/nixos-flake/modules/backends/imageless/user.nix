# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Imageless-specific defaults for the unprivileged account.
# Auto-imported by the imageless backend module. An imageless
# guest does not run libvirt locally (it boots as a guest under
# a host's libvirtd, served via virtiofs), so the account only
# needs wheel and kvm by default.
#
# The shared option schema in ../../user-options.nix makes
# nixos-flake.user.extraGroups available even when modules/
# user.nix is not in the import set (e.g. the standalone
# backend check builds the backend without the user module).
#
# mkDefault on the value so a consumer who wants a different
# group set can override at normal priority without lib.mkForce.
{ lib, ... }:
{
  imports = [ ../../user-options.nix ];

  nixos-flake.user.extraGroups = lib.mkDefault [
    "wheel"
    "kvm"
  ];
}

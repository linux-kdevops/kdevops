# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Libvirt-specific defaults for the unprivileged account.
# Auto-imported by the libvirt backend module. A libvirt-backed
# system frequently runs libvirtd locally (controller nodes
# compose the controller profile on top of this backend), so the
# account gets libvirtd group membership by default.
# Membership in libvirtd is silently dropped on systems where
# the group does not exist, so the default is safe on a plain
# libvirt guest that never enables libvirtd.
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
    "libvirtd"
  ];
}

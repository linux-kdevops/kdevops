# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Opt-in virtiofs shares. Each share is a host-to-guest mount
# announced by the host's virtiofsd under a tag; the guest mounts
# it at a path of the consumer's choice.
#
# Shares are attrsOf submodule keyed by mount point, mirroring the
# fileSystems.<path> convention. The module emits one fileSystems
# entry per share and nothing else: no overlays, no env vars, no
# directory creation. Consumers compose those themselves when they
# need them.
{ config, lib, ... }:
let
  cfg = config.nixos-qemu.shares;
in {
  options.nixos-qemu.shares = lib.mkOption {
    default = {};
    description = "Virtiofs shares to mount in the guest, keyed by mount point.";
    type = lib.types.attrsOf (lib.types.submodule ({ name, ... }: {
      options = {
        tag = lib.mkOption {
          type = lib.types.str;
          description = "Virtiofs tag announced by the host's virtiofsd.";
        };
        options = lib.mkOption {
          type = lib.types.listOf lib.types.str;
          default = [];
          example = [ "ro" ];
          description = "Additional mount options passed to mount(8).";
        };
      };
    }));
  };

  config.fileSystems = lib.mapAttrs (mountPoint: share: {
    device = share.tag;
    fsType = "virtiofs";
  } // lib.optionalAttrs (share.options != []) {
    inherit (share) options;
  }) cfg;
}

# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Opt-in block-device mounts with optional pre-mount mkfs. Each
# entry is keyed by its mount point and declares the source device,
# filesystem type, mount options, and either a list of mkfs
# arguments or an autoFormat flag for default first-mount
# formatting. The two format modes are mutually exclusive; an
# assertion rejects configurations that set both.
#
# When mkfsArgs is non-empty, a oneshot service runs
# mkfs --type <fsType> with those arguments before the mount unit,
# guarded by blkid so a device that already carries a filesystem is
# left untouched. When autoFormat is true, the fileSystems entry
# passes through to NixOS's own first-mount format machinery.
{ config, lib, pkgs, utils, ... }:
let
  cfg = config.nixos-qemu.storage;

  mkFormatUnit = mountPoint: drive: {
    name = "format-${utils.escapeSystemdPath drive.device}";
    value = {
      description = "Format ${drive.device} before ${mountPoint} mounts";
      wantedBy = [ "${utils.escapeSystemdPath mountPoint}.mount" ];
      before = [ "${utils.escapeSystemdPath mountPoint}.mount" ];
      requires = [ "${utils.escapeSystemdPath drive.device}.device" ];
      after = [ "${utils.escapeSystemdPath drive.device}.device" ];
      unitConfig.DefaultDependencies = false;
      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        ExecCondition = pkgs.writeShellScript "blkid-empty-${utils.escapeSystemdPath drive.device}" ''
          ! ${pkgs.util-linux}/bin/blkid --probe ${lib.escapeShellArg drive.device}
        '';
        ExecStart = lib.escapeShellArgs (
          [ "${pkgs.util-linux}/bin/mkfs" "--type" drive.fsType ] ++ drive.mkfsArgs ++ [ drive.device ]
        );
      };
    };
  };
in {
  options.nixos-qemu.storage = lib.mkOption {
    default = {};
    description = "Extra block-device mounts, keyed by mount point.";
    type = lib.types.attrsOf (lib.types.submodule {
      options = {
        device = lib.mkOption {
          type = lib.types.str;
          example = "/dev/nvme0n1";
          description = "Source block device.";
        };
        fsType = lib.mkOption {
          type = lib.types.str;
          example = "xfs";
          description = "Filesystem type passed to mount(8) and mkfs(8).";
        };
        options = lib.mkOption {
          type = lib.types.listOf lib.types.str;
          default = [];
          description = "Additional mount options passed to mount(8).";
        };
        mkfsArgs = lib.mkOption {
          type = lib.types.listOf lib.types.str;
          default = [];
          example = [ "-b" "size=16k" "-s" "size=16k" ];
          description = ''
            Arguments passed to <literal>mkfs --type &lt;fsType&gt;</literal>
            before the mount unit runs. The format service skips
            devices that already carry a filesystem. Mutually
            exclusive with <option>autoFormat</option>.
          '';
        };
        autoFormat = lib.mkOption {
          type = lib.types.bool;
          default = false;
          description = ''
            Pass through to
            <option>fileSystems.&lt;path&gt;.autoFormat</option> so
            NixOS formats the device with default mkfs arguments on
            first mount if it has no filesystem. Mutually exclusive
            with <option>mkfsArgs</option>.
          '';
        };
      };
    });
  };

  config = {
    assertions = lib.mapAttrsToList (mountPoint: drive: {
      assertion = !(drive.autoFormat && drive.mkfsArgs != []);
      message = ''
        nixos-qemu.storage."${mountPoint}": autoFormat and mkfsArgs
        are mutually exclusive. Pick one.
      '';
    }) cfg;

    fileSystems = lib.mapAttrs (mountPoint: drive: {
      inherit (drive) device fsType autoFormat;
    } // lib.optionalAttrs (drive.options != []) {
      inherit (drive) options;
    }) cfg;

    systemd.services = lib.listToAttrs (
      lib.mapAttrsToList mkFormatUnit (lib.filterAttrs (_: d: d.mkfsArgs != []) cfg)
    );
  };
}

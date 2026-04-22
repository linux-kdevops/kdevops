# SPDX-License-Identifier: copyleft-next-0.3.1
#
# blktests workflow: block layer regression tests.
#
# Upstream: https://github.com/osandov/blktests
#
# Provides the block-device userland tools and SCSI target
# framework that blktests scripts invoke, plus the I/O generator
# and metrics collectors a few test groups rely on.
{ pkgs, ... }: {
  environment.systemPackages = with pkgs; [
    # Block-device userland tools
    nvme-cli
    sg3_utils
    multipath-tools
    dmraid
    lvm2
    mdadm

    # SCSI target framework used by iSCSI and FC test groups
    # (nixpkgs ships the fork as targetcli-fb; the upstream name
    # 'targetcli' has been retired from nixpkgs.)
    targetcli-fb

    # I/O generator and stats used across several groups
    fio
    sysstat
  ];
}

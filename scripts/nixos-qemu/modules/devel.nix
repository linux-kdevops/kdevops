# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Development profile: kernel testing and storage tools.
#
# Import this module on top of the base configuration to get a
# full kernel development environment with storage, NVMe, NFS,
# BPF, and filesystem testing tools.
#
# Usage in a flake:
#   modules = [
#     nixos-qemu.nixosModules.imageless      # or .libvirt
#     nixos-qemu.nixosModules.devel
#     { nixpkgs.overlays = [ nixos-qemu.overlays.default ]; }
#   ];
{ pkgs, ... }: {
  # Wire up completion scripts for bash so tab completion works for
  # the tools installed below. Just having bash-completion on the path
  # does not enable it; the NixOS option sources the completion
  # dispatcher from /etc/bashrc.
  programs.bash.completion.enable = true;

  environment.systemPackages = with pkgs; [
    # Storage and filesystem tools
    btrfs-progs
    e2fsprogs
    f2fs-tools
    lvm2
    libndctl
    parted
    xfsdump
    xfsprogs

    # NVMe and SCSI
    libnvme
    nvme-cli
    sg3_utils
    xnvme

    # I/O performance
    fio
    libaio
    liburing
    stress-ng

    # NFS
    nfstest
    nfs-utils
    pynfs

    # Network
    iperf

    # BPF and tracing
    bcc
    blktrace
    bpftrace
    libbpf-tools
    trace-cmd

    # Monitoring
    cpupower
    btop
    damo
    dmidecode
    gnuplot
    htop
    iotop
    lsof
    numactl
    pagemon
    perf
    powertop
    sysstat

    # Test suites and runtime dependencies
    xfstests

    # fstests/blktests/selftests runtime dependencies
    acl
    attr
    keyutils
    libcap
    libseccomp
    mdadm
    quota
    rpcbind

    # General development
    bc
    ethtool
    file
    gawk
    git
    helix
    iproute2
    jq
    kmod
    neovim
    pciutils
    screen
    strace
    tmux
    usbutils
    util-linux
    vim
    zellij

    # Python: interpreter plus data analysis libraries. The bare
    # python3 interpreter is kept next to the libraries so downstream
    # automation (Ansible, ad-hoc scripting) can find
    # /run/current-system/sw/bin/python3 without having to pull in a
    # workflow module that happens to install it transitively.
    python3
    python3Packages.matplotlib
    python3Packages.numpy
    python3Packages.pandas
  ];
}

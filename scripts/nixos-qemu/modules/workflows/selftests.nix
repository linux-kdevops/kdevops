# SPDX-License-Identifier: copyleft-next-0.3.1
#
# selftests workflow: Linux kernel in-tree self-tests.
#
# Upstream: tools/testing/selftests in the Linux kernel tree.
#
# Installs the userland tools selftests invoke: perf and related
# tracing, CPU and memory placement, capability and seccomp
# userland, traffic-control helpers, and ethernet link controls.
# tc(8) is provided by iproute2 on NixOS, so no separate package
# is required for the kselftest net suites.
{ pkgs, ... }: {
  environment.systemPackages = with pkgs; [
    perf-tools

    numactl

    libcap
    libseccomp
    keyutils

    iproute2
    ethtool
  ];
}

# SPDX-License-Identifier: copyleft-next-0.3.1
#
# mmtests workflow: memory management test and benchmark harness.
#
# Upstream: https://github.com/gormanm/mmtests
#
# mmtests is perl-based and consumes its own result sets through
# gnuplot. CPU frequency control, DMI inventory, and the standard
# system metric collectors are invoked by several benchmark
# harnesses in the suite.
{ pkgs, ... }: {
  environment.systemPackages = with pkgs; [
    perl
    gnuplot

    cpupower
    dmidecode

    sysstat
    iotop
    powertop
  ];
}

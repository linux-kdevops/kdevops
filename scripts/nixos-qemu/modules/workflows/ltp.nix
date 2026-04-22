# SPDX-License-Identifier: copyleft-next-0.3.1
#
# LTP workflow: Linux Test Project test suites.
#
# Upstream: https://github.com/linux-test-project/ltp
#
# LTP is cloned and built from source by the consumer's own
# tooling (kdevops clones the upstream tree). This module supplies
# only the build toolchain LTP's configure-and-make cycle expects
# and the runtime libraries the syscall, IPC, security, and
# filesystem suites link against. LTP itself is not in nixpkgs.
{ pkgs, ... }: {
  environment.systemPackages = with pkgs; [
    # Build toolchain LTP's configure and make cycle invokes.
    autoconf
    automake
    m4
    libtool
    pkg-config
    flex
    bison

    # Runtime libraries LTP suites link against. libacl is provided
    # by the acl package, libnuma by numactl, libssl by openssl.
    acl
    libcap
    libaio
    numactl
    libsepol
    libselinux
    openssl
  ];
}

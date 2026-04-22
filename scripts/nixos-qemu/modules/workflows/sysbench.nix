# SPDX-License-Identifier: copyleft-next-0.3.1
#
# sysbench workflow: scriptable benchmarking tool, commonly used
# for MySQL and PostgreSQL workload measurement.
#
# Upstream: https://github.com/akopytov/sysbench
#
# Enables MariaDB (NixOS' mysql service uses it) and PostgreSQL
# with lib.mkDefault so consumers can disable one or both when
# a run only targets a specific backend. The MySQL service
# package is also set via mkDefault so downstreams that prefer
# the upstream Oracle MySQL can substitute without mkForce.
{ pkgs, lib, ... }: {
  environment.systemPackages = with pkgs; [
    sysbench
    mariadb
    postgresql
  ];

  services.mysql = {
    enable = lib.mkDefault true;
    package = lib.mkDefault pkgs.mariadb;
  };

  services.postgresql.enable = lib.mkDefault true;
}

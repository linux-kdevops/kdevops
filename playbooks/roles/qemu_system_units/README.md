qemu_system_units
=================

Ansible role that drives the qsu (imageless NixOS) backend: builds
per-VM closures, renders systemd user unit drop-ins and virtiofsd
env files, and starts and stops VMs via systemd user units.

Entry points
------------

  * `tasks/bringup.yml` — first-time start.
  * `tasks/destroy.yml` — tear down.
  * `tasks/generate_configs.yml` — render per-VM flake.nix and default.nix.
  * `tasks/imageless_build.yml` — build the per-VM NixOS closure.

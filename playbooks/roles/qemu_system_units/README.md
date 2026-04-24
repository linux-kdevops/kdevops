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
  * `tasks/rebuild_test.yml` — `nixos-rebuild test` analog: hot-activate.
  * `tasks/rebuild_boot.yml` — `nixos-rebuild boot` analog: persist for next start.

Iteration loop for local workflow source trees
-----------------------------------------------

When a workflow's source is pinned to a local checkout via a `path:`
flake input (the fstests workflow does this with CONFIG_FSTESTS_GIT),
edits to the checkout don't reach a running guest on their own. A
full destroy+bringup is heavy for iterating on scripts and helpers.

The role exposes three Make targets that map 1:1 onto the
`nixos-rebuild test|switch|boot` modes:

  * `make rebuild-test` — hot-activate via `switch-to-configuration
    test`. Ephemeral: a `systemctl --user restart qemu-system@<vm>`
    re-reads the unchanged `vm.env` and reverts to the closure the
    bringup originally pinned. Use for tight iteration where you do
    not want the change to persist.

  * `make rebuild-boot` — re-render the per-VM `vm.env` so the next
    start of `qemu-system@<vm>.service` boots from the latest
    closure. No hot activation; the running guest is unchanged
    until you restart the unit yourself. Use when an in-flight test
    must not be disturbed.

  * `make rebuild-switch` — both: re-render `vm.env` and hot-activate
    via `switch-to-configuration test`. The running guest picks up
    the change now, and a later restart picks up the same closure.
    Use when you have committed to the change.

Iteration with `rebuild-test`:

```
$EDITOR ~/src/xfstests-dev/tests/generic/042
make rebuild-test
make fstests-baseline TESTS="generic/042"
```

Mechanics common to all three modes:

  1. `nix flake update ... xfstests-src` refreshes the lock entry
     for the `path:` input. Nix otherwise trusts the narHash
     recorded at first evaluation and does not re-hash the
     checkout on subsequent builds.
  2. `nix build .#toplevel` evaluates the flake with the refreshed
     input and produces a new system closure. The guest's
     /nix/store is a virtiofs mount of the controller's, so new
     store paths are visible to the guest the moment the
     controller finishes.

`rebuild-boot` and `rebuild-switch` additionally re-render
`vm.env` (kernel `init=` argument changes to the new toplevel)
and reload the user systemd bus. `rebuild-test` and
`rebuild-switch` additionally run `switch-to-configuration test`
on each guest, which re-runs systemd-tmpfiles and rewrites the
tmpfiles L+ symlinks (/usr/lib/xfstests, /bin/bash, …) to point
at the new store paths.

The activation step accepts switch-to-configuration-ng exit codes
4 (some systemd units failed to (re)start — path/symlink updates
have already taken effect) and 100 (reboot requested). Only code
2, which means the activation script itself errored, is treated
as failure.

# NIXOSFI — nixos-flake imageless backend

`NIXOSFI` runs each guest imagelessly: a nixos-flake `backends.imageless`
closure (tmpfs root; `/nix/store` and `/lib/modules` shared read-only over
virtiofs) booted via QEMU's `-kernel` against a kernel you build on the
controller. No disk image, no distro. Each guest runs on the qsu runtime
as a systemd-machined machine — see [qsu.md](qsu.md) — and
[nixos-flake-backends.md](nixos-flake-backends.md) for how it relates to
the libvirt `NIXOSFL` backend.

## Enable

```
make menuconfig   # Node bring up method -> NixOS imageless configuration with systemd-machined
```

or `CONFIG_NIXOSFI=y`. `BOOTLINUX_DIRECT_BOOT` is auto-selected: the guest
boots the controller-built kernel. Guest contents use the shared
`NIXOS_FLAKE_*` options; the VM runtime (cpu, memory, NVMe, ssh, vsock)
uses the `QSU_*` knobs.

## Bring up

```
make
make bringup        # build kernel + closures, render units, start machines, wait for SSH
ssh <guest>
```

`make bringup` builds the direct-boot kernel, then runs
`playbooks/nixosfi.yml`: it renders per-guest imageless flakes,
`nix build`s each `toplevel` closure, and drives the qsu runtime to render
the systemd units and start each guest.

## Fast kernel iteration

```
make linux-direct-boot      # build a new kernel on the controller
make nixosfi-rebuild-boot   # reboot guests onto it, no image rebuild
```

## Inspect and tear down

See [qsu.md](qsu.md) for `machinectl` / `systemctl --user`. Then
`make destroy`.

## Prerequisites

Nix on the controller (`make nixos-flake-runtime-deps-setup`) and the qsu
runtime dependencies (QEMU, virtiofsd, socat, systemd-container), installed
by the bringup itself.

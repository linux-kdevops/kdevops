# NIXOSFL — nixos-flake libvirt backend

`NIXOSFL` brings guests up as libvirt domains whose root disk is a qcow2
image built declaratively from the nixos-flake library, instead of from a
distro image. It is the Nix counterpart of `GUESTFS`: the same libvirtd
runtime, a reproducible flake-built image. See
[nixos-flake-backends.md](nixos-flake-backends.md) for how it relates to
the imageless `NIXOSFI` backend.

## Enable

```
make menuconfig   # Node bring up method -> NixOS declarative configuration with libvirt
```

or in a defconfig, `CONFIG_NIXOSFL=y`. The libvirt-specific knobs are
`NIXOSFL_CONFIG_DIR` (where per-guest flakes render) and
`NIXOSFL_STORAGE_DIR` (where the built qcow2 is staged into the libvirt
pool). Guest contents — profiles, mounts, testSuites — come from the
shared `NIXOS_FLAKE_*` options.

## Bring up

```
make
make bringup        # build each guest's qcow2, define + start the domain, wait for SSH
ssh <guest>
```

`make bringup` runs `playbooks/nixosfl.yml`: it renders a per-guest
`flake.nix`/`default.nix` under `NIXOSFL_CONFIG_DIR`, runs `nix build`
for the `image` output, stages the qcow2 into the libvirt pool, defines
and starts the domain, and registers it in `~/.ssh/config`.

## Inspect and tear down

```
virsh list --all
virsh console <guest>
make destroy
```

## Prerequisites

A working libvirt/KVM stack (as for `GUESTFS`) plus Nix on the controller.
Install Nix once with `make nixos-flake-runtime-deps-setup`.

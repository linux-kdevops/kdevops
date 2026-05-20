# NixOS-flake bring-up backends

kdevops can build guests declaratively from the **nixos-flake** library
(vendored at `scripts/nixos-flake/`) instead of from a distro image. Two
"Node bring up method" choices select which nixos-flake backend module to
build and how to run it:

| Choice | nixos-flake module | Image | Runtime | Manager |
|---|---|---|---|---|
| `NIXOSFL` | `backends.libvirt` | qcow2 disk image | libvirtd | `virsh` |
| `NIXOSFI` | `backends.imageless` | system closure (virtiofs root) | qsu / systemd-machined | `machinectl` |

`NIXOSFL` is the Nix counterpart of `GUESTFS`: the same libvirt runtime,
with the image built from a reproducible flake instead of by libguestfs.
`NIXOSFI` swaps that runtime for qemu-system-units (qsu)  — no disk
image, no daemon — and boots a controller-built kernel directly
(`BOOTLINUX_DIRECT_BOOT`).

## Layers

- **library** — `scripts/nixos-flake/` (the flake: modules, overlays,
  backend definitions), configured by the shared `Kconfig.nixos_flake`
  menu (`NIXOS_FLAKE_*`: profiles, mounts, testSuites) and a one-time Nix
  install on the controller (`make nixos-flake-runtime-deps-setup`).
- **backends** — `NIXOSFL` ([nixosfl.md](nixosfl.md)) and `NIXOSFI`
  ([nixosfi.md](nixosfi.md)).
- **runtime** — libvirtd for `NIXOSFL`; qsu ([qsu.md](qsu.md)) for `NIXOSFI`.

## Scope today

Both backends gate off the test workflows (fstests, blktests, ...) and the
monitors. A nixos-flake guest is built declaratively, so once it boots
there is no per-guest Ansible step left for kdevops to run; wiring those
workflows needs a controller/guest setup separation that is not in place
yet.

## Source overrides

Any guest can rebuild a tracked package — fio, xfstests, xfsprogs, libbpf,
libbpf-tools, damo, nfstest, pynfs, xnvme, or cpupower — from your own
source instead of the bundled overlay. Set `NIXOS_FLAKE_OVERRIDE_<PKG>=y`
plus `_SRC` (a local path or a git URL) and an optional `_REF`; kdevops
routes it in as a `<pkg>-src` flake input that a `default.nix` overlay
`overrideAttrs` consumes. It applies to both backends and has no effect
when every override is off. After changing a `_SRC`/`_REF`, refresh the
pinned input with `nix flake update --update-input <pkg>-src`.

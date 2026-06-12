# nixos-flake

NixOS modules, overlays, and templates for provisioning NixOS
systems. The same module set drives several modes:

- **imageless guest**: a system closure that boots a VM directly —
  tmpfs root, systemd initramfs, external kernel, `/nix/store` and
  `/lib/modules` mounted via virtiofs from the host. No disk image
  and nothing persists across boots.
- **libvirt guest**: a qcow2 disk image consumed by libvirt —
  `/dev/vda` root, grub bootloader, NixOS-built kernel, DHCP from
  libvirt's default network.
- **baremetal**: the imageless system activated on real hardware
  with `switch-to-configuration` instead of booted in QEMU.
- **controller**: a host that builds kernels, runs Kconfig and
  Ansible, and provisions the guests above.

All modes compose with the opt-in modules — `user`, the mounts
modules (`shares`, `storage`), the profiles (`devel`,
`build-tools`, `monitoring`, `controller`), and the per-suite
modules under `testSuites.*` — so a system can be minimal or
carry the full kernel and storage testing toolchain.

Beyond provisioning, the flake exposes development shells that bring
the same reproducible toolchain to any host via `nix develop`:
`build-kernel` and `build-qemu` for kernel and QEMU builds (the
package set the `controller` profile installs, defined once in
`lib/toolchain.nix`) and `systemd` for the host systemd control
toolkit.

**License**: copyleft-next-0.3.1

## Prerequisites

The [Nix package manager](https://nixos.org/download/) with flake
support enabled:

```shell
mkdir --parents ~/.config/nix
echo 'experimental-features = nix-command flakes' >> ~/.config/nix/nix.conf
```

## Quick start

Validate that both backends evaluate and build:

```shell
nix flake check
```

Build a single backend closure:

```shell
nix build .#checks.x86_64-linux.imageless    # or .libvirt
readlink --canonicalize result
```

The `result` symlink points to the system closure. For imageless,
`result/boot.json` contains the `init` and `initrd` paths needed to
configure QEMU:

```shell
cat result/boot.json
```

To create a downstream configuration, use a template:

```shell
nix flake init --template "github:linux-kdevops/nixos-flake#imageless"
nix flake init --template "github:linux-kdevops/nixos-flake#libvirt"
```

See [docs/usage.md](docs/usage.md) for customizing packages and
NixOS options.

## Development shells

The same toolchain is available on any host without building a NixOS
system:

```shell
nix develop .#build-kernel -c make ...        # kernel build env (gcc)
nix develop .#build-kernel -c make LLVM=1 ... # clang
nix develop .#build-qemu   -c make ...        # QEMU build env
nix develop .#systemd -c systemctl --user list-units  # host systemd control
```

See [docs/usage.md](docs/usage.md) for what each shell provides.

## How it boots

### Imageless

This backend builds two artifacts: a NixOS system closure and a
systemd initramfs. Booting requires an external kernel and QEMU
with virtiofsd sharing the host's `/nix/store` and `/lib/modules`
into the guest.

The external kernel must have the boot-critical virtio drivers
built-in (`CONFIG_VIRTIO_FS=y`, `CONFIG_VIRTIO_PCI=y`,
`CONFIG_TMPFS=y`). All other drivers can be kernel modules loaded
from `/lib/modules` after switch-root.

QEMU needs two virtiofsd instances sharing host directories into
the guest with these tags:

- `store`: the host's `/nix/store` (read-only)
- `modules`: the kernel build's `/lib/modules` directory

The kernel command line:

```
root=tmpfs console=ttyS0,115200 console=hvc0 init=/nix/store/<hash>/init
```

systemd in the initramfs reads the NixOS-generated fstab, mounts
root (tmpfs), `/nix/store` (virtiofs tag `store`), and
`/lib/modules` (virtiofs tag `modules`), then switch-roots into
the system closure. The `init=` and `initrd` paths change on
every rebuild and are available in `result/boot.json`.

### Libvirt

This backend builds a full NixOS system closure including its own
kernel. The consumer supplies a qcow2 disk image containing the
closure; libvirt presents it to the guest as `/dev/vda`. Grub on
the MBR loads the kernel, initramfs mounts the ext4 root from
`/dev/vda1`, and systemd activation proceeds normally. Networking
comes up via DHCP from libvirt's default network (typically
`192.168.122.0/24`).

## Baremetal

The imageless backend builds a NixOS system closure. A VM is one
way to run it; a real machine is another. Activate the closure on
baremetal with the closure's own switch script — no QEMU, no VM:

```shell
<closure>/bin/switch-to-configuration switch
```

The host then runs the same NixOS system the imageless backend
builds. A baremetal host supplies its own root filesystem and
kernel, so it overrides the `fileSystems` and `boot` entries the
imageless module declares for the virtiofs case.

## Controller

The `profiles.controller` module turns a NixOS host into a control node:
the toolchain to build a kernel and drive `make menuconfig`,
Ansible and its Python runtime, git, the QEMU and virtiofs
tooling, and system libvirt with the QEMU/KVM stack. Enable it on
top of a backend on a real machine:

```nix
modules = [
  nixos-flake.nixosModules.backends.libvirt
  nixos-flake.nixosModules.profiles.controller
  { nixos-flake.controller.enable = true; }
];
```

The same host can also import a test-suite module and run the
suite itself — the baremetal case above, driven from the
controller.

## Documentation

| Document | Content |
|---|---|
| [docs/usage.md](docs/usage.md) | Configurations, modules, overlays, packages, home overlay, block-device filesystems |
| [docs/design-decisions.md](docs/design-decisions.md) | Imageless and libvirt boot model, upstream references |
| [docs/verifying.md](docs/verifying.md) | Pre-commit checklist: format, flake check, image and package builds |

## Related work

- [run-kernel](https://github.com/metaspace/run-kernel). Rust init + NixOS boot via virtiofs. The direct inspiration for the imageless boot model.
- [nixos-shell](https://github.com/Mic92/nixos-shell). Nix-based lightweight QEMU VMs with host mounts.
- [kernel-development-flake](https://github.com/jordanisaacs/kernel-development-flake). Nix flake for Linux kernel development with QEMU.

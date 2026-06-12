# CLAUDE.md

## Project Overview

Library flake of NixOS modules, overlays, and templates for
provisioning NixOS systems. Two backend modules differ in the
artifact each produces: `backends.imageless` (a system closure
that boots a VM directly — tmpfs root, systemd initramfs,
external kernel, `/nix/store` and `/lib/modules` via virtiofs)
and `backends.libvirt` (a qcow2 disk image — `/dev/vda` root,
grub, NixOS-built kernel). The imageless closure also activates
on real hardware with `switch-to-configuration` instead of QEMU
— the baremetal case. Opt-in modules — `user`, the mounts
modules (`mounts.shares`, `mounts.storage`), the profiles
(`profiles.devel`, `profiles.build-tools`, `profiles.monitoring`,
`profiles.controller`), and the per-suite modules under
`testSuites.*` — compose on top of a backend; the `controller`
profile turns a host into a control node that builds kernels and
provisions guests.

**License**: copyleft-next-0.3.1

## Project Structure

```
nixos-flake/
├── flake.nix              Flake (nixosModules, overlays, templates, packages, checks)
├── flake.lock             Pinned nixpkgs revision
├── docs/
│   ├── usage.md             Configurations, overlays, packages, updating
│   └── design-decisions.md  Hardcoded choices and upstream references
├── modules/
│   ├── backends/
│   │   ├── imageless/     Imageless boot (tmpfs root, virtiofs, networkd), standalone
│   │   │   ├── default.nix  Backend module
│   │   │   └── user.nix     Imageless extraGroups defaults for the unprivileged account
│   │   └── libvirt/       Disk-image boot (grub on vda, DHCP, nix+flakes), standalone
│   │       ├── default.nix  Backend module
│   │       └── user.nix     Libvirt extraGroups defaults for the unprivileged account
│   ├── profiles/
│   │   ├── build-tools.nix  Build toolchain (Autotools plus common headers)
│   │   ├── controller.nix   Control-node profile: kernel build, Ansible, libvirt (options.nixos-flake.controller)
│   │   ├── devel.nix        Development profile (kernel testing tools)
│   │   └── monitoring.nix   Test-run-bracketed monitor units (options.nixos-flake.monitoring)
│   ├── mounts/
│   │   ├── shares.nix     Opt-in virtiofs shares (options.nixos-flake.shares)
│   │   └── storage.nix    Opt-in block-device mounts with optional mkfs (options.nixos-flake.storage)
│   ├── testSuites/        Per-suite modules (fstests, blktests, ltp, …)
│   ├── user.nix           Opt-in unprivileged account with configurable name (options.nixos-flake.user)
│   └── user-options.nix   Shared option schema for the unprivileged account
├── pkgs/
│   ├── default.nix        Custom packages via callPackage
│   ├── cpupower.nix       Standalone cpupower from kernel source tree
│   ├── damo.nix           DAMON user-space tool
│   ├── libbpf-tools.nix   CO-RE BPF tracing tools from BCC
│   ├── nfstest.nix        NFS test suite
│   ├── pynfs.nix          Python NFSv4 conformance tests
│   └── xnvme.nix          Cross-platform NVMe library and tools
├── overlays/
│   ├── default.nix        Composes per-package overlays + pkgs/
│   ├── fio.nix            fio with liburing + test suite + examples
│   └── xfstests.nix       Bump xfstests to 2026.03.20
├── templates/
│   ├── imageless/flake.nix  Imageless starter (default)
│   └── libvirt/flake.nix    Libvirt disk-image starter
├── LICENSES/
│   └── preferred/copyleft-next-0.3.1
├── COPYING                License overview and dual-licensing guidance
├── LICENSE                Copyright and license reference
└── README.md
```

## Critical Rules

### Never fabricate facts

Every NixOS option must be verified against the NixOS options search
(search.nixos.org/options) or the nixpkgs source.

### Long-form command options

NEVER use short flags when a long-form alternative exists.
`--template` not `-t`, `--recursive` not `-r`, `--parents` not
`-p`. Exception: tools without long-form options (`ssh -p`).

### Reference only upstream projects

Comments and commit messages describe this flake and the upstream
projects it packages — the Linux kernel, QEMU, xfstests, SPDK, BCC,
and so on. Never name the downstream projects that combine this
flake, nor the pipeline that drives it. The flake stands on its own;
how a consumer wires it up belongs in that consumer's tree.

## Rules

### Imageless: external kernel, NixOS-built initramfs

`boot.kernel.enable = false` tells NixOS not to build a kernel.
`boot.initrd.systemd.enable = true` tells NixOS to build a systemd
initramfs that mounts root (tmpfs), /nix/store, and /lib/modules
via virtiofs before switch-root into the system closure.

### Imageless: tmpfs root

`fileSystems."/" = lib.mkImageMediaOverride { fsType = "tmpfs"; }`
declares root as tmpfs. `mkImageMediaOverride` has higher priority
than default NixOS filesystem declarations. Changes are lost on
shutdown.

### Imageless: minimal profile

`imports = [ (modulesPath + "/profiles/minimal.nix") ]` reduces the
closure size by excluding unnecessary packages. Libvirt does not
import this profile; disk-image deployments expect a full system.

### Libvirt: grub on /dev/vda, ext4 root

`boot.loader.grub.device = "/dev/vda"` and
`fileSystems."/" = { device = "/dev/vda1"; fsType = "ext4"; }`
assume the standard virt-builder qcow2 layout. Consumers with
different disk bus or partition schemes override these.

### Password auth

`users.users.root.initialPassword = "root"` with
`users.mutableUsers = false` sets the root password on every boot
(tmpfs root resets it). The password is a serial-console
break-glass; SSH itself is key-only (each backend module sets
`PasswordAuthentication = false` inline to keep modules
standalone).

### Overlays

Each file in `overlays/` overrides one nixpkgs package using
`overrideAttrs`. The `overlays/default.nix` composes all per-package
overlays and merges custom packages from `pkgs/` into a single
overlay exported as `overlays.default`.

### Custom packages (pkgs/)

Packages not available in nixpkgs are defined in `pkgs/` using the
`callPackage` pattern from nix.dev. Each package is a file declaring
a function whose arguments are its dependencies. The overlay imports
`pkgs/default.nix` and merges them into the nixpkgs set.

### Templates

`templates/imageless/` (default) and `templates/libvirt/` are
copied by `nix flake init --template`. Each imports its matching
backend plus `user`, `devel`, and `overlays.default`. Users add
their own packages and NixOS options below.

### Baremetal: activate, do not boot

The imageless backend builds a `system.build.toplevel` closure.
On real hardware the closure is activated with
`<closure>/bin/switch-to-configuration switch` rather than booted
in QEMU. There is no baremetal module: the difference from the VM
case is how the closure is activated, not how it is built. A
baremetal host overrides the `fileSystems` and `boot` options the
imageless module declares for the virtiofs case.

### Controller: gated profile, composes on a backend

`profiles/controller.nix` is gated behind
`nixos-flake.controller.enable` and composes on top of a
disk-booted backend. It adds the kernel and Kconfig build
toolchain, Ansible and its Python runtime, git, the QEMU and
virtiofs tooling, and system libvirt with the QEMU/KVM stack
(`runAsRoot` off, virtiofsd as a vhost-user backend).

### Per-backend unprivileged-account defaults

`modules/user.nix` declares the unprivileged account and imports
the shared option schema from `modules/user-options.nix`. Each
backend ships its own `user.nix` (e.g.
`modules/backends/imageless/user.nix`) that sets
`nixos-flake.user.extraGroups` at `lib.mkDefault` priority — the
imageless backend defaults to `[ "wheel" "kvm" ]`, the libvirt
backend to `[ "wheel" "kvm" "libvirtd" ]`. Each backend's
`default.nix` imports its sibling `user.nix` so the default
applies whenever the backend is composed. The shared schema in
`user-options.nix` is what lets the backend set the option even
when `modules/user.nix` itself is not in the import set.

## Build

```shell
nix flake check                              # both backends
nix build .#checks.x86_64-linux.imageless    # single backend
readlink --canonicalize result
```

The `result` symlink points to the system closure. The NixOS init
is at `<closure>/init`. The init= path changes on every rebuild.

Before committing, run the verification steps in
[docs/verifying.md](docs/verifying.md): `nix fmt`, `nix flake check`,
the libvirt disk-image build, and the custom-package builds.

## Git Commit Guidelines

### One commit per change

Atomic commits. Spell fixes go in separate commits from code changes.

### Commit message format

```
subsystem: brief description in imperative mood (max 50 chars)

Plain English explanation of the change, 1-3 short paragraphs.
NEVER use bullet points or itemized lists in commit messages.

Generated-by: Claude AI
Signed-off-by: Your Name <your.email@example.org>
```

The subject line stays at or below 50 characters.

### Use Signed-off-by and Generated-by tags

Generated-by MUST be immediately followed by Signed-off-by with NO
empty lines between them. No Co-Authored-By trailer.

### No shopping cart lists

NEVER use bullet points or itemized lists in commit messages. Use
plain English paragraphs.

### Subsystem prefix

Prefix with the part of the flake the change touches: `flake:` for
flake.nix, `modules:` or the specific module name for a module,
`overlays:` for package overlays, `pkgs:` for custom packages,
`templates:` for template changes, `docs:` for documentation in
docs/, `README:` for README changes. Use `tree:` for the rare
change that genuinely spans the whole repository.

## Related work

- [run-kernel](https://github.com/metaspace/run-kernel). Rust init + NixOS boot via virtiofs. The direct inspiration for this project's boot model.
- [nixos-shell](https://github.com/Mic92/nixos-shell). Nix-based lightweight QEMU VMs with host mounts.
- [kernel-development-flake](https://github.com/jordanisaacs/kernel-development-flake). Nix flake for Linux kernel development with QEMU.

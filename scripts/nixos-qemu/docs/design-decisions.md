# Design decisions

This project exposes two NixOS backend modules for QEMU VMs:
`imageless` (tmpfs root, systemd initramfs, external kernel,
`/nix/store` and `/lib/modules` via virtiofs) and `libvirt` (qcow2
root disk, grub, NixOS-built kernel, libvirt DHCP). Each section
below explains the upstream mechanisms the backend relies on and
the design choices the module makes, deferring to NixOS defaults
where practical and using `lib.mkDefault` so downstream consumers
can override.

# Imageless

Boots from a NixOS system closure and systemd initramfs running
against the host's `/nix/store` shared read-only into the guest.
Root is tmpfs and does not persist across boots.

## systemd initramfs

NixOS builds a systemd-based initramfs where systemd runs as
PID 1. systemd's
[fstab-generator](https://github.com/systemd/systemd/blob/main/src/fstab-generator/fstab-generator.c)
reads the NixOS-generated initrd fstab and creates mount units
for `/nix/store` automatically. All upstream code, no custom init
binary.

The NixOS module that implements `boot.initrd.systemd` is
[`nixos/modules/system/boot/systemd/initrd.nix`](https://github.com/NixOS/nixpkgs/blob/master/nixos/modules/system/boot/systemd/initrd.nix).
The initrd fstab generation and `SYSTEMD_SYSROOT_FSTAB` wiring is
in
[`nixos/modules/tasks/filesystems.nix`](https://github.com/NixOS/nixpkgs/blob/master/nixos/modules/tasks/filesystems.nix).

The configuration enables the systemd initramfs and declares
virtiofs filesystems:

```nix
boot.initrd.systemd.enable = true;
boot.initrd.supportedFilesystems = [ "virtiofs" ];

fileSystems."/nix/store" = {
  device = "store";
  fsType = "virtiofs";
};
```

Kernel command line (standard parameters only):
```
root=tmpfs console=ttyS0,115200 console=hvc0 init=/nix/store/<hash>/init
```

## How the systemd initramfs works

The boot sequence uses standard systemd and NixOS mechanisms. Every
step is upstream code.

### NixOS initrd fstab generation

NixOS generates an initrd-specific fstab from `fileSystems`
declarations. The function `fsNeededForBoot` in
`nixos/lib/utils.nix` determines which filesystems go into the
initrd fstab. It returns true for any filesystem where either
`neededForBoot = true` or the mount point is in `pathsNeededForBoot`:

```nix
pathsNeededForBoot = [
  "/"
  "/nix"
  "/nix/store"
  "/var"
  "/var/log"
  "/var/lib"
  "/var/lib/nixos"
  "/etc"
  "/usr"
];
```

`/nix/store` is explicitly in this list. Any `fileSystems."/nix/store"`
declaration is automatically included in the initrd fstab without
requiring `neededForBoot = true`.

The initrd fstab is written to a file and passed to systemd via the
`SYSTEMD_SYSROOT_FSTAB` environment variable. NixOS wires this up in
`nixos/modules/tasks/filesystems.nix` through
`boot.initrd.systemd.managerEnvironment` and the `initrd-parse-etc`
service environment.

### systemd fstab-generator in the initrd

systemd-fstab-generator runs in the initrd and reads the initrd
fstab (from `SYSTEMD_SYSROOT_FSTAB`). For each entry, it generates
a systemd mount unit. The mount points are prefixed with `/sysroot`
because the generator runs in the initrd context
(`src/fstab-generator/fstab-generator.c`, `prefix_sysroot` logic).

For our configuration, the generator creates:
- `sysroot.mount`: tmpfs on `/sysroot` (from `root=tmpfs`)
- `sysroot-nix-store.mount`: virtiofs `store` on `/sysroot/nix/store`

### root=tmpfs handling

systemd-fstab-generator explicitly supports `root=tmpfs` as a
shortcut for a writable tmpfs root (see the `arg_root_what == "tmpfs"`
branch in `src/fstab-generator/fstab-generator.c`):

```c
} else if (streq(arg_root_what, "tmpfs")) {
    /* If root=tmpfs is specified, then take this as shortcut
       for a writable tmpfs mount as root */
    what = strdup("rootfs");
    fstype = arg_root_fstype ?: "tmpfs";
```

This creates a tmpfs mount at `/sysroot` with mode 0755.

### switch-root sequence

After all initrd mounts complete (`initrd-fs.target`), systemd
performs switch-root to `/sysroot`:

1. systemd reaches `initrd.target` (all initrd services done)
2. `initrd-cleanup.service` runs
3. `initrd-switch-root.target` activates
4. `initrd-switch-root.service` calls `systemctl switch-root /sysroot`

After switch-root, `/sysroot` becomes `/`. The virtiofs mount that
was at `/sysroot/nix/store` is now at `/nix/store`. The NixOS
stage-2 init at `/nix/store/<hash>/init` becomes accessible at its
expected path.

### Kernel module matching

When NixOS builds the initramfs, it can include kernel modules
from the NixOS kernel package. These modules must match the
running kernel version exactly. With an external custom kernel
(`boot.kernel.enable = false`), the versions will not match and
module loading in the initramfs will fail.

The solution is to exclude all kernel modules from the initramfs
and provide them via virtiofs instead:

```nix
boot.initrd.availableKernelModules = lib.mkForce [];
boot.initrd.kernelModules = lib.mkForce [];
```

This requires the external kernel to have the boot-critical
drivers built-in: `CONFIG_VIRTIO_FS=y` (mount /nix/store and
/lib/modules in the initramfs), `CONFIG_VIRTIO_PCI=y` (PCI
transport), and `CONFIG_TMPFS=y` (root filesystem). All other
drivers can be kernel modules (`=m`), loaded from `/lib/modules`
after switch-root. The `/lib/modules` directory is mounted via
virtiofs from the external kernel build's module install path.

## Root filesystem: tmpfs

```nix
fileSystems."/" = lib.mkImageMediaOverride {
  fsType = "tmpfs";
  options = [ "mode=0755" ];
};
```

Root is tmpfs. Everything written to `/` is lost on shutdown. This
is the standard NixOS approach for ephemeral systems. The operating
system state comes from `/nix/store` (read-only, shared from host)
and `/etc` (generated by NixOS activation from the store).

`lib.mkImageMediaOverride` sets the NixOS option priority to 60,
overriding the default root filesystem declaration from NixOS
modules. Without this, NixOS expects a persistent root device.
See: `lib/modules.nix` in nixpkgs (`mkImageMediaOverride`).

`systemd.services.systemd-remount-fs.enable = false` is set because
there is nothing to remount. The root is already writable tmpfs.

## /nix/store: virtiofs read-only

```nix
fileSystems."/nix/store" = {
  device = "store";
  fsType = "virtiofs";
};
```

The Nix store is immutable by design. Packages are content-addressed
and never modified in place. Read-only virtiofs mounting enforces
this at the mount level. The `device` field is the virtiofs tag
name that must match the tag configured in the virtiofsd instance
sharing the host's `/nix/store` into the guest.

## External kernel

```nix
boot.kernel.enable = false;
```

NixOS does not build a kernel. The kernel is built separately using
Kconfig fragments and installed to a destdir. This allows rapid
kernel development iteration without rebuilding the NixOS closure.

The kernel command line is passed to QEMU via the `-append` flag
(or equivalent configuration), not by NixOS. The imageless module
does not set `boot.kernelParams` because no NixOS bootloader is
active to enforce it. The QEMU configuration must include
`root=tmpfs` and `init=<closure>/init` explicitly.

## Minimal profile

```nix
imports = [ (modulesPath + "/profiles/minimal.nix") ];
```

The minimal profile disables documentation, fonts, and other
non-essential modules. This reduces the system closure size from
~500MB to ~200MB. The closure contains only systemd, SSH, network
configuration, and coreutils.

## Password authentication

```nix
users.mutableUsers = false;
users.users.root.initialPassword = "root";
services.openssh.settings.PasswordAuthentication = lib.mkDefault false;
```

SSH itself is key-only: the imageless module sets
`PasswordAuthentication = lib.mkDefault false`, and consumers
inject authorized keys per node. Root keeps a known
`initialPassword` for serial-console break-glass only. Because
root is tmpfs, `/etc/shadow` is generated fresh on every boot from
the NixOS configuration; `mutableUsers = false` ensures the
password is always reset to the configured value. The weak
password is not reachable over SSH and the console socket is only
accessible from the host.

## systemd-networkd

```nix
networking.useNetworkd = true;
systemd.network.networks."80-ethernet" = {
  matchConfig.Name = "en*";
  networkConfig.DHCP = "yes";
};
```

systemd-networkd is the standard network manager for systemd-based
systems. NetworkManager is heavier and designed for desktop use.
The network configuration matches all ethernet interfaces (virtio
NIC appears as `enp0s2` in QEMU with q35 machine type) and enables
DHCP.

# Libvirt

Boots from a qcow2 disk image that libvirt presents to the guest as
`/dev/vda`. The kernel and initramfs are part of the NixOS closure
installed on the disk. Grub on the MBR loads them; systemd
activation proceeds normally.

## Grub on /dev/vda

```nix
boot.loader.grub = {
  enable = true;
  device = "/dev/vda";
};
boot.loader.timeout = lib.mkDefault 1;
```

Libvirt's default virtio-blk configuration exposes the qcow2 disk
to the guest as `/dev/vda`. Grub installs into its MBR. The short
one-second timeout skips the interactive menu for test boots.
Consumers with a different disk bus (SCSI, SATA) set
`boot.loader.grub.device` to the matching path; consumers who
prefer the interactive menu override `boot.loader.timeout`.

## ext4 on /dev/vda1

```nix
fileSystems."/" = {
  device = "/dev/vda1";
  fsType = "ext4";
};
```

Assumes the standard virt-builder qcow2 layout (MBR partition
table, first partition formatted ext4). Consumers with a different
partition scheme override `fileSystems."/".device` and `fsType`.

## Kernel from nixpkgs

```nix
boot.kernelPackages = lib.mkDefault pkgs.linuxPackages_latest;
```

The libvirt backend does not disable `boot.kernel.enable`; NixOS
builds a kernel as part of the closure. `linuxPackages_latest`
tracks the most recent nixpkgs kernel. Consumers who want to pin
to a specific branch or use a custom kernel override
`boot.kernelPackages`.

## Scripted DHCP

```nix
networking.useDHCP = lib.mkDefault true;
```

Libvirt's default network assigns DHCP leases from
`192.168.122.0/24`. `networking.useDHCP` enables the NixOS
scripted-networking path, which brings up every interface with
DHCP. Consumers who prefer systemd-networkd or need static
addresses override `useDHCP` and declare their own configuration.
(Imageless uses `useNetworkd = true` instead because its minimal
profile excludes scripted-networking; libvirt carries the full
system, so the default scripted path works.)

## Nix with flakes and weekly garbage collection

```nix
nix.settings.experimental-features = [ "nix-command" "flakes" ];
nix.gc = {
  automatic = lib.mkDefault true;
  dates = lib.mkDefault "weekly";
  options = lib.mkDefault "--delete-older-than 7d";
};
```

Flakes are required because workflow-driven consumers may
re-evaluate nix expressions inside the guest. Weekly garbage
collection with a seven-day retention keeps the qcow2 from growing
unbounded across long workflow iterations.

## No nested libvirt

```nix
virtualisation.libvirtd.enable = lib.mkDefault false;
```

Nested virtualization is off by default. Workflows that need
virt-within-virt (KVM nested, for instance) opt in from a per-node
override.

## SSH posture matches imageless

The libvirt module inherits the same key-only sshd posture
described under Imageless. It does not carry its own
`initialPassword`: disk persistence means any break-glass setup
survives, and workflow consumers compose the user module (which
does set an initial root password) on top when they need it. A
standalone libvirt consumer with SSH keys injected does not get a
weak password baked in.

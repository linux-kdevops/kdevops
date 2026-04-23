# Design decisions

Managing QEMU VMs has two parts: generating the QEMU command line
(machine type, devices, disks, networking, kernel boot, passthrough)
and VM lifecycle (start, stop, restart, dependencies, logging,
resource control). systemd handles the lifecycle. Templates handle
the command line. No new daemon, no new wrapper.

Rendering and deploying the templates is left to the consumer.
The raw workflow is `minijinja-cli` + `systemctl`. Automation
layers are out of scope for this project.

The templates aim to be as unopinionated as possible. When a value
is hardcoded, it is either required by the underlying tool (QEMU,
virtiofsd, systemd), a workaround with documented reasoning, or a
sensible default that the user can override. This document lists
every such choice, the upstream reference that justifies it, and
how to change it when possible.

## Variable naming

Variable names match upstream flag or parameter names when a 1:1
mapping exists. When a variable controls a higher-level concept,
a descriptive name is used.

**`image`** — QEMU's flag is `-drive`. QEMU's own docs describe the
value as "which disk image to use with this drive." The sub-properties
(`image.file`, `image.format`, `image.cache`) match `-drive` property
names exactly. The name `image` describes what the user configures (a
disk image), while the properties map 1:1 to QEMU's `-drive`
properties.

**`cpus`** — QEMU's flag is `-smp`. The parameter inside `-smp` is
called `cpus=`. The variable matches the parameter name.

**`vsock_cid`** — QEMU's device property is `guest-cid`. The variable
adds the technology context (`vsock`) because `guest_cid` alone is
ambiguous. Maps to `-device vhost-vsock-pci,guest-cid=`.

**`ssh_port`** — No upstream equivalent. Maps to
`-nic hostfwd=tcp:127.0.0.1:<port>-:22`. The concept (SSH port
forwarding) spans multiple flag components.

**`pci_passthrough`** — No upstream equivalent. Maps to
`-device vfio-pci,host=<addr>`. Combines the bus type (PCI) with the
operation (passthrough).

**`autostart`** — No upstream equivalent. Inverted boolean: `false`
maps to `-S` (QEMU starts paused). QEMU has no "autostart" flag.

**`firmware`** — QEMU has no `-firmware` flag. Firmware selection is
implicit: pflash0 populated → UEFI, pflash0 absent → BIOS. QEMU's
own firmware specification (`docs/interop/firmware.json`) calls the
top-level concept `Firmware` and the internal function is
`pc_system_firmware_init()`. The sub-properties `code` and `vars`
match the OVMF file naming convention (`OVMF_CODE_4M.fd`,
`OVMF_VARS_4M.fd`). QEMU's spec uses the more verbose `executable`
and `nvram-template` but the OVMF file names are what users encounter
directly.

**`cloud_init.users[].password`** — Cloud-init's key is
`plain_text_passwd`. The variable uses `password` for simplicity. The
template maps it to `plain_text_passwd`.

## User-configurable (vars file)

Fully controlled by the user. See [vars.md](vars.md) for reference.

`cpu`, `accel`, `ram`, `cpus`, `machine_type`, `iommu`,
`firmware` (code, vars, vars_format), `gdb`, `autostart`,
`image` (file, format, cache, aio, discard, detect-zeroes),
`drives`, `ssh_port`, `vsock_cid`, `ssh_private_key`,
`kernel` (image, append, initrd),
`shares` (tag, mount, dir, translate_uid, translate_gid),
`share_transport`, `virtiofsd_binary`,
`cloud_init` (seed, locale, ssh_pubkey, users),
`pci_passthrough`, `nvme` (drives, subsystems),
`service` (any `[Service]` directive)

## systemd service properties

**`KillMode=`** — Set to `mixed`. Sends `KillSignal=` to the main
process. After the main process exits or `TimeoutSec=` elapses,
remaining processes in the cgroup receive `SIGKILL`. For VMs, the
main process is QEMU. After `ExecStop=` runs QMP graceful shutdown,
if QEMU exits cleanly, any leaked child processes are killed
immediately. The alternative `control-group` would send `KillSignal=`
to all processes simultaneously, which is unnecessary when only QEMU
needs the signal. See: `man systemd.kill`.

**`TimeoutSec=`** — Set to `2min`. Grace period for `ExecStop=`
before systemd sends `SIGKILL`. The systemd default
(`DefaultTimeoutStopSec=`) is 90s. VMs need longer because ACPI
powerdown triggers a full guest OS shutdown sequence (flushing
buffers, stopping services, unmounting filesystems). Override:

```yaml
service:
  TimeoutSec: 5min
```

See: `man systemd.service`.

**`Slice=`** — Set to `machine.slice`. All virtual machines and
containers registered with systemd-machined are placed in
machine.slice. Canonical cgroup placement for VMs.
See: `man systemd.special`.

**`PartOf=`**, **`Before=`**, **`WantedBy=`** — Set to
`machines.target`. Standard target for starting all containers and
virtual machines. `PartOf=` ensures VMs stop when machines.target
stops. `WantedBy=` enables auto-start. See: `man systemd.special`.

**`Type=`** — Set to `simple`. QEMU does not implement
`sd_notify()`. `notify` would be correct but requires the service to
call `sd_notify(READY=1)` after initialization. A patch adding
`sd_notify()` to QEMU was submitted (qemu-devel, 2025-12-17) but has
not been merged. When QEMU gains `sd_notify()` support, this should
change to `notify`. See: `man systemd.service`.

## machined registration

Each VM registers itself with machined at start-up via
`ExecStartPost=` running
`varlinkctl call <socket> io.systemd.Machine.Register <json>`.
Socket path: `/run/user/%U/systemd/machine/io.systemd.Machine`
(user scope) or `/run/systemd/machine/io.systemd.Machine`
(system scope). Required JSON fields: `name`, `class=vm`,
`service=qemu-system`, `leader=${MAINPID}`. Optional:
`vSockCid` when the vars file sets `vsock_cid`.

Registering `vSockCid` is what makes `ssh machine/<vm>` route
over AF_VSOCK. The shipped
`/etc/ssh/ssh_config.d/20-systemd-ssh-proxy.conf` hands the
`machine/*` pattern to `systemd-ssh-proxy`, which looks the
machine up over Varlink and reads the registered CID. Without
it, `systemd-ssh-proxy` exits with "Machine has no AF_VSOCK
CID assigned" (`src/ssh-generator/ssh-proxy.c`).

### Why two `ExecStartPost=` lines across two templates

The shared `qemu-system@.service.j2` renders once for all
instances and has no per-VM variables at that render time, so
its Jinja cannot branch on `vsock_cid`. It emits one
`ExecStartPost=` that registers without CID - correct for any
VM, always safe.

The per-VM `qemu-system-override.conf.j2` renders with
`vsock_cid` in scope. When set, it emits `ExecStartPost=`
(empty) followed by `ExecStartPost=-varlinkctl ... vSockCid:N`.
Systemd treats the empty directive as a reset of the
accumulated list, so the drop-in's call replaces the shared
template's call rather than running alongside. Net effect:
every VM makes one registration call, with CID if configured,
without otherwise. VMs that never set `vsock_cid` hit only the
shared template's call and behave exactly as before.

### Why Varlink and not `busctl`

The legacy DBus `RegisterMachine` method
(`src/machine/machined-dbus.c`) has a fixed `sayssus`
signature with no `vSockCid` field. `RegisterMachineEx`
accepts `VSockCID` but requires the leader identified by
`LeaderPIDFD` or `LeaderPID+LeaderPIDFDID`, neither of which
a shell script can synthesise. Varlink's
`io.systemd.Machine.Register` leader dispatcher accepts a
bare integer PID and machined acquires the pidfd daemon-side
(`json_dispatch_pidref` in
`src/libsystemd/sd-json/json-util.c`).

### Quoting and expansion

`${MAINPID}` uses the brace form because systemd's exec parser
expands `${VAR}` (but not `$VAR`) inside escape-quoted
arguments, letting the JSON body ride as one argv entry
without a `/bin/sh -c` wrapper. The drop-in inlines
`{{ vsock_cid }}` at Jinja render time rather than pulling
`${VSOCK_CID}` from the environment because the value is
already known per-VM.

The `-` prefix on `ExecStartPost=` keeps the VM running if
machined is unreachable. Registration is informational.

## QEMU workarounds

**`KillSignal=`** — Set to `SIGCONT`. QEMU on `SIGTERM` calls
`qemu_system_killed()` which sets `force_shutdown=true` and exits
immediately without ACPI powerdown. `SIGCONT` is a no-op signal that
keeps QEMU alive, giving `ExecStop=` time to send QMP
system_powerdown for proper ACPI shutdown. After `TimeoutSec=`,
systemd sends `SIGKILL` (via `KillMode=mixed`). Not
user-configurable. See: `man systemd.kill`.

**`ExecStop=`** — Sends QMP system_powerdown via socat for graceful
guest shutdown. QEMU does not translate `SIGTERM` to ACPI powerdown.
When `ssh_private_key` is defined, `ExecStop=` first attempts SSH
shutdown (guest-initiated poweroff) with QMP as fallback. Not
user-configurable (the mechanism is fixed; the SSH path is enabled by
setting `ssh_private_key` and `vsock_cid`).

## QEMU firmware

**`-drive if=pflash`** — OVMF firmware via pflash drives. QEMU's
firmware specification (`docs/interop/firmware.json`) defines the
`split` mode: the executable (CODE) is read-only and shared, the
NVRAM template (VARS) is cloned per-VM and configured read-write.
pflash0 holds the executable, pflash1 holds the per-VM NVRAM file.

QEMU selects firmware mode based on pflash0 presence: if pflash0 is
populated, QEMU enters pflash mode (UEFI); if absent, ROM mode
(SeaBIOS). There is no explicit firmware flag; the presence of pflash
drives is the entire mechanism. See: `hw/i386/pc_sysfw.c`
`pc_system_firmware_init()`.

pflash is created by `pc_system_flash_create()` which is part of the
PC machine initialization path. microvm does not call this function;
it calls `x86_bios_rom_init()` directly, even with `pcie=on`. The
`pcie=on` property on microvm only enables the GPEX PCIe host bridge
for PCI devices; it does not change the firmware initialization path.
ARM virt machines create pflash independently (256 KB sectors vs
x86's 4 KB).

The NVRAM file stores UEFI boot order, Secure Boot key databases
(PK, KEK, db, dbx), and guest-written variables. Each VM needs its
own writable NVRAM file for independent variable state. QEMU enforces
this with file-level locking. A second VM attempting to open the same
writable NVRAM file will fail to start. Create a per-VM copy from the
template:

```shell
cp /usr/share/OVMF/OVMF_VARS_4M.fd images/test-ovmf-vars.fd
```

The firmware spec also supports qcow2 format. An alternative to
copying is a qcow2 overlay with the template as backing file:

```shell
qemu-img create --format qcow2 \
  --backing /usr/share/OVMF/OVMF_VARS_4M.fd \
  --backing-format raw \
  images/test-ovmf-vars.qcow2
```

This saves disk space (only changed variables are stored) and keeps
the system template untouched. Use `format: qcow2` in the vars file
when using a qcow2 NVRAM file.

When the `firmware` section is absent from vars, no pflash drives are
rendered and QEMU defaults to SeaBIOS. Backward compatible.
User-configurable: set `firmware.code` and `firmware.vars`.

## QEMU device choices

**`-device virtio-*-pci-non-transitional`** — All virtio devices use
non-transitional variants. These only require `CONFIG_VIRTIO_PCI` in
the guest kernel. Transitional devices additionally require
`CONFIG_VIRTIO_PCI_LEGACY`, which custom kernels often disable. On
microvm, devices use the `-device virtio-*-device` suffix
(virtio-mmio transport). vhost-user-fs-pci has no non-transitional
variant (modern-only device). Not user-configurable (determined by
`machine_type`). See: `<qemu_binary> -device help`.

**`-device virtio-rng-*`** — Always present. Provides entropy to the
guest. Without it, `/dev/random` may block and boot can stall waiting
for entropy. Not user-configurable.

**`-nographic`**, **`-serial mon:stdio`** — Headless operation with
serial console on stdio. Standard interface for kernel development
VMs. The serial output goes to the systemd journal via stdout
capture. VGA, SPICE, and VNC are not supported. Not
user-configurable.

**`-nic user`** — User-mode networking (SLIRP). No host privileges
required. Port forwarding controlled via `ssh_port`. Alternative
host-guest transport via VSOCK (`vsock_cid`). TAP and bridge
networking are not supported (require root or network namespace
setup). The NIC model is determined by `machine_type`.
See: `man qemu-system`.

**`-object memory-backend-memfd,share=on`** — Required by virtiofs.
virtiofsd accesses guest memory via shared memory mapping. Without
`share=on`, virtiofsd cannot map guest memory. Only emitted when
virtiofs shares are defined. Not user-configurable.

**`LimitMEMLOCK=`** — Auto-computed as `<ram+256>M` when
`pci_passthrough` is defined. VFIO DMA mapping requires locked
memory. The 256M overhead covers QEMU allocations beyond guest RAM.
Override:

```yaml
service:
  LimitMEMLOCK: 8G
```

See: `man systemd.exec`.

## virtiofsd

**`--sandbox=`** — Set to `namespace` with `--uid-map :0:%U:1:` and
`--gid-map :0:%G:1:`. Provides PID, mount, network, and user
namespace isolation as an unprivileged user. The `--uid-map` maps
root inside the namespace to the service user outside (`%U`/`%G` are
systemd specifiers expanded at runtime). Without `--uid-map`,
virtiofsd warns "Couldn't set the process uid as root" because the
default 1-to-1 UID mapping does not include UID 0 (virtiofsd calls
`setresuid(0)` after creating the namespace). Override via per-share
env file: set `VIRTIOFSD_SANDBOX_ARGS=--sandbox=none`. See:
`/usr/libexec/virtiofsd --help`.

**`--xattr`** — Extended attribute support. Required for correct
POSIX semantics (security labels, capabilities, ACLs). Not
user-configurable. See: `/usr/libexec/virtiofsd --help`.

**`--no-announce-submounts`** — QEMU does not support submounts.
Prevents virtiofsd from announcing submount boundaries that the VMM
cannot handle. Not user-configurable. See:
`/usr/libexec/virtiofsd --help`.

**`--fd=3`** — Socket activation. systemd passes the listening socket
as FD 3 per the `sd_listen_fds` protocol. Not user-configurable.
See: `man sd_listen_fds`.

## Cloud-init

### Network configuration gap

Debian generic and genericcloud images ship with an empty
`/etc/netplan/` directory. They depend on cloud-init's fallback
network detection to generate netplan YAML at first boot. The
fallback scans all physical NICs and generates DHCP config for the
first one. This works when cloud-init boots with the image's own
distro kernel and initramfs.

With direct kernel boot and a custom initramfs, the fallback is
unreliable. The symptom: `/etc/netplan/` stays empty,
`systemd-networkd-wait-online.service` hangs, the guest has no
network connectivity.

The fix: provide a `network-config` file in the seed ISO. The
NoCloud datasource processes `network-config` before the fallback,
so it works regardless of boot mode. `files/network-config` is a
static file (no template rendering needed). Pass it to
`cloud-localds`:

```shell
cloud-localds --network-config=files/network-config \
  images/seed.iso /tmp/user-data /tmp/meta-data
```

The network config matches both predictable interface names (`en*`)
and classic names (`eth*`). Custom kernels without full PCI sysfs
support or with `net.ifnames=0` on the command line leave interfaces
as `eth0`. Both patterns are needed.

Images that do NOT need this fix:
nocloud (ships `/etc/netplan/90-default.yaml` baked in),
mkosi (ships `/etc/systemd/network/80-dhcp.network` baked in),
imageless (debootstrap includes network config).

See: https://cloudinit.readthedocs.io/en/latest/reference/network-config-format-v2.html

### user-data

Infrastructure requirements for the VM to be usable with the
service templates. Apply only when `cloud_init` is defined.

**`disable_root`**, **`PermitRootLogin`**,
**`PasswordAuthentication`** — Set to `false`, `yes`, `yes`. Root SSH
access required for non-interactive VM management (`ExecStop=` SSH
shutdown, automated provisioning). Not user-configurable.

**`locale`** — The `locale:` directive uses cloud-init's built-in
locale module, which handles per-distro differences automatically.
Debian: writes `/etc/locale.gen` and runs `locale-gen`. Fedora:
writes `/etc/locale.conf`. No distro-specific `write_files` or
`packages` needed.

**`growpart`** and **`resizefs`** — Cloud-init's built-in `growpart`
and `resizefs` modules run automatically (enabled in
`cloud_init_modules` by default on both Debian and Fedora). They
detect the root partition from the mount table and resize it to fill
the disk. No `runcmd` needed. Verified against upstream Fedora Cloud
image `/etc/cloud/cloud.cfg` which lists both modules.

**`runcmd`** — Runs `touch /etc/cloud/cloud-init.disabled` only.
Disables cloud-init after first run to prevent re-provisioning on
reboot. Not user-configurable. See: `man cloud-init`.

**`ssh_pwauth`** — Set to `true`. Password authentication fallback
for console access when no SSH key is configured. Not
user-configurable.

## 9P

**`security_model=`** — Set to `none`. Passes through file
permissions without UID/GID mapping. Correct for sharing host
directories where the user already owns the files. Other models
(mapped-xattr, passthrough) require root or change on-disk xattrs.
Not user-configurable. See: `man qemu-system`.

**`multidevs=`** — Set to `remap`. Remaps device/inode numbers for
filesystems spanning multiple host devices. Prevents inode collisions
when sharing directories that contain mount points. Not
user-configurable. See: `man qemu-system`.

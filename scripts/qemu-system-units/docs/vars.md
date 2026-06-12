# Variable reference

One vars file per VM. All templates render from the same file.

Variable names match upstream terminology when a 1:1 mapping exists
(e.g. `cpu` → `-cpu`, `accel` → `-accel`). When a variable maps to
a parameter inside a flag, the parameter name is used (e.g. `cpus`
→ `-smp cpus=N`). When a variable controls a higher-level concept
that spans multiple flags, a descriptive name is used (e.g.
`ssh_port`, `pci_passthrough`). See [design-decisions.md](design-decisions.md) for
naming rationale.

Relative paths resolve against `WorkingDirectory=`. The template sets
`WorkingDirectory=%S/qemu-system/%i`, which resolves to
`$XDG_STATE_HOME/qemu-system/<vm>` for user services and
`/var/lib/qemu-system/<vm>` for system services. That directory is
auto-created and owned by the service via `StateDirectory=qemu-system/%i`,
so per-VM state files like NVMe qcow2 images can be referenced with
bare filenames in vars (for example `image: disk.qcow2`) and land in a
predictable, per-unit location. See [exec directories](#exec-directories)
below for when to pick `StateDirectory=` vs the five sibling directives,
and for override semantics.

## VM identity

**`vm_name`** — VM instance name. Used as the systemd template
instance specifier (`qemu-system@<vm_name>`), the machined
registration name, and the cloud-init `instance-id` /
`local-hostname`. Required.

**`service_scope`** — `user` or `system`. Determines deploy paths
and unit behavior. User scope deploys to `~/.config/systemd/user/`,
needs no sudo. System scope deploys to `/etc/systemd/system/`,
requires root. Default: `user`.

**`uuid`** — RFC 4122 UUID string for the VM. Optional. When set,
maps to `-uuid` (QEMU SMBIOS / DMI identity, surfaces inside the
guest as `dmidecode -s system-uuid` and `/sys/class/dmi/id/product_uuid`)
and to the `id` field of the `io.systemd.Machine.Register` varlink
call (surfaces on the host as `Id=` in `machinectl show <vm_name>`).
Pairing the two correlates the same VM across QEMU's identification
table and machined's record. When omitted, QEMU passes through its
default (all-zeros UUID) and the Register call omits `id` entirely.
See: `man qemu-system`, `src/machine/machine-varlink.c` Register
dispatch table.

## QEMU

**`qemu_binary`** — Absolute path to the QEMU system emulator
binary. Required. The name encodes the guest architecture
(`qemu-system-x86_64` for x86_64 guests, `qemu-system-aarch64` for
ARM64). Works on both Intel and AMD hosts; the name is the guest
architecture, not the host CPU vendor. Distros ship symlinks (`kvm`,
`qemu-system-amd64`, `qemu-kvm`) that all point to the same binary.
Use the upstream name. Maps to the `ExecStart=` binary path.
Example: `/usr/bin/qemu-system-x86_64`.

**`cpu`** — CPU model. Maps to `-cpu`. Default: `host` (passthrough
host CPU features to guest). Common values: `host`, `max` (all
emulatable features, useful with TCG). List available models with
`<qemu_binary> -cpu help`. See: `man qemu-system`.

**`accel`** — Accelerator. Maps to `-accel`. Default: `kvm`. Common
values: `kvm` (hardware virtualization), `tcg` (software emulation),
`hvf` (macOS Hypervisor.framework). When `iommu` is `intel-iommu` or
`amd-iommu`, the template auto-appends `kernel-irqchip=split` to
`-accel` (required for interrupt remapping). See: `man qemu-system`.

**`ram`** — Guest memory in megabytes. Integer. Maps to `-m`. Also
used for `-object memory-backend-memfd,size=<ram>M` (virtiofs shared
memory) and `LimitMEMLOCK=<ram+256>M` (VFIO DMA mapping overhead,
see systemd.exec(5)). QEMU default: 128. Suffixes M, G accepted by
QEMU but the template passes the raw integer to `-m` which defaults
to megabytes. See: `man qemu-system`.

**`cpus`** — Virtual CPU count. Integer. Maps to `-smp`. Default: 1.
See: `man qemu-system`.

**`machine_type`** — QEMU machine type. Maps to `-machine type=`.
Common values: `q35` (x86_64, modern PCIe), `pc` (x86_64, legacy
ISA/PCI), `virt` (aarch64), `microvm` (x86_64, minimal). `q35` is
required for x86 IOMMUs and recommended for modern x86 guests.

Machine properties can be appended after the type name:
`microvm,pcie=on,rtc=on`. QEMU parses these as machine options.

microvm uses virtio-mmio transport instead of PCI. The template
auto-detects microvm from the machine_type value and switches to
`*-device` suffix (MMIO) for all virtio devices. NVMe, VFIO, and
IOMMU are PCI-only and require `pcie=on` on microvm. Without
`pcie=on`, these features are silently omitted.

List available types with `<qemu_binary> -machine help`. Required.

**`iommu`** — IOMMU device type. Maps to `-device <iommu>`.

`intel-iommu`: Intel VT-d. Requires `-machine q35`. Auto-sets
`kernel-irqchip=split` on `-accel` (required for intremap) and
`caching-mode=on` so the guest's IOMMU page-table updates are
trapped into QEMU's DMA path. That is needed both for VFIO
passthrough and for a guest-side userspace driver (VFIO/SPDK/DPDK)
that maps an emulated device for DMA; without it the guest IOMMU
only does interrupt remapping and DPDK fails with "failed to select
IOMMU type".

`amd-iommu`: AMD-Vi. Requires `-machine q35`. Auto-sets
`kernel-irqchip=split` and `dma-remap=on` (same reason as
intel-iommu's `caching-mode=on`).

`virtio-iommu-pci`: virtio IOMMU. Works with `-machine q35`
(x86_64) and `-machine virt` (aarch64). No kernel-irqchip
requirement.

`arm-smmuv3`: ARM SMMUv3. Requires `-machine virt` (aarch64 only).
No kernel-irqchip requirement.

See: `man qemu-system`.

**`firmware`** — Dict. UEFI firmware via pflash drives. Omit for
BIOS boot (SeaBIOS default on x86). Maps to two
`-drive if=pflash` entries. Supported on q35, i440fx, and ARM virt.
microvm does not support pflash. See:
[design-decisions.md](design-decisions.md) (QEMU firmware).

**`firmware.code`** — Path to the shared firmware executable.
Read-only at runtime. Maps to
`-drive if=pflash,format=raw,readonly=on,file=`. x86_64:
`/usr/share/OVMF/OVMF_CODE_4M.fd` (`ovmf`). aarch64:
`/usr/share/AAVMF/AAVMF_CODE.fd` (`qemu-efi-aarch64`).
See: `man qemu-system`.

**`firmware.vars`** — Path to the per-VM NVRAM file. Writable; each
VM needs its own file for independent UEFI variable state. Raw copy
or qcow2 overlay of `/usr/share/OVMF/OVMF_VARS_4M.fd`. Maps to
`-drive if=pflash,format=<vars_format>,file=`. See:
[design-decisions.md](design-decisions.md) (QEMU firmware).

**`firmware.vars_format`** — NVRAM file format. Default: `raw`. Set
to `qcow2` when using a qcow2 overlay. Maps to `-drive format=`.
See: `man qemu-system`.

**`gdb`** — Boolean. Maps to `-gdb unix:<socket>`. The socket is
placed in the systemd `RuntimeDirectory=`. Connect with:
`gdb vmlinux -ex "target remote <socket>"`.

**`autostart`** — Boolean. Default: `true`. When `false`, maps to
`-S` (QEMU starts paused, waiting for GDB continue).

## Root disk

**`image`** — Dict. Root disk image configuration. Omit for imageless
boot (virtiofs rootfs). Maps to `-drive`.

**`image.file`** — Path to the disk image. Relative paths resolve
against `WorkingDirectory=`. Required when `image` is defined. Maps
to `-drive file=`. See: `man qemu-system`, `man qemu-img`.

**`image.format`** — Disk image container format. Default: `raw`.
Common values: `qcow2`, `raw`. QEMU can auto-detect but explicit is
safer. Maps to `-drive format=`. See: `man qemu-system`.

**`image.cache`** — Block cache mode. Maps to `-drive cache=`.
Values: `writeback` (default), `none` (direct I/O, data integrity),
`writethrough`, `directsync`, `unsafe`. See: `man qemu-system`.

**`image.aio`** — Asynchronous I/O mode. Maps to `-drive aio=`.
Values: `threads` (default), `native` (Linux AIO, requires
`cache=none` or `cache=directsync`), `io_uring`.
See: `man qemu-system`.

**`image.discard`** — Discard (TRIM/UNMAP) support. Maps to
`-drive discard=`. Values: `ignore` (default), `unmap`.
See: `man qemu-system`.

**`image.detect-zeroes`** — Zero write optimization. Maps to
`-drive detect-zeroes=`. Values: `off` (default), `on`, `unmap`
(convert zero writes to discard). See: `man qemu-system`.

## Extra drives

**`drives`** — List of additional virtio-blk drives. Each entry maps
to a `-drive` with the same backend properties as the root disk:
`file`, `format`, `cache`, `aio`, `discard`, `detect-zeroes`.

## Networking

**`ssh_port`** — Host TCP port forwarded to guest port 22. Integer.
Maps to `-nic hostfwd=tcp:127.0.0.1:<port>-:22`. Bound to localhost
only. Must be unique per VM. Omit to disable TCP port forwarding
(use VSOCK instead).

**`vsock_cid`** — VSOCK Context ID for direct host-guest
communication. Integer, range 3-4294967295 (0=hypervisor, 1=local,
2=host). Must be unique per VM. Maps to
`-device vhost-vsock-pci,guest-cid=<cid>`. Also used by the graceful
shutdown `ExecStop=` which targets `root@vsock/<cid>`.
See: `man qemu-system`.

**`ssh_private_key`** — Path to the SSH private key for
non-interactive VM access. Used by the graceful shutdown
`ExecStop=ssh -i`. Requires `vsock_cid`.

## Direct kernel boot

**`kernel`** — Dict. Presence enables direct kernel boot, bypassing
the disk image bootloader.

**`kernel.image`** — Path to the kernel image (bzImage/vmlinuz). Maps
to `-kernel`. Required when `kernel` is defined. Example:
`/home/user/kernel/destdir/boot/vmlinuz-6.x.y`.
See: `man qemu-system`.

**`kernel.append`** — Kernel command line. Maps to `-append`.
Example: `root=/dev/vda1 console=ttyS0,115200 rw`. For imageless
boot: `root=rootfs rootfstype=virtiofs`.

**`kernel.initrd`** — Path to the initramfs image. Maps to
`-initrd`. Required for imageless boot (the init binary mounts root
before switch_root). Example: `images/initramfs.img`.

## File sharing

**`shares`** — List of host-guest directory shares. Each share
produces virtiofsd socket and service dependencies, cloud-init mount
entries, and either virtiofs chardev/device pairs or 9P fsdev/device
pairs depending on `share_transport`.

Per-share properties:

`tag`: mount tag visible inside the guest. Required. Used as part of
the virtiofsd instance name (`virtiofsd@<vm>-<tag>`).

`mount`: guest mount point. Required. Rendered into cloud-init
`mounts:` entries.

`dir`: host directory to share. Optional. When omitted, virtiofsd
serves the user's home directory (systemd `%h` specifier). When set,
overrides `VIRTIOFSD_SHARED_DIR` via a per-share `EnvironmentFile=`.

`translate_uid`: virtiofsd UID mapping for imageless boot. Maps to
virtiofsd `--translate-uid`. Format:
`map:<guest-base>:<host-base>:<count>`. Example: `map:0:1000:1` maps
host UID 1000 to guest UID 0 (root). See:
`/usr/libexec/virtiofsd --help`.

`translate_gid`: same as `translate_uid` but for GIDs. Maps to
virtiofsd `--translate-gid`. Defaults to `translate_uid` value when
omitted.

**`virtiofsd_binary`** — Path to the virtiofsd binary. Default:
`/usr/libexec/virtiofsd`. Maps to the virtiofsd `ExecStart=` binary
path.

**`share_transport`** — `virtiofs` (default) or `9p`. virtiofs uses
socket-activated virtiofsd daemons per share. 9P is built into QEMU
(`-fsdev` + `-device virtio-9p-pci`), no daemon, no socket
activation. When using 9P, `dir` is required for each share (no
implicit home default). See: kernel
`Documentation/filesystems/9p.rst`.

## Cloud-init

**`cloud_init`** — Dict. Presence enables cloud-init provisioning.
Omit the entire section for mkosi or imageless boot. When defined,
the seed ISO is attached as a `-drive` and cloud-init
user-data/meta-data are rendered.

**`cloud_init.seed`** — Path to the cloud-init seed ISO. Maps to
`-drive file=<seed>,format=raw`. Generated by `cloud-localds` from
rendered user-data and meta-data. Always raw format (ISO9660 inside
raw container). See: `man cloud-localds`.

**`cloud_init.locale`** — VM locale. Default: `en_US.UTF-8`. Maps to
cloud-init `locale:` and `write_files:` for `/etc/locale.gen`.

**`cloud_init.ssh_pubkey`** — SSH public key. Applied to all users
via cloud-init `ssh_authorized_keys:`. Required for non-interactive
SSH access (password auth needs `/dev/tty`).

**`cloud_init.users`** — List of user accounts to create. Each entry
maps to a cloud-init `users:` entry. Root is not special; include it
in the list with a password to enable root login. The template always
emits `disable_root: false` and a `PermitRootLogin yes` sshd drop-in
regardless of the user list.

Per-user properties:

`name`: username. Required. Maps to cloud-init `name`.

`password`: plain text password. Default: same as `name`. Maps to
cloud-init `plain_text_passwd`.

`groups`: comma-separated group list. Example: `sudo`. Maps to
cloud-init `groups`.

`sudo`: sudo rule. Example: `ALL=(ALL) NOPASSWD:ALL`. Maps to
cloud-init `sudo`.

`shell`: login shell path. Example: `/bin/bash`. Maps to cloud-init
`shell`.

See: https://cloudinit.readthedocs.io/en/latest/reference/modules.html

## PCIe passthrough

**`pci_passthrough`** — List of host PCI devices to pass through via
VFIO. Maps to `-device vfio-pci,host=<addr>`. Also generates systemd
`Requires=vfio-bind@<addr>.service` dependencies and
`LimitMEMLOCK=<ram+256>M` (see systemd.exec(5)).

Requires one-time root setup: deploy rendered udev rules and
`vfio-pci` module config. After setup, all operations run in user
mode.

Per-device properties:

`addr`: PCI address in domain:bus:device.function format. Required.
Example: `0000:2d:00.0`. Identify with `lspci -nv`. All devices in
the same IOMMU group must be passed through together.

`opts`: additional `-device vfio-pci` properties. Example:
`rombar=0`.

See: kernel `Documentation/driver-api/vfio.rst`.

## NVMe

**`nvme`** — Dict containing `drives` and `subsystems` lists. Maps
to `-device nvme`, `-device nvme-ns`, `-device nvme-subsys`, and
their associated `-drive` entries.

Guest device paths: `/dev/nvme0n1`, `/dev/nvme1n1`, ...

Stable names:
`/dev/disk/by-id/nvme-QEMU_NVMe_Ctrl_<serial>_1`.

`serial` is required by QEMU (errors with "serial property not set"
if omitted). The template defaults to `nvme0`, `nvme1`, etc.

**`nvme.drives`** — List of NVMe controllers. Simple form (no
`namespaces` key) creates one controller with one implicit namespace.
Explicit `namespaces` key gives full per-namespace control.

Drive backend properties (simple and explicit forms): `file`,
`format` (default: qcow2), `aio`, `cache`, `discard`,
`detect-zeroes`.

Controller properties (maps to `-device nvme`): `serial`,
`max_ioqpairs`, `msix_qsize`, `mdts`, `vsl`, `cmb_size_mb`,
`legacy-cmb`, `pmr` (see below), `ioeventfd`, `ocp`, `use-intel-id`,
`dbcs`, `aerl`, `aer_max_queued`, `mqes`, `ctratt.mem`, `atomic.dn`,
`atomic.awun`, `atomic.awupf`, `zoned.zasl`, `zoned.auto_transition`,
`opts`.

**`nvme.drives[].pmr`** — Dict. Adds a Persistent Memory Region to that
controller. Maps to a `-device nvme,pmrdev=<id>` link plus a
`-object memory-backend-file` that the link names. The PMR occupies PCI
BAR 4/5 (`hw/nvme/ctrl.c`). CMB and PMR can coexist on one controller.
PMR is rejected by QEMU under SR-IOV and when MSI-X claims the
exclusive BAR. `nvme.drives` controllers only (both the simple and
the explicit-namespace form), not subsystem controllers. Omit the
key for a controller with no PMR (backward compatible).

`size`: backing region size in bytes. Required. Must be a power of 2;
QEMU's NVMe code requires at least 16 bytes and the memory backend
additionally rejects a size below one host page, so the practical
minimum is one page (4096 bytes on x86_64). Maps to
`-object memory-backend-file,size=`.

`mem-path`: backing file path. Default: `nvme-pmr-<index>.img`, a bare
filename that resolves against the unit `WorkingDirectory=`
(`StateDirectory=`), so the region persists across restarts in the
per-VM state directory. QEMU creates the file on first boot and reopens
it afterwards. Maps to `-object memory-backend-file,mem-path=`.

`share`: whether guest writes are written through to the backing file.
Default: `true` (`share=on`, persistent). Set `false` for a volatile
region (`share=off`). Maps to `-object memory-backend-file,share=`.

`pmem`: real persistent-memory flush semantics for the backing file.
Default: off. Only takes effect with `share` on — with `share` off QEMU
maps the region `MAP_PRIVATE`, never requests `MAP_SYNC`, and silently
ignores `pmem` (no error, no warning), so the template emits `pmem=on`
only when `share` is also on. Maps to
`-object memory-backend-file,pmem=`. See:
`<qemu_binary> -object memory-backend-file,help`.

BlockConf (simple form only, inherited by implicit namespace):
`logical_block_size`, `physical_block_size`, `min_io_size`,
`opt_io_size`, `discard_granularity`, `write-cache`, `share-rw`.

Namespace properties (maps to `-device nvme-ns`): `nsid`, `uuid`,
`eui64`, `shared`, `detached`, `logical_block_size`,
`physical_block_size`, `min_io_size`, `opt_io_size`,
`discard_granularity`, `write-cache`, `share-rw`, `zoned`,
`zoned.zone_size`, `zoned.zone_capacity`, `zoned.max_active`,
`zoned.max_open`, `zoned.cross_read`, `zoned.descr_ext_size`,
`zoned.numzrwa`, `zoned.zrwas`, `zoned.zrwafg`, `ms`, `mset`, `pi`,
`pil`, `pif`, `mssrl`, `mcl`, `msrc`, `fdp.ruhs`, `atomic.nawun`,
`atomic.nawupf`, `atomic.nabsn`, `atomic.nabspf`, `atomic.nabo`,
`opts`.

See: `<qemu_binary> -device nvme,help`,
`<qemu_binary> -device nvme-ns,help`, man qemu-system.

**`nvme.subsystems`** — List of NVMe subsystems for multipath (shared
namespaces across controllers). Maps to `-device nvme-subsys`.

Subsystem properties: `nqn`, `fdp`, `fdp.nrg`, `fdp.nruh`,
`fdp.runs`.

Each subsystem contains `controllers` (list with per-controller
`serial`, `max_ioqpairs`, `msix_qsize`, etc.) and `namespaces` (list
with per-namespace properties, `shared: true` for multipath).

See: `<qemu_binary> -device nvme-subsys,help`.

## Service overrides

**`service`** — Dict of systemd `[Service]` section directives. Any
systemd.exec(5), systemd.resource-control(5), or systemd.kill(5)
directive. Use `systemctl --user set-property` for runtime changes
without re-rendering.

User scope (delegated: cpu, memory, pids): `CPUQuota=`,
`CPUWeight=`, `CPUQuotaPeriodSec=`, `MemoryMax=`, `MemoryHigh=`,
`MemoryMin=`, `MemorySwapMax=`, `TasksMax=`, `WorkingDirectory=`,
`LimitMEMLOCK=`, `LimitNOFILE=`, `Nice=`, `OOMScoreAdjust=`,
`TimeoutSec=`.

System scope only (not delegated to user services): `IOWeight=`,
`IODeviceWeight=`, `IOReadBandwidthMax=`, `IOWriteBandwidthMax=`,
`AllowedCPUs=`, `AllowedMemoryNodes=`, `DeviceAllow=`,
`DevicePolicy=`.

See: `man systemd.resource-control`, `man systemd.exec`,
`man systemd.kill`.

## Exec directories

systemd provides six directives that each address a specific lifecycle
for per-unit file storage. The template hardcodes four of them so every
VM gets a consistent filesystem layout out of the box. Pick the right
one when you need to extend the layout; don't reuse `WorkingDirectory=`
as a catch-all storage knob.

| Directive | Purpose | User root | System root | Lifetime | Auto-created | Cleaned on stop |
|---|---|---|---|---|---|---|
| `ConfigurationDirectory=` | read-only unit configuration (env files, helper scripts) | `$XDG_CONFIG_HOME` (`~/.config`) | `/etc` | forever | yes | no |
| `RuntimeDirectory=` | ephemeral runtime state (sockets, PID files, IPC) | `$XDG_RUNTIME_DIR` (`/run/user/<uid>`) | `/run` | unit runtime only | yes | **yes** (unless `RuntimeDirectoryPreserve=`) |
| `StateDirectory=` | persistent per-unit state that must survive restart | `$XDG_STATE_HOME` (`~/.local/state`) | `/var/lib` | forever | yes | no |
| `CacheDirectory=` | regeneratable data; safe to delete | `$XDG_CACHE_HOME` (`~/.cache`) | `/var/cache` | until purge | yes | no |
| `LogsDirectory=` | log files | `$XDG_STATE_HOME/log` | `/var/log` | forever | yes | no |
| `WorkingDirectory=` | CWD for the process | n/a (scalar path) | n/a (scalar path) | n/a | **no** — does not create | n/a |

The template sets four of these:

```
ConfigurationDirectory=systemd/qemu-system
RuntimeDirectory=qemu-system/%i
StateDirectory=qemu-system/%i
WorkingDirectory=%S/qemu-system/%i
```

`%S` resolves to the same root that `StateDirectory=` uses (systemd
`unit-printf.c:117-121` + `manager.c:717,725`). `WorkingDirectory=` on
its own does not create or own a directory — coupling it with
`StateDirectory=` is what gives you a predictable per-VM CWD that
auto-exists.

### Mapping file kinds to directives

**QEMU per-VM state (NVMe qcow2 images, seed ISOs, cloud-init data)** —
`StateDirectory=`. These must survive a service stop and restart; they
encode the guest's own filesystem state. Reference them by bare filename
in vars (`file: nvme0.qcow2`, `file: seed.iso`) and the relative path
resolves against `WorkingDirectory=%S/qemu-system/%i`.

**QEMU runtime sockets (qmp.sock, console.sock, gdb.sock)** —
`RuntimeDirectory=`. These are unix sockets the supervisor opens for
the VM's lifetime and that should disappear when the service stops.
The template already wires them with `%t/qemu-system/%i/...` which is
the `RuntimeDirectory` root.

**Unit configuration files (per-VM env file, QMP helper script)** —
`ConfigurationDirectory=`. The per-VM env file lives at
`%E/systemd/qemu-system/%i.env` and must be present before `ExecStart=`
runs. Consumers that render these — from a flake, a script, or by
hand — place them under `$XDG_CONFIG_HOME/systemd/qemu-system/` for
user services.

**Disk image caches (intermediate images, overlay images that can be
re-exported)** — `CacheDirectory=`. If the workflow can recreate the
image from a source tree or build artefact, cache-class storage is
correct: a machine-wide cache purge won't lose unique state.

**VM console and test logs that outlive the service** —
`LogsDirectory=`. Typically systemd already journals service stdout;
use `LogsDirectory=` only for artefacts you want persisted alongside
other `/var/log/` entries (e.g. timestamped test output captured by a
harness running inside the VM).

**Just changing CWD without any lifecycle management** —
`WorkingDirectory=` on its own. Rarely correct — if you care about the
directory existing, chown, or survival, you want one of the five above
pointing at it first.

### Overriding via the `service` dict

`WorkingDirectory=` is a scalar directive: setting
`service: { WorkingDirectory: /some/other/path }` in a vars file
produces an override drop-in that cleanly replaces the default. For
relative paths in vars to keep working you need the override target
to exist and be writable by the service user.

`StateDirectory=`, `RuntimeDirectory=`, `CacheDirectory=`,
`LogsDirectory=`, `ConfigurationDirectory=` are list-type directives
(`systemd.exec(5)` "whitespace-separated list of directory names").
A drop-in that sets a new value **appends** to the template default.
To replace, first reset with an empty assignment. Via the `service`
dict you cannot express the two-line reset+set with a single yaml
key; drop to writing a drop-in by hand for that case:

```
[Service]
StateDirectory=
StateDirectory=myconvention/%i
```

(Reset semantics are in systemd `load-fragment.c:4475-4478`:
`isempty(rvalue)` triggers `exec_directory_done(ed)`.)

### Specifiers used here

- `%i` — instance name, the part after `@` in the unit
  (`qemu-system@<vm>.service` → `<vm>`).
- `%E` — configuration directory root (`$XDG_CONFIG_HOME` or `/etc`).
- `%S` — state directory root (`$XDG_STATE_HOME` or `/var/lib`).
- `%t` — runtime directory root (`$XDG_RUNTIME_DIR` or `/run`).

`systemd.unit(5)` SPECIFIERS table has the full list.

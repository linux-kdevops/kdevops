# Driving nixos-flake and qsu by hand

This is the manual counterpart to the `make` targets. It walks the full
pipeline command-by-command so you can reproduce, debug, or operate a
guest without the Ansible roles. Everything here is what the roles run on
your behalf; nothing is hidden.

Two backends share the nixos-flake library:

- **NIXOSFL** (`nixosfl`) — a NixOS qcow2 built from a flake closure and
  run under **libvirtd**. The libvirt peer of `guestfs`.
- **NIXOSFI** (`nixosfi`) — the same declarative NixOS run **imageless**
  on **systemd-machined** via the **qsu** runtime (`qemu-system@<vm>`
  user services). No disk image; rootfs is the closure over virtiofs.

Conventions used below: one guest named `nixosfi-dev`, index `0`, so its
SSH port is `QSU_SSH_PORT_BASE + 0 = 10022` and its vsock CID is
`QSU_VSOCK_CID_BASE + 0 = 100`. `$CFG` is your `NIXOSFI_CONFIG_DIR` (or
`NIXOSFL_CONFIG_DIR`); `$TOP` is the kdevops tree.

Nix lives off-`PATH` for non-login shells; prefix it once:

```sh
export PATH=/nix/var/nix/profiles/default/bin:$PATH
```

Prerequisites: a flake-enabled Nix (`experimental-features = nix-command
flakes`); for NIXOSFI also `qemu-system`, `qemu-utils`, `socat`,
`virtiofsd`, `systemd-container` (`varlinkctl` lives in systemd), and
`minijinja-cli` (`cargo install minijinja-cli`), plus membership in the
`kvm` and `systemd-journal` groups. See
`scripts/qemu-system-units/docs/requirements.md` for the per-distro list.

---

## NIXOSFI: imageless + qsu, end to end

### 1. Build the kernel on the controller

NIXOSFI boots a controller-built kernel directly (`-kernel`), no guest
copy. `BOOTLINUX_DIRECT_BOOT` builds the tree out-of-tree into a destdir
on the controller. `$SRC` is the kernel checkout, `$BUILD` the
out-of-tree build dir (`O=`), `$DEST` the destdir staged for QEMU:

```sh
# Tree: clone it, or point $SRC at an existing checkout/worktree and skip this
git clone --branch <ref> <target_linux_git> $SRC

# Configure: stage the resolved .config, then resolve it against the tree
mkdir --parents $BUILD $DEST/boot
cp <resolved-.config> $BUILD/.config
make --directory=$SRC O=$BUILD olddefconfig
make --directory=$SRC O=$BUILD syncconfig

# The release string the rest of the pipeline keys off, e.g. 7.0.0-rc1+
make --silent --directory=$SRC O=$BUILD kernelrelease   # -> $REL

# Build with all cores
make --directory=$SRC O=$BUILD --jobs="$(nproc)"

# Install the image by hand. Avoid `make install`: it execs the distro
# /sbin/installkernel hook (initramfs + bootloader against the
# controller's own /boot, often needs root). `make image_name` prints
# the built image path relative to $SRC, e.g. arch/x86/boot/bzImage.
cp "$BUILD/$(make --silent --directory=$SRC O=$BUILD image_name)" $DEST/boot/vmlinuz-$REL

# Modules into the destdir; virtiofs serves $DEST/lib/modules to the guest
make --directory=$SRC O=$BUILD INSTALL_MOD_PATH=$DEST modules_install
# kernel image:  $DEST/boot/vmlinuz-$REL
# modules:       $DEST/lib/modules/$REL/
```

The above is what the `make linux-direct-boot` target open-codes
(`roles/bootlinux/tasks/build/direct-boot.yml`).

### 2. Render the per-guest flake

One flake directory per guest pins the vendored nixos-flake subtree and
selects the **imageless** backend (`packages.<system>.toplevel`):

```sh
mkdir --parents $CFG/nixosfi-dev
# $CFG/nixosfi-dev/flake.nix   inputs.nixos-flake.url = path:$TOP/scripts/nixos-flake
#                              modules = [ nixos-flake.nixosModules.backends.imageless ... ]
# $CFG/nixosfi-dev/default.nix  guest config + SSH authorized key
```

**What kdevops autogenerates and why.** nixos-flake ships *starter*
flakes —
[`scripts/nixos-flake/templates/imageless/{flake,default}.nix`](../scripts/nixos-flake/templates/imageless/flake.nix) —
meant to be copied with `nix flake init --template`. They are plain Nix,
not Jinja, and carry a placeholder input
`nixos-flake.url = "path:/path/to/nixos-flake"`. kdevops cannot use them
as-is: it has to rewrite that URL to the vendored subtree
(`path:$TOP/scripts/nixos-flake`) and inject per-guest values (the SSH
authorized key, the enabled `profiles.*`/`testSuites.*` modules, and one
`<pkg>-src` input per source override). So kdevops keeps Jinja mirrors of
the starters at `roles/nixosfi/templates/{flake,default}.nix.j2`, and the
Ansible `template` module renders one concrete `flake.nix` + `default.nix`
per guest. **When the subtree is updated, re-sync the `.j2` mirrors
against the upstream starters above** — they intentionally track them.

Pin the input so an edited subtree is actually picked up (a stale
`flake.lock` silently reuses the old closure):

```sh
nix flake update --flake path:$CFG/nixosfi-dev nixos-flake
```

### 3. Build the closure and read the bootspec

```sh
nix build path:$CFG/nixosfi-dev#toplevel --out-link $CFG/nixosfi-dev/result
cat $CFG/nixosfi-dev/result/boot.json        # org.nixos.bootspec.v1 -> .init, .initrd
```

`init` and `initrd` from `boot.json` are what the guest boots. The
imageless module builds no bootloader and sets no `boot.kernelParams`, so
QEMU must supply the command line explicitly: it needs both `root=tmpfs`
(systemd-fstab-generator turns this into the tmpfs `/sysroot` it
switch-roots into) and `init=<path>` from the bootspec. Omitting
`root=tmpfs` leaves the guest with no root to switch to.

### 4. Render the qsu unit + env files

qsu is a set of Jinja templates under
`$TOP/scripts/qemu-system-units/templates/` — there is no daemon and no
wrapper. kdevops renders them with the Ansible `template` module (roles
`qsu/tasks/render-units.yml` and `render-per-vm.yml`). **Outside Ansible,
qsu's own tooling is `minijinja-cli --trim-blocks`** with a per-VM YAML
vars file; install it once with `cargo install minijinja-cli`. kdevops
does *not* use minijinja-cli — it feeds the same `.j2` files the Kconfig
values resolved into `extra_vars`. Both produce byte-identical output.

There are eight rendered artefacts. Four are host-wide (render once); four
are per-guest (render once per VM). `nvme.env.j2` is a macro library
imported by `vm.env.j2`, not a standalone file, so keep it alongside when
rendering.

Host-wide, deploy once:

```sh
install --directory ~/.config/systemd/user ~/.config/systemd/qemu-system
cd $TOP/scripts/qemu-system-units
minijinja-cli --trim-blocks --output ~/.config/systemd/user/qemu-system@.service \
  templates/qemu-system@.service.j2 vars/nixosfi-dev.yaml
minijinja-cli --trim-blocks --output ~/.config/systemd/user/virtiofsd@.service \
  templates/virtiofsd@.service.j2 vars/nixosfi-dev.yaml
minijinja-cli --trim-blocks --output ~/.config/systemd/user/virtiofsd@.socket \
  templates/virtiofsd@.socket.j2 vars/nixosfi-dev.yaml
cp files/qmp-powerdown ~/.config/systemd/qemu-system/      # static, not rendered
```

Per-guest, one set per VM. `vm.env` is where every knob lands — the QEMU
argv, the controller kernel/init/initrd, NVMe drives, virtiofs shares, the
SSH hostfwd and the vsock CID:

```sh
# 1. QEMU environment file
minijinja-cli --trim-blocks --output ~/.config/systemd/qemu-system/nixosfi-dev.env \
  templates/vm.env.j2 vars/nixosfi-dev.yaml
# 2. Per-instance service drop-in (vsock CID, Requires= the virtiofsd sockets)
install --directory ~/.config/systemd/user/qemu-system@nixosfi-dev.service.d
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/qemu-system@nixosfi-dev.service.d/override.conf \
  templates/qemu-system-override.conf.j2 vars/nixosfi-dev.yaml
# 3. Per-(vm,share) virtiofsd env — one per non-home share (store, modules, ...)
install --directory ~/.config/systemd/virtiofsd
minijinja-cli --trim-blocks --define share_tag=store \
  --output ~/.config/systemd/virtiofsd/nixosfi-dev-store.env \
  templates/virtiofsd.env.j2 vars/nixosfi-dev.yaml       # VIRTIOFSD_SHARED_DIR=/nix/store
minijinja-cli --trim-blocks --define share_tag=modules \
  --output ~/.config/systemd/virtiofsd/nixosfi-dev-modules.env \
  templates/virtiofsd.env.j2 vars/nixosfi-dev.yaml       # VIRTIOFSD_SHARED_DIR=<destdir>/lib/modules
# 4. Per-(vm,share) virtiofsd stop-ordering drop-in — one per share
install --directory ~/.config/systemd/user/virtiofsd@nixosfi-dev-store.service.d
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/virtiofsd@nixosfi-dev-store.service.d/override.conf \
  templates/virtiofsd-override.conf.j2 vars/nixosfi-dev.yaml
# (repeat the drop-in for -modules and any further shares)
```

The rendered `vm.env` reads, abbreviated:

```sh
QEMU_BINARY=qemu-system-x86_64
QEMU_ARGS="-machine type=q35 -accel kvm -cpu host -m 4096 -smp 4 \
  -nic user,model=virtio-net-pci-non-transitional,hostfwd=tcp:127.0.0.1:10022-:22 \
  -device vhost-vsock-pci-non-transitional,guest-cid=100 \
  -fsdev ... mount_tag=store ...        # /nix/store over virtiofs
  -device nvme,serial=kdevops0 ...      # one per QSU_NVME drive
  -nographic -serial mon:stdio"
KERNEL_ARGS=-kernel <destdir>/boot/vmlinuz-<rel> \
  -append "root=tmpfs console=ttyS0,115200 console=hvc0 init=<init-from-bootspec>" \
  -initrd <initrd-from-bootspec>
```

Finally create the NVMe backing files the `vm.env` drives reference
(relative to the service `WorkingDirectory`, `%S/qemu-system/<vm>`):

```sh
install --directory ~/.local/state/qemu-system/nixosfi-dev
qemu-img create --format qcow2 ~/.local/state/qemu-system/nixosfi-dev/nvme0.qcow2 20G  # x QSU_NVME_DRIVE_COUNT
```

### 5. Start the guest

`virtiofsd@*.socket` units are socket-activated; QEMU's first connect
spawns the matching `virtiofsd@*.service`. The `qemu-system@.service`
`ExecStartPost` registers the guest with machined over Varlink, so it
shows up in `machinectl`:

```sh
systemctl --user daemon-reload
systemctl --user restart virtiofsd@nixosfi-dev-store.socket virtiofsd@nixosfi-dev-modules.socket
systemctl --user start qemu-system@nixosfi-dev.service
machinectl --user list                           # nixosfi-dev, class=vm
ssh -p 10022 root@127.0.0.1                      # or: ssh nixosfi-dev (if ~/.ssh/config updated)
```

### 6. Operate it (qsu cheat sheet)

```sh
systemctl --user status  qemu-system@nixosfi-dev.service
journalctl --user-unit=qemu-system@nixosfi-dev.service --follow   # serial console in the journal
machinectl --user status nixosfi-dev
systemctl --user stop    qemu-system@nixosfi-dev.service    # graceful: QMP system_powerdown via ExecStop
systemctl --user restart qemu-system@nixosfi-dev.service
```

The qsu services run in user scope and register with the **user**
machine manager (needs systemd v259+), so `machinectl` needs `--user`
(like `systemctl --user`) to list or inspect them; without it
`machinectl` talks to the system manager and shows nothing.
`machinectl --user terminate <vm>` is the non-graceful kill. Likewise
`--user-unit=` (not `--user -u`): user-service stdout lands in the
**system** journal via `user@UID.service`.

### 7. Fast kernel iteration

After rebuilding the kernel, re-pin, rebuild the closure against it,
re-render the env, and restart — the live-run results symlink follows the
new release automatically:

```sh
make linux-direct-boot
nix flake update --flake path:$CFG/nixosfi-dev nixos-flake
nix build path:$CFG/nixosfi-dev#toplevel --out-link $CFG/nixosfi-dev/result
# re-render nixosfi-dev.env with the new kernel/init/initrd, then:
systemctl --user restart qemu-system@nixosfi-dev.service
```

The `make` wrapper for all of step 7 is `make nixosfi-rebuild-boot`.

### 8. Tear down

```sh
systemctl --user stop qemu-system@nixosfi-dev.service
rm --recursive --force ~/.local/state/qemu-system/nixosfi-dev   # NVMe qcow2 + ephemeral config
rm --force ~/.config/systemd/qemu-system/nixosfi-dev.env
```

---

## NIXOSFL: imageless's libvirt peer

Same flake library, **libvirt** backend (`backends.libvirt`), output is a
qcow2 (`packages.<system>.image`) run under libvirtd. No kernel build, no
qsu — the guest is self-contained.

```sh
# 1. Render the per-guest flake (libvirt variant) into $CFG/nixosfl-dev/
#    from roles/nixosfl/templates/{flake,default}.nix.j2

# 2. Build the disk image
nix build path:$CFG/nixosfl-dev#image --out-link $CFG/nixosfl-dev/result

# 3. Stage it into the libvirt storage pool
cp $CFG/nixosfl-dev/result/nixos.qcow2 $NIXOSFL_STORAGE_DIR/nixosfl-dev.qcow2

# 4. Define and start the domain (libvirt XML from vm-libvirt.xml.j2)
export LIBVIRT_DEFAULT_URI=qemu:///system
virsh define $NIXOSFL_STORAGE_DIR/nixosfl-dev.xml
virsh start  nixosfl-dev

# 5. Connect
virsh domifaddr nixosfl-dev      # find the DHCP address
ssh nixosfl-dev                  # once ~/.ssh/config is updated
virsh console nixosfl-dev        # serial console
```

`make nixosfl-bringup` / `nixosfl-console` / `nixosfl-destroy` wrap these.

---

## Source overrides (both backends)

Rebuild a tracked package (fio, xfstests, xfsprogs, libbpf, libbpf-tools,
damo, nfstest, pynfs, xnvme, cpupower) from your own tree. Set
`NIXOS_FLAKE_OVERRIDE_<PKG>=y` plus `_SRC` (local path or git URL) and
optional `_REF`; kdevops adds a `<pkg>-src` flake input that a
`default.nix` overlay `overrideAttrs` consumes. After changing a
`_SRC`/`_REF`, refresh the pinned input and rebuild:

```sh
nix flake update --flake path:$CFG/<vm> <pkg>-src
nix build path:$CFG/<vm>#toplevel --out-link $CFG/<vm>/result   # or #image for nixosfl
```

---

## Where the knobs live

`Kconfig.qsu` (`QSU_*`) — runtime sizing NIXOSFI reuses: `QSU_RAM` (4096),
`QSU_CPUS` (4), `QSU_MACHINE_TYPE` (q35), `QSU_SSH_PORT_BASE` (10022),
`QSU_VSOCK_CID_BASE` (100), `QSU_NVME_DRIVE_COUNT` (4) /
`_SIZE_GB` (20) plus the NVMe block-geometry and atomic-write fields.

`Kconfig.nixos_flake` (`NIXOS_FLAKE_*`) — shared library: profiles,
mounts, testSuites, source overrides; baked into the closure.

`NIXOSFI_CONFIG_DIR` / `NIXOSFL_CONFIG_DIR` — where per-guest flakes
render. `NIXOSFL_STORAGE_DIR` — the libvirt qcow2 pool.

For the upstream tools themselves, see `man qemu-system`,
`man systemd.service`, `man machinectl`, and the vendored projects under
`scripts/qemu-system-units/` and `scripts/nixos-flake/`.

# kdevops QEMU_SYSTEM_UNITS bringup backend

Integration notes for the `QEMU_SYSTEM_UNITS` bringup method.
Everything that belongs to qsu itself (unit templates, vars, QMP
graceful shutdown, machined registration over Varlink, service
properties) lives in `scripts/qemu-system-units/docs/`. This
document covers only what kdevops adds around it.

## Enabling the backend

```
make defconfig-qemu-system-units
make
make linux
make bringup
```

`QEMU_SYSTEM_UNITS` selects `KDEVOPS_ENABLE_NIXOS` (the guest is
NixOS) and `BOOTLINUX_CONTROLLER` (the kernel is built on the
control node and served to the guest over virtiofs).

## kdevops-side Kconfig

Knobs under `kconfigs/Kconfig.qemu_system_units`, all gated by
`if QEMU_SYSTEM_UNITS`:

- `QEMU_SYSTEM_UNITS_QEMU_BINARY`, `QEMU_SYSTEM_UNITS_CPU`,
  `QEMU_SYSTEM_UNITS_ACCEL`, `QEMU_SYSTEM_UNITS_MACHINE_TYPE`,
  `QEMU_SYSTEM_UNITS_RAM`, `QEMU_SYSTEM_UNITS_CPUS` — scalar
  values the role passes through to qsu's vars. Semantics match
  `scripts/qemu-system-units/docs/vars.md` one-to-one.
- `QEMU_SYSTEM_UNITS_SSH_PORT_BASE` — host TCP port forwarded
  to guest port 22; each guest gets `ssh_port_base + index`.
- `QEMU_SYSTEM_UNITS_VSOCK_CID_BASE` — AF_VSOCK CID; each guest
  gets `vsock_cid_base + index`. Valid range 3..4294967295.
- `QEMU_SYSTEM_UNITS_SSH_DEFAULT` — `VSOCK` (default) or `TCP`;
  selects which transport the bare `Host <vm>` ssh_config alias
  uses.

## Guest kernel (config-qsu)

Controller mode builds from `config-qsu`
(`playbooks/roles/bootlinux/templates/config-qsu`) and installs
to `$KDEVOPS_CONTROLLER_DATA_PATH/linux-destdir/boot`. The guest
boots `-kernel <that image>` with `-initrd <NixOS initramfs>`.

Drivers built in (`=y`) rather than modules so they bind at PCI
enumeration before userspace starts, because `/lib/modules` is
only available after the virtiofs mount:

- `CONFIG_VIRTIO`, `CONFIG_VIRTIO_PCI`, `CONFIG_VIRTIO_FS`,
  `CONFIG_FUSE_FS`, `CONFIG_TMPFS` — tmpfs root and virtiofs
  mounts for `/nix/store` and `/lib/modules`.
- `CONFIG_VIRTIO_NET`, `CONFIG_VIRTIO_CONSOLE` — networking and
  `hvc0` console before `/lib/modules` is up.
- `CONFIG_PACKET` — `AF_PACKET` raw sockets systemd-networkd's
  DHCP and LLDP clients bind.
- `CONFIG_VSOCKETS`, `CONFIG_VIRTIO_VSOCKETS`,
  `CONFIG_VIRTIO_VSOCKETS_COMMON` — AF_VSOCK transport;
  `systemd-ssh-generator` in the guest emits
  `sshd-vsock.socket` on port 22 when these are built in.

## SSH aliases

`scripts/update_ssh_config_nixos.py` writes three aliases per VM
into `~/.ssh/config`:

```
Host <vm> <vm>-vsock
    ProxyCommand /usr/lib/systemd/systemd-ssh-proxy vsock/<cid> 22
    ...

Host <vm>-tcp
    HostName 127.0.0.1
    Port <host_tcp_port>
    ...
```

The bare `<vm>` groups with whichever transport
`QEMU_SYSTEM_UNITS_SSH_DEFAULT` points at. The `-vsock` and
`-tcp` aliases are always available, so you can pick either
transport explicitly. Switching the default does not require a
rebuild — re-run `make` and the script rewrites the block.

`ssh root@machine/<vm>` would resolve the CID through
`systemd-ssh-proxy` querying machined, but the packaged
`systemd-ssh-proxy` on Debian 13 (systemd v260.1) segfaults in
the `machine/` handler after the Varlink query. The direct
`ProxyCommand vsock/<cid> 22` path sidesteps that bug. Drop the
hardcoded CID from the alias template once the packaged proxy
fix lands.

## Verifying

```
machinectl --user show <vm> | grep VSockCID   # registered CID
ssh <vm>-tcp -- uname -a                       # SLIRP hostfwd
ssh <vm>-vsock -- uname -a                     # AF_VSOCK
ssh <vm> -- uname -a                           # Kconfig default
```

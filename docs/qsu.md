# qsu runtime (qemu-system-units)

The `NIXOSFI` backend runs each guest through **qsu**, the vendored
qemu-system-units project (`scripts/qemu-system-units/`): every guest is a
`qemu-system@<vm>` systemd **user** service registered with
systemd-machined, so it appears as a machine and is managed like one. This
is the systemd-vmspawn model — `machinectl` is to qsu what `virsh` is to
libvirt.

## Inspect running guests

```
machinectl list                              # registered machines
systemctl --user status qemu-system@<vm>
systemctl --user list-units 'qemu-system@*' 'virtiofsd@*'
```

## Lifecycle (via kdevops)

```
make nixosfi-console VM=<vm>     # serial console
make nixosfi-status              # inventory + running state
make nixosfi-stop / nixosfi-start / nixosfi-restart
```

## Shipped configuration

kdevops writes, per guest, under `~/.config/systemd/`:
`qemu-system/<vm>.env` (the QEMU command line), the
`qemu-system@<vm>.service.d/` and `virtiofsd@<vm>-<tag>.service.d/`
drop-ins, and a debug snapshot at `$QSU_VARS_DIR/<vm>.yaml`. Reading those
shows exactly what each machine boots with. The `QSU_*` Kconfig knobs (cpu,
ram, cpus, machine type, ssh/vsock, NVMe geometry) configure this runtime.

For the qsu project itself — the systemd unit templates and the standalone
(non-Ansible) workflow — see the upstream docs under
`scripts/qemu-system-units/`.

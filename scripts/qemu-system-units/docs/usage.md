# Usage

All templates render with `minijinja-cli --trim-blocks` and one
vars file. Output goes to stdout by default; use `--output <path>`
to write directly to the deploy location.

`vars/example.yaml` is the starting point and ships with the repo.
Copy it to create per-VM configurations. The filename should match
`vm_name` inside the file (e.g. `vars/test.yaml` for `vm_name: test`,
`vars/dev.yaml` for `vm_name: dev`). User vars files are gitignored.

The examples below use `vars/test.yaml` (a copy of `vars/example.yaml`
which has `vm_name: test`). User scope deploys to `~/.config/systemd/`.

## qemu-system

Service template, per-instance drop-in, `EnvironmentFile=`, and QMP
powerdown commands.

```shell
# Service template (deploy once)
mkdir --mode=0755 --parents ~/.config/systemd/user
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/qemu-system@.service \
  templates/qemu-system@.service.j2 \
  vars/test.yaml

# Per-instance drop-in (one per VM)
mkdir --mode=0755 --parents ~/.config/systemd/user/qemu-system@test.service.d
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/qemu-system@test.service.d/override.conf \
  templates/qemu-system-override.conf.j2 \
  vars/test.yaml

# QEMU environment file (one per VM)
mkdir --mode=0755 --parents ~/.config/systemd/qemu-system
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/qemu-system/test.env \
  templates/vm.env.j2 \
  vars/test.yaml

# QMP powerdown commands (static file, deploy once)
cp files/qmp-powerdown ~/.config/systemd/qemu-system/qmp-powerdown
```

## virtiofsd

Socket unit, socket-activated service, and per-share `EnvironmentFile=`
for host-guest directory sharing.

```shell
# Socket and service templates (deploy once)
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/virtiofsd@.socket \
  templates/virtiofsd@.socket.j2 \
  vars/test.yaml

minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/virtiofsd@.service \
  templates/virtiofsd@.service.j2 \
  vars/test.yaml

# Per-share environment (one per non-home share)
mkdir --mode=0755 --parents ~/.config/systemd/virtiofsd
minijinja-cli --trim-blocks \
  --define share_tag=modules \
  --output ~/.config/systemd/virtiofsd/test-modules.env \
  templates/virtiofsd.env.j2 \
  vars/test.yaml
```

## vfio

`Type=oneshot` service for device binding and udev rules for unprivileged
access. One-time sudo required for module config, udev rules, and
rule reload. After setup, all VFIO operations run in user mode.

```shell
# Bind service (deploy once)
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/vfio-bind@.service \
  templates/vfio-bind@.service.j2 \
  vars/test.yaml

# One-time root setup
sudo cp files/vfio-pci.conf /etc/modules-load.d/vfio-pci.conf
sudo modprobe vfio-pci

minijinja-cli --trim-blocks \
  templates/vfio-udev.rules.j2 \
  vars/test.yaml \
  | sudo tee /etc/udev/rules.d/10-vfio-kvm.rules

sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=pci
```

## cloud-init

user-data, meta-data, and network-config rendered into a seed ISO for
first-boot provisioning. Only needed for cloud image boot.

The network-config is required when using direct kernel boot with
generic cloud images (cloud-init's fallback network detection is
unreliable without the distro initramfs). It is optional for cloud
image boot with the distro kernel. See
[design-decisions.md](design-decisions.md) for details.

```shell
minijinja-cli --trim-blocks \
  --output /tmp/user-data \
  templates/user-data.j2 \
  vars/test.yaml

minijinja-cli --trim-blocks \
  --output /tmp/meta-data \
  templates/meta-data.j2 \
  vars/test.yaml

cloud-localds --network-config=files/network-config \
  images/seed.iso /tmp/user-data /tmp/meta-data
```

## Start

```shell
systemctl --user daemon-reload
systemctl --user start qemu-system@test
systemctl --user status qemu-system@test
```

## machinectl

VMs registered with systemd-machined appear alongside containers
in `machinectl`. Registration happens automatically via
`ExecStartPost=busctl RegisterMachine` in the service template.
User scope requires `--user` (systemd v259+).

```shell
# List all registered machines
machinectl --user list

# Machine details (PID, cgroup, service)
machinectl --user status test

# Machine properties (parseable output)
machinectl --user show test

# Emergency kill (not graceful, kills QEMU immediately)
machinectl --user terminate test
```

`machinectl login`, `shell`, `poweroff`, `bind`, and `copy-to/from`
are container-only. See: `man machinectl`, `man systemd-machined`.

## Console

Every persistent VM has a virtio console on a unix socket for
interactive access. The serial console (ttyS0) continues to capture
output in the systemd journal.

```shell
socat -,raw,echo=0,escape=0x1d \
    UNIX-CONNECT:$XDG_RUNTIME_DIR/qemu-system/test/console.sock
```

Press Enter to get the login prompt. Disconnect with `Ctrl-]`.
The VM keeps running. Reconnect at any time.

The guest needs `console=hvc0` on the kernel command line and a
getty on hvc0. The guest kernel needs `CONFIG_VIRTIO_CONSOLE=y`
or `=m`.

For initramfs debugging (before hvc0 is available), use the
transient-run template:

```shell
minijinja-cli --trim-blocks \
    --output /tmp/run-test.sh \
    templates/transient-run.sh.j2 vars/test.yaml
bash /tmp/run-test.sh
```

See [transient-units.md](transient-units.md) for details and
limitations.

## Logs

```shell
# VM service log
journalctl --user-unit=qemu-system@test.service

# virtiofsd log (per share)
journalctl --user-unit=virtiofsd@test-home.service

# Follow live output
journalctl --user-unit=qemu-system@test.service --follow

# All VM-related units since last boot
journalctl --user-unit='qemu-system@*' --user-unit='virtiofsd@*' --boot
```

## Stop

Graceful shutdown via `ExecStop=`: QMP `system_powerdown` triggers
ACPI shutdown inside the guest. When `ssh_private_key` and
`vsock_cid` are configured, SSH shutdown is attempted first with
QMP as fallback. If the guest does not shut down within
`TimeoutSec=` (default 2min), systemd sends `SIGKILL`.

```shell
# Graceful stop (ExecStop QMP powerdown, then SIGKILL after timeout)
systemctl --user stop qemu-system@test

# Force kill (immediate SIGKILL, no graceful shutdown)
systemctl --user kill qemu-system@test --signal=SIGKILL

# Stop all VMs (PartOf=machines.target)
systemctl --user stop machines.target

# Reset failed state after a crash or forced kill
systemctl --user reset-failed qemu-system@test
```

## Multiple VMs

The `qemu-system@.service` template supports multiple instances.
Each VM gets its own vars file, env file, and drop-in. The service
template and virtiofsd units are shared.

`vm_name`, `ssh_port`, and `vsock_cid` must be unique per VM.

```shell
cp vars/example.yaml vars/dev.yaml
```

Edit `vars/dev.yaml`. E.g. set `vm_name: dev`, `ssh_port: 10023`,
`vsock_cid: 101`.

```shell
# Render test VM
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/qemu-system/test.env \
  templates/vm.env.j2 vars/test.yaml
mkdir --mode=0755 --parents ~/.config/systemd/user/qemu-system@test.service.d
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/qemu-system@test.service.d/override.conf \
  templates/qemu-system-override.conf.j2 vars/test.yaml

# Render dev VM
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/qemu-system/dev.env \
  templates/vm.env.j2 vars/dev.yaml
mkdir --mode=0755 --parents ~/.config/systemd/user/qemu-system@dev.service.d
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/qemu-system@dev.service.d/override.conf \
  templates/qemu-system-override.conf.j2 vars/dev.yaml

systemctl --user daemon-reload
systemctl --user start qemu-system@test qemu-system@dev
machinectl --user list
```

A/B kernel testing: two vars files with different `kernel.image`
paths. Both VMs share the same service template. Only the env files
differ.

## Cleanup

### Remove a single VM

Stop the VM and remove its per-instance files. Shared templates
and virtiofsd units stay for other VMs.

```shell
systemctl --user stop qemu-system@test
rm ~/.config/systemd/qemu-system/test.env
rm --recursive --force ~/.config/systemd/user/qemu-system@test.service.d
rm --recursive --force ~/.config/systemd/virtiofsd/test-*.env
systemctl --user daemon-reload
```

### Remove everything

Stop all VMs, remove all deployed units and configuration.

```shell
systemctl --user stop machines.target
systemctl --user stop 'virtiofsd@*.socket'
rm --recursive --force \
  ~/.config/systemd/user/qemu-system@.service \
  ~/.config/systemd/user/qemu-system@*.service.d \
  ~/.config/systemd/user/virtiofsd@.socket \
  ~/.config/systemd/user/virtiofsd@.service \
  ~/.config/systemd/user/vfio-bind@.service \
  ~/.config/systemd/qemu-system \
  ~/.config/systemd/virtiofsd
systemctl --user daemon-reload
```

### Upgrading templates

After re-deploying `virtiofsd@.service` with changed sandbox
settings, restart running virtiofsd sockets. `daemon-reload`
reloads unit definitions but does not restart running sockets.
Stale sockets may pass FDs in a state incompatible with the new
service configuration.

```shell
systemctl --user daemon-reload
systemctl --user restart 'virtiofsd@*.socket'
```

## Deploy all

Set `VARS` to your vars file. `VM` is derived from `vm_name`
inside it.

```shell
VARS=vars/test.yaml
VM=$(minijinja-cli --template '{{ vm_name }}' '' $VARS)

# Shared templates (deploy once)
mkdir --mode=0755 --parents ~/.config/systemd/user ~/.config/systemd/qemu-system ~/.config/systemd/virtiofsd
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/qemu-system@.service \
  templates/qemu-system@.service.j2 $VARS
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/virtiofsd@.socket \
  templates/virtiofsd@.socket.j2 $VARS
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/virtiofsd@.service \
  templates/virtiofsd@.service.j2 $VARS
cp files/qmp-powerdown ~/.config/systemd/qemu-system/qmp-powerdown

# Per-VM files
mkdir --mode=0755 --parents ~/.config/systemd/user/qemu-system@${VM}.service.d
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/qemu-system/${VM}.env \
  templates/vm.env.j2 $VARS
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/qemu-system@${VM}.service.d/override.conf \
  templates/qemu-system-override.conf.j2 $VARS

# Per-share virtiofsd env (only for shares with dir: set)
# Repeat for each non-home share tag:
# minijinja-cli --trim-blocks \
#   --define share_tag=modules \
#   --output ~/.config/systemd/virtiofsd/${VM}-modules.env \
#   templates/virtiofsd.env.j2 $VARS

systemctl --user daemon-reload
systemctl --user start qemu-system@${VM}
```

For multiple VMs, run the per-VM block for each vars file:

```shell
for VARS in vars/test.yaml vars/dev.yaml; do
  VM=$(minijinja-cli --template '{{ vm_name }}' '' $VARS)
  minijinja-cli --trim-blocks \
    --output ~/.config/systemd/qemu-system/${VM}.env \
    templates/vm.env.j2 $VARS
  mkdir --mode=0755 --parents ~/.config/systemd/user/qemu-system@${VM}.service.d
  minijinja-cli --trim-blocks \
    --output ~/.config/systemd/user/qemu-system@${VM}.service.d/override.conf \
    templates/qemu-system-override.conf.j2 $VARS
  # Per-share virtiofsd env (only for shares with dir: set)
  # minijinja-cli --trim-blocks --define share_tag=modules \
  #   --output ~/.config/systemd/virtiofsd/${VM}-modules.env \
  #   templates/virtiofsd.env.j2 $VARS
done
systemctl --user daemon-reload
for VARS in vars/test.yaml vars/dev.yaml; do
  VM=$(minijinja-cli --template '{{ vm_name }}' '' $VARS)
  systemctl --user start qemu-system@${VM}
done
```

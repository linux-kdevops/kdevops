# qemu-system-units

Systemd unit templates for running QEMU virtual machines as first-class
systemd services.

**License**: copyleft-next-0.3.1

## Features

- **Machine types**: q35, microvm (auto MMIO), ARM virt
- **Boot modes**: cloud image, mkosi, direct kernel, imageless (virtiofs rootfs)
- **File sharing**: virtiofs (socket-activated), 9P fallback
- **Networking**: user-mode with port forwarding, VSOCK
- **Devices**: NVMe emulation (ZNS, multipath, FDP), PCIe passthrough (VFIO)
- **IOMMU**: Intel VT-d, AMD-Vi, virtio-iommu, ARM SMMUv3
- **Debugging**: GDB via unix socket, paused start
- **Lifecycle**: machined registration, QMP graceful shutdown, resource control

## Quick start

```shell
sudo apt install qemu-system-x86 qemu-utils socat \
  systemd-container virtiofsd cloud-image-utils cargo
cargo install minijinja-cli
sudo usermod --append --groups kvm $(whoami)
```

Log out and back in for group changes to take effect.
See [docs/requirements.md](docs/requirements.md) for Fedora, openSUSE, and NixOS.

```shell
cp vars/example.yaml vars/test.yaml

mkdir --mode=0755 --parents ~/.config/systemd/user ~/.config/systemd/qemu-system ~/.config/systemd/virtiofsd
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/qemu-system@.service \
  templates/qemu-system@.service.j2 vars/test.yaml
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/virtiofsd@.socket \
  templates/virtiofsd@.socket.j2 vars/test.yaml
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/virtiofsd@.service \
  templates/virtiofsd@.service.j2 vars/test.yaml
mkdir --mode=0755 --parents ~/.config/systemd/user/qemu-system@test.service.d
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/user/qemu-system@test.service.d/override.conf \
  templates/qemu-system-override.conf.j2 vars/test.yaml
minijinja-cli --trim-blocks \
  --output ~/.config/systemd/qemu-system/test.env \
  templates/vm.env.j2 vars/test.yaml
cp files/qmp-powerdown ~/.config/systemd/qemu-system/qmp-powerdown

systemctl --user daemon-reload
systemctl --user start qemu-system@test
machinectl --user list
```

## Documentation

| Document | Content |
|---|---|
| [docs/requirements.md](docs/requirements.md) | Packages for Debian, Fedora, openSUSE, NixOS |
| [docs/usage.md](docs/usage.md) | Rendering, deployment, machinectl, console, logs, stop, multiple VMs |
| [docs/vars.md](docs/vars.md) | Variable reference for all template fields |
| [docs/design-decisions.md](docs/design-decisions.md) | Hardcoded choices and upstream references |
| [docs/transient-units.md](docs/transient-units.md) | `systemd-run` and transient unit patterns |
| [vars/example.yaml](vars/example.yaml) | Starting point for VM configuration |

## Related work

Community systemd service files for QEMU VMs:

- [rafaelmartins/kvm-systemd](https://github.com/rafaelmartins/kvm-systemd). `kvm@.service`, `Type=forking`, per-VM conf in `/etc/kvm/`
- [eaon/qemu-kvm-systemd-service](https://codeberg.org/eaon/qemu-kvm-systemd-service). `qemu@.service`, per-VM conf in `/etc/qemu/vms/`
- [dehesselle/virtctl](https://github.com/dehesselle/virtctl). `virtctl@.service`, `hypervisor.target` pattern
- [0xef53/kvmrun](https://github.com/0xef53/kvmrun). Go, systemd-native, per-VM chroot, gRPC API

QEMU upstream ships helper units (guest-agent, pr-helper, vmsr-helper) in
[contrib/systemd/](https://gitlab.com/qemu-project/qemu/-/tree/master/contrib/systemd)
but no VM lifecycle service. virtiofsd ships no systemd units. Neither
Debian nor Fedora package a `qemu-system@.service` template.

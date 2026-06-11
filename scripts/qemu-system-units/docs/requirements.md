# Requirements

## Debian

```shell
sudo apt install qemu-system-x86 qemu-utils socat \
  systemd-container virtiofsd cloud-image-utils ovmf cargo
cargo install minijinja-cli
```

## Fedora

```shell
sudo dnf install qemu-system-x86-core qemu-img socat \
  systemd-container virtiofsd cloud-utils-cloud-localds \
  edk2-ovmf cargo
cargo install minijinja-cli
```

## openSUSE

```shell
sudo zypper install qemu-x86 qemu-img socat \
  systemd-container virtiofsd qemu-ovmf-x86_64 cargo
cargo install minijinja-cli
```

`cloud-localds` is not packaged on openSUSE. Use `genisoimage`
directly to create seed ISOs for cloud-init boot.

## NixOS

```nix
environment.systemPackages = with pkgs; [
  qemu socat virtiofsd minijinja cloud-utils OVMF
];
```

## Groups

```shell
sudo usermod --append --groups kvm,systemd-journal $(whoami)
```

`kvm` is required for `-accel kvm` (`/dev/kvm` access).
`systemd-journal` allows reading the journal without sudo.
Log out and back in for group changes to take effect.

## Verify

```shell
qemu-system-x86_64 --version
minijinja-cli --version
id --name --groups | grep kvm
ls -l --all /dev/kvm
```

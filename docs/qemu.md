# qemu

The qemu component builds and installs QEMU from source on the controller
(localhost). It is meant for cases where the distribution package of QEMU lacks
a feature you need, for example a custom QEMU git tree you are developing
against.

The build inputs are set through `kconfigs/Kconfig.qemu` and reach the qemu
role through `output yaml`. The role fetches the git tree, configures it for the
target architecture out of tree, builds it, and installs it under a prefix the
invoking user owns.

## Enabling the build (`QEMU`)

Enable `CONFIG_QEMU` to have kdevops build QEMU for you. When disabled, kdevops
uses the QEMU already present on the system.

## Git tree (`QEMU_GIT`)

Select which QEMU git URL to fetch:

- upstream `https://gitlab.com/qemu-project/qemu.git`
- Cameron's tree `https://gitlab.com/jic23/qemu.git`, which carries CXL changes
  not yet upstream
- a custom URL

When a local Linux mirror is configured, the matching `/mirror/*.git` path is
used instead of the remote URL.

## Fetch destination (`QEMU_GIT_DATA_PATH`)

The directory the git tree is fetched into. Default:
`{{ kdevops_controller_data_path }}/qemu`, alongside the out-of-tree build
directory `qemu-build/` and the install destdir `qemu-destdir/`.

## Version (`QEMU_GIT_VERSION`)

The git ref (tag or branch) to check out and build. For the upstream tree this
defaults to the latest stable release, inferred from the `/mirror/qemu.git`
mirror by `scripts/infer_last_stable_qemu.sh`; when no mirror is present it
falls back to a recent release. Override it to pin a specific tag, and use at
least v7.2.0 for CXL support.

## Build target (`QEMU_TARGET`)

The QEMU `--target-list` value, derived from the target architecture:
`x86_64-softmmu`, `aarch64-softmmu`, or `ppc64-softmmu`.

## Install prefix (`QEMU_INSTALL_DIR`, `QEMU_INSTALL_NEEDS_SUDO`)

The `--prefix` passed to QEMU's configure. Every backend except libvirt installs
into `qemu-destdir/` under the controller data path, which the invoking user
owns, so the install needs no root and the binary stays out of confined system
locations.

The libvirt backend is the exception. Its QEMU runs under libvirtd's AppArmor
and SELinux confinement, which only permits binaries under `/usr/local`, so
libvirt installs there and the install needs sudo. `QEMU_INSTALL_NEEDS_SUDO`
tracks whether the install needs root.

## Binary path (`QEMU_BIN_PATH`)

The absolute path to the installed `qemu-system-*` binary, derived from
`QEMU_INSTALL_DIR` so the configure prefix and the consumed path share one
source of truth. gen-nodes uses it for the libvirt domain emulator and qsu uses
it for the systemd unit `ExecStart`.

## Make targets

QEMU builds only when you run its targets, never during `make` or
`make bringup`. The build targets form a chain; each pulls in the ones
before it, and `make qemu` runs the whole chain:

- `make qemu-controller-setup` — install the build and runtime dependencies (may sudo)
- `make qemu-verify` — verify the build toolchain is present (read-only)
- `make qemu-fetch` — fetch the QEMU git tree
- `make qemu-configure` — configure the QEMU build
- `make qemu-build` — build QEMU
- `make qemu-install` — install QEMU on localhost
- `make qemu` — verify, fetch, configure, build, and install QEMU

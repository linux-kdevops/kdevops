# Usage

nixos-qemu exports NixOS modules, overlays, and a template.
Downstream projects consume these as a flake input to build their
own NixOS system closures. This document covers building, creating
configurations, and customizing packages.

## Validating the library

`nix flake check` evaluates and builds both backends so you can
verify the modules still produce a valid system closure:

```shell
nix flake check
```

To build a single backend directly:

```shell
nix build .#checks.x86_64-linux.imageless
nix build .#checks.x86_64-linux.libvirt
readlink --canonicalize result
```

The `result` symlink points to the system closure in `/nix/store`.
The NixOS init is at `<closure>/init`. The `init=` path contains a
Nix store hash that changes on every rebuild.

For kernel development, create a downstream configuration from a
template; see the next section.

List all files installed by a package (equivalent to
`dpkg --listfiles` on Debian):

```shell
find $(dirname $(readlink --canonicalize $(which fio)))/.. -type f | sort
```

`readlink --canonicalize` resolves the profile symlink to the
actual store path. Replace `fio` with any binary name.

## Creating a configuration

A configuration is a standalone flake project: its own directory
with a `flake.nix` that references nixos-qemu as a flake input
and imports its modules and overlays. Each configuration has its own
`flake.lock` and `result` symlink. Multiple configurations can coexist
independently.

The `configurations/` directory is gitignored for this purpose.
Create configurations there to keep them out of the tracked tree:

```shell
mkdir --parents configurations/my-vm && cd configurations/my-vm
```

### Using the template

The flake exports a
[template](https://nix.dev/manual/nix/stable/command-ref/new-cli/nix3-flake-init)
that scaffolds a configuration with the development profile,
overlays, and commented-out examples for building packages from
local source checkouts:

```shell
nix flake init --template "path:$PWD/../.."
```

`nix flake init` copies `templates/imageless/flake.nix` into the
current directory. The copied file is independent of the template:
future changes to the upstream template do not update your copy.
The link between your configuration and nixos-qemu is the
`inputs.nixos-qemu.url` flake input, not the template itself.

Edit `flake.nix` and set `nixos-qemu.url` to the absolute path of
your nixos-qemu checkout. The `path:` scheme does not expand `~`,
use the full path or `$HOME`:

```shell
$EDITOR flake.nix
```

Nix flakes only evaluate files
[tracked by git](https://nix.dev/manual/nix/stable/command-ref/new-cli/nix3-flake#flake-references).
The `git add` is required before the first build. Subsequent edits
to `flake.nix` are picked up from the working tree without a new
commit:

```shell
git init && git add flake.nix
nix build .#nixosConfigurations.vm.config.system.build.toplevel
readlink --canonicalize result
```

### Writing a configuration from scratch

The template is optional. Any flake that declares nixos-qemu as an
input and imports its modules works as a configuration:

```nix
{
  inputs = {
    nixos-qemu.url = "path:/home/user/src/nixos-qemu";
    nixpkgs.follows = "nixos-qemu/nixpkgs";
  };

  outputs = { self, nixpkgs, nixos-qemu, ... }: {
    nixosConfigurations.vm = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        nixos-qemu.nixosModules.imageless
        nixos-qemu.nixosModules.devel
        {
          nixpkgs.overlays = [ nixos-qemu.overlays.default ];
          environment.systemPackages = with nixpkgs.legacyPackages.x86_64-linux; [
            gdb
          ];
        }
      ];
    };
  };
}
```

`nixpkgs.follows = "nixos-qemu/nixpkgs"` ensures both flakes use
the same nixpkgs revision. Without it, the configuration would
pull a second copy of nixpkgs.

### What the modules provide

`nixosModules.imageless` (`modules/imageless.nix`) declares the
imageless base NixOS system:

- Root as tmpfs (`fileSystems."/" = lib.mkImageMediaOverride { fsType = "tmpfs"; }`)
- Key-only SSH; root carries a known initial password (`root`)
  for serial-console break-glass only
- systemd-networkd with DHCP on `en*` interfaces
- No bootloader, no kernel (external, `boot.kernel.enable = false`)
- Firewall disabled, unnecessary services disabled

`nixosModules.libvirt` (`modules/libvirt.nix`) is the disk-image
counterpart: grub on `/dev/vda`, ext4 root, DHCP through
scripted networking, nix with flakes, and weekly garbage
collection. Each backend module is standalone (no cross-import);
both set `system.stateVersion` and the sshd posture inline.

`nixosModules.user` (`modules/user.nix`) adds an opt-in
unprivileged account in `wheel`, `libvirt`, and `kvm` with
passwordless sudo. The account name is parametric through
`options.nixos-qemu.user.name` (default `user`); downstream
consumers override it to their project name. The module also
sets the serial-console break-glass root password. Workflow-driven
nodes import it; hand-development nodes do not.

`nixosModules.shares` (`modules/shares.nix`) turns a set of
virtiofs shares into `fileSystems` entries. Each share is keyed by
its mount point and declares the virtiofs `tag` announced by the
host and optional mount `options`. The module does nothing else:
overlays, XDG env vars, and directory creation stay the consumer's
responsibility. See "Host configuration via virtiofs" for usage.

`nixosModules.storage` (`modules/storage.nix`) turns a set of
block devices into `fileSystems` entries. Each entry is keyed by
mount point with fields `device`, `fsType`, `options`, `mkfsArgs`,
and `autoFormat`. Set `mkfsArgs` for a pre-mount `mkfs` oneshot
with custom arguments, or `autoFormat = true` for NixOS's default
first-mount formatting (the two are mutually exclusive). See
"Block device filesystems" for usage.

`nixosModules.devel` (`modules/devel.nix`) adds kernel testing and
storage tools, grouped by purpose: filesystem and block layer tooling
(xfstests, xfsprogs, btrfs-progs, e2fsprogs, lvm2, parted), NVMe and
SCSI (nvme-cli, libnvme, sg3_utils, xnvme), I/O generation (fio with
liburing, stress-ng), NFS (nfs-utils, nfstest, pynfs), BPF and tracing
(bpftrace, bcc, libbpf-tools, blktrace, trace-cmd), monitoring and
profiling (perf, cpupower, damo, htop, iotop, numactl, pagemon,
powertop, sysstat), selftest and blktests/fstests runtime dependencies
(acl, attr, keyutils, libcap, libseccomp, mdadm, quota, rpcbind), and
general developer comfort (editors, shells, git, jq, strace, kmod).
The module also pulls in `programs.bash.completion.enable` and the
Python data-analysis stack (matplotlib, numpy, pandas). See
`modules/devel.nix` for the authoritative list.

## Updating nixpkgs

`flake.lock` pins the exact nixpkgs revision used by every build.
Refresh it to pick up upstream package and module changes:

```shell
nix flake update
git add flake.lock
nix flake check
```

`flake.lock` must be tracked by git for the updated revision to
be picked up on the next build.

Downstream configurations that use `nixpkgs.follows` inherit
the nixpkgs pin from nixos-qemu. After updating nixos-qemu, run
`nix flake update` in each configuration to pick up the new pin.

## Overlays

Nix
[overlays](https://nixos.org/manual/nixpkgs/stable/#chap-overlays)
modify or extend the nixpkgs package set. An overlay is a function
`final: prev: { ... }` where `prev` is the package set from all
previous overlays and `final` is the fully evaluated set including
the current overlay. Overlays are applied in order, so each layer
can see and build on the changes from previous layers.

[`overrideAttrs`](https://nixos.org/manual/nixpkgs/stable/#sec-pkg-overrideAttrs)
modifies a derivation by merging new attributes into the existing
ones. Attributes not specified in the override are retained from
the original. This means overrides compose: each `overrideAttrs`
call wraps the previous derivation, replacing only the attributes
it specifies.

### What nixos-qemu provides

The `overlays/` directory customizes nixpkgs packages. Each file
overrides one package. The default overlay (`overlays.default`)
composes all per-package overlays and merges custom packages from
`pkgs/`.

Currently included:

- **fio**: enables liburing, installs t/io_uring exerciser,
  NVMe test scripts, and example job files
- **xfstests**: bumps nixpkgs 2023.05.14 (broken with modern
  GCC) to 2026.03.20

### Overriding a package from a configuration

A configuration lists overlays in order. nixos-qemu's overlay
goes first, then any user overlays that build on top of it.

For example, xfstests goes through three layers:

```
nixpkgs base                → xfstests 2023.05.14 (broken)
nixos-qemu.overlays.default → xfstests 2026.03.20 (bumped)
user overlay                → xfstests from local checkout
```

The user overlay's `prev.xfstests` is the xfstests from
nixos-qemu's overlay (the bumped version). `overrideAttrs`
replaces only `src`, keeping everything else (build inputs,
install phase, patches) from the previous layer:

```nix
nixpkgs.overlays = [
  nixos-qemu.overlays.default
  (final: prev: {
    xfstests = prev.xfstests.overrideAttrs {
      src = inputs.xfstests-src;
    };
  })
];
```

The `xfstests-src` input is a local source checkout declared as
a flake input with `flake = false` (see the template for
commented-out examples).

### Pinning a specific upstream commit

To pin a package to a specific commit without a local checkout,
use a fetcher in the overlay. The fetcher depends on where the
canonical upstream repository is hosted.

For projects hosted on kernel.org, use `fetchgit`:

```nix
# xfstests: git://git.kernel.org/pub/scm/fs/xfs/xfstests-dev.git
(final: prev: {
  xfstests = prev.xfstests.overrideAttrs {
    src = final.fetchgit {
      url = "git://git.kernel.org/pub/scm/fs/xfs/xfstests-dev.git";
      rev = "<commit-hash>";
      hash = "";
    };
  };
})

# fio: https://git.kernel.org/pub/scm/linux/kernel/git/axboe/fio
(final: prev: {
  fio = prev.fio.overrideAttrs {
    src = final.fetchgit {
      url = "https://git.kernel.org/pub/scm/linux/kernel/git/axboe/fio.git";
      rev = "<commit-hash>";
      hash = "";
    };
    patches = [];
  };
})
```

For projects hosted on GitHub, use `fetchFromGitHub`:

```nix
# damo: https://github.com/damonitor/damo
(final: prev: {
  damo = prev.damo.overrideAttrs {
    src = final.fetchFromGitHub {
      owner = "damonitor";
      repo = "damo";
      rev = "<commit-hash>";
      hash = "";
    };
  };
})

# xnvme: https://github.com/xnvme/xnvme
(final: prev: {
  xnvme = prev.xnvme.overrideAttrs {
    src = final.fetchFromGitHub {
      owner = "xnvme";
      repo = "xnvme";
      rev = "<commit-hash>";
      hash = "";
    };
  };
})
```

Nix will fail with a hash mismatch on the first build and print
the correct `hash` value to use. Clear `patches = [];` when the
upstream source already includes fixes that nixos-qemu's overlay
backports.

The user never needs to modify nixos-qemu's overlays. All
customization happens in the configuration's own `flake.nix`.

## Building from local source

To build a package from a local source checkout (for development
or testing), declare the source directory as a flake input with
`flake = false` and reference it in an overlay. This lets you
rebuild the NixOS closure with your modified source without
publishing it upstream.

In the `inputs` block of your configuration's `flake.nix`:

```nix
kmod-src = {
  url = "path:/home/user/src/kmod";
  flake = false;
};
```

`flake = false` tells Nix to import the path as plain source
rather than expecting a `flake.nix`. Then in the `nixpkgs.overlays`
list, add an overlay that replaces the package source:

```nix
(final: prev: {
  kmod = prev.kmod.overrideAttrs {
    src = inputs.kmod-src;
  };
})
```

`prev.kmod` is kmod from nixpkgs (or from a previous overlay).
`overrideAttrs` replaces only `src`, keeping the build system,
dependencies, and install phase from the original derivation.
Changes to the local source directory are picked up on every
`nix build` without updating the flake lock.

This pattern works for any nixpkgs package. The template includes
commented-out examples for fio and kmod. Clear `patches = [];`
when the local source already includes fixes that the nixos-qemu
overlay backports.

The following packages are supported by the devel module and can
be overridden this way:

| Package | Input name | Overlay |
|---|---|---|
| cpupower | `kernel-src` | `prev.cpupower.overrideAttrs { src = inputs.kernel-src; }` |
| damo | `damo-src` | `prev.damo.overrideAttrs { src = inputs.damo-src; }` |
| fio | `fio-src` | `prev.fio.overrideAttrs { src = inputs.fio-src; patches = []; }` |
| kmod | `kmod-src` | `prev.kmod.overrideAttrs { src = inputs.kmod-src; }` |
| nfstest | `nfstest-src` | `prev.nfstest.overrideAttrs { src = inputs.nfstest-src; }` |
| pynfs | `pynfs-src` | `prev.pynfs.overrideAttrs { src = inputs.pynfs-src; }` |
| xfstests | `xfstests-src` | `prev.xfstests.overrideAttrs { src = inputs.xfstests-src; }` |
| xnvme | `xnvme-src` | `prev.xnvme.overrideAttrs { src = inputs.xnvme-src; }` |

`cpupower` uses the kernel source tree (it builds from
`tools/power/cpupower/`). Point `kernel-src` to your kernel
checkout to match the running kernel version.

## Custom packages

The `pkgs/` directory holds packages not available in nixpkgs.
Each package is a file declaring a function, composed via
[callPackage](https://nix.dev/tutorials/callpackage). The overlay
imports `pkgs/default.nix` and merges them into the nixpkgs set.

Currently included:

- **damo**: DAMON user-space tool for data access monitoring
- **libbpf-tools**: standalone CO-RE BPF tracing tools (74
  binaries with `-libbpf` suffix, matching Debian convention)
- **nfstest**: NFS test suite (17 test scripts)
- **pynfs**: Python NFSv4 conformance test suite
- **xnvme**: cross-platform NVMe user space library and tools

## Host configuration via virtiofs

XDG-compliant tools (helix, neovim, git, etc.) read configuration
from `XDG_CONFIG_HOME` (per-user, defaults to `~/.config/`) and
fall back to `XDG_CONFIG_DIRS` (system-wide, colon-separated
list). On a tmpfs root `~/.config/` is always empty, so the
fallback is the only source of configuration.

To share the host's `~/.config` into the guest, add a virtiofsd
instance with tag `xdg` sharing the host's `~/.config`
directory, then mount it in the configuration and set
`XDG_CONFIG_HOME` to point to it:

```nix
fileSystems."/etc/xdg-host" = {
  device = "xdg";
  fsType = "virtiofs";
};

environment.variables.XDG_CONFIG_HOME = "/etc/xdg-host";
environment.variables.XDG_CONFIG_DIRS = lib.mkForce "/etc/xdg-host:/etc/xdg";
```

Or declare it through the shares module:

```nix
imports = [ nixos-qemu.nixosModules.shares ];

nixos-qemu.shares."/etc/xdg-host" = { tag = "xdg"; };

environment.variables.XDG_CONFIG_HOME = "/etc/xdg-host";
environment.variables.XDG_CONFIG_DIRS = lib.mkForce "/etc/xdg-host:/etc/xdg";
```

The module replaces only the `fileSystems` entry. The XDG env vars
stay in the consumer's module because they are a policy choice tied
to one specific share's role, not a generic virtiofs concern.

`XDG_CONFIG_HOME` is the primary config directory that all
XDG-compliant tools check first. Some tools (like helix) only
read from `XDG_CONFIG_HOME` and do not fall back to
`XDG_CONFIG_DIRS`, so setting both ensures all tools find the
host configs. On a tmpfs root `~/.config` is always empty, so
redirecting `XDG_CONFIG_HOME` loses nothing.

The mount point is `/etc/xdg-host` rather than `/etc/xdg` because
NixOS generates its own files in `/etc/xdg`. The `XDG_CONFIG_DIRS`
override uses `lib.mkForce` because NixOS already sets this
variable in `shells-environment.nix`. Changes on the host are live
in the guest without rebuilding.

This works for any user in the guest (root, test accounts) because
both variables are system-wide. The guest finds host configs at
`/etc/xdg-host/helix/`, `/etc/xdg-host/nvim/`,
`/etc/xdg-host/git/`, and so on.

### Sharing a curated subset

The host's `~/.config` may contain application state, browser
profiles, or credentials that should not be exposed to the guest.
To share only specific tool configs, create a dedicated directory
on the host and symlink the configs you want:

```shell
mkdir --parents ~/.config/vm
ln --symbolic ~/.config/helix ~/.config/vm/helix
ln --symbolic ~/.config/nvim ~/.config/vm/nvim
ln --symbolic ~/.config/git ~/.config/vm/git
```

Share `~/.config/vm` with virtiofsd tag `xdg` instead of the
full `~/.config`. The NixOS configuration is the same — only the
virtiofsd source directory changes.

### Dotfiles repo as a flake input

A dotfiles repository can be declared as a flake input with
`flake = false` and its files referenced directly in the NixOS
configuration. This bakes the configs into the closure, so
changes require a rebuild:

```nix
inputs.dotfiles = {
  url = "path:/home/user/src/dotfiles";
  flake = false;
};
```

Then in the module block:

```nix
environment.etc."xdg-host/helix/config.toml".source =
  "${inputs.dotfiles}/.config/helix/config.toml";
environment.etc."xdg-host/nvim".source =
  "${inputs.dotfiles}/.config/nvim";
environment.variables.XDG_CONFIG_DIRS = lib.mkForce "/etc/xdg-host:/etc/xdg";
```

This is declarative and version-controlled. The dotfiles input
is pinned in `flake.lock` like any other dependency. Run
`nix flake update` to pick up changes from the dotfiles repo.

### Home-manager

[Home-manager](https://github.com/nix-community/home-manager) is
a Nix tool for managing user configuration declaratively. Instead
of maintaining dotfiles as plain text, tool configs are expressed
as Nix options that home-manager evaluates into the correct files.

Add it as a flake input in the configuration:

```nix
inputs.home-manager = {
  url = "github:nix-community/home-manager";
  inputs.nixpkgs.follows = "nixos-qemu/nixpkgs";
};
```

Then import the home-manager NixOS module and declare user
configs:

```nix
imports = [ inputs.home-manager.nixosModules.home-manager ];

home-manager.users.root = {
  programs.helix = {
    enable = true;
    settings = {
      theme = "onedark";
      editor.line-number = "relative";
    };
  };
  programs.git = {
    enable = true;
    userName = "Your Name";
    userEmail = "your.email@example.org";
  };
};
```

Home-manager generates the dotfiles from these declarations and
places them in the user's home directory. This is the fully
declarative NixOS-native approach but adds a dependency and
requires expressing configs in Nix rather than using existing
dotfiles directly.

## Host home directory with ephemeral overlay

The host's home directory can be shared into the guest via
virtiofs for access to scripts, source trees, and tools. Mounting
it read-only protects the host, and an overlayfs layer on top
provides ephemeral writable storage for programs that write to
the home directory (shell history, `.ssh/known_hosts`, editor
state). Writes go to the tmpfs upper layer and are lost on
shutdown.

```nix
# Host home via virtiofs (read-only base).
fileSystems."/mnt/home" = {
  device = "home";
  fsType = "virtiofs";
  options = [ "ro" ];
};

# Overlay: host home (read-only) + tmpfs (writable, ephemeral).
fileSystems."/root" = {
  device = "overlay";
  fsType = "overlay";
  options = [
    "lowerdir=/mnt/home"
    "upperdir=/.root-overlay/upper"
    "workdir=/.root-overlay/work"
  ];
  depends = [ "/mnt/home" ];
};

# Create overlay work directories before the mount.
systemd.services."prepare-root-overlay" = {
  description = "Create overlay work directories for /root";
  wantedBy = [ "local-fs.target" ];
  before = [ "root.mount" ];
  unitConfig.DefaultDependencies = false;
  serviceConfig = {
    Type = "oneshot";
    RemainAfterExit = true;
    ExecStart = "${pkgs.coreutils}/bin/mkdir --parents /.root-overlay/upper /.root-overlay/work";
  };
};
```

The read-only base mount can also be declared through the shares
module, leaving the overlay and prepare-root-overlay service in the
consumer's module:

```nix
imports = [ nixos-qemu.nixosModules.shares ];

nixos-qemu.shares."/mnt/home" = { tag = "home"; options = [ "ro" ]; };

# Overlay and prepare-root-overlay service as above.
```

The virtiofsd instance on the host shares the home directory with
tag `home`. The upper and work directories live on the root tmpfs
(`/`), so they are created fresh on every boot by the
`prepare-root-overlay` service.

This requires `CONFIG_OVERLAY_FS=y` or `CONFIG_OVERLAY_FS=m` in
the guest kernel. If built as a module, it loads from
`/lib/modules` after switch-root.

## Block device filesystems

NixOS can format and mount block devices (NVMe, virtio-blk)
declared in the configuration.

### Default formatting

`autoFormat = true` runs `mkfs` with default options if the
device has no filesystem:

```nix
fileSystems."/mnt/nvme0" = {
  device = "/dev/nvme0n1";
  fsType = "xfs";
  autoFormat = true;
};
```

### Custom block and sector size

For non-default formatting options (block size, sector size,
inode size), use a systemd service that runs before the mount
unit:

```nix
systemd.services."format-nvme0" = {
  description = "Format /dev/nvme0n1 with XFS (16k block/sector)";
  wantedBy = [ "local-fs.target" ];
  before = [ "mnt-nvme0.mount" ];
  requires = [ "dev-nvme0n1.device" ];
  after = [ "dev-nvme0n1.device" ];
  unitConfig.DefaultDependencies = false;
  serviceConfig = {
    Type = "oneshot";
    RemainAfterExit = true;
    ExecStart = "${pkgs.xfsprogs}/bin/mkfs.xfs -b size=16k -s size=16k /dev/nvme0n1";
  };
};

fileSystems."/mnt/nvme0" = {
  device = "/dev/nvme0n1";
  fsType = "xfs";
};
```

NixOS generates the mount unit name from the path (`/mnt/nvme0`
becomes `mnt-nvme0.mount`). The ordering chain is: device appears,
format service runs mkfs, mount unit mounts the filesystem.

### Using the storage module

The storage module consolidates multiple extra drives into one
attrset keyed by mount point. Devices with `mkfsArgs` go through a
pre-mount format oneshot guarded by `blkid --probe`; devices with
`autoFormat = true` fall through to NixOS's own first-mount
format machinery; devices with neither are assumed pre-formatted:

```nix
imports = [ nixos-qemu.nixosModules.storage ];

nixos-qemu.storage = {
  "/mnt/nvme0" = {
    device = "/dev/nvme0n1";
    fsType = "xfs";
    mkfsArgs = [ "-b" "size=16k" "-s" "size=16k" ];
  };
  "/mnt/nvme1" = {
    device = "/dev/nvme1n1";
    fsType = "xfs";
    autoFormat = true;
  };
  "/mnt/data" = {
    device = "/dev/vdb";
    fsType = "ext4";
  };
};
```

`mkfsArgs` and `autoFormat` are mutually exclusive; an assertion
rejects configurations that set both.

## Multiple configurations

Each configuration in `configurations/` is fully independent.
Configurations do not share state, lock files, or build results.
Common patterns:

```
configurations/
├── devel/          Development VM with all testing tools
│   ├── flake.nix
│   └── flake.lock
├── storage/        VM for storage subsystem testing only
│   ├── flake.nix
│   └── flake.lock
└── minimal/        Base VM without the development profile
    ├── flake.nix
    └── flake.lock
```

Each configuration can import different modules, apply different
overlays, and add different packages. All of them share the same
nixos-qemu base through the `inputs.nixos-qemu.url` flake input.

# CLAUDE.md

## Project Overview

Systemd unit templates for running QEMU virtual machines as first-class
systemd services. Jinja2 templates rendered by `minijinja-cli` into
systemd units and environment files. No daemon, no wrapper.

**License**: copyleft-next-0.3.1

## Project Structure

```
qemu-system-units/
├── templates/           Jinja2 templates (persistent + transient)
├── vars/                YAML variable files (per-VM configuration)
│   └── example.yaml     Starting point (copy to vars/<vm_name>.yaml)
├── files/               Static files deployed as-is
├── docs/                Reference documentation
│   ├── vars.md          Variable reference
│   ├── usage.md         Rendering, deployment, operations
│   ├── design-decisions.md  Hardcoded choices and rationale
│   ├── requirements.md  Distro-specific packages
│   └── transient-units.md   systemd-run patterns
├── LICENSES/
└── README.md            Landing page and quick start
```

## Critical Rules

### Never fabricate facts

Every command-line flag, sysfs path, systemd directive, and expected
output must be verified against the actual source before being written
into any project file. `man <tool>` or `<tool> --help` before writing
any command. If a tool only has short flags (`lspci`, `ss`, `ip`), use
short flags.

### Never cheat during verification

When verifying that templates render and deploy correctly, start from
a clean state. Never pre-deploy files, reuse leftover artifacts, or
skip steps. A verification that depends on state from a previous test
is a lie.

## Rules

### Variable names match upstream

YAML variable names must use the exact terminology from the upstream
tool they configure. Do not invent prefixes or synonyms.

`ram` maps to QEMU `-m`. `cpu` maps to `-cpu`. `accel` maps to
`-accel`. `image.file` maps to `-drive file=`. `image.format` maps
to `-drive format=`. The test is: can you read the variable name and
immediately know which upstream flag it maps to?

### Flat variables for cross-cutting, nested for single-consumer

Variables used by multiple templates stay flat (e.g. `ram`, `shares`,
`vsock_cid`). Variables consumed by a single template block can be
nested when they form a cohesive group (e.g. `kernel.image`,
`kernel.append`, `kernel.initrd` all map to one `KERNEL_ARGS=` block).

### Backward compatibility

Every new template variable must be gated with `| default([])` (lists),
`| default('value')` (scalars with defaults), or `is defined`
(optional features). Templates must render identically when new
variables are absent.

### Non-transitional virtio devices

All virtio devices use `*-pci-non-transitional` suffix on PCI machines
and `*-device` suffix on microvm (MMIO). Transitional devices require
`CONFIG_VIRTIO_PCI_LEGACY` which custom kernels often disable. The
template auto-detects microvm from `machine_type` and switches device
suffixes. `vhost-user-fs-pci` has no non-transitional variant
(modern-only device).

### Zero-tool naming

All rendered output references the consumer (qemu-system@ service),
never the generator project. Config directories are named after the
service prefix (`qemu-system`, `virtiofsd`). Only the README and
CLAUDE.md mention the project name.

### Long-form command options

NEVER use short flags when a long-form alternative exists in README,
templates, docs, and any commands shown to the user. `--follow` not
`-f`, `--parents` not `-p`, `--append --groups` not `-aG`.
Exception: tools without long-form options (`ssh -p`, `lspci -nv`).

### Documentation references

Reference only QEMU and systemd manuals, not wrapper projects.

`See: man qemu-system` for QEMU flags. `See: man systemd.kill` for
systemd directives. `See: /usr/libexec/virtiofsd --help` for
virtiofsd flags. Use `<qemu_binary>` not `qemu-system-x86_64` when
the flag is architecture-independent.

### Maps-to references

"Maps to" in docs/vars.md references the upstream flag or directive,
not template filenames or env variable names. `ram` maps to `-m`,
not "QEMU_ARGS in vm.env."

### Technical identifiers in docs

Backtick-format systemd directives (`KillMode=`, `ExecStop=`), signal
constants (`SIGTERM`, `SIGKILL`), function calls (`sd_notify()`),
kernel configs (`CONFIG_VIRTIO_PCI`), and paths (`/dev/kvm`). Plain
text for tool names in natural language (virtiofsd, QEMU, systemd).
Systemd directives include trailing `=` matching man page convention.

### Shell examples

No shell variables (`$VM`, `${VM}`) in per-component documentation.
Use literal values that match vars file content (`test`, `dev`).
The deploy-all section at the bottom of docs/usage.md uses variables
for automation convenience.

Prose instructions (editing files, logging out) go in markdown
paragraphs, not shell comments.

### vars file convention

`vars/example.yaml` is the template. Users copy it to
`vars/<vm_name>.yaml` (e.g. `vars/test.yaml` for `vm_name: test`).
The filename matches `vm_name` inside the file. User vars files are
gitignored.

## Git Commit Guidelines

### One commit per change

Atomic commits. Spell fixes go in separate commits from code changes.

### Commit message format

```
subsystem: brief description in imperative mood

Plain English explanation of the change. NEVER use bullet points
or itemized lists in commit messages.

Generated-by: Claude AI
Signed-off-by: Your Name <your.email@example.org>
```

### Use Signed-off-by and Generated-by tags

Generated-by MUST be immediately followed by Signed-off-by with NO
empty lines between them. No Co-Authored-By trailer.

### No shopping cart lists

NEVER use bullet points or itemized lists in commit messages. Use
plain English paragraphs.

### Subsystem prefix

Use the template or doc name as prefix: `vm.env:`, `virtiofsd:`,
`docs:`, `vars:`, `README:`. Use `qemu-system-units:` for
cross-cutting changes.

## Key Technical Patterns

### `EnvironmentFile=` path

`%E/systemd/qemu-system/%i.env` uses the `%E` specifier for
scope-agnostic paths. User mode: `~/.config/systemd/qemu-system/`.
System mode: `/etc/systemd/qemu-system/`.

### ExecStart binary path must be literal

systemd requires the first argument of `ExecStart=` to be a literal
path, not a variable. The binary path is rendered by Jinja2 at
template time. See: `load-fragment.c` in systemd source.

### $MAINPID in ExecStartPost

Available for `Type=simple` services. systemd sets the main PID
before entering the start-post phase. No shell wrapper needed for
the `busctl RegisterMachine` call.

### Journal: --user-unit= not --user -u

`journalctl --user -u` constrains to user journal files. But user
service output goes through `user@UID.service` to the SYSTEM
journal. `journalctl --user-unit=` matches `_SYSTEMD_USER_UNIT`
across all journal files.

### Cloud-init only runs once

cloud-init marks first-boot completion in `/var/lib/cloud/`. A new
seed ISO does NOT trigger cloud-init to rerun on an existing image.
To re-provision, either use a fresh disk image or delete
`/var/lib/cloud/` inside the guest.

### Three-layer template pattern

Templates follow three layers: (1) static unit structure that never
changes, (2) conditional blocks gated on vars (`{% if X is defined %}`),
and (3) loops over lists (`{% for dev in list | default([]) %}`).
Layers 2 and 3 emit nothing when the variable is absent. New
features add new conditional/loop blocks without modifying the
static layer.

## Rendering

All rendering uses `minijinja-cli --trim-blocks`. One vars file drives
all templates.

```shell
minijinja-cli --trim-blocks \
  --output <deploy-path> \
  templates/<template>.j2 \
  vars/<vm_name>.yaml
```

## Source Code References

### QEMU

`qemu-options.hx` (all command-line options),
`hw/nvme/ctrl.c` (NVMe device, serial requirement at line 8600),
`hw/i386/microvm.c` (microvm machine type, pcie=on property),
`system/runstate.c` (SIGTERM handling, force_shutdown at line 786),
`hw/virtio/vhost-vsock.c` (VSOCK CID range validation at line 134).

### systemd

`man systemd.service` (Type=, ExecStart=, ExecStop=),
`man systemd.exec` (WorkingDirectory=, LimitMEMLOCK=, %U/%G/%h/%E specifiers),
`man systemd.resource-control` (CPUQuota=, MemoryMax=, Slice=),
`man systemd.kill` (KillMode=, KillSignal=, TimeoutSec=),
`man systemd.special` (machine.slice, machines.target).

systemd does NOT expand specifiers in `EnvironmentFile=` values. `%h`
in `Environment=` is expanded. `%h` inside an `EnvironmentFile=` is
literal.

### virtiofsd

`src/sandbox.rs` (namespace sandbox, setresuid at line 497,
default UID mapping at line 331),
`--sandbox=namespace --uid-map :0:%U:1: --gid-map :0:%G:1:` is the
canonical unprivileged configuration.

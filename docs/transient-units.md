# Transient and persistent units for QEMU VMs

## Two patterns in systemd

systemd provides two mechanisms for managing processes. Both vmspawn
and nspawn use both.

### Persistent template service (on disk)

A unit file lives on disk. systemd forks the process, manages its
lifecycle, resolves dependencies, captures logs.

```
units/user/systemd-vmspawn@.service.in:
ExecStart=systemd-vmspawn --quiet --keep-unit --register=yes --network-tap --machine=%i
```

```
units/systemd-nspawn@.service.in:
ExecStart=systemd-nspawn --quiet --keep-unit --boot --link-journal=try-guest --network-veth -U --settings=override --machine=%i
```

Source: `systemd/units/user/systemd-vmspawn@.service.in`,
`systemd/units/systemd-nspawn@.service.in`.

### Transient scope (programmatic, in memory)

The process starts first, then gets placed into a transient scope
via the `StartTransientUnit` D-Bus call. No file on disk. The scope
exists only while the process runs.

```c
/* vmspawn-scope.c:57 */
/* Creates a transient scope unit which tracks the lifetime of the current process */
r = bus_message_new_method_call(bus, &m, bus_systemd_mgr, "StartTransientUnit");
```

Source: `systemd/src/vmspawn/vmspawn-scope.c:57-67`,
`systemd/src/nspawn/nspawn.c:5634`.

### The --keep-unit bridge

When vmspawn or nspawn runs inside its service template, `--keep-unit`
tells it: "you are already in a service unit, do not create a scope on
top of it." When run directly from the terminal (without the service),
they create a transient scope.

This is how both patterns coexist. The service template is the managed
path. The transient scope is the ad-hoc path.

## systemd-run

`systemd-run` is the CLI for creating transient units. It calls
`StartTransientUnit` on the D-Bus manager interface.

Source: `systemd/man/systemd-run.xml`, "Run programs in transient
scope units, service units, or path-, socket-, or timer-triggered
service units."

### Using our infrastructure with systemd-run

A transient unit can depend on persistent units via `--property=`.
The deployed virtiofsd sockets, vfio-bind services, and
`EnvironmentFile=` paths are all reusable.

Verified empirically. Transient unit referencing persistent socket:

```shell
$ systemd-run --user --collect --no-block \
    --unit=transient-test \
    --property=Requires=virtiofsd@test-home.socket \
    --property=After=virtiofsd@test-home.socket \
    --property=Slice=machine.slice \
    --property=LimitMEMLOCK=2304M \
    sleep 30

$ systemctl --user show transient-test.service \
    | grep -E '^(Requires|After|Slice|LimitMEMLOCK)='
Requires=machine.slice virtiofsd@test-home.socket basic.target
After=machine.slice virtiofsd@test-home.socket -.mount basic.target
Slice=machine.slice
LimitMEMLOCK=2415919104
```

EnvironmentFile loading also works. `$QEMU_ARGS` from the rendered
env file is available inside the transient service:

```shell
$ systemd-run --user --pty --collect \
    --property=EnvironmentFile=%E/systemd/qemu-system/debian.env \
    sh -c 'echo "QEMU_ARGS=$QEMU_ARGS" | head -c 200'
QEMU_ARGS=  -machine type=q35   -accel kvm   -cpu host   -m 2048 ...
```

### Full interactive VM with transient-run template

The `transient-run.sh.j2` template renders a self-contained script
that combines `--pty` for interactive console, `--property=` for
dependencies and `EnvironmentFile=`, and `sh -c` for shell word
splitting of `$QEMU_ARGS`:

```shell
minijinja-cli --trim-blocks \
    --output /tmp/run-test.sh \
    templates/transient-run.sh.j2 vars/test.yaml
bash /tmp/run-test.sh
```

The script stops the persistent service if running (port conflicts),
sets up `QEMU_EXTRA_ARGS` with resolved paths, and calls
`systemd-run --user --pty` with all virtiofsd dependencies.

Disconnect with `^]` pressed three times within 1 second.

Source: `systemd/src/shared/ptyfwd.c:211-230`, `look_for_escape()`
checks for `0x1D` (Ctrl-]) three times within `ESCAPE_USEC`
(1 second).

### Pitfalls discovered empirically

**Do not pipe through bash.** `minijinja-cli ... | bash` steals
stdin from the terminal. `systemd-run --pty` needs the terminal's
stdin for interactive console forwarding. Always render to a file
first, then run with `bash /tmp/run-test.sh`.

**systemd specifiers do not expand in transient Environment=.**
`%t` and `%i` expand in persistent unit files but are passed as
literal strings in `--property=Environment=` for transient units.
The template resolves paths at render time using `$XDG_RUNTIME_DIR`
(shell-expanded before `systemd-run` is called) and passes the
result via `--property=PassEnvironment=QEMU_EXTRA_ARGS`.

Verified empirically:

```shell
$ systemd-run --user --collect --no-block --unit=specifier-test \
    --property='Environment=TEST=%t/foo' \
    sh -c 'echo $TEST'
$ journalctl --user-unit=specifier-test --output=cat
%t/foo
```

**KERNEL_ARGS requires eval.** The rendered env file contains
`-append "console=ttyS0,115200 init=..."` with embedded quotes.
systemd's `EnvironmentFile=` parser preserves quotes as literal
characters. Without `eval`, the shell passes `"console=...` and
`init=..."` as separate arguments to QEMU. The template uses
`eval exec $QEMU_BINARY ...` to process the quotes correctly.

### Why sh -c is required

systemd-run passes command arguments as separate argv entries.
`$QEMU_ARGS` in the `EnvironmentFile=` is a single string with spaces.
Without `sh -c`, systemd would treat `$QEMU_ARGS` as one token. With
`sh -c`, the shell performs word splitting.

In persistent services, `ExecStart=` handles this natively. systemd's
own command parser expands `$QEMU_ARGS` with word splitting. This is
specific to unit file parsing (`load-fragment.c`), not to the D-Bus
`StartTransientUnit` interface.

## --pty and persistent services

`--pty` is a `systemd-run` feature. It opens a PTY master
(`openpt_allocate` in `run.c:2476`), passes the slave FD as
`StandardInputFileDescriptor` / `StandardOutputFileDescriptor` to the
transient unit (`run.c:1501-1506`), and runs `PTYForward` to forward
between the local terminal and the service.

Source: `systemd/src/run/run.c:1419-1506`, `systemd/src/shared/ptyfwd.c`.

Persistent services have no controlling terminal by design. There is
no mechanism to retroactively attach a PTY to a running service.
`machinectl login` and `machinectl shell` work for containers (nspawn)
but not for VMs, since the guest OS is fully isolated.

Source: `systemd/man/machinectl.xml`, login is "only supported for
containers running systemd as init system."

### Interactive console for persistent VMs (virtconsole)

The override template adds a virtio console on a unix socket to
every persistent VM. ttyS0 stays on stdio (captured by the journal).
hvc0 is a virtconsole on a socket for interactive access.

QEMU flags (generated by the override template):

```
-device virtio-serial-pci
-chardev socket,id=console0,path=%t/qemu-system/%i/console.sock,server=on,wait=off
-device virtconsole,chardev=console0
```

Connect:

```shell
socat -,raw,echo=0,escape=0x1d \
    UNIX-CONNECT:$XDG_RUNTIME_DIR/qemu-system/test/console.sock
```

Disconnect with `Ctrl-]` (single press, `escape=0x1d`). The VM
keeps running. Reconnect at any time.

Guest requirements:
- `console=hvc0` on the kernel command line (in addition to
  `console=ttyS0`)
- A getty on hvc0 (e.g., `systemd.services."getty@hvc0"` in NixOS)
- `CONFIG_VIRTIO_CONSOLE=y` or `=m` in the guest kernel

Source: QEMU `qemu-options.hx`, libvirt `virsh console` uses the
same virtio-serial + virtconsole pattern.

Limitations:
- hvc0 only works after the guest kernel loads. BIOS output and
  early boot messages are on ttyS0 (journal only).
- The initramfs emergency shell is on ttyS0, not hvc0. Use the
  transient-run template (approach 3) for initramfs debugging.
- QEMU monitor (`Ctrl-a c`) is on ttyS0, not the virtconsole.

## When to use each pattern

| Use case | Mechanism |
|---|---|
| Long-lived, managed VMs | Persistent template (`systemctl start qemu-system@test`) |
| Console access to running VMs | `socat` to virtconsole socket (hvc0) |
| Interactive debugging (initramfs) | `transient-run.sh.j2` with `systemd-run --pty` (ttyS0) |
| CI / ephemeral VMs | `systemd-run --user --collect` (no `--pty`) |
| Quick test, no env file | `systemd-run --user --pty /usr/bin/qemu-system-x86_64 -m 2048 ...` |

Both patterns place VMs in `machine.slice`, both can register with
machined, both reuse the deployed virtiofsd sockets and vfio-bind
services. The infrastructure is shared.

## Proxmox comparison

Proxmox uses transient scopes exclusively. The `qm start` command
forks, calls `enter_systemd_scope()` via D-Bus
`StartTransientUnit()`, places the QEMU process in `$VMID.scope`
under `qemu.slice` (not `machine.slice`). No persistent service
files. System scope only (root).

Source: `git.proxmox.com/pve-common.git`, `src/PVE/Systemd.pm`,
`enter_systemd_scope()`. `git.proxmox.com/qemu-server.git` —
`PVE/QemuServer.pm`.

#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""Update SSH config for NixOS VMs.

This script manages SSH configuration entries for NixOS VMs running
via native QEMU virtualization (not libvirt). It handles both adding
and removing SSH config entries.

Usage:
    update_ssh_config_nixos.py update <hostname> <host> <port> <user>
        <ssh_config> <privkey> <tag>
        [--vsock-cid <N>] [--default-transport vsock|tcp]
    update_ssh_config_nixos.py remove <hostname> '' '' '' <ssh_config>
        '' <tag>

When --vsock-cid is given, emit three Host stanzas:
    <hostname>-vsock    : ProxyCommand systemd-ssh-proxy vsock/<cid> 22
    <hostname>-tcp      : TCP via <host>:<port>
    <hostname>          : alias of whichever --default-transport picks
                          (defaults to vsock when --vsock-cid is set).

Without --vsock-cid, one <hostname> stanza is emitted over TCP
(backward-compatible with the libvirt NIXOS caller).
"""

import argparse
import os
import re
import sys


SYSTEMD_SSH_PROXY = "/usr/lib/systemd/systemd-ssh-proxy"


def render_vsock_stanza(host_tokens, user, key, cid):
    return (
        f"Host {host_tokens}\n"
        f"    User {user}\n"
        f"    IdentityFile {key}\n"
        f"    ProxyCommand {SYSTEMD_SSH_PROXY} vsock/{cid} 22\n"
        f"    ProxyUseFdpass yes\n"
        f"    CheckHostIP no\n"
        f"    StrictHostKeyChecking no\n"
        f"    UserKnownHostsFile /dev/null\n"
        f"    LogLevel ERROR\n"
    )


def render_tcp_stanza(host_tokens, host_ip, port, user, key):
    return (
        f"Host {host_tokens}\n"
        f"    HostName {host_ip}\n"
        f"    Port {port}\n"
        f"    User {user}\n"
        f"    IdentityFile {key}\n"
        f"    StrictHostKeyChecking no\n"
        f"    UserKnownHostsFile /dev/null\n"
        f"    LogLevel ERROR\n"
    )


def build_entries(hostname, host_ip, port, user, key, vsock_cid, default_transport):
    """Return a list of (alias, block_body) pairs to write.

    Each block starts with its own `# kdevops-managed: {tag} - {alias}`
    marker so remove-on-update can match and drop the old block via
    regex.
    """
    if vsock_cid is None:
        # Legacy single-stanza form used by libvirt NIXOS path.
        return [
            (hostname, render_tcp_stanza(hostname, host_ip, port, user, key)),
        ]

    # Three-stanza form: default alias groups with either -vsock or -tcp.
    if default_transport == "tcp":
        default_alias = f"{hostname} {hostname}-tcp"
        bare_stanza = render_tcp_stanza(default_alias, host_ip, port, user, key)
        return [
            (hostname, bare_stanza),
            (f"{hostname}-vsock",
             render_vsock_stanza(f"{hostname}-vsock", user, key, vsock_cid)),
        ]

    # default_transport == "vsock"
    default_alias = f"{hostname} {hostname}-vsock"
    bare_stanza = render_vsock_stanza(default_alias, user, key, vsock_cid)
    return [
        (hostname, bare_stanza),
        (f"{hostname}-tcp",
         render_tcp_stanza(f"{hostname}-tcp", host_ip, port, user, key)),
    ]


def managed_block_regex(tag, hostname):
    """Match every `# kdevops-managed: {tag} - <alias>` block whose alias
    is either the base hostname or starts with it followed by a dash.
    This catches qsu, qsu-vsock, qsu-tcp in one sweep without disturbing
    unrelated entries that share the tag prefix.
    """
    return re.compile(
        rf"^# kdevops-managed: {re.escape(tag)} - "
        rf"{re.escape(hostname)}(?:-[\w-]+)?\n"
        r"Host [^\n]+\n"
        r"(?:[ \t]+[^\n]+\n)*",
        re.MULTILINE,
    )


def update_ssh_config(
    action, hostname, host_ip, port, username, ssh_config_path, ssh_key_path,
    tag, vsock_cid, default_transport,
):
    ssh_config_path = os.path.expanduser(ssh_config_path)
    os.makedirs(os.path.dirname(ssh_config_path), exist_ok=True)

    config_content = ""
    if os.path.exists(ssh_config_path):
        with open(ssh_config_path, "r") as f:
            config_content = f.read()

    entry_pattern = managed_block_regex(tag, hostname)

    # Always drop prior managed blocks for this base hostname.
    config_content = entry_pattern.sub("", config_content)

    if action == "remove":
        print(f"Removed SSH config entries for {hostname}")
    elif action == "update":
        blocks = []
        for alias, body in build_entries(
            hostname, host_ip, port, username, ssh_key_path,
            vsock_cid, default_transport,
        ):
            blocks.append(
                f"# kdevops-managed: {tag} - {alias}\n{body}"
            )
        new_entries = "\n".join(blocks)
        config_content = config_content.rstrip() + "\n\n" + new_entries + "\n"
        if vsock_cid is None:
            print(f"Updated SSH config entry for {hostname} (port {port})")
        else:
            print(
                f"Updated SSH config entries for {hostname}, "
                f"{hostname}-vsock, {hostname}-tcp "
                f"(default={default_transport}, vsock CID={vsock_cid}, "
                f"TCP port={port})"
            )

    with open(ssh_config_path, "w") as f:
        f.write(config_content)


def main():
    parser = argparse.ArgumentParser(
        description="Manage SSH config entries for NixOS-on-QEMU VMs.",
    )
    parser.add_argument("action", choices=["update", "remove"])
    parser.add_argument("hostname")
    parser.add_argument("host_ip", nargs="?", default="localhost")
    parser.add_argument("port", nargs="?", default="22")
    parser.add_argument("username", nargs="?", default="kdevops")
    parser.add_argument("ssh_config_path")
    parser.add_argument("ssh_key_path", nargs="?", default="")
    parser.add_argument("tag", nargs="?", default="NixOS VM")
    parser.add_argument(
        "--vsock-cid", type=int, default=None,
        help="VSOCK CID of the VM. When set, emit qsu-style three-stanza "
             "layout (host, host-vsock, host-tcp).",
    )
    parser.add_argument(
        "--default-transport", choices=["vsock", "tcp"], default="vsock",
        help="Which transport the bare <hostname> alias groups with. Only "
             "meaningful when --vsock-cid is set.",
    )
    args = parser.parse_args()

    try:
        update_ssh_config(
            args.action,
            args.hostname,
            args.host_ip or "localhost",
            args.port or "22",
            args.username or "kdevops",
            args.ssh_config_path,
            args.ssh_key_path,
            args.tag,
            args.vsock_cid,
            args.default_transport,
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

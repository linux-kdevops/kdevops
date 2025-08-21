#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""Update SSH config for NixOS VMs.

This script manages SSH configuration entries for NixOS VMs running
via native QEMU virtualization (not libvirt). It handles both adding
and removing SSH config entries.

Usage:
    update_ssh_config_nixos.py update <hostname> <host> <port> <user> <ssh_config> <privkey> <tag>
    update_ssh_config_nixos.py remove <hostname> '' '' '' <ssh_config> '' <tag>
"""

import os
import sys
import re
from pathlib import Path


def update_ssh_config(
    action, hostname, host_ip, port, username, ssh_config_path, ssh_key_path, tag
):
    """Update or remove SSH config entries for NixOS VMs.

    Args:
        action: 'update' to add/update entry, 'remove' to remove entry
        hostname: VM hostname
        host_ip: Host IP (usually localhost for NixOS VMs)
        port: SSH port number
        username: SSH username
        ssh_config_path: Path to SSH config file
        ssh_key_path: Path to SSH private key
        tag: Tag to identify entries (e.g., 'NixOS VM')
    """

    ssh_config_path = os.path.expanduser(ssh_config_path)

    # Ensure SSH config directory exists
    os.makedirs(os.path.dirname(ssh_config_path), exist_ok=True)

    # Read existing config
    config_content = ""
    if os.path.exists(ssh_config_path):
        with open(ssh_config_path, "r") as f:
            config_content = f.read()

    # Pattern to match our managed entries
    entry_pattern = re.compile(
        rf"^# kdevops-managed: {re.escape(tag)} - {re.escape(hostname)}\n"
        r"Host [^\n]+\n"
        r"(?:[ \t]+[^\n]+\n)*",
        re.MULTILINE,
    )

    if action == "remove":
        # Remove existing entry
        config_content = entry_pattern.sub("", config_content)
        print(f"Removed SSH config entry for {hostname}")

    elif action == "update":
        # Remove existing entry first
        config_content = entry_pattern.sub("", config_content)

        # Create new entry
        new_entry = f"""# kdevops-managed: {tag} - {hostname}
Host {hostname}
    HostName {host_ip}
    Port {port}
    User {username}
    IdentityFile {ssh_key_path}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR

"""

        # Add new entry at the end
        config_content = config_content.rstrip() + "\n\n" + new_entry
        print(f"Updated SSH config entry for {hostname} (port {port})")

    # Write updated config
    with open(ssh_config_path, "w") as f:
        f.write(config_content)


def main():
    """Main function to handle command line arguments."""
    if len(sys.argv) < 8:
        print(
            "Usage: update_ssh_config_nixos.py <action> <hostname> <host> <port> <user> <ssh_config> <privkey> <tag>"
        )
        print("  action: 'update' or 'remove'")
        print("  hostname: VM hostname")
        print("  host: Host IP (use 'localhost' for local VMs)")
        print("  port: SSH port number")
        print("  user: SSH username")
        print("  ssh_config: Path to SSH config file")
        print("  privkey: Path to SSH private key")
        print("  tag: Tag to identify entries (e.g., 'NixOS VM')")
        sys.exit(1)

    action = sys.argv[1]
    hostname = sys.argv[2]
    host_ip = sys.argv[3] if sys.argv[3] else "localhost"
    port = sys.argv[4] if sys.argv[4] else "22"
    username = sys.argv[5] if sys.argv[5] else "kdevops"
    ssh_config_path = sys.argv[6]
    ssh_key_path = sys.argv[7] if len(sys.argv) > 7 else ""
    tag = sys.argv[8] if len(sys.argv) > 8 else "NixOS VM"

    if action not in ["update", "remove"]:
        print(f"Error: Invalid action '{action}'. Use 'update' or 'remove'.")
        sys.exit(1)

    try:
        update_ssh_config(
            action,
            hostname,
            host_ip,
            port,
            username,
            ssh_config_path,
            ssh_key_path,
            tag,
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

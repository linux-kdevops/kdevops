#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Update SSH config for Lambda Labs instances.
Based on the existing SSH config update scripts.
"""

import sys
import os
import re
import argparse


def update_ssh_config(
    action, hostname, ip_address, username, ssh_config_path, ssh_key_path, tag
):
    """Update or remove SSH config entries for Lambda Labs instances."""

    # Normalize paths
    ssh_config_path = (
        os.path.expanduser(ssh_config_path) if ssh_config_path else "~/.ssh/config"
    )
    # For ssh_key_path, only expand and use if not None and if action is update
    if action == "update" and ssh_key_path:
        ssh_key_path = os.path.expanduser(ssh_key_path)

    # Ensure SSH config directory exists
    ssh_config_dir = os.path.dirname(ssh_config_path)
    if not os.path.exists(ssh_config_dir):
        os.makedirs(ssh_config_dir, mode=0o700)

    # Read existing SSH config
    if os.path.exists(ssh_config_path):
        with open(ssh_config_path, "r") as f:
            config_lines = f.readlines()
    else:
        config_lines = []

    # Find and remove existing entry for this host
    new_lines = []
    skip_block = False
    for line in config_lines:
        if line.strip().startswith(f"Host {hostname}"):
            skip_block = True
        elif skip_block and line.strip().startswith("Host "):
            skip_block = False

        if not skip_block:
            new_lines.append(line)

    # Add new entry if action is update
    if action == "update":
        if not ssh_key_path:
            print(f"Error: SSH key path is required for update action")
            return

        # Add Lambda Labs tag comment if not present
        tag_comment = f"# {tag} instances\n"
        if tag_comment not in new_lines:
            new_lines.append(f"\n{tag_comment}")

        # Add host configuration
        host_config = f"""
Host {hostname}
    HostName {ip_address}
    User {username}
    IdentityFile {ssh_key_path}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
    LogLevel ERROR
"""
        new_lines.append(host_config)

    # Write updated config
    with open(ssh_config_path, "w") as f:
        f.writelines(new_lines)

    if action == "update":
        print(f"Updated SSH config for {hostname} ({ip_address})")
    else:
        print(f"Removed SSH config for {hostname}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Update SSH config for Lambda Labs instances"
    )
    parser.add_argument(
        "action", choices=["update", "remove"], help="Action to perform"
    )
    parser.add_argument("hostname", help="Hostname for the SSH config entry")
    parser.add_argument(
        "ip_address", nargs="?", help="IP address of the instance (required for update)"
    )
    parser.add_argument(
        "username", nargs="?", help="SSH username (required for update)"
    )
    parser.add_argument(
        "ssh_config_path",
        nargs="?",
        default="~/.ssh/config",
        help="Path to SSH config file",
    )
    parser.add_argument(
        "ssh_key_path",
        nargs="?",
        default=None,
        help="Path to SSH private key",
    )
    parser.add_argument(
        "tag", nargs="?", default="Lambda Labs", help="Tag for grouping instances"
    )

    args = parser.parse_args()

    if args.action == "update":
        if not args.ip_address or not args.username:
            print("Error: IP address and username are required for update action")
            sys.exit(1)
        update_ssh_config(
            args.action,
            args.hostname,
            args.ip_address,
            args.username,
            args.ssh_config_path,
            args.ssh_key_path,
            args.tag,
        )
    else:
        # For remove action, we don't need all parameters
        update_ssh_config(
            args.action,
            args.hostname,
            None,
            None,
            args.ssh_config_path or "~/.ssh/config",
            None,
            args.tag,
        )


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
"""
Update SSH config for Lambda Labs instances.
Creates/updates SSH config entries for Lambda Labs cloud instances.
"""

import sys
import os
from pathlib import Path


def update_ssh_config(
    action, hostname, ip_address, username, config_file, ssh_key, provider_name, port=22
):
    """
    Update SSH configuration file with Lambda Labs instance details.

    Args:
        action: 'update' or 'remove'
        hostname: Instance hostname
        ip_address: Instance IP address
        username: SSH username (usually 'ubuntu')
        config_file: SSH config file path
        ssh_key: Path to SSH private key
        provider_name: Provider name for comments
        port: SSH port number (default: 22)
    """
    config_file = os.path.expanduser(config_file)
    ssh_key = os.path.expanduser(ssh_key)

    # SSH config template for Lambda Labs
    ssh_template = f"""# {provider_name} instance
Host {hostname} {ip_address}
\tHostName {ip_address}
\tUser {username}
\tPort {port}
\tIdentityFile {ssh_key}
\tUserKnownHostsFile /dev/null
\tStrictHostKeyChecking no
\tPasswordAuthentication no
\tIdentitiesOnly yes
\tLogLevel FATAL
"""

    if action == "update":
        # Remove existing entry if present
        remove_from_config(hostname, config_file)

        # Add new entry
        with open(config_file, "a") as f:
            f.write(ssh_template)
        print(f"✓ Updated SSH config for {hostname} ({ip_address}) in {config_file}")

    elif action == "remove":
        remove_from_config(hostname, config_file)
        print(f"✓ Removed SSH config for {hostname} from {config_file}")

    else:
        print(f"Unknown action: {action}", file=sys.stderr)
        sys.exit(1)


def remove_from_config(hostname, config_file):
    """Remove an entry from SSH config file."""
    if not os.path.exists(config_file):
        return

    with open(config_file, "r") as f:
        lines = f.readlines()

    # Find and remove the host block
    new_lines = []
    skip = False
    for line in lines:
        if line.startswith(f"Host {hostname} ") or line.startswith(
            f"Host {hostname}\t"
        ):
            skip = True
        elif skip and line.startswith("Host "):
            skip = False

        if not skip:
            new_lines.append(line)

    with open(config_file, "w") as f:
        f.writelines(new_lines)


def main():
    """Main entry point."""
    if len(sys.argv) < 7:
        print(
            f"Usage: {sys.argv[0]} <action> <hostname> <ip_address> <username> <config_file> <ssh_key> [provider_name] [port]"
        )
        print("  action: 'update' or 'remove'")
        print("  hostname: Instance hostname")
        print("  ip_address: Instance IP address")
        print("  username: SSH username")
        print("  config_file: SSH config file path")
        print("  ssh_key: Path to SSH private key")
        print("  provider_name: Optional provider name (default: 'Lambda Labs')")
        print("  port: Optional SSH port (default: 22)")
        sys.exit(1)

    action = sys.argv[1]
    hostname = sys.argv[2]
    ip_address = sys.argv[3]
    username = sys.argv[4]
    config_file = sys.argv[5]
    ssh_key = sys.argv[6]
    provider_name = sys.argv[7] if len(sys.argv) > 7 else "Lambda Labs"
    port = int(sys.argv[8]) if len(sys.argv) > 8 else 22

    update_ssh_config(
        action,
        hostname,
        ip_address,
        username,
        config_file,
        ssh_key,
        provider_name,
        port,
    )


if __name__ == "__main__":
    main()

#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Detect the appropriate libvirt session type (system vs user) based on
# distribution defaults, similar to how guestfs handles it.

SCRIPTS_DIR=$(dirname $0)
source ${SCRIPTS_DIR}/libvirt_pool.sh

OS_FILE="/etc/os-release"
LIBVIRT_URI="qemu:///system"  # Default to system

# Get the pool variables which includes distribution detection
get_pool_vars

# Fedora defaults to user session
if [[ "$USES_QEMU_USER_SESSION" == "y" ]]; then
    LIBVIRT_URI="qemu:///session"
fi

# Override detection if explicitly configured
if [[ -n "$CONFIG_LIBVIRT_URI_PATH" ]]; then
    LIBVIRT_URI="$CONFIG_LIBVIRT_URI_PATH"
fi

echo "$LIBVIRT_URI"

#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Show status of NixOS VMs

SCRIPTS_DIR=$(dirname $0)
source ${SCRIPTS_DIR}/libvirt_pool.sh

# Get libvirt session settings
get_pool_vars

# Detect libvirt URI
if [[ -x "${SCRIPTS_DIR}/detect_libvirt_session.sh" ]]; then
    LIBVIRT_URI=$("${SCRIPTS_DIR}/detect_libvirt_session.sh")
else
    LIBVIRT_URI="qemu:///system"
fi

export LIBVIRT_DEFAULT_URI="$LIBVIRT_URI"

echo "NixOS VM Status (using $LIBVIRT_URI):"
echo "======================================"

# Check if virsh is available
if ! command -v virsh &> /dev/null; then
    echo "Error: virsh command not found. Please install libvirt."
    exit 1
fi

# List all VMs with nixos prefix or from kdevops
if [[ "$USES_QEMU_USER_SESSION" != "y" && "$CAN_SUDO" == "y" ]]; then
    sudo virsh list --all | grep -E "(nixos|kdevops)" || echo "No NixOS VMs found."
else
    virsh list --all | grep -E "(nixos|kdevops)" || echo "No NixOS VMs found."
fi

echo ""
echo "Network Status:"
echo "==============="

# Show network status
if [[ "$USES_QEMU_USER_SESSION" != "y" && "$CAN_SUDO" == "y" ]]; then
    sudo virsh net-list --all | grep nixos || echo "No NixOS networks found."
else
    virsh net-list --all | grep nixos || echo "No NixOS networks found."
fi

echo ""
echo "Storage Pool Status:"
echo "===================="

# Show storage pool status
if [[ "$USES_QEMU_USER_SESSION" != "y" && "$CAN_SUDO" == "y" ]]; then
    sudo virsh pool-list --all | grep nixos || echo "No NixOS storage pools found."
else
    virsh pool-list --all | grep nixos || echo "No NixOS storage pools found."
fi

#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
# Check if a device supports TCG/OPAL

# Usage: check_tcg_device.sh <device>
# Example: check_tcg_device.sh /dev/nvme0n1

set -e

DEVICE="${1:-/dev/nvme0n1}"

if [ ! -e "$DEVICE" ]; then
    echo "Error: Device $DEVICE does not exist"
    exit 1
fi

echo "Checking TCG/OPAL support for $DEVICE..."

# Check if sedutil-cli is available (alternative tool)
if command -v sedutil-cli &> /dev/null; then
    echo "Using sedutil-cli to check device..."
    sedutil-cli --scan | grep -q "$DEVICE" && echo "Device supports TCG/OPAL" || echo "Device does not support TCG/OPAL"
fi

# Check if device is NVMe and has security features
if [[ "$DEVICE" == /dev/nvme* ]]; then
    echo "NVMe device detected, checking security capabilities..."
    nvme id-ctrl "$DEVICE" 2>/dev/null | grep -i "opal\|tcg" || echo "No TCG/OPAL info in NVMe identify"
fi

# Check kernel TCG OPAL support
if [ -d /sys/kernel/security/tpm0 ]; then
    echo "TPM support detected in kernel"
fi

# Check for OPAL sysfs entries
DEVICE_NAME=$(basename "$DEVICE")
if [ -d "/sys/block/$DEVICE_NAME" ]; then
    if [ -f "/sys/block/$DEVICE_NAME/device/sed_opal_key" ]; then
        echo "Kernel OPAL support detected for device"
    fi
fi

echo "TCG device check complete"
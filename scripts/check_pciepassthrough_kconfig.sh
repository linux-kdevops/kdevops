#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

# Check if the PCI passthrough Kconfig file exists
KCONFIG_FILE="$1"

if [ -z "$KCONFIG_FILE" ]; then
    echo n
    exit 0
fi

# Check both with and without Kconfig. prefix
if [ -f "Kconfig.${KCONFIG_FILE}" ] || [ -f "${KCONFIG_FILE}" ]; then
    echo y
else
    echo n
fi

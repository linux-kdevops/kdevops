#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

# Part of kdevops reboot-limit loop testing with kernel-of-the-day
# This script would normally update to the latest kernel before running the loop,
# but since CONFIG_KERNEL_CI is being removed, this is now just a placeholder
# that runs the regular loop.

if [[ "$TOPDIR" == "" ]]; then
	TOPDIR=$PWD
fi

source ${TOPDIR}/.config
source ${TOPDIR}/scripts/lib.sh

TARGET_HOSTS="baseline"
if [[ "$1" != "" ]]; then
	TARGET_HOSTS=$1
fi

echo "Note: kernel-of-the-day updates are not yet implemented for reboot-limit"
echo "Running regular reboot-limit loop instead..."

# For now, just run the regular loop
${TOPDIR}/scripts/workflows/demos/reboot-limit/run_loop.sh

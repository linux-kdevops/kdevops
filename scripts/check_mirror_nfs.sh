#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

MIRROR_PATH="$1"

if [[ ! -d $MIRROR_PATH ]]; then
	echo n
	exit
fi

if mount | grep -q "on $MIRROR_PATH type nfs"; then
	echo "y"
	exit
fi

echo n

#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

FILE="$1"

# Ensure directory and file are created
mkdir --parents $(dirname $FILE)
if [ ! -f "$FILE" ]; then
	touch $FILE
fi

if [ -s "$FILE" ]; then
	echo y
	exit
fi

echo n

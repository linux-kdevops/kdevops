#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

STR=""

if [[ $# -eq 0 ]]; then
	echo \"\"
	exit 0
fi

# Concatenate every argument as-is. Callers pass the pieces of a single
# string already split on spaces (e.g. a scheme, a bridge IP, and a mirror
# path) and expect them joined without a separator.
STR=""
while [[ ${#1} -gt 0 ]]; do
	STR="${STR}${1}"
	shift
done

echo $STR

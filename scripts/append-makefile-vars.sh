#!/bin/bash

STR=""

if [[ $# -eq 0 ]]; then
	echo \"\"
	exit 0
fi

# First argument is the prefix (e.g., ~/.ssh/config_kdevops_)
STR="${1}"
shift

# Second argument is the SHA256 hash - use only first 8 characters
# to match terraform tfvars template behavior
if [[ ${#1} -gt 0 ]]; then
	STR="${STR}${1:0:8}"
	shift
fi

# Append any remaining arguments as-is
while [[ ${#1} -gt 0 ]]; do
	STR="${STR}${1}"
	shift
done

echo $STR

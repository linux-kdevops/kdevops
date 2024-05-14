#!/bin/bash

STR=""

if [[ $# -eq 0 ]]; then
	echo \"\"
	exit 0
fi

while [[ ${#1} -gt 0 ]]; do
	STR="${STR}${1}"
	shift
done

echo $STR

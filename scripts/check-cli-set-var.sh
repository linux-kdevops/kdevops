#!/bin/bash

if [[ $# -ne 1 ]]; then
	echo n
	exit 0
fi

which env > /dev/null
if [[ $? -ne 0 ]]; then
	echo n
	exit 0
fi

VAR=$(env | grep ^"$1=" | head -1 | awk '{print $1}')

if [[ "$VAR" != "" ]]; then
	echo y
	exit 0
fi

echo n
exit 0

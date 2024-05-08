#!/bin/bash
DEBIAN_VERSION_FILE="/etc/debian_version"

if [[ ! -f $DEBIAN_VERSION_FILE ]]; then
	echo n
fi

check_debian_version()
{
	grep -qi $1 $DEBIAN_VERSION_FILE
	if [[ $? -eq 0 ]]; then
		echo y
		exit
	fi
	echo n
	exit
}

check_debian_version $1

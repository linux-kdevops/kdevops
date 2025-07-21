#!/bin/bash

DISTRO=$1
VIRT_TYPE=$2

# We currently ignore the distro because as far as we're concerned
# they all use the default IP. If your distribution needs
# a different default it should be easy for you to extend it here.

DISTRO_FEDORA=`scripts/os-release-check.sh fedora`
if [[ "$DISTRO_FEDORA" == "y" ]]; then
	echo "192.168.122.1"
	exit 0
fi

echo "192.168.122.1"

#!/bin/bash
DEBIAN_VERSION_FILE="/etc/debian_version"
ACCEPTABLE_HOPS=1

if [[ $# -eq 1 ]]; then
	ACCEPTABLE_HOPS=$1
fi

# For now we only support debian. Adding other distros should be easy, its
# just a matter of mapping a sources file to a column we can use for a server
# hostname.
if [[ ! -f $DEBIAN_VERSION_FILE ]]; then
	echo n
	exit 0
fi

SOURCES_FILE="/etc/apt/sources.list"

if [[ ! -f $SOURCES_FILE ]]; then
	echo n
	exit 0
fi

which traceroute > /dev/null
if [[ $? -ne 0 ]]; then
	echo n
	exit 0
fi

LINE=$(grep -v "^#" $SOURCES_FILE | head -1)
HOST_URL_LINE=$(echo $LINE | awk '{print $2}')
HOST=$(echo $HOST_URL_LINE | awk -F[/:] '{print $4}')
HOP_COUNT=$(traceroute -n -w 1,1,1 $HOST | wc -l)
HOP_COUNT=$((HOP_COUNT -1))

if [[ $HOP_COUNT -le $ACCEPTABLE_HOPS ]]; then
	echo y
	exit 0
fi

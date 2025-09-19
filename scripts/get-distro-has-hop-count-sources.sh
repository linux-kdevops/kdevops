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
DEB822_SOURCES_FILE="/etc/apt/sources.list.d/debian.sources"

# Check for DEB822 format first
if [[ -f $DEB822_SOURCES_FILE ]]; then
	SOURCES_FILE=$DEB822_SOURCES_FILE
	IS_DEB822=true
elif [[ ! -f $SOURCES_FILE ]]; then
	echo n
	exit 0
else
	IS_DEB822=false
fi

which traceroute > /dev/null
if [[ $? -ne 0 ]]; then
	echo n
	exit 0
fi

# Extract host depending on format
if [[ "$IS_DEB822" == "true" ]]; then
	# DEB822 format: URIs: https://deb.debian.org/debian
	HOST_URL_LINE=$(grep -E "^URIs:" $SOURCES_FILE | head -1 | awk '{print $2}')
	# Strip protocol and port, extract just hostname
	HOST=$(echo $HOST_URL_LINE | sed -E 's|https?://||' | cut -d'/' -f1 | cut -d':' -f1)
else
	# Legacy format: deb http://deb.debian.org/debian ...
	LINE=$(grep -v "^#" $SOURCES_FILE | head -1)
	HOST_URL_LINE=$(echo $LINE | awk '{print $2}')
	HOST=$(echo $HOST_URL_LINE | awk -F[/:] '{print $4}')
fi

if [[ -z "$HOST" ]]; then
	echo n
	exit 0
fi

HOP_COUNT=$(traceroute -n -w 1,1,1 $HOST | wc -l)
HOP_COUNT=$((HOP_COUNT -1))

if [[ $HOP_COUNT -le $ACCEPTABLE_HOPS ]]; then
	echo y
	exit 0
fi
echo n
exit 0

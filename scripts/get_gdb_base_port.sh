#!/bin/bash

# This script is used to get the base port for gdbserver

# get the sha1sum of the script

base_md5sum=$(md5sum "$0" | awk '{print $1}')
digits_only=$(echo $base_md5sum | tr -cd '0-9')

# extract the last 4 digits from md5sum

base_port=${digits_only: -4}
echo $base_port

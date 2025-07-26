#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

source ${TOPDIR}/.config
source ${TOPDIR}/scripts/lib.sh

echo "Creating $KDEVOPS_SSH_PRIVKEY"
ssh-keygen -t rsa -C generated-by-kdevops -f $KDEVOPS_SSH_PRIVKEY -q -N ""

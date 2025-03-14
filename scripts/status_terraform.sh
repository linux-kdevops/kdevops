#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

[ -z "${TOPDIR}" ] && TOPDIR='.'
source ${TOPDIR}/.config
source ${TOPDIR}/scripts/lib.sh

cd ${TOPDIR}/terraform/$1
terraform refresh > /dev/null
COUNT=`terraform state list | wc -l`
if [[ ${COUNT} -eq 1 ]]; then
  echo "There is 1 active terraform resource on '$1'."
else
  echo "There are ${COUNT} active terraform resources on '$1'."
fi
terraform output public_ip_map
exit 0

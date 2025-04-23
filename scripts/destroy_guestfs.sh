#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

[ -z "${TOPDIR}" ] && TOPDIR='.'
source ${TOPDIR}/.config
source ${TOPDIR}/scripts/lib.sh

export LIBVIRT_DEFAULT_URI=$CONFIG_LIBVIRT_URI

STORAGEDIR="${CONFIG_LIBVIRT_STORAGE_POOL_PATH}/${CONFIG_KDEVOPS_STORAGE_POOL_USER}/guestfs"
GUESTFSDIR="${TOPDIR}/guestfs"

if [ -f "$GUESTFSDIR/kdevops_nodes.yaml" ]; then
	# FIXME: is there a yaml equivalent to jq ?
	grep -e '^  - name: ' "${GUESTFSDIR}/kdevops_nodes.yaml"  | sed 's/^  - name: //' | while read name
	do
		domstate=$(virsh domstate $name 2>/dev/null)
		if [ $? -eq 0 ]; then
			if [ "$domstate" = 'running' ]; then
				virsh destroy $name
			fi
			virsh undefine --nvram $name
		fi
		rm -rf "$GUESTFSDIR/$name"
		rm -rf "$STORAGEDIR/$name"
		ssh-keygen -q -f ~/.ssh/known_hosts -R $name 1> /dev/null 2>&1
	done
fi

if [[ "$CONFIG_TOPDIR_PATH_HAS_SHA256SUM" == "y" ]]; then
	rm -f ~/.ssh/config_kdevops_$CONFIG_TOPDIR_PATH_SHA256SUM
else
	rm -f ~/.ssh/config_kdevops_$CONFIG_KDEVOPS_HOSTS_PREFIX
fi
rm -f $GUESTFSDIR/.provisioned_once
rm -f $GUESTFSDIR/kdevops_nodes.yaml

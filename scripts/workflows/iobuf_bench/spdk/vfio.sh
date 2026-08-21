#!/bin/bash
# vfio.sh -- safe VFIO bind/reset for the SPDK arm.
#
# SPDK's setup.sh binds NVMe controllers to vfio-pci. The danger is binding a
# drive your OS is using. This wrapper binds ONLY the BDFs you pass, and SPDK's
# setup.sh additionally refuses any drive with an active mount/md holder, so a
# root-mirror member can never be taken. Always pass FREE namespaces.
#
#   vfio.sh bind  <spdk_dir> "<bdf1> [<bdf2> ...]"    # bind, verify, or fail
#   vfio.sh reset <spdk_dir> "<bdf1> [<bdf2> ...]"    # rebind to nvme
set -eu
action=$1; SPDK=$2; BDFS=$3
ALLOW=$(IFS=" "; echo "$BDFS")

case "$action" in
bind)
	sudo PCI_ALLOWED="$ALLOW" HUGEMEM="$(( 4096 ))" "$SPDK/scripts/setup.sh" >/tmp/spdk_setup.log 2>&1
	# fail closed: every requested BDF must actually be on vfio-pci now
	for b in $BDFS; do
		drv=$(basename "$(readlink -f /sys/bus/pci/devices/$b/driver 2>/dev/null)" 2>/dev/null)
		if [ "$drv" != vfio-pci ]; then
			echo "vfio.sh: $b did NOT bind to vfio-pci (driver=$drv) -- aborting SPDK arm" >&2
			echo "  (a drive with a mount/md holder is refused by setup.sh -- pass only free namespaces)" >&2
			exit 1
		fi
	done
	echo "vfio.sh: bound [$ALLOW] to vfio-pci"
	;;
reset)
	sudo PCI_ALLOWED="$ALLOW" "$SPDK/scripts/setup.sh" reset >/tmp/spdk_reset.log 2>&1
	sleep 3
	echo "vfio.sh: reset [$ALLOW] back to the kernel nvme driver"
	;;
*)
	echo "usage: vfio.sh bind|reset <spdk_dir> \"<bdf...>\"" >&2; exit 2 ;;
esac

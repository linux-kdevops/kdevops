#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

[ -z "${TOPDIR}" ] && TOPDIR='.'
source ${TOPDIR}/.config
source ${TOPDIR}/scripts/lib.sh

export LIBVIRT_DEFAULT_URI=$CONFIG_LIBVIRT_URI

# We use the NVMe setting for virtio too (go figure), but IDE
# requires qcow2
#
IMG_FMT="qcow2"
if [ "${CONFIG_LIBVIRT_EXTRA_DRIVE_FORMAT_RAW}" = "y" ]; then
	IMG_FMT="raw"
fi
STORAGETOPDIR="${CONFIG_KDEVOPS_STORAGE_POOL_PATH}"
STORAGEDIR="${STORAGETOPDIR}/kdevops/guestfs"
QEMU_GROUP=$CONFIG_LIBVIRT_QEMU_GROUP
GUESTFSDIR="${TOPDIR}/guestfs"
OS_VERSION=${CONFIG_VIRT_BUILDER_OS_VERSION}
BASE_IMAGE_DIR="${STORAGEDIR}/base_images"
BASE_IMAGE="${BASE_IMAGE_DIR}/${OS_VERSION}.raw"

if id -nG "$(whoami)" | grep -qw "$QEMU_GROUP"; then
    echo "User $USER is part of the $QEMU_GROUP group."
else
    echo "Error: User $USER is not part of the $QEMU_GROUP group. Exiting..."
    echo "Fix this and come back and try again."
    exit 1
fi

build_custom_source()
{
	SOURCE_TMP=$(mktemp)
	cat <<_EOT >$SOURCE_TMP
[local]
uri=file:///${CUSTOM_INDEX}
proxy=off
_EOT
	sudo mv $SOURCE_TMP $CUSTOM_SOURCE
}

build_custom_index()
{
	cat <<_EOT >$CUSTOM_INDEX
[$OS_VERSION]
file=${OS_VERSION}.raw
_EOT
}

fetch_custom_image()
{
	wget --directory-prefix=$CUSTOM_IMAGE_DIR $CONFIG_GUESTFS_CUSTOM_RAW_IMAGE_URL
	if [[ $? -ne 0 ]]; then
		echo -e "Could not download:\n$CONFIG_GUESTFS_CUSTOM_RAW_IMAGE_URL"
		exit 1
	fi
}

check_custom_image()
{
	SHA512SUMS_FILE="$(basename $CONFIG_GUESTFS_CUSTOM_RAW_IMAGE_SHA512SUMS_URL)"
	CUSTOM_IMAGE_SHA512SUM="$CUSTOM_IMAGE_DIR/$SHA512SUMS_FILE"
	if [[ ! -f $CUSTOM_IMAGE_SHA512SUM ]]; then
		wget --directory-prefix=$CUSTOM_IMAGE_DIR $CONFIG_GUESTFS_CUSTOM_RAW_IMAGE_SHA512SUMS_URL
		if [[ $? -ne 0 ]]; then
			echo "Could not get sha512sum file: $CONFIG_GUESTFS_CUSTOM_RAW_IMAGE_SHA512SUMS_URL"
			exit 1
		fi
	fi
	echo "Checking $CUSTOM_IMAGE_DIR/$SHA512SUMS_FILE"

	# This subshell let's us keep below in the current directory.
	# sha512sum files are relative to the local directory
	(cd $CUSTOM_IMAGE_DIR && sha512sum --ignore-missing -c $SHA512SUMS_FILE)
	if [[ $? -ne 0 ]]; then
		echo "Invalid SHA512SUM checksum for $CUSTOM_IMAGE as per $SHA512SUMS_FILE"
		exit 1
	fi
	touch $CUSTOM_IMAGE_OK
}

# Ensure folks are not surprised. If you're using rolling distros you know what
# you are doing. This gives us the right later to change this at will.
#
# In the future we can make this smoother, as we used to have it with vagrant
# update, but for now downloading *once* for a rolling distro seems ok to start.
# We give enough information so you can update.
build_warn_rolling_distro()
{
	echo "------------------------------------------------------------------"
	echo "This is a rolling distribution release! To upgrade just do:"
	echo
	echo "rm -rf ${CUSTOM_IMAGE}/*"
	echo "rm -f  ${CUSTOM_SOURCE}"
	echo "rm -f  ${CUSTOM_INDEX}"
	echo
	echo "Running guests always use their own copy. To rebuild your custom"
	echo "base image from the custom image, also remove the base image:"
	echo
	echo "rm -f  ${BASE_IMAGE}"
	echo
	echo "This can always be done safely without affecting running guests."
	echo "------------------------------------------------------------------"
}

build_custom_image()
{
	CUSTOM_IMAGE_DIR="${STORAGEDIR}/custom_images/${OS_VERSION}"
	CUSTOM_IMAGE="${CUSTOM_IMAGE_DIR}/${OS_VERSION}.raw"
	CUSTOM_IMAGE_OK="${CUSTOM_IMAGE_DIR}.ok"
	CUSTOM_SOURCE="/etc/virt-builder/repos.d/kdevops-custom-images-${OS_VERSION}.conf"
	mkdir -p ${CUSTOM_IMAGE_DIR}
	CUSTOM_INDEX="$(realpath ${CUSTOM_IMAGE_DIR}/index)"

	if [[ ! -f $CUSTOM_IMAGE && "$CONFIG_GUESTFS_HAS_CUSTOM_RAW_IMAGE_URL" == "y" ]]; then
		fetch_custom_image
	fi

	if [[ ! -f $CUSTOM_IMAGE_OK && "$CONFIG_GUESTFS_HAS_CUSTOM_RAW_IMAGE_SHA512SUMS" == "y" ]]; then
		check_custom_image
	fi

	if [[ ! -f $CUSTOM_IMAGE ]]; then
		echo "Custom image on path $CUSTOM_IMAGE not found"
		exit 1
	fi

	if [[ ! -f $CUSTOM_SOURCE ]]; then
		build_custom_source
	fi

	if [[ ! -f $CUSTOM_INDEX ]]; then
		build_custom_index
	fi

	echo "Custom virt-builder source: $CUSTOM_SOURCE"
	echo "Custom virt-builder index:  $CUSTOM_INDEX"
	echo "Custom image source:        $CUSTOM_IMAGE"

	if [[ "$CONFIG_GUESTFS_HAS_CUSTOM_RAW_IMAGE_ROLLING" == "y" ]]; then
		build_warn_rolling_distro
	fi

	echo "Going to build index for $OS_VERSION ..."
	virt-builder-repository --no-compression $CUSTOM_IMAGE_DIR
	if [[ $? -ne 0 ]]; then
		echo "Failed to build repository ..."
		exit 1
	fi

	# Note, we don't build $BASE_IMAGE, virt-builder does that later. We
	# just build $virt-builder, which is the pristine upstream image.
}

handle_rhel_activation()
{
	if [ -n "$CONFIG_RHEL_ORG_ID" -a -n "$CONFIG_RHEL_ACTIVATION_KEY" ]; then
		DO_UNREG=1
		cat <<_EOT >>$cmdfile
run-command subscription-manager register --org=${CONFIG_RHEL_ORG_ID} --activationkey=${CONFIG_RHEL_ACTIVATION_KEY}
_EOT
	fi
}

handle_rhel_unreg()
{
	cat <<_EOT >>$cmdfile
sm-unregister
_EOT
}

copy_yum_repo()
{
	cat <<_EOT >>$cmdfile
copy-in $CONFIG_KDEVOPS_CUSTOM_YUM_REPOFILE:/etc/yum.repos.d
_EOT
}

copy_host_sources()
{
	TARGET_DIR="$(dirname $CONFIG_GUESTFS_DISTRO_SOURCE_AND_DEST_FILE)"
	cat <<_EOT >>$cmdfile
mkdir $TARGET_DIR
copy-in $CONFIG_GUESTFS_DISTRO_SOURCE_AND_DEST_FILE:$TARGET_DIR
_EOT
}

pre_install_customizations()
{
	KDEVOPS_UID=""
	id -u kdevops > /dev/null 2>&1
	if [ $? -eq 0 ]; then
		KDEVOPS_UID="-u `id -u kdevops`"
	fi
	if echo $OS_VERSION | grep -qE "^(rhel|fedora|centos)"; then
		UPDATE_GRUB_CMD="/usr/sbin/grub2-mkconfig -o /boot/grub2/grub.cfg"
	else
		UPDATE_GRUB_CMD="/usr/sbin/update-grub2"
	fi
	cat <<_EOT >>$cmdfile
install sudo,qemu-guest-agent,python3,bash
run-command useradd ${KDEVOPS_UID} -s /bin/bash -m kdevops
append-line /etc/sudoers.d/kdevops:kdevops   ALL=(ALL)       NOPASSWD: ALL
edit /etc/default/grub:s/^GRUB_CMDLINE_LINUX_DEFAULT=.*/GRUB_CMDLINE_LINUX_DEFAULT="console=ttyS0"/
run-command $UPDATE_GRUB_CMD
root-password password:kdevops
_EOT
}

# Ugh, debian has to be told to bring up the network and regenerate ssh keys
# Hope we get that interface name right!
debian_pre_install_hacks()
{
	cat <<_EOT >>$cmdfile
install isc-dhcp-client,ifupdown
mkdir /etc/network/interfaces.d/
append-line /etc/network/interfaces.d/enp1s0:auto enp1s0
append-line /etc/network/interfaces.d/enp1s0:allow-hotplug enp1s0
append-line /etc/network/interfaces.d/enp1s0:iface enp1s0 inet dhcp
firstboot-command systemctl stop ssh
firstboot-command DEBIAN_FRONTEND=noninteractive DEBCONF_NONINTERACTIVE_SEEN=true dpkg-reconfigure -p low --force openssh-server
firstboot-command systemctl start ssh
firstboot-command apt update && apt upgrade --yes
_EOT
	# CONFIG_GUESTFS_COPY_SOURCES_FROM_HOST_TO_GUEST will not work
	# if /etc/nsswitch.conf has a line like this:
	#
	# hosts:          files myhostname resolve [!UNAVAIL=return] dns
	#
	# We need DNS to be used so virb0 will be used for a DNS request
	# For the life of me I can't get the following line to work with
	# the virt-builder command and so we do a full edit of the file for now
	# edit /etc/nsswitch.conf:'s/\[!UNAVAIL=return\]//'
	if [[ "$CONFIG_GUESTFS_DEBIAN_TRIXIE" == "y" ]]; then
		cat <<_EOT >>$cmdfile
write /etc/nsswitch.conf: # kdevops generated /etc/nsswitch.conf
append-line /etc/nsswitch.conf:passwd:         files
append-line /etc/nsswitch.conf:group:          files
append-line /etc/nsswitch.conf:shadow:         files
append-line /etc/nsswitch.conf:gshadow:        files
append-line /etc/nsswitch.conf:hosts:          files myhostname resolve dns
append-line /etc/nsswitch.conf:networks:       files
append-line /etc/nsswitch.conf:protocols:      db files
append-line /etc/nsswitch.conf:services:       db files
append-line /etc/nsswitch.conf:ethers:         db files
append-line /etc/nsswitch.conf:rpc:            db files
append-line /etc/nsswitch.conf:netgroup:       nis
uninstall cloud-init
write /etc/default/locale:LANG=en_US.UTF-8
append-line /etc/default/locale:LANGUAGE=en_US:en
write /etc/locale.gen:en_US.UTF-8 UTF-8
firstboot-command locale-gen en_US.UTF-8
firstboot-command update-locale LANG=en_US.UTF-8
firstboot-command DEBIAN_FRONTEND=noninteractive DEBCONF_NONINTERACTIVE_SEEN=true dpkg-reconfigure -p low --force locales
firstboot-command systemctl stop ssh
firstboot-command systemctl start ssh
_EOT
		if [[ "$CONFIG_GUESTFS_COPY_SOURCES_FROM_HOST_TO_GUEST" == "y" ]]; then
		cat <<_EOT >>$cmdfile
delete /etc/apt/sources.list.d/debian.sources
_EOT
		fi
	fi
}

USE_SUDO=""
if [[ "$CONFIG_LIBVIRT_URI_SYSTEM" == "y" ]]; then
	USE_SUDO="sudo "
fi

$USE_SUDO mkdir -p $STORAGEDIR
$USE_SUDO mkdir -p $BASE_IMAGE_DIR


if [[ "$CONFIG_LIBVIRT_URI_SYSTEM" == "y" ]]; then
	sudo chown -R $(whoami):$QEMU_GROUP $STORAGETOPDIR
	sudo chmod -R g+rw $STORAGETOPDIR
	sudo chmod -R g+s $STORAGETOPDIR
fi

cmdfile=$(mktemp)

if [ ! -f $BASE_IMAGE ]; then
	if [[ "$CONFIG_GUESTFS_HAS_CUSTOM_RAW_IMAGE" == "y" ]]; then
		build_custom_image
	fi

	DO_UNREG=0
	if echo $OS_VERSION | grep -q '^rhel'; then
		handle_rhel_activation
	fi

	if [ -n "$CONFIG_KDEVOPS_CUSTOM_YUM_REPOFILE" ]; then
		copy_yum_repo
	fi

	if [[ "$CONFIG_GUESTFS_COPY_SOURCES_FROM_HOST_TO_GUEST" == "y" ]]; then
		copy_host_sources
	fi

	pre_install_customizations

	if [ $DO_UNREG -ne 0 ]; then
		handle_rhel_unreg
	fi

	if echo $OS_VERSION | grep -q '^debian'; then
		debian_pre_install_hacks
	fi

	echo "Generating new base image for ${OS_VERSION}"
	$USE_SUDO virt-builder ${OS_VERSION} --arch `uname -m` -o $BASE_IMAGE --size 20G --format raw --commands-from-file $cmdfile
	if [[ $? -ne 0 ]]; then
		echo "Failed to build custom image $BASE_IMAGE"
		exit 1
	fi
fi

# FIXME: is there a yaml equivalent of jq?
grep -e '^  - name: ' ${TOPDIR}/guestfs/kdevops_nodes.yaml | sed 's/^  - name: //' | while read name
do
	#
	# If the guest is already defined, then just stop what we're doing
	# and plead to the developer to clean things up.
	#
	virsh domstate $name 1>/dev/null 2>&1
	if [ $? -eq 0 ]; then
		echo "Domain $name is already defined."
		virsh start $name
		exit 0
	fi

	SSH_KEY_DIR="${GUESTFSDIR}/$name/ssh"
	SSH_KEY="${SSH_KEY_DIR}/id_ed25519"

	# Generate a new ssh key
	mkdir -p "$SSH_KEY_DIR"
	chmod 0700 "$SSH_KEY_DIR"
	rm -f $SSH_KEY $SSH_KEY.pub
	ssh-keygen -q -t ed25519 -f $SSH_KEY -N ""

	mkdir -p "$STORAGEDIR/$name"

	# Copy the base image and prep it
	ROOTIMG="$STORAGEDIR/$name/root.raw"
	cp --reflink=auto $BASE_IMAGE $ROOTIMG
	TZ="$(timedatectl show -p Timezone --value)"
	$USE_SUDO virt-sysprep -a $ROOTIMG --hostname $name --ssh-inject "kdevops:file:$SSH_KEY.pub" --timezone $TZ

	if [[ "$CONFIG_LIBVIRT_ENABLE_LARGEIO" == "y" ]]; then
		lbs_idx=0
		for i in $(seq 1 $(($CONFIG_QEMU_LARGEIO_MAX_POW_LIMIT+1))); do
			for x in $(seq 0 $CONFIG_QEMU_EXTRA_DRIVE_LARGEIO_NUM_DRIVES_PER_SPACE); do
				diskimg="$STORAGEDIR/$name/extra${lbs_idx}.${IMG_FMT}"
				rm -f $diskimg
				qemu-img create -f $IMG_FMT "$diskimg" 100G
				if [[ "$CONFIG_LIBVIRT_URI_SYSTEM" == "y" ]]; then
					chmod g+rw $diskimg
				fi
				let lbs_idx=$lbs_idx+1
			done
		done
	else
		# build some extra disks
		for i in $(seq 0 3); do
			diskimg="$STORAGEDIR/$name/extra${i}.${IMG_FMT}"
			rm -f $diskimg
			qemu-img create -f $IMG_FMT "$STORAGEDIR/$name/extra${i}.$IMG_FMT" 100G
			if [[ "$CONFIG_LIBVIRT_URI_SYSTEM" == "y" ]]; then
				chmod g+rw $STORAGEDIR/$name/extra${i}.$IMG_FMT
			fi
		done
	fi

	virsh define $GUESTFSDIR/$name/$name.xml
	XML_DEVICES_COUNT=$(find $GUESTFSDIR/$name/ -name pcie_passthrough_*.xml | wc -l)
	if [[ $XML_DEVICES_COUNT -gt 0 ]]; then
		for xml in $GUESTFSDIR/$name/pcie_passthrough_*.xml; do
			echo "Doing PCI-E passthrough for device $xml"
			virsh attach-device $name $xml --config
		done
	fi
	virsh start $name
	if [[ $? -ne 0 ]]; then
		echo "Failed to start $name"
		exit 1
	fi
done

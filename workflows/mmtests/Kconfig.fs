config MMTESTS_REQUIRES_MKFS_DEVICE
	bool
	output yaml

choice
	prompt "Filesystem configuration to use"
	default MMTESTS_FS_XFS
	help
	  The target type of filesystem test to use or none.

config MMTESTS_FS_SKIP
	bool "Skip - don't use a filesystem"
	output yaml
	help
	  Disable filesystem testing.

config MMTESTS_FS_XFS
	bool "XFS"
	output yaml
	select MMTESTS_REQUIRES_MKFS_DEVICE
	help
	  Enable if you want to test mmtests against XFS.

config MMTESTS_FS_EXT4
	bool "ext4"
	output yaml
	select MMTESTS_REQUIRES_MKFS_DEVICE
	help
	  Enable if you want to test mmtests against ext4.

endchoice

if MMTESTS_REQUIRES_MKFS_DEVICE

source "workflows/mmtests/Kconfig.xfs"
source "workflows/mmtests/Kconfig.ext4"

config MMTESTS_MKFS_TYPE
	string
	output yaml
	default "xfs" if MMTESTS_FS_XFS
	default "ext4" if MMTESTS_FS_EXT4

config MMTESTS_MKFS_CMD
	string "mkfs command to use"
	output yaml
	default MMTESTS_XFS_CMD if MMTESTS_FS_XFS
	default MMTESTS_EXT4_CMD if MMTESTS_FS_EXT4
	help
	  The filesystem mkfs configuration command to run

config MMTESTS_DEVICE
	string "Device to use to create a filesystem for sysbench tests"
	output yaml
	default "/dev/disk/by-id/nvme-QEMU_NVMe_Ctrl_kdevops1" if LIBVIRT && LIBVIRT_EXTRA_STORAGE_DRIVE_NVME
	default "/dev/disk/by-id/virtio-kdevops1" if LIBVIRT && LIBVIRT_EXTRA_STORAGE_DRIVE_VIRTIO
	default "/dev/disk/by-id/ata-QEMU_HARDDISK_kdevops1" if LIBVIRT && LIBVIRT_EXTRA_STORAGE_DRIVE_IDE
	default "/dev/nvme2n1" if TERRAFORM_AWS_INSTANCE_M5AD_2XLARGE
	default "/dev/nvme2n1" if TERRAFORM_AWS_INSTANCE_M5AD_4XLARGE
	default "/dev/nvme1n1" if TERRAFORM_GCE
	default "/dev/sdd" if TERRAFORM_AZURE
	default TERRAFORM_OCI_SPARSE_VOLUME_DEVICE_FILE_NAME if TERRAFORM_OCI
	help
	  The device to use to create a filesystem where we will place the
	  database.

config MMTESTS_LABEL
	string "The label to use"
	output yaml
	default "mmtests"
	help
	  The label to use when creating the filesystem.

config MMTESTS_MNT
	string "Mount point for the database"
	output yaml
	default "/mmtests-test"
	help
	  The path where to mount the filesystem testing.

endif

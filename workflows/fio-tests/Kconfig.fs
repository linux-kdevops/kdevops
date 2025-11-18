config FIO_TESTS_REQUIRES_MKFS_DEVICE
	bool
	output yaml

choice
	prompt "Filesystem configuration to use"
	default FIO_TESTS_FS_XFS

config FIO_TESTS_FS_SKIP
	bool "Skip - don't use a filesystem"
	output yaml
	help
	  Disable filesystem testing and use direct block device access.

config FIO_TESTS_FS_XFS
	bool "XFS"
	output yaml
	select FIO_TESTS_REQUIRES_MKFS_DEVICE
	help
	  Enable if you want to test fio against XFS filesystem.
	  XFS is a high-performance journaling filesystem with
	  excellent scalability and large file support.

config FIO_TESTS_FS_EXT4
	bool "ext4"
	output yaml
	select FIO_TESTS_REQUIRES_MKFS_DEVICE
	help
	  Enable if you want to test fio against ext4 filesystem.
	  ext4 is the fourth extended filesystem, commonly used
	  as the default on many Linux distributions.

config FIO_TESTS_FS_BTRFS
	bool "btrfs"
	output yaml
	select FIO_TESTS_REQUIRES_MKFS_DEVICE
	help
	  Enable if you want to test fio against btrfs filesystem.
	  Btrfs is a modern copy-on-write filesystem with advanced
	  features like snapshots, compression, and checksums.

endchoice

if FIO_TESTS_REQUIRES_MKFS_DEVICE

source "workflows/fio-tests/Kconfig.xfs"
source "workflows/fio-tests/Kconfig.ext4"
source "workflows/fio-tests/Kconfig.btrfs"

config FIO_TESTS_MKFS_TYPE
	string
	output yaml
	default "xfs" if FIO_TESTS_FS_XFS
	default "ext4" if FIO_TESTS_FS_EXT4
	default "btrfs" if FIO_TESTS_FS_BTRFS

config FIO_TESTS_MKFS_CMD
	string "mkfs command to use"
	output yaml
	default FIO_TESTS_XFS_CMD if FIO_TESTS_FS_XFS
	default FIO_TESTS_EXT4_CMD if FIO_TESTS_FS_EXT4
	default FIO_TESTS_BTRFS_CMD if FIO_TESTS_FS_BTRFS
	help
	  The filesystem mkfs configuration command to run

config FIO_TESTS_MOUNT_OPTS
	string "Mount options"
	output yaml
	default FIO_TESTS_XFS_MOUNT_OPTS if FIO_TESTS_FS_XFS
	default FIO_TESTS_EXT4_MOUNT_OPTS if FIO_TESTS_FS_EXT4
	default FIO_TESTS_BTRFS_MOUNT_OPTS if FIO_TESTS_FS_BTRFS
	help
	  The mount options to use when mounting the filesystem

endif # FIO_TESTS_REQUIRES_MKFS_DEVICE

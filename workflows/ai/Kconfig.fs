menu "Target filesystem to use"

choice
	prompt "Target filesystem"
	default AI_FILESYSTEM_XFS

config AI_FILESYSTEM_XFS
	bool "xfs"
	select HAVE_SUPPORTS_PURE_IOMAP if BOOTLINUX_TREE_LINUS || BOOTLINUX_TREE_STABLE
	help
	  This will target testing AI workloads on top of XFS.
	  XFS provides excellent performance for large datasets
	  and is commonly used in high-performance computing.

config AI_FILESYSTEM_BTRFS
	bool "btrfs"
	help
	  This will target testing AI workloads on top of btrfs.
	  Btrfs provides features like snapshots and compression
	  which can be useful for AI dataset management.

config AI_FILESYSTEM_EXT4
	bool "ext4"
	help
	  This will target testing AI workloads on top of ext4.
	  Ext4 is widely supported and provides reliable performance
	  for AI workloads.

endchoice

config AI_FILESYSTEM
	string
	output yaml
	default "xfs" if AI_FILESYSTEM_XFS
	default "btrfs" if AI_FILESYSTEM_BTRFS
	default "ext4" if AI_FILESYSTEM_EXT4

config AI_FSTYPE
	string
	output yaml
	default "xfs" if AI_FILESYSTEM_XFS
	default "btrfs" if AI_FILESYSTEM_BTRFS
	default "ext4" if AI_FILESYSTEM_EXT4

if AI_FILESYSTEM_XFS

menu "XFS configuration"

config AI_XFS_MKFS_OPTS
	string "mkfs.xfs options"
	output yaml
	default "-f -s size=4096"
	help
	  Additional options to pass to mkfs.xfs when creating
	  the filesystem for AI workloads.

config AI_XFS_MOUNT_OPTS
	string "XFS mount options"
	output yaml
	default "rw,relatime,attr2,inode64,logbufs=8,logbsize=32k,noquota"
	help
	  Mount options for XFS filesystem. These options are
	  optimized for AI workloads with large sequential I/O.

endmenu

endif # AI_FILESYSTEM_XFS

if AI_FILESYSTEM_BTRFS

menu "Btrfs configuration"

config AI_BTRFS_MKFS_OPTS
	string "mkfs.btrfs options"
	output yaml
	default "-f"
	help
	  Additional options to pass to mkfs.btrfs when creating
	  the filesystem for AI workloads.

config AI_BTRFS_MOUNT_OPTS
	string "Btrfs mount options"
	output yaml
	default "rw,relatime,compress=lz4,space_cache=v2"
	help
	  Mount options for Btrfs filesystem. LZ4 compression
	  can help with AI datasets while maintaining performance.

endmenu

endif # AI_FILESYSTEM_BTRFS

if AI_FILESYSTEM_EXT4

menu "Ext4 configuration"

config AI_EXT4_MKFS_OPTS
	string "mkfs.ext4 options"
	output yaml
	default "-F"
	help
	  Additional options to pass to mkfs.ext4 when creating
	  the filesystem for AI workloads.

config AI_EXT4_MOUNT_OPTS
	string "Ext4 mount options"
	output yaml
	default "rw,relatime,data=ordered"
	help
	  Mount options for Ext4 filesystem optimized for
	  AI workload patterns.

endmenu

endif # AI_FILESYSTEM_EXT4


endmenu

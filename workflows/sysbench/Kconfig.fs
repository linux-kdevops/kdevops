choice
	prompt "What type of sysbench target test do you want to run?"
	default SYSBENCH_TEST_ATOMICS

config SYSBENCH_TEST_ATOMICS
	bool "Large atomic write test"
	output yaml
	select KDEVOPS_BASELINE_AND_DEV
	help
	  This type of test is aimed of testing the empirical value of support
	  for large atomics on storage devices and its impact on databases.
	  Most drives today support only power-fail safe guarantees when writing
	  up to 4 KiB. Drives which support 16 KiB atomic writes or larger can
	  take advanage of software features in databases which typically
	  do software work arounds to guarantee writes above 4 KiB will be
	  recoverable in case of power failure.

	  Different database have different features one can disable if one has
	  support for an atomic matching the configured database page size. Below
	  we list the features which an be disabled:

	    * MySQL:
		- innodb_doublewrite
	    * PostgreSQL:
		- full_page_writes

	  In order to test disabling these features we need A/B testing for
	  each target filesystem configuration we want to support testing.
	  kdevops supports A/B testing with KDEVOPS_BASELINE_AND_DEV which
	  creates an extra "dev" node for each target test we want. In the
	  case of filesystem testing we thereore will end up with two nodes
	  for each filesystem we want to test.

	  Configurations for sysbench can vary depending on the target system.
	  A sensible baseline configuration is selected depending on the type
	  of bringup you configure with kdevops. Each type of virtualization,
	  and cloud setup can have its own configuration database and / or
	  sysbench configuration.

endchoice

if SYSBENCH_TEST_ATOMICS

choice
	prompt "What type of atomic test do you want to run?"
	default SYSBENCH_TEST_ATOMICS_TPS_VARIABILITY

config SYSBENCH_TEST_ATOMICS_TPS_VARIABILITY
	bool "TPS variability test"
	output yaml
	select KDEVOPS_BASELINE_AND_DEV
	help
	  This test is designed to verify the TPS variabilility over long
	  periods of time on a database when atomics are enabled.

endchoice

choice
	prompt "When do you want to disable innodb_doublewrite?"
	default SYSBENCH_DISABLE_DOUBLEWRITE_AUTO

config SYSBENCH_DISABLE_DOUBLEWRITE_AUTO
	bool "Use hostname postfix"
	output yaml
	help
	  To allow for A/B testing this option will only disable the
	  innodb_doublewrite on nodes which have a hostname which end
	  with "-dev".

config SYSBENCH_DISABLE_DOUBLEWRITE_ALWAYS
	bool "Disable it always"
	output yaml
	help
	  If you don't want to spawn nodes to do A/B testing and just want
	  to test disabling the innodb_doublewrite enable this.

endchoice

config SYSBENCH_TEST_ATOMICS_XFS_16K_4KS_LBS
	bool "XFS 16k LBS - 4k sector size"
	select SYSBENCH_FS_XFS
	select SYSBENCH_XFS_SECTOR_SIZE_4K
	select SYSBENCH_XFS_SECTION_REFLINK_16K
	output yaml
	help
	  This enables the XFS filesystem configuration to test 16k atomics
	  with LBS.

config SYSBENCH_TEST_ATOMICS_XFS_32K_4KS_LBS
	bool "XFS 32k LBS - 4k sector size"
	select SYSBENCH_FS_XFS
	select SYSBENCH_XFS_SECTOR_SIZE_4K
	select SYSBENCH_XFS_SECTION_REFLINK_32K
	output yaml
	help
	  This enables the XFS filesystem configuration to test 32k atomics
	  with LBS.

config SYSBENCH_TEST_ATOMICS_XFS_64K_4KS_LBS
	bool "XFS 64k LBS - 4k sector size"
	select SYSBENCH_FS_XFS
	select SYSBENCH_XFS_SECTOR_SIZE_4K
	select SYSBENCH_XFS_SECTION_REFLINK_64K
	output yaml
	help
	  This enables the XFS filesystem configuration to test 64k atomics
	  with LBS.

config SYSBENCH_TEST_ATOMICS_EXT4_4K_4KS_BIGALLOC_16K
	bool "ext4 4k block size bigalloc 16k cluster sizes -  4k sector size"
	select SYSBENCH_FS_EXT4
	select SYSBENCH_EXT4_SECTOR_SIZE_4K
	select SYSBENCH_EXT4_SECTION_4K_BIGALLOC_16K
	output yaml
	help
	  This enables the ext4 filesystem configuration to test 16k atomics
	  with a 4 KiB data and sector size and the bigalloc feature with 16k
	  cluster sizes.

config SYSBENCH_TEST_ATOMICS_EXT4_4K_4KS_BIGALLOC_32K
	bool "ext4 4k block size bigalloc 32k cluster sizes -  4k sector size"
	select SYSBENCH_FS_EXT4
	select SYSBENCH_EXT4_SECTOR_SIZE_4K
	select SYSBENCH_EXT4_SECTION_4K_BIGALLOC_32K
	output yaml
	help
	  This enables the ext4 filesystem configuration to test 32k atomics
	  with a 4 KiB data and sector size and the bigalloc feature with 32k
	  cluster sizes.

config SYSBENCH_TEST_ATOMICS_EXT4_4K_4KS_BIGALLOC_64K
	bool "ext4 4k block size bigalloc 64k cluster sizes -  4k sector size"
	select SYSBENCH_FS_EXT4
	select SYSBENCH_EXT4_SECTOR_SIZE_4K
	select SYSBENCH_EXT4_SECTION_4K_BIGALLOC_64K
	output yaml
	help
	  This enables the ext4 filesystem configuration to test 32k atomics
	  with a 4 KiB data and sector size and the bigalloc feature with 32k
	  cluster sizes.

endif # SYSBENCH_TEST_ATOMICS

config SYSBENCH_DEVICE
	string "Device to use to create a filesystem for sysbench tests"
	output yaml
	default "/dev/disk/by-id/nvme-QEMU_NVMe_Ctrl_kdevops1" if LIBVIRT && LIBVIRT_EXTRA_STORAGE_DRIVE_NVME
	default "/dev/disk/by-id/virtio-kdevops1" if LIBVIRT && LIBVIRT_EXTRA_STORAGE_DRIVE_VIRTIO
	default "/dev/disk/by-id/ata-QEMU_HARDDISK_kdevops1" if LIBVIRT && LIBVIRT_EXTRA_STORAGE_DRIVE_IDE
	default "/dev/nvme2n1" if TERRAFORM_AWS_INSTANCE_M5AD_4XLARGE
	default "/dev/nvme1n1" if TERRAFORM_GCE
	default "/dev/sdd" if TERRAFORM_AZURE
	default TERRAFORM_OCI_SPARSE_VOLUME_DEVICE_FILE_NAME if TERRAFORM_OCI
	help
	  The device to use to create a filesystem where we will place the
	  database.

config SYSBENCH_LABEL
	string "The label to use"
	output yaml
	default "sysbench_db"
	help
	  The label to use when creating the filesystem.

config SYSBENCH_MNT
	string "Mount point for the database"
	output yaml
	default "/db"
	help
	  The path where to mount the filesystem we'll use for the database.

source "workflows/sysbench/Kconfig.xfs"
source "workflows/sysbench/Kconfig.ext4"

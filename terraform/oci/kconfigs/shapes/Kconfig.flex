choice
	prompt "OCI shape"
	default TERRAFORM_OCI_SHAPE_VM_STANDARD3_FLEX
	help
	  Select the basic hardware capabilities that are in each
	  instance. For more detail, see:

	  https://docs.oracle.com/en-us/iaas/Content/Compute/References/computeshapes.htm#flexible

config TERRAFORM_OCI_SHAPE_VM_STANDARD3_FLEX
	bool "VM.Standard3.Flex"
	depends on TARGET_ARCH_X86_64
	help
	  Selecting this option provisions each guest with between 1
	  and 32 OCPUs (physical cores) and up to 512MB of memory.

config TERRAFORM_OCI_SHAPE_VM_STANDARD_E4_FLEX
	bool "VM.Standard.E4.Flex"
	depends on TARGET_ARCH_X86_64
	help
	  Selecting this option provisions each guest with between 1
	  and 114 OCPUs (physical AMD cores) and up to 1760MB of memory.

config TERRAFORM_OCI_SHAPE_VM_STANDARD_E5_FLEX
	bool "VM.Standard.E5.Flex"
	depends on TARGET_ARCH_X86_64
	help
	  Selecting this option provisions each guest with between 1
	  and 94 OCPUs (physical AMD cores) and up to 1048MB of memory.

config TERRAFORM_OCI_SHAPE_VM_STANDARD_A1_FLEX
	bool "VM.Standard.A1.Flex"
	depends on TARGET_ARCH_ARM64
	help
	  Selecting this option provisions each guest with between 1
	  and 80 OCPUs (physical ARM cores) and up to 512MB of memory.

config TERRAFORM_OCI_SHAPE_VM_STANDARD_A2_FLEX
	bool "VM.Standard.A2.Flex"
	depends on TARGET_ARCH_ARM64
	help
	  Selecting this option provisions each guest with between 1
	  and 78 OCPUs (physical ARM cores) and up to 946MB of memory.

config TERRAFORM_OCI_SHAPE_VM_DENSEIO_E4_FLEX
	bool "VM.DenseIO.E4.Flex"
	depends on TARGET_ARCH_X86_64
	help
	  Selecting this option provisions each instance with either
	  8 OCPUs and 128 GB memory, 16 OCPUs and 256 GB memory, or
	  32 OCPUs and 512 GB memory. CPUs are based on the AMD
	  x86_64 platform.

config TERRAFORM_OCI_SHAPE_VM_OPTIMIZED3_FLEX
	bool "VM.Optimized3.Flex"
	depends on TARGET_ARCH_X86_64
	help
	  Selecting this option provisions each instance with up to
	  18 OCPUS. The memory provisioned for each instance is
	  typically matches a multiple of the number of OCPUS.

endchoice

config TERRAFORM_OCI_SHAPE
	string
	output yaml
	default "VM.Standard3.Flex" if TERRAFORM_OCI_SHAPE_VM_STANDARD3_FLEX
	default "VM.Standard.E4.Flex" if TERRAFORM_OCI_SHAPE_VM_STANDARD_E4_FLEX
	default "VM.Standard.E5.Flex" if TERRAFORM_OCI_SHAPE_VM_STANDARD_E5_FLEX
	default "VM.Standard.A1.Flex" if TERRAFORM_OCI_SHAPE_VM_STANDARD_A1_FLEX
	default "VM.Standard.A2.Flex" if TERRAFORM_OCI_SHAPE_VM_STANDARD_A2_FLEX
	default "VM.DenseIO.E4.Flex" if TERRAFORM_OCI_SHAPE_VM_DENSEIO_E4_FLEX
	default "VM.Optimized3.Flex" if TERRAFORM_OCI_SHAPE_VM_OPTIMIZED3_FLEX

config TERRAFORM_OCI_INSTANCE_FLEX_OCPUS
	int "Number of flexible instance OCPUs"
	default 2
	help
	  The number of OCPUs to use per flexible instance.

config TERRAFORM_OCI_INSTANCE_FLEX_MEMORY_IN_GBS
	int "How much RAM to use per flexible instance in GB"
	default 4
	help
	  How much GiB of RAM to use per flexible instance.

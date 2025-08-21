# SPDX-License-Identifier: copyleft-next-0.3.1

WORKFLOW_ARGS           :=
WORKFLOW_ARGS_SEPARATED	:=

include workflows/common/Makefile

BOOTLINUX_ARGS	:=
ifeq (y,$(CONFIG_BOOTLINUX))
WORKFLOW_ARGS += kdevops_bootlinux='True'
include workflows/linux/Makefile
endif # CONFIG_BOOTLINUX == y
ifeq (,$(CONFIG_BOOTLINUX))
WORKFLOW_ARGS += kdevops_bootlinux='False'
endif

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_FSTESTS))
include workflows/fstests/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_FSTESTS == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_BLKTESTS))
include workflows/blktests/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_BLKTESTS == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_CXL))
include workflows/cxl/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_CXL == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_PYNFS))
include workflows/pynfs/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_PYNFS == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_SELFTESTS))
include workflows/selftests/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_SELFTESTS

ifeq (y,$(CONFIG_WORKFLOWS_REBOOT_LIMIT))
include workflows/demos/reboot-limit/Makefile
endif # CONFIG_WORKFLOWS_REBOOT_LIMIT == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_GITR))
include workflows/gitr/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_GITR == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_LTP))
include workflows/ltp/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_LTP == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_NFSTEST))
include workflows/nfstest/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_NFSTEST == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_SYSBENCH))
include workflows/sysbench/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_SYSBENCH == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_MMTESTS))
include workflows/mmtests/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_MMTESTS == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_SSD_STEADY_STATE))
include workflows/steady_state/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_SSD_STEADY_STATE == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_FIO_TESTS))
include workflows/fio-tests/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_FIO_TESTS == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_AI))
include workflows/ai/Makefile
endif # CONFIG_KDEVOPS_WORKFLOW_ENABLE_AI == y

ANSIBLE_EXTRA_ARGS += $(WORKFLOW_ARGS)
ANSIBLE_EXTRA_ARGS_SEPARATED += $(WORKFLOW_ARGS_SEPARATED)
ANSIBLE_EXTRA_ARGS_DIRECT += $(WORKFLOW_ARGS_DIRECT)

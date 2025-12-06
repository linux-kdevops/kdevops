# SPDX-License-Identifier: copyleft-next-0.3.1
#
# User-private Makefile for kdevops workflows
#
# This file is included by kdevops when KDEVOPS_USER_CONFIG_ENABLE=y
# and placed at ~/.config/kdevops/Makefile
#
# Include your workflow Makefiles here:

USER_CONFIG_DIR := $(CONFIG_KDEVOPS_USER_CONFIG_DIR_EXPANDED)

ifeq (y,$(CONFIG_KDEVOPS_USER_WORKFLOW_KNLP))
include $(USER_CONFIG_DIR)/workflows/knlp/Makefile
endif

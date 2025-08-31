# SPDX-License-Identifier: copyleft-next-0.3.1

DYNAMIC_KCONFIG :=
DYNAMIC_KCONFIG_PCIE_ARGS :=

HELP_TARGETS += dynamic-kconfig-help

include $(TOPDIR)/scripts/dynamic-pci-kconfig.Makefile
include $(TOPDIR)/scripts/dynamic-cloud-kconfig.Makefile

ANSIBLE_EXTRA_ARGS += $(DYNAMIC_KCONFIG_PCIE_ARGS)

Kconfig: _refs-default $(DYNAMIC_KCONFIG)

dynamic-kconfig-help:
	@echo "Dynamic kconfig targets:"
	@echo "dynconfig          - enables all dynamically generated kconfig content"

PHONY += dynamic-kconfig-help

dynconfig:
	$(Q)$(MAKE) dynconfig-pci
	$(Q)$(MAKE) cloud-config

PHONY += dynconfig

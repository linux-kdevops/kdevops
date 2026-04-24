# SPDX-License-Identifier: copyleft-next-0.3.1

firstconfig:
	$(Q)ansible-playbook \
		--extra-vars '{ kdevops_cli_install: True }' \
		--tags vars_simple,firstconfig \
		$(KDEVOPS_PLAYBOOKS_DIR)/devconfig.yml

# firstconfig runs devconfig.yml with a tag subset that only touches
# distro package managers; on the imageless NixOS guest every task
# either skips (non-Debian branches) or has nothing to do (empty
# package list). Skip it on the qsu path for the same reason
# update_etc_hosts and the main devconfig are skipped.
ifneq (y,$(CONFIG_QEMU_SYSTEM_UNITS))
KDEVOPS_BRING_UP_DEPS_EARLY += firstconfig
endif

firstconfig-help:
	@echo "firstconfig    - Setup firstconfig"

HELP_TARGETS += firstconfig-help

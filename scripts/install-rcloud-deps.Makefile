# SPDX-License-Identifier: copyleft-next-0.3.1

rcloud-deps:
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/install-rcloud-deps.yml \
		-e 'kdevops_first_run=True'
PHONY += rcloud-deps

ifeq (y,$(CONFIG_RCLOUD))
ifeq (y,$(CONFIG_KDEVOPS_FIRST_RUN))
LOCALHOST_SETUP_WORK += rcloud-deps
endif # CONFIG_KDEVOPS_FIRST_RUN
endif # CONFIG_RCLOUD

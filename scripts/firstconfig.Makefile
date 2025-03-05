# SPDX-License-Identifier: copyleft-next-0.3.1

firstconfig:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) -l baseline,dev \
		-f 30 -i hosts  \
		--extra-vars '{ kdevops_cli_install: True }' \
		--tags vars_simple,firstconfig \
		$(KDEVOPS_PLAYBOOKS_DIR)/devconfig.yml

KDEVOPS_BRING_UP_DEPS_EARLY += firstconfig

firstconfig-help:
	@echo "firstconfig    - Setup firstconfig"

HELP_TARGETS += firstconfig-help

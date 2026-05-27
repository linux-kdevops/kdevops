# SPDX-License-Identifier: copyleft-next-0.3.1
#
# User-private KNLP workflow Makefile

ifeq (y,$(CONFIG_KDEVOPS_USER_WORKFLOW_KNLP))

USER_CONFIG_DIR := $(CONFIG_KDEVOPS_USER_CONFIG_DIR_EXPANDED)
KNLP_ARGS :=

export KNLP_DATA := $(subst ",,$(CONFIG_WORKFLOW_KNLP_DATA_PATH))

WORKFLOW_ARGS += workflow_knlp_data='$(KNLP_DATA)'

knlp:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-f 30 -i hosts -l all \
		$(USER_CONFIG_DIR)/playbooks/knlp.yml \
		--extra-vars=@./extra_vars.yaml $(KNLP_ARGS)

knlp-help-menu:
	@echo "knlp workflow targets:"
	@echo "knlp               - Setup knlp on target systems"

HELP_TARGETS += knlp-help-menu

PHONY += knlp

endif # CONFIG_KDEVOPS_USER_WORKFLOW_KNLP

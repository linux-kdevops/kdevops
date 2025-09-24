# SPDX-License-Identifier: copyleft-next-0.3.1

ifeq (,$(wildcard $(CURDIR)/.config))
else
# stage-2-y targets gets called after all local config files have been generated
stage-2-$(CONFIG_TERRAFORM)			+= kdevops_terraform_deps
stage-2-$(CONFIG_LIBVIRT_INSTALL)	+= kdevops_install_libvirt
stage-2-$(CONFIG_LIBVIRT_CONFIGURE)	+= kdevops_configure_libvirt

kdevops_stage_2: .config
	$(Q)$(MAKE) -f Makefile.kdevops $(stage-2-y)

ifneq (,$(stage-2-y))
DEFAULT_DEPS += kdevops_stage_2
endif

endif

bringup: $(KDEVOPS_BRING_UP_DEPS)

status: $(KDEVOPS_STATUS_DEPS)

destroy: $(KDEVOPS_DESTROY_DEPS)

cloud-bill:
	$(Q)$(MAKE) -f scripts/terraform.Makefile cloud-bill

slack-billing-setup:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-i hosts \
		playbooks/slack-billing.yml

slack-billing-test:
	$(Q)@echo "Testing Slack billing notification..."
	$(Q)bash scripts/slack-billing-notify.sh

slack-billing-status:
	$(Q)@if systemctl is-active --quiet kdevops-slack-billing.timer; then \
		echo "Slack billing timer is active"; \
		systemctl status kdevops-slack-billing.timer; \
	else \
		echo "Slack billing timer is not active"; \
	fi

bringup-help-menu:
	@echo "Bringup targets:"
	@echo "bringup            - Brings up target hosts"
	@echo "status             - Reports the status of target hosts"
	@echo "destroy            - Destroy all target hosts"
	@echo "cloud-bill         - Check cloud provider costs (AWS only)"
	@echo "slack-billing-setup - Deploy Slack billing notification system"
	@echo "slack-billing-test  - Test Slack billing notifications"
	@echo "slack-billing-status - Check status of Slack billing timer"
	@echo "cleancache	  - Remove all cached images"
	@echo ""

HELP_TARGETS+=bringup-help-menu

bringup-setup-help-menu:
	@echo "Generic bring up set up targets:"
	@echo "kdevops-deps        - Installs what we need on the localhost"

HELP_TARGETS += bringup-setup-help-menu

bringup-setup-help-end:
	@echo ""

HELP_TARGETS += bringup-setup-help-end

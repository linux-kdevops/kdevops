# SPDX-License-Identifier: copyleft-next-0.3.1

qemu: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml
PHONY += qemu

qemu-install: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,install
PHONY += qemu-install

qemu-configure: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,configure
PHONY += qemu-configure

qemu-build: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,build
PHONY += qemu-build


qemu-help-menu:
	@echo "qemu options:"
	@echo "qemu                                 - Git fetches QEMU, builds and install it on localhost"
	@echo "qemu-configure                       - Configure QEMU build"
	@echo "qemu-build                           - Build QEMU"
	@echo "qemu-install                         - Do the install of the QEMU build on localhost"
	@echo ""

HELP_TARGETS += qemu-help-menu

LOCALHOST_SETUP_WORK += qemu

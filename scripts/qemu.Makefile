# SPDX-License-Identifier: copyleft-next-0.3.1

qemu-controller-setup: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,qemu_controller_setup
PHONY += qemu-controller-setup

qemu-verify: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,qemu_verify
PHONY += qemu-verify

qemu-fetch: qemu-verify
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,qemu_fetch
PHONY += qemu-fetch

qemu-configure: qemu-fetch
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,qemu_configure
PHONY += qemu-configure

qemu-build: qemu-configure
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,qemu_build
PHONY += qemu-build

qemu-install: qemu-build
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/qemu.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,qemu_install
PHONY += qemu-install

qemu: qemu-install
PHONY += qemu

qemu-help-menu:
	@echo "qemu options:"
	@echo "qemu-controller-setup                - Install QEMU build and runtime deps (controller setup, may sudo)"
	@echo "qemu                                 - Verify, fetch, configure, build and install QEMU"
	@echo "qemu-verify                          - Verify the build toolchain is present (read-only)"
	@echo "qemu-fetch                           - Fetch the QEMU git tree (after verify)"
	@echo "qemu-configure                       - Configure the QEMU build (after fetch)"
	@echo "qemu-build                           - Build QEMU (after configure)"
	@echo "qemu-install                         - Install QEMU (after build)"
	@echo "controller-setup                     - Runs qemu-controller-setup as part of opt-in controller setup"
	@echo ""

HELP_TARGETS += qemu-help-menu

CONTROLLER_SETUP_WORK += qemu-controller-setup

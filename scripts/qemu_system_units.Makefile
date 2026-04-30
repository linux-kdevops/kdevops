# SPDX-License-Identifier: copyleft-next-0.3.1

export KDEVOPS_PROVISIONED_SSH := $(KDEVOPS_PROVISIONED_SSH_DEFAULT_GUARD)

KDEVOPS_PROVISION_METHOD		:= bringup_qemu_system_units
KDEVOPS_PROVISION_DESTROY_METHOD	:= destroy_qemu_system_units

install_qemu_system_units_deps:
	$(Q)ansible-playbook \
		playbooks/qemu_system_units.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags install-deps

generate_qemu_system_units_configs:
	$(Q)ansible-playbook \
		playbooks/qemu_system_units.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags generate-configs

bringup_qemu_system_units: install_qemu_system_units_deps generate_qemu_system_units_configs
	$(Q)ansible-playbook \
		playbooks/qemu_system_units.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags build-vms,bringup,console
	$(Q)touch $(KDEVOPS_PROVISIONED_SSH)
PHONY += bringup_qemu_system_units

destroy_qemu_system_units:
	$(Q)ansible-playbook \
		playbooks/qemu_system_units.yml \
		$(if $(wildcard ./extra_vars.yaml),--extra-vars=@./extra_vars.yaml) \
		--tags destroy
PHONY += destroy_qemu_system_units

rebuild-test:
	$(Q)ansible-playbook \
		playbooks/qemu_system_units.yml \
		$(if $(wildcard ./extra_vars.yaml),--extra-vars=@./extra_vars.yaml) \
		--tags rebuild-test
PHONY += rebuild-test

rebuild-boot:
	$(Q)ansible-playbook \
		playbooks/qemu_system_units.yml \
		$(if $(wildcard ./extra_vars.yaml),--extra-vars=@./extra_vars.yaml) \
		--tags rebuild-boot
PHONY += rebuild-boot

rebuild-switch:
	$(Q)ansible-playbook \
		playbooks/qemu_system_units.yml \
		$(if $(wildcard ./extra_vars.yaml),--extra-vars=@./extra_vars.yaml) \
		--tags rebuild-boot,rebuild-test
PHONY += rebuild-switch

restart-vms:
	$(Q)ansible-playbook \
		playbooks/qemu_system_units.yml \
		$(if $(wildcard ./extra_vars.yaml),--extra-vars=@./extra_vars.yaml) \
		--tags restart-vms
PHONY += restart-vms

# rebuild-boot + restart-vms in one tag invocation. Use this
# (not rebuild-switch + restart-vms) for any change that lands
# in vm.env (kernel/initrd path, NVMe BlockConf knobs, NVMe
# atomic-write knobs, virtiofs share list, etc.). The
# rebuild-test step in rebuild-switch performs a
# switch-to-configuration on the running guest, which is wasted
# work when the very next step is a QEMU restart that boots the
# guest fresh against the new closure anyway.
rebuild-restart:
	$(Q)ansible-playbook \
		playbooks/qemu_system_units.yml \
		$(if $(wildcard ./extra_vars.yaml),--extra-vars=@./extra_vars.yaml) \
		--tags rebuild-boot,restart-vms
PHONY += rebuild-restart

qemu-system-units-help-menu:
	@echo "qemu-system-units (qsu) targets:"
	@echo "rebuild-boot       - re-render vm.env + build closure (queued for next QEMU restart)"
	@echo "rebuild-test       - rebuild closure + switch-to-configuration on running guest (live)"
	@echo "rebuild-switch     - rebuild-boot + rebuild-test (renders vm.env AND live-switches)"
	@echo "restart-vms        - restart qemu-system@<vm> services + wait for sshd"
	@echo "rebuild-restart    - rebuild-boot + restart-vms (use after vm.env changes)"
	@echo ""

HELP_TARGETS += qemu-system-units-help-menu

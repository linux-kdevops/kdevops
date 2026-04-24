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

# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Bringup glue for CONFIG_NIXOSFL.
#
# User-facing entry points are the kdevops top-level targets:
# `make bringup`, `make destroy`, `make console`. They dispatch
# through the KDEVOPS_PROVISION_*_METHOD variables below to the
# per-phase tag-gated targets in playbooks/nixosfl.yml. The
# nixosfl-* targets in this file are dispatch internals;
# users do not call them directly.
#
# This backend does not set REBUILD_BOOT_METHOD or REBUILD_TEST_METHOD:
# the libvirt qcow2 bakes its kernel at image-build time. `make
# rebuild-boot` and `make rebuild-test` are imageless-only (qsu).

KDEVOPS_NODES_TEMPLATE :=	$(KDEVOPS_NODES_ROLE_TEMPLATE_DIR)/guestfs_nodes.j2
KDEVOPS_NODES :=		guestfs/kdevops_nodes.yaml

export KDEVOPS_PROVISIONED_SSH := $(KDEVOPS_PROVISIONED_SSH_DEFAULT_GUARD)

NIXOSFL_BRINGUP_DEPS :=

ifeq (y,$(CONFIG_BOOTLINUX_9P))
NIXOSFL_BRINGUP_DEPS += 9p_linux_clone
endif

KDEVOPS_PROVISION_METHOD		:= bringup_nixosfl
KDEVOPS_PROVISION_DESTROY_METHOD	:= destroy_nixosfl
KDEVOPS_PROVISION_STATUS_METHOD		:= nixosfl-status
KDEVOPS_PROVISION_CONSOLE_METHOD	:= nixosfl-console

$(KDEVOPS_PROVISIONED_SSH): $(KDEVOPS_HOSTS_PREFIX)
	$(Q)touch $(KDEVOPS_PROVISIONED_SSH)

bringup_nixosfl: $(NIXOSFL_BRINGUP_DEPS)
	$(Q)$(MAKE) nixosfl-bringup
PHONY += bringup_nixosfl

destroy_nixosfl:
	$(Q)$(MAKE) nixosfl-destroy
PHONY += destroy_nixosfl

PHONY += nixos-flake-runtime-deps-setup
nixos-flake-runtime-deps-setup: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/nixosfl.yml \
		--tags nixos_flake_runtime_deps_setup \
		--extra-vars=@./extra_vars.yaml

PHONY += nixosfl-bringup
nixosfl-bringup: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/nixosfl.yml \
		--tags nixosfl_bringup \
		--extra-vars=@./extra_vars.yaml

PHONY += nixosfl-destroy
nixosfl-destroy: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/nixosfl.yml \
		--tags nixosfl_destroy \
		--extra-vars=@./extra_vars.yaml

PHONY += nixosfl-console
# Attach to a running libvirt domain's serial console via virsh.
# Defaults to the single inventory host; pass VM=<name> when more
# than one guest is declared.
nixosfl-console:
	$(Q)set -e; \
	if [ -n "$$VM" ]; then \
		vm="$$VM"; \
	else \
		hosts=$$(ansible all --list-hosts 2>/dev/null \
			| tail -n +2 | awk '$$1 != "localhost" {print $$1}'); \
		count=$$(printf '%s\n' "$$hosts" | sed '/^$$/d' | wc -l); \
		case $$count in \
		0) echo "no inventory hosts found"; exit 1 ;; \
		1) vm="$$hosts" ;; \
		*) echo "multiple guests in inventory, pick one with VM=<name>:"; \
		   printf '  %s\n' $$hosts; exit 1 ;; \
		esac; \
	fi; \
	uri=$${LIBVIRT_DEFAULT_URI:-qemu:///system}; \
	command -v virsh >/dev/null || { echo "virsh is required"; exit 1; }; \
	exec virsh -c "$$uri" console "$$vm"

PHONY += nixosfl-status
# Report virsh domstate for every guest the active inventory
# declares.
nixosfl-status:
	$(Q)set -e; \
	hosts=$$(ansible all --list-hosts 2>/dev/null \
		| tail -n +2 | awk '$$1 != "localhost" {print $$1}'); \
	if [ -z "$$hosts" ]; then \
		echo "no inventory hosts found (run 'make' first?)"; \
		exit 0; \
	fi; \
	uri=$${LIBVIRT_DEFAULT_URI:-qemu:///system}; \
	command -v virsh >/dev/null || { echo "virsh is required"; exit 1; }; \
	printf '%-20s %s\n' VM STATE; \
	for vm in $$hosts; do \
		st=$$(virsh -c "$$uri" domstate "$$vm" 2>/dev/null || echo absent); \
		printf '%-20s %s\n' "$$vm" "$$st"; \
	done

# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Bringup glue for CONFIG_NIXOSFI.
#
# User-facing entry points are the kdevops top-level targets:
# `make bringup`, `make destroy`, `make console`, `make rebuild-boot`,
# `make rebuild-test`. They dispatch through the
# KDEVOPS_PROVISION_*_METHOD variables below to the per-phase
# tag-gated targets in playbooks/nixosfi.yml. The nixosfi-* targets in this
# file are dispatch internals; users do not call them directly.

KDEVOPS_NODES_TEMPLATE :=	$(KDEVOPS_NODES_ROLE_TEMPLATE_DIR)/guestfs_nodes.j2
KDEVOPS_NODES :=		guestfs/kdevops_nodes.yaml

export KDEVOPS_PROVISIONED_SSH := $(KDEVOPS_PROVISIONED_SSH_DEFAULT_GUARD)

NIXOSFI_BRINGUP_DEPS :=

ifeq (y,$(CONFIG_BOOTLINUX_DIRECT_BOOT))
NIXOSFI_BRINGUP_DEPS += linux-direct-boot
endif

KDEVOPS_PROVISION_METHOD		:= bringup_nixosfi
KDEVOPS_PROVISION_DESTROY_METHOD	:= destroy_nixosfi
KDEVOPS_PROVISION_STATUS_METHOD		:= nixosfi-status
KDEVOPS_PROVISION_CONSOLE_METHOD	:= nixosfi-console
KDEVOPS_PROVISION_REBUILD_BOOT_METHOD	:= nixosfi-rebuild-boot
KDEVOPS_PROVISION_REBUILD_TEST_METHOD	:= nixosfi-rebuild-test

$(KDEVOPS_PROVISIONED_SSH): $(KDEVOPS_HOSTS_PREFIX)
	$(Q)touch $(KDEVOPS_PROVISIONED_SSH)

bringup_nixosfi: $(NIXOSFI_BRINGUP_DEPS)
	$(Q)$(MAKE) nixosfi-bringup
PHONY += bringup_nixosfi

destroy_nixosfi:
	$(Q)$(MAKE) nixosfi-destroy
PHONY += destroy_nixosfi

PHONY += nixosfi-bringup
nixosfi-bringup: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(KDEVOPS_PLAYBOOKS_DIR)/nixosfi.yml \
		--tags install-deps,generate-configs,build-vms,bringup,console \
		--extra-vars=@./extra_vars.yaml

PHONY += nixosfi-destroy
nixosfi-destroy: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(KDEVOPS_PLAYBOOKS_DIR)/nixosfi.yml \
		--tags destroy \
		--extra-vars=@./extra_vars.yaml

PHONY += nixosfi-console
# Attach to a running qsu VM's serial console via socat. Defaults to
# the single running VM; pass VM=<name> when more than one is up.
nixosfi-console:
	$(Q)set -e; \
	if [ -n "$$VM" ]; then \
		vm="$$VM"; \
	else \
		vms=$$(systemctl --user list-units 'qemu-system@*.service' \
			--no-legend --state=active 2>/dev/null \
			| awk '{sub(/qemu-system@/,"",$$1); sub(/\.service/,"",$$1); print $$1}'); \
		count=$$(printf '%s\n' "$$vms" | sed '/^$$/d' | wc -l); \
		case $$count in \
		0) echo "no running qsu VM found"; exit 1 ;; \
		1) vm="$$vms" ;; \
		*) echo "multiple qsu VMs running, pick one with VM=<name>:"; \
		   printf '  %s\n' $$vms; exit 1 ;; \
		esac; \
	fi; \
	sock="$${XDG_RUNTIME_DIR}/qemu-system/$$vm/console.sock"; \
	[ -S "$$sock" ] || { echo "qsu console socket missing: $$sock"; exit 1; }; \
	command -v socat >/dev/null || { echo "socat is required"; exit 1; }; \
	echo "Attaching to $$vm (Ctrl-] then Q to detach)"; \
	exec socat -,raw,echo=0,escape=0x1d UNIX-CONNECT:"$$sock"

PHONY += nixosfi-status
# Report the run-state and currently-booted kernel for every guest
# the active inventory declares. Running guests are probed over SSH;
# stopped guests show '-'.
nixosfi-status:
	$(Q)set -e; \
	hosts=$$(ansible all --list-hosts 2>/dev/null \
		| tail -n +2 | awk '$$1 != "localhost" {print $$1}'); \
	if [ -z "$$hosts" ]; then \
		echo "no qsu hosts in inventory (run 'make' first?)"; \
		exit 0; \
	fi; \
	printf '%-20s %-10s %s\n' VM STATE KERNEL; \
	for vm in $$hosts; do \
		st=stopped; \
		k=-; \
		if systemctl --user is-active --quiet "qemu-system@$$vm.service"; then \
			st=running; \
			k=$$(ssh -o BatchMode=yes -o ConnectTimeout=3 \
				-o StrictHostKeyChecking=no \
				"$$vm" uname -r 2>/dev/null || echo "?"); \
		fi; \
		printf '%-20s %-10s %s\n' "$$vm" "$$st" "$$k"; \
	done

PHONY += nixosfi-rebuild-boot
nixosfi-rebuild-boot: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(KDEVOPS_PLAYBOOKS_DIR)/nixosfi.yml \
		--tags rebuild-boot,restart-vms \
		--extra-vars=@./extra_vars.yaml

PHONY += nixosfi-rebuild-test
nixosfi-rebuild-test: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(KDEVOPS_PLAYBOOKS_DIR)/nixosfi.yml \
		--tags rebuild-test \
		--extra-vars=@./extra_vars.yaml

PHONY += nixosfi-stop
nixosfi-stop: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(KDEVOPS_PLAYBOOKS_DIR)/nixosfi.yml \
		--tags stop-vms \
		--extra-vars=@./extra_vars.yaml

PHONY += nixosfi-start
nixosfi-start: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(KDEVOPS_PLAYBOOKS_DIR)/nixosfi.yml \
		--tags start-vms \
		--extra-vars=@./extra_vars.yaml

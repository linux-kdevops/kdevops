# SPDX-License-Identifier: copyleft-next-0.3.1

NIXOS_ARGS :=

KDEVOPS_NODES_TEMPLATE :=	$(KDEVOPS_NODES_ROLE_TEMPLATE_DIR)/nixos_nodes.j2
KDEVOPS_NODES :=		nixos/kdevops_nodes.yaml

export KDEVOPS_PROVISIONED_SSH := $(KDEVOPS_PROVISIONED_SSH_DEFAULT_GUARD)

NIXOS_ARGS += nixos_path='$(TOPDIR_PATH)/nixos'
NIXOS_ARGS += data_home_dir=/home/kdevops
NIXOS_ARGS += nixos_channel=$(CONFIG_NIXOS_CHANNEL)

NIXOS_ARGS += libvirt_provider=True

QEMU_GROUP:=$(subst ",,$(CONFIG_LIBVIRT_QEMU_GROUP))
NIXOS_ARGS += kdevops_storage_pool_group='$(QEMU_GROUP)'
NIXOS_ARGS += storage_pool_group='$(QEMU_GROUP)'

9P_HOST_CLONE :=
ifeq (y,$(CONFIG_BOOTLINUX_9P))
9P_HOST_CLONE := 9p_linux_clone
endif

LIBVIRT_PCIE_PASSTHROUGH :=
ifeq (y,$(CONFIG_KDEVOPS_LIBVIRT_PCIE_PASSTHROUGH))
LIBVIRT_PCIE_PASSTHROUGH := libvirt_pcie_passthrough_permissions
endif

ANSIBLE_EXTRA_ARGS += $(NIXOS_ARGS)

NIXOS_BRINGUP_DEPS :=
NIXOS_BRINGUP_DEPS +=  $(9P_HOST_CLONE)
NIXOS_BRINGUP_DEPS +=  $(LIBVIRT_PCIE_PASSTHROUGH)
NIXOS_BRINGUP_DEPS +=  install_nixos_deps

KDEVOPS_PROVISION_METHOD		:= bringup_nixos
KDEVOPS_PROVISION_STATUS_METHOD		:= status_nixos
KDEVOPS_PROVISION_DESTROY_METHOD	:= destroy_nixos

9p_linux_clone:
	$(Q)make linux-clone

libvirt_pcie_passthrough_permissions:
	$(Q)ansible-playbook \
		playbooks/libvirt_pcie_passthrough.yml

$(KDEVOPS_PROVISIONED_SSH): $(KDEVOPS_HOSTS_PREFIX)
	$(Q)# The SSH connectivity is verified during NixOS VM provisioning
	$(Q)# VMs get DHCP IPs and SSH is tested directly in the playbook
	$(Q)touch $(KDEVOPS_PROVISIONED_SSH)

install_nixos_deps:
	$(Q)ansible-playbook \
		--limit 'localhost' \
		playbooks/nixos.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags install-deps

generate_nixos_configs:
	$(Q)ansible-playbook \
		--limit 'localhost' \
		playbooks/nixos.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags generate-configs

bringup_nixos: $(NIXOS_BRINGUP_DEPS) generate_nixos_configs
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/nixos.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags build-vms,bringup,console
PHONY += bringup_nixos

status_nixos:
	$(Q)scripts/status_nixos.sh
PHONY += status_nixos

destroy_nixos:
	$(Q)ansible-playbook \
		playbooks/nixos.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags destroy
PHONY += destroy_nixos

clean_nixos_cache: destroy_nixos
	$(Q)echo "Performing deep clean of NixOS cached images..."
	$(Q)sudo /nix/store/*/bin/nix-collect-garbage -d 2>/dev/null || \
		sudo nix-collect-garbage -d 2>/dev/null || \
		echo "Warning: Could not run nix garbage collection"
	$(Q)rm -rf nixos/generated nixos/result nixos/*.qcow2 2>/dev/null || true
	$(Q)rm -rf /xfs1/libvirt/kdevops/nixos/nixos-image-* 2>/dev/null || true
	$(Q)echo "NixOS cache cleaned"
PHONY += clean_nixos_cache

# SPDX-License-Identifier: copyleft-next-0.3.1

GUESTFS_ARGS :=

KDEVOPS_NODES_TEMPLATE :=	$(KDEVOPS_NODES_ROLE_TEMPLATE_DIR)/guestfs_nodes.j2
KDEVOPS_NODES :=		guestfs/kdevops_nodes.yaml

export KDEVOPS_PROVISIONED_SSH := $(KDEVOPS_PROVISIONED_SSH_DEFAULT_GUARD)

GUESTFS_ARGS += guestfs_path='$(TOPDIR_PATH)/guestfs'
GUESTFS_ARGS += data_home_dir=/home/kdevops
GUESTFS_ARGS += virtbuilder_os_version=$(CONFIG_VIRT_BUILDER_OS_VERSION)

GUESTFS_ARGS += libvirt_provider=True

QEMU_GROUP:=$(subst ",,$(CONFIG_LIBVIRT_QEMU_GROUP))
GUESTFS_ARGS += kdevops_storage_pool_group='$(QEMU_GROUP)'
GUESTFS_ARGS += storage_pool_group='$(QEMU_GROUP)'

9P_HOST_CLONE :=
ifeq (y,$(CONFIG_BOOTLINUX_9P))
9P_HOST_CLONE := 9p_linux_clone
endif

LIBVIRT_PCIE_PASSTHROUGH :=
ifeq (y,$(CONFIG_KDEVOPS_LIBVIRT_PCIE_PASSTHROUGH))
LIBVIRT_PCIE_PASSTHROUGH := libvirt_pcie_passthrough_permissions
endif

ifneq ($(strip $(CONFIG_RHEL_ORG_ID)),)
ifneq ($(strip $(CONFIG_RHEL_ACTIVATION_KEY)),)
RHEL_ORG_ID:=$(subst ",,$(CONFIG_RHEL_ORG_ID))
RHEL_ACTIVATION_KEY:=$(subst ",,$(CONFIG_RHEL_ACTIVATION_KEY))
GUESTFS_ARGS += rhel_org_id="$(RHEL_ORG_ID)"
GUESTFS_ARGS += rhel_activation_key="$(RHEL_ACTIVATION_KEY)"
endif
endif

ANSIBLE_EXTRA_ARGS += $(GUESTFS_ARGS)

GUESTFS_BRINGUP_DEPS :=
GUESTFS_BRINGUP_DEPS +=  $(9P_HOST_CLONE)
GUESTFS_BRINGUP_DEPS +=  $(LIBVIRT_PCIE_PASSTHROUGH)
GUESTFS_BRINGUP_DEPS +=  install_libguestfs

KDEVOPS_PROVISION_METHOD		:= bringup_guestfs
KDEVOPS_PROVISION_STATUS_METHOD		:= status_guestfs
KDEVOPS_PROVISION_DESTROY_METHOD	:= destroy_guestfs

9p_linux_clone:
	$(Q)make linux-clone

libvirt_pcie_passthrough_permissions:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) --connection=local \
		--inventory localhost, \
		playbooks/libvirt_pcie_passthrough.yml

$(KDEVOPS_PROVISIONED_SSH):
	$(Q)if [[ "$(CONFIG_KDEVOPS_SSH_CONFIG_UPDATE)" == "y" ]]; then \
		ansible-playbook $(ANSIBLE_VERBOSE) --connection=local \
			--inventory localhost, \
			playbooks/update_ssh_config_guestfs.yml \
			--extra-vars=@./extra_vars.yaml; \
			LIBVIRT_DEFAULT_URI=$(CONFIG_LIBVIRT_URI) \
			$(TOPDIR)/scripts/update_ssh_config_guestfs.py; \
	fi
	$(Q)ansible $(ANSIBLE_VERBOSE) -i hosts 'baseline:dev' -m wait_for_connection
	$(Q)touch $(KDEVOPS_PROVISIONED_SSH)

install_libguestfs:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--inventory localhost, \
		playbooks/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags install-deps

bringup_guestfs: $(GUESTFS_BRINGUP_DEPS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=local --inventory localhost, \
		$(KDEVOPS_PLAYBOOKS_DIR)/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags network,pool,base_image
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-i hosts playbooks/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags bringup
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=local --inventory localhost, \
		$(KDEVOPS_PLAYBOOKS_DIR)/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags console
PHONY += bringup_guestfs

status_guestfs:
	$(Q)scripts/status_guestfs.sh
PHONY += status_guestfs

destroy_guestfs:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-i hosts playbooks/guestfs.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags destroy
	$(Q)rm -f $(KDEVOPS_PROVISIONED_SSH) $(KDEVOPS_PROVISIONED_DEVCONFIG)
PHONY += destroy_guestfs

cleancache:
	$(Q)rm -f $(CONFIG_LIBVIRT_STORAGE_POOL_PATH)/$(CONFIG_KDEVOPS_STORAGE_POOL_USER)/guestfs/base_images/*

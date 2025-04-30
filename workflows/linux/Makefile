# SPDX-License-Identifier: copyleft-next-0.3.1

TREE_URL:=$(subst ",,$(CONFIG_BOOTLINUX_TREE))
TREE_NAME:=$(notdir $(TREE_URL))
TREE_NAME:=$(subst .git,,$(TREE_NAME))
TREE_REF:=$(subst ",,$(CONFIG_BOOTLINUX_TREE_REF))
TREE_KERNELRELEASE:=$(subst ",,$(CONFIG_BOOTLINUX_TREE_KERNELRELEASE))
TREE_LOCALVERSION:=$(subst ",,$(CONFIG_BOOTLINUX_TREE_LOCALVERSION))
TREE_SHALLOW_DEPTH:=$(subst ",,$(CONFIG_BOOTLINUX_SHALLOW_CLONE_DEPTH))

TREE_CONFIG:=config-$(TREE_REF)
ifeq (y,$(CONFIG_BOOTLINUX_PURE_IOMAP))
TREE_CONFIG:=config-$(TREE_REF)-pure-iomap
endif

# Describes the Linux clone
BOOTLINUX_ARGS	+= target_linux_git=$(TREE_URL)
# ifeq (y,$(CONFIG_BOOTLINUX_TREE_CUSTOM_NAME))
ifdef CONFIG_BOOTLINUX_TREE_CUSTOM_NAME
BOOTLINUX_ARGS	+= target_linux_tree=$(CONFIG_BOOTLINUX_TREE_CUSTOM_NAME)
else
BOOTLINUX_ARGS	+= target_linux_tree=$(TREE_NAME)
endif
BOOTLINUX_ARGS	+= target_linux_ref=$(TREE_REF)
BOOTLINUX_ARGS	+= target_linux_config=$(TREE_CONFIG)
BOOTLINUX_ARGS	+= target_linux_kernelrelease=$(TREE_KERNELRELEASE)
BOOTLINUX_ARGS	+= target_linux_localversion=$(TREE_LOCALVERSION)

ifeq (y,$(CONFIG_BOOTLINUX_SHALLOW_CLONE))
TREE_SHALLOW_DEPTH:=$(subst ",,$(CONFIG_BOOTLINUX_SHALLOW_CLONE_DEPTH))
BOOTLINUX_ARGS	+= target_linux_shallow_depth=$(TREE_SHALLOW_DEPTH)
endif

ifeq (y,$(CONFIG_WORKFLOW_MAKE_CMD_OVERRIDE))
BOOTLINUX_ARGS	+= target_linux_make_cmd='$(WORKFLOW_MAKE_CMD)'
endif

ifeq (y,$(CONFIG_BOOTLINUX_TEST_MESSAGE_ID))
BOOTLINUX_ARGS	+= target_linux_apply_patch_message_id='$(CONFIG_BOOTLINUX_TEST_MESSAGE_ID_THREAD_ID)'
BOOTLINUX_ARGS	+= target_linux_install_b4='$(CONFIG_BOOTLINUX_TEST_MESSAGE_ID_INSTALL_B4)'
endif

LINUX_CLONE_DEFAULT_TYPE := linux-clone-clients
ifeq (y,$(CONFIG_BOOTLINUX_9P))
BOOTLINUX_ARGS	+= bootlinux_9p=True
BOOTLINUX_ARGS	+= bootlinux_9p_host_path='$(subst ",,$(CONFIG_BOOTLINUX_9P_HOST_PATH))'
BOOTLINUX_ARGS	+= bootlinux_9p_msize='$(subst ",,$(CONFIG_BOOTLINUX_9P_MSIZE))'
BOOTLINUX_ARGS	+= bootlinux_9p_fsdev='$(subst ",,$(CONFIG_BOOTLINUX_9P_FSDEV))'
BOOTLINUX_ARGS	+= bootlinux_9p_security_model='$(subst ",,$(CONFIG_BOOTLINUX_9P_SECURITY_MODEL))'
BOOTLINUX_ARGS	+= bootlinux_9p_driver='$(subst ",,$(CONFIG_BOOTLINUX_9P_DRIVER))'
BOOTLINUX_ARGS	+= bootlinux_9p_mount_tag='$(subst ",,$(CONFIG_BOOTLINUX_9P_MOUNT_TAG))'
LINUX_CLONE_DEFAULT_TYPE := linux-clone-9p
endif

# XXX: I can't seem to use after this LINUX_DYNAMIC_RUNTIME_VARS += for other
# future dynamic run time variables. So figure how the hell to do that
# so we can enable other dynamic variables for other make targets other
# than uninstall. For now this does it for us.
#
# https://www.gnu.org/software/make/manual/html_node/Overriding.html
#
# We use override as other subsystems may use this too.
ifneq (,$(KVER))
override LINUX_DYNAMIC_RUNTIME_VARS = "uninstall_kernel_ver": "$(KVER)"
endif

BOOTLINUX_ARGS += bootlinux_cxl_test=$(CONFIG_ENABLE_CXL_TEST)
WORKFLOW_ARGS += $(BOOTLINUX_ARGS)

PHONY +=  linux-help-menu
linux-help-menu:
	@echo "Linux git kernel development options"
	@echo "linux              - Git clones a linux git tree, build Linux, installs and reboots into it"
	@if [[ "$(CONFIG_BOOTLINUX_9P)" == "y" ]]; then \
		echo "linux-mount        - Mounts 9p path on targets" ;\
	fi
	@echo "linux-deploy       - Builds, installs, updates GRUB and reboots - useful for rapid development"
	@echo "linux-install      - Only builds and installs Linux"
	@echo "linux-uninstall    - Remove a kernel you can pass arguments for the version such as KVER=6.5.0-rc7-next-20230825"
	@echo "linux-clone        - Only clones Linux"
	@echo "linux-grub-setup   - Ensures the appropriate target kernel is set to boot"
	@echo "linux-reboot       - Reboot guests"
	@echo "uname              - Prints current running kernel"

PHONY += linux-help-end
linux-help-end:
	@echo ""

LINUX_HELP_EXTRA :=

PHONY += linux
linux: $(KDEVOPS_NODES)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) -i \
		$(KDEVOPS_HOSTFILE) $(KDEVOPS_PLAYBOOKS_DIR)/bootlinux.yml \
		--extra-vars="$(BOOTLINUX_ARGS)" $(LIMIT_HOSTS)

PHONY += linux-mount
linux-mount:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) -i \
		$(KDEVOPS_HOSTFILE) $(KDEVOPS_PLAYBOOKS_DIR)/bootlinux.yml \
		--tags vars,9p_mount \
		--extra-vars="$(BOOTLINUX_ARGS)" $(LIMIT_HOSTS)

PHONY += linux-deploy
linux-deploy:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) -i \
		$(KDEVOPS_HOSTFILE) $(KDEVOPS_PLAYBOOKS_DIR)/bootlinux.yml \
		--tags vars,build-linux,install-linux,manual-update-grub,saved,vars,reboot \
		--extra-vars="$(BOOTLINUX_ARGS)" $(LIMIT_HOSTS)

PHONY += linux-install
linux-install:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) -i \
		$(KDEVOPS_HOSTFILE) $(KDEVOPS_PLAYBOOKS_DIR)/bootlinux.yml \
		--tags vars,build-linux,install-linux \
		--extra-vars="$(BOOTLINUX_ARGS)" $(LIMIT_HOSTS)

PHONY += linux-uninstall
linux-uninstall:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) -i \
		$(KDEVOPS_HOSTFILE) $(KDEVOPS_PLAYBOOKS_DIR)/bootlinux.yml \
		--tags uninstall-linux,vars \
		--extra-vars '{ "uninstall_kernel_enable": "True", $(LINUX_DYNAMIC_RUNTIME_VARS) }' \
		$(LIMIT_HOSTS)

linux-clone-clients: $(KDEVOPS_NODES)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) -i \
		$(KDEVOPS_HOSTFILE) $(KDEVOPS_PLAYBOOKS_DIR)/bootlinux.yml \
		--extra-vars="$(BOOTLINUX_ARGS)" $(LIMIT_HOSTS) \
		--tags vars,clone

PHONY += linux-clone-9p
linux-clone-9p: $(KDEVOPS_NODES)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) --connection=local \
		--inventory localhost, \
		$(KDEVOPS_PLAYBOOKS_DIR)/bootlinux.yml \
		--extra-vars="$(BOOTLINUX_ARGS)" \
		--tags vars,clone

PHONY += linux-clone
linux-clone: $(KDEVOPS_NODES) $(LINUX_CLONE_DEFAULT_TYPE)

PHONY += linux-grub-setup
linux-grub-setup:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) -i \
		$(KDEVOPS_HOSTFILE) $(KDEVOPS_PLAYBOOKS_DIR)/bootlinux.yml \
		--extra-vars="$(BOOTLINUX_ARGS)" $(LIMIT_HOSTS) --tags manual-update-grub,saved,vars

PHONY += linux-reboot
linux-reboot:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) -i \
		$(KDEVOPS_HOSTFILE) $(KDEVOPS_PLAYBOOKS_DIR)/bootlinux.yml \
		--extra-vars="$(BOOTLINUX_ARGS)" $(LIMIT_HOSTS) --tags vars,reboot

PHONY += uname
uname:
	$(Q)ansible 'baseline:dev' -i hosts -b -m command -a "uname -r" -o \
	| awk -F '|' '{gsub(/^ +| +$$/, "", $$2); printf "%-30s %s\n", $$1, $$4}' \
	| sed -e 's|(stdout)||'

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_CXL))
PHONY += linux-cxl
linux-cxl: $(KDEVOPS_NODES)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) -i \
		$(KDEVOPS_HOSTFILE) $(KDEVOPS_PLAYBOOKS_DIR)/bootlinux.yml \
		--tags 'vars,cxl-build,cxl-install'                             \
		--extra-vars="$(BOOTLINUX_ARGS)" $(LIMIT_HOSTS)

PHONY += linux-help-cxl
linux-help-cxl:
	@echo "linux-cxl          - Builds cxl_test only and installs it"

LINUX_HELP_EXTRA += linux-help-cxl
endif

HELP_TARGETS+=linux-help-menu
HELP_TARGETS+=$(LINUX_HELP_EXTRA)
HELP_TARGETS+=linux-help-end

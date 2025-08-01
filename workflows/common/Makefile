# SPDX-License-Identifier: copyleft-next-0.3.1

# How we create the partition for the workflow data partition
WORKFLOW_DATA_DEVICE:=$(subst ",,$(CONFIG_WORKFLOW_DATA_DEVICE))
WORKFLOW_DATA_PATH:=$(subst ",,$(CONFIG_WORKFLOW_DATA_PATH))
WORKFLOW_DATA_FSTYPE:=$(subst ",,$(CONFIG_WORKFLOW_DATA_FSTYPE))
WORKFLOW_DATA_LABEL:=$(subst ",,$(CONFIG_WORKFLOW_DATA_LABEL))

WORKFLOW_KDEVOPS_GIT:=$(subst ",,$(CONFIG_WORKFLOW_KDEVOPS_GIT))
WORKFLOW_KDEVOPS_GIT_VERSION:=$(subst ",,$(CONFIG_WORKFLOW_KDEVOPS_GIT_VERSION))
WORKFLOW_KDEVOPS_GIT_DATA:=$(subst ",,$(CONFIG_WORKFLOW_KDEVOPS_GIT_DATA))
WORKFLOW_KDEVOPS_DIR:=$(subst ",,$(CONFIG_WORKFLOW_KDEVOPS_DIR))

WORKFLOW_ARGS	+= data_device=$(WORKFLOW_DATA_DEVICE)
WORKFLOW_ARGS	+= data_path=$(WORKFLOW_DATA_PATH)
WORKFLOW_ARGS	+= data_fstype=$(WORKFLOW_DATA_FSTYPE)
WORKFLOW_ARGS	+= data_label=$(WORKFLOW_DATA_LABEL)
WORKFLOW_ARGS	+= kdevops_git=$(WORKFLOW_KDEVOPS_GIT)
WORKFLOW_ARGS	+= kdevops_git_version=$(WORKFLOW_KDEVOPS_GIT_VERSION)
WORKFLOW_ARGS	+= kdevops_data=\"$(WORKFLOW_KDEVOPS_GIT_DATA)\"
WORKFLOW_ARGS	+= kdevops_dir=\"$(WORKFLOW_KDEVOPS_DIR)\"

ifeq (y,$(CONFIG_WORKFLOW_MAKE_CMD_OVERRIDE))
WORKFLOW_MAKE_CMD:=$(subst ",,$(CONFIG_WORKFLOW_MAKE_CMD))
endif

ifeq (y,$(CONFIG_WORKFLOW_INFER_USER_AND_GROUP))
WORKFLOW_ARGS	+= infer_uid_and_group=True
else
WORKFLOW_DATA_USER:=$(subst ",,$(CONFIG_WORKFLOW_DATA_USER))
WORKFLOW_DATA_GROUP:=$(subst ",,$(CONFIG_WORKFLOW_DATA_GROUP))

WORKFLOW_ARGS	+= data_user=$(WORKFLOW_DATA_USER)
WORKFLOW_ARGS	+= data_group=$(WORKFLOW_DATA_GROUP)

endif # CONFIG_WORKFLOW_INFER_USER_AND_GROUP == y

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_GIT_CLONES_KDEVOPS_GIT))
kdevops-git-reset:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/common.yml --tags vars,kdevops_reset \
		--extra-vars '{ kdevops_git_reset: True }' $(LIMIT_HOSTS)

kdevops-help-menu:
	@echo "Common workflow options:"
	@echo "kdevops-git-reset:                      - Resets your kdevops git tree URL and contents on guests"
	@echo

HELP_TARGETS += kdevops-help-menu
endif # CONFIG_KDEVOPS_WORKFLOW_GIT_CLONES_KDEVOPS_GIT

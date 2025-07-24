# SPDX-License-Identifier: copyleft-next-0.3.1

TERRAFORM_EXTRA_VARS :=

KDEVOPS_PROVISION_METHOD		:= bringup_terraform
KDEVOPS_PROVISION_STATUS_METHOD		:= status_terraform
KDEVOPS_PROVISION_DESTROY_METHOD	:= destroy_terraform

export KDEVOPS_CLOUD_PROVIDER=aws
ifeq (y,$(CONFIG_TERRAFORM_AWS))
endif
ifeq (y,$(CONFIG_TERRAFORM_GCE))
export KDEVOPS_CLOUD_PROVIDER=gce
endif
ifeq (y,$(CONFIG_TERRAFORM_AZURE))
export KDEVOPS_CLOUD_PROVIDER=azure
endif
ifeq (y,$(CONFIG_TERRAFORM_OCI))
export KDEVOPS_CLOUD_PROVIDER=oci
endif
ifeq (y,$(CONFIG_TERRAFORM_OPENSTACK))
export KDEVOPS_CLOUD_PROVIDER=openstack
endif

KDEVOPS_NODES_TEMPLATE :=	$(KDEVOPS_NODES_ROLE_TEMPLATE_DIR)/terraform_nodes.tf.j2
KDEVOPS_NODES :=		terraform/$(KDEVOPS_CLOUD_PROVIDER)/nodes.tf

TERRAFORM_EXTRA_VARS += kdevops_enable_terraform='True'
TERRAFORM_EXTRA_VARS += kdevops_terraform_provider='$(KDEVOPS_CLOUD_PROVIDER)'

export KDEVOPS_PROVISIONED_SSH := $(KDEVOPS_PROVISIONED_SSH_DEFAULT_GUARD)

TFVARS_TEMPLATE_DIR=playbooks/roles/gen_tfvars/templates
TFVARS_FILE_NAME=terraform.tfvars
TFVARS_FILE_POSTFIX=$(TFVARS_FILE_NAME).j2

TFVARS_TEMPLATE=$(KDEVOPS_CLOUD_PROVIDER)/$(TFVARS_FILE_POSTFIX)
KDEVOPS_TFVARS_TEMPLATE=$(TFVARS_TEMPLATE_DIR)/$(KDEVOPS_CLOUD_PROVIDER)/$(TFVARS_FILE_POSTFIX)
KDEVOPS_TFVARS=terraform/$(KDEVOPS_CLOUD_PROVIDER)/$(TFVARS_FILE_NAME)

TERRAFORM_EXTRA_VARS += kdevops_terraform_tfvars_template='$(TFVARS_TEMPLATE)'
TERRAFORM_EXTRA_VARS += kdevops_terraform_tfvars_template_full_path='$(TOPDIR_PATH)/$(KDEVOPS_TFVARS_TEMPLATE)'
TERRAFORM_EXTRA_VARS += kdevops_terraform_tfvars='$(KDEVOPS_TFVARS)'

KDEVOPS_MRPROPER += terraform/$(KDEVOPS_CLOUD_PROVIDER)/.terraform.lock.hcl
KDEVOPS_MRPROPER += $(KDEVOPS_NODES)

DEFAULT_DEPS_REQS_EXTRA_VARS += $(KDEVOPS_TFVARS)

ifeq (y,$(CONFIG_TERRAFORM_OPENSTACK))
TERRAFORM_EXTRA_VARS += terraform_openstack_cloud_name=$(subst ",,$(CONFIG_TERRAFORM_TERRAFORM_OPENSTACK_CLOUD_NAME))
TERRAFORM_EXTRA_VARS += terraform_openstack_instance_prefix=$(subst ",,$(CONFIG_TERRAFORM_TERRAFORM_OPENSTACK_INSTANCE_PREFIX))
TERRAFORM_EXTRA_VARS += terraform_openstack_flavor=$(subst ",,$(CONFIG_TERRAFORM_OPENSTACK_FLAVOR))
TERRAFORM_EXTRA_VARS += terraform_openstack_ssh_pubkey_name=$(subst ",,$(CONFIG_TERRAFORM_OPENSTACK_SSH_PUBKEY_NAME))
TERRAFORM_EXTRA_VARS += terraform_openstack_public_network_name=$(subst ",,$(CONFIG_TERRAFORM_OPENSTACK_PUBLIC_NETWORK_NAME))

ANSIBLE_EXTRA_ARGS_SEPARATED += terraform_openstack_image_name=$(subst $(space),+,$(CONFIG_TERRAFORM_OPENSTACK_IMAGE_NAME))
endif

ifeq (y,$(CONFIG_TERRAFORM_PRIVATE_NET))
TERRAFORM_EXTRA_VARS += terraform_private_net_enabled='true'
TERRAFORM_EXTRA_VARS += terraform_private_net_prefix=$(subst ",,$(CONFIG_TERRAFORM_PRIVATE_NET_PREFIX))
TERRAFORM_EXTRA_VARS += terraform_private_net_mask=$(subst ",,$(CONFIG_TERRAFORM_PRIVATE_NET_MASK))
endif

SSH_CONFIG_USER:=$(subst ",,$(CONFIG_TERRAFORM_SSH_CONFIG_USER))
# XXX: add support to auto-infer in devconfig role as we did with the bootlinux
# role. Then we can re-use the same infer_uid_and_group=True variable and
# we could then remove this entry.
TERRAFORM_EXTRA_VARS += data_home_dir=/home/${SSH_CONFIG_USER}

ifeq (y,$(CONFIG_KDEVOPS_SSH_CONFIG_UPDATE))
TERRAFORM_EXTRA_VARS += kdevops_terraform_ssh_config_update='True'

ifeq (y,$(CONFIG_KDEVOPS_SSH_CONFIG_UPDATE_STRICT))
TERRAFORM_EXTRA_VARS += kdevops_terraform_ssh_config_update_strict='True'
endif

ifeq (y,$(CONFIG_KDEVOPS_SSH_CONFIG_UPDATE_BACKUP))
TERRAFORM_EXTRA_VARS += kdevops_terraform_ssh_config_update_backup='True'
endif

endif # CONFIG_KDEVOPS_SSH_CONFIG_UPDATE

export KDEVOPS_SSH_PUBKEY:=$(shell realpath $(subst ",,$(CONFIG_TERRAFORM_SSH_CONFIG_PUBKEY_FILE)))
TERRAFORM_EXTRA_VARS += kdevops_terraform_ssh_config_pubkey_file='$(KDEVOPS_SSH_PUBKEY)'
TERRAFORM_EXTRA_VARS += kdevops_terraform_ssh_config_user='$(SSH_CONFIG_USER)'
TERRAFORM_EXTRA_VARS += kdevops_terraform_ssh_config_privkey_file='$(basename $(KDEVOPS_SSH_PUBKEY))'

ifeq (y,$(CONFIG_TERRAFORM_SSH_CONFIG_GENKEY))
export KDEVOPS_SSH_PRIVKEY:=$(basename $(KDEVOPS_SSH_PUBKEY))

ifeq (y,$(CONFIG_TERRAFORM_SSH_CONFIG_GENKEY_OVERWRITE))
DEFAULT_DEPS += remove-ssh-key
endif

DEFAULT_DEPS += $(KDEVOPS_SSH_PRIVKEY)
endif # CONFIG_TERRAFORM_SSH_CONFIG_GENKEY

ANSIBLE_EXTRA_ARGS += $(TERRAFORM_EXTRA_VARS)

bringup_terraform:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/terraform.yml --tags bringup \
		--extra-vars=@./extra_vars.yaml

$(KDEVOPS_PROVISIONED_SSH):
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/terraform.yml --tags ssh \
		--extra-vars=@./extra_vars.yaml
	$(Q)touch $(KDEVOPS_PROVISIONED_SSH)

status_terraform:
	$(Q)scripts/status_terraform.sh $(KDEVOPS_CLOUD_PROVIDER)

destroy_terraform:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/terraform.yml --tags destroy \
		--extra-vars=@./extra_vars.yaml
	$(Q)rm -f $(KDEVOPS_PROVISIONED_SSH) $(KDEVOPS_PROVISIONED_DEVCONFIG)

$(KDEVOPS_TFVARS): $(KDEVOPS_TFVARS_TEMPLATE) .config
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		$(KDEVOPS_PLAYBOOKS_DIR)/gen_tfvars.yml \
		--extra-vars=@./extra_vars.yaml

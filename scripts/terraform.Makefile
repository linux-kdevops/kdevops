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
ifeq (y,$(CONFIG_TERRAFORM_LAMBDALABS))
export KDEVOPS_CLOUD_PROVIDER=lambdalabs
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

# Lambda Labs SSH key management
ifeq (y,$(CONFIG_TERRAFORM_LAMBDALABS))

LAMBDALABS_SSH_KEY_NAME := $(subst ",,$(CONFIG_TERRAFORM_LAMBDALABS_SSH_KEY_NAME))

ifeq (y,$(CONFIG_TERRAFORM_LAMBDALABS_SSH_KEY_AUTO_CREATE))
# Auto-create mode: Always ensure key exists and create if missing
lambdalabs-ssh-check: $(KDEVOPS_SSH_PUBKEY)
	@echo "Lambda Labs SSH key setup (auto-create mode)..."
	@echo "Using SSH key name: $(LAMBDALABS_SSH_KEY_NAME)"
	@if python3 scripts/lambdalabs_ssh_keys.py check "$(LAMBDALABS_SSH_KEY_NAME)" 2>/dev/null; then \
		echo "✓ SSH key already exists in Lambda Labs"; \
	else \
		echo "Creating new SSH key in Lambda Labs..."; \
		if python3 scripts/lambdalabs_ssh_keys.py add "$(LAMBDALABS_SSH_KEY_NAME)" "$(KDEVOPS_SSH_PUBKEY)"; then \
			echo "✓ Successfully created SSH key '$(LAMBDALABS_SSH_KEY_NAME)'"; \
		else \
			echo "========================================================"; \
			echo "ERROR: Could not create SSH key automatically"; \
			echo "========================================================"; \
			echo "Please check your Lambda Labs API key configuration:"; \
			echo "  cat ~/.lambdalabs/credentials"; \
			echo ""; \
			echo "Or add the key manually:"; \
			echo "1. Go to: https://cloud.lambdalabs.com/ssh-keys"; \
			echo "2. Click 'Add SSH key'"; \
			echo "3. Name it: $(LAMBDALABS_SSH_KEY_NAME)"; \
			echo "4. Paste content from: $(KDEVOPS_SSH_PUBKEY)"; \
			echo "========================================================"; \
			exit 1; \
		fi \
	fi
else
# Manual mode: Just check if key exists
lambdalabs-ssh-check: $(KDEVOPS_SSH_PUBKEY)
	@echo "Lambda Labs SSH key setup (manual mode)..."
	@echo "Checking for SSH key: $(LAMBDALABS_SSH_KEY_NAME)"
	@if python3 scripts/lambdalabs_ssh_keys.py check "$(LAMBDALABS_SSH_KEY_NAME)" 2>/dev/null; then \
		echo "✓ SSH key exists in Lambda Labs"; \
	else \
		echo "========================================================"; \
		echo "ERROR: SSH key not found"; \
		echo "========================================================"; \
		echo "The SSH key '$(LAMBDALABS_SSH_KEY_NAME)' does not exist."; \
		echo ""; \
		echo "Please add your SSH key manually:"; \
		echo "1. Go to: https://cloud.lambdalabs.com/ssh-keys"; \
		echo "2. Click 'Add SSH key'"; \
		echo "3. Name it: $(LAMBDALABS_SSH_KEY_NAME)"; \
		echo "4. Paste content from: $(KDEVOPS_SSH_PUBKEY)"; \
		echo "========================================================"; \
		exit 1; \
	fi
endif

lambdalabs-ssh-setup: $(KDEVOPS_SSH_PUBKEY)
	@echo "Setting up Lambda Labs SSH key..."
	@python3 scripts/lambdalabs_ssh_keys.py add "$(LAMBDALABS_SSH_KEY_NAME)" "$(KDEVOPS_SSH_PUBKEY)" || true
	@python3 scripts/lambdalabs_ssh_keys.py list

lambdalabs-ssh-list:
	@echo "Current Lambda Labs SSH keys:"
	@python3 scripts/lambdalabs_ssh_keys.py list

lambdalabs-ssh-clean:
ifeq (y,$(CONFIG_TERRAFORM_LAMBDALABS_SSH_KEY_AUTO_CREATE))
	@echo "Cleaning up auto-created SSH key '$(LAMBDALABS_SSH_KEY_NAME)'..."
	@if python3 scripts/lambdalabs_ssh_keys.py check "$(LAMBDALABS_SSH_KEY_NAME)" 2>/dev/null; then \
		echo "Removing SSH key from Lambda Labs..."; \
		python3 scripts/lambdalabs_ssh_keys.py delete "$(LAMBDALABS_SSH_KEY_NAME)" || true; \
	else \
		echo "SSH key not found, nothing to clean"; \
	fi
else
	@echo "Manual SSH key mode - not removing key '$(LAMBDALABS_SSH_KEY_NAME)'"
	@echo "To remove manually, run: python3 scripts/lambdalabs_ssh_keys.py delete $(LAMBDALABS_SSH_KEY_NAME)"
endif

else
lambdalabs-ssh-check:
	@true
lambdalabs-ssh-setup:
	@true
lambdalabs-ssh-list:
	@echo "Lambda Labs provider not configured"
lambdalabs-ssh-clean:
	@true
lambdalabs-ssh-clean-after:
	@true
endif

# Handle cleanup after destroy for Lambda Labs
ifeq (y,$(CONFIG_TERRAFORM_LAMBDALABS))
ifeq (y,$(CONFIG_TERRAFORM_LAMBDALABS_SSH_KEY_AUTO_CREATE))
lambdalabs-ssh-clean-after:
	@$(MAKE) lambdalabs-ssh-clean
endif
endif

bringup_terraform: lambdalabs-ssh-check
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/terraform.yml --tags bringup \
		--extra-vars=@./extra_vars.yaml

$(KDEVOPS_PROVISIONED_SSH):
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/terraform.yml --tags ssh \
		--extra-vars=@./extra_vars.yaml
	$(Q)ansible $(ANSIBLE_VERBOSE) \
		baseline:dev:service \
		-m wait_for_connection
	$(Q)touch $(KDEVOPS_PROVISIONED_SSH)

status_terraform:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/terraform.yml --tags status \
		--extra-vars=@./extra_vars.yaml

destroy_terraform: destroy_terraform_base lambdalabs-ssh-clean-after

destroy_terraform_base:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/terraform.yml --tags destroy \
		--extra-vars=@./extra_vars.yaml
	$(Q)rm -f $(KDEVOPS_PROVISIONED_SSH) $(KDEVOPS_PROVISIONED_DEVCONFIG)

$(KDEVOPS_TFVARS): $(KDEVOPS_TFVARS_TEMPLATE) .config
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		$(KDEVOPS_PLAYBOOKS_DIR)/gen_tfvars.yml \
		--extra-vars=@./extra_vars.yaml

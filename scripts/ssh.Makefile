# SPDX-License-Identifier: copyleft-next-0.3.1

ifeq (y,$(CONFIG_HAVE_DISTRO_REQUIRES_CUSTOM_SSH_KEXALGORITHMS))
SSH_KEXALGORITHMS:=$(subst ",,$(CONFIG_KDEVOPS_CUSTOM_SSH_KEXALGORITHMS))
ANSIBLE_EXTRA_ARGS += use_kexalgorithms=True
ANSIBLE_EXTRA_ARGS += kexalgorithms=$(SSH_KEXALGORITHMS)
endif

ifeq (y,$(CONFIG_KDEVOPS_SSH_CONFIG_UPDATE))
SSH_CONFIG_FILE:=$(subst ",,$(CONFIG_KDEVOPS_SSH_CONFIG))
ANSIBLE_EXTRA_ARGS += sshconfig=$(shell realpath $(SSH_CONFIG_FILE))

ANSIBLE_EXTRA_ARGS += kdevops_ssh_config=$(shell scripts/append-makefile-vars.sh $(CONFIG_KDEVOPS_SSH_CONFIG_PREFIX) $(TOPDIR_PATH_SHA256SUM))

endif # CONFIG_KDEVOPS_SSH_CONFIG_UPDATE

PHONY += remove-ssh-key
remove-ssh-key:
	$(NQ) Removing key pair for $(KDEVOPS_SSH_PRIVKEY)
	$(Q)rm -f $(KDEVOPS_SSH_PRIVKEY)
	$(Q)rm -f $(KDEVOPS_SSH_PUBKEY)

$(KDEVOPS_SSH_PRIVKEY): .config
	$(NQ) Generating new private key: $(KDEVOPS_SSH_PRIVKEY)
	$(NQ) Generating new public key: $(KDEVOPS_SSH_PUBKEY)
	$(Q)$(TOPDIR)/scripts/gen_ssh_key.sh

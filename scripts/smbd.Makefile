ifeq (y,$(CONFIG_KDEVOPS_SETUP_SMBD))

SMBD_EXTRA_ARGS += smbd_share_fstype='$(subst ",,$(CONFIG_SMBD_SHARE_FSTYPE))'
SMBD_EXTRA_ARGS += smbd_share_path='$(subst ",,$(CONFIG_SMBD_SHARE_PATH))'
SMBD_EXTRA_ARGS += smb_root_pw='$(subst ",,$(CONFIG_SMB_ROOT_PW))'
SMBD_EXTRA_ARGS += kdevops_smbd_enable=True

ANSIBLE_EXTRA_ARGS += $(SMBD_EXTRA_ARGS)

smbd:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'smbd' \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/smbd.yml

KDEVOPS_BRING_UP_DEPS += smbd

PHONY += smbd

endif

ifeq (y,$(CONFIG_KDEVOPS_SETUP_NFSD))

ifeq (y,$(CONFIG_NFSD_EXPORT_STORAGE_LOCAL))
NFSD_EXTRA_ARGS += nfsd_export_storage_local=true
endif

ifeq (y,$(CONFIG_NFSD_EXPORT_STORAGE_ISCSI))
NFSD_EXTRA_ARGS += nfsd_export_storage_iscsi=true
endif

ifeq (y,$(CONFIG_FSTESTS_NFS_SECTION_NFSD))
NFSD_EXTRA_ARGS += kdevops_loopback_nfs_enable=true
endif

NFSD_EXTRA_ARGS += nfsd_export_fstype='$(subst ",,$(CONFIG_NFSD_EXPORT_FSTYPE))'
NFSD_EXTRA_ARGS += nfsd_export_path='$(subst ",,$(CONFIG_NFSD_EXPORT_PATH))'
NFSD_EXTRA_ARGS += nfsd_threads=$(CONFIG_NFSD_THREADS)
NFSD_EXTRA_ARGS += nfsd_lease_time=$(CONFIG_NFSD_LEASE_TIME)
NFSD_EXTRA_ARGS += kdevops_nfsd_enable=True

EXTRA_VAR_INPUTS += extend-extra-args-nfsd

extend-extra-args-nfsd:
	$(Q)echo "nfsd_export_options: '$(CONFIG_NFSD_EXPORT_OPTIONS)'" >> $(KDEVOPS_EXTRA_VARS) ;\

PHONY += extend-extra-args-nfsd

ANSIBLE_EXTRA_ARGS += $(NFSD_EXTRA_ARGS)

nfsd:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'nfsd' \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/nfsd.yml

KDEVOPS_BRING_UP_DEPS += nfsd

PHONY += nfsd

endif

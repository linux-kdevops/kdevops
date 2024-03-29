FSTESTS_ARGS += fstests_cifs_enable='True'
FSTESTS_SMB_SERVER_HOST:=$(subst ",,$(CONFIG_FSTESTS_SMB_SERVER_HOST))
ifeq (y,$(CONFIG_FSTESTS_USE_KDEVOPS_SMBD))
FSTESTS_SMB_SERVER_HOST:=$(subst ",,$(CONFIG_KDEVOPS_HOSTS_PREFIX))-smbd
FSTESTS_ARGS += fstests_cifs_use_kdevops_smbd='True'
endif # CONFIG_FSTESTS_USE_KDEVOPS_SMBD
FSTESTS_ARGS += fstests_smb_server_host='$(FSTESTS_SMB_SERVER_HOST)'

ifeq (y,$(CONFIG_FSTESTS_CIFS_SECTION_SMB3))
FSTESTS_ARGS += fstests_cifs_section_smb3=True
endif
ifeq (y,$(CONFIG_FSTESTS_CIFS_SECTION_SMB3_SEAL))
FSTESTS_ARGS += fstests_cifs_section_smb3_seal=True
endif
ifeq (y,$(CONFIG_FSTESTS_CIFS_SECTION_SMB3_SIGN))
FSTESTS_ARGS += fstests_cifs_section_smb3_sign=True
endif

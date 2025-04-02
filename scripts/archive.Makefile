# SPDX-License-Identifier: copyleft-next-0.3.1

# Automatically archive of CI results

ifeq (,$(wildcard $(CURDIR)/.config))
else

ARCHIVE_DYNAMIC_RUNTIME_VARS :=

ifneq (,$(DEMO))
ARCHIVE_DYNAMIC_RUNTIME_VARS += \
	"kdevops_archive_demo": True
endif

ci-archive:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) --connection=local \
		--inventory localhost, \
		playbooks/kdevops_archive.yml \
		--extra-vars '{ $(ARCHIVE_DYNAMIC_RUNTIME_VARS) }' \
		--extra-vars=@./extra_vars.yaml
endif

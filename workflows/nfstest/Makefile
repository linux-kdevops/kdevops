
ifeq (y,$(CONFIG_NFSTEST_USE_KDEVOPS_NFSD))
NFSTEST_ARGS += nfstest_nfs_server_host='$(subst ",,$(CONFIG_KDEVOPS_HOSTS_PREFIX))-nfsd'
NFSTEST_ARGS += nfstest_nfs_use_kdevops_nfsd='true'
else # CONFIG_NFSTEST_USE_KDEVOPS_NFSD
NFSTEST_ARGS += nfstest_nfs_server_host='$(subst ",,$(CONFIG_NFSTEST_NFS_SERVER_HOSTNAME))'
NFSTEST_ARGS += nfstest_nfs_server_export='$(subst ",,$(CONFIG_NFSTEST_NFS_SERVER_EXPORT))'
NFSTEST_ARGS += nfstest_nfs_use_kdevops_nfsd='false'
endif # CONFIG_NFSTEST_USE_KDEVOPS_NFSD

NFSTEST_MNT:=$(subst ",,$(CONFIG_NFSTEST_MNT))
NFSTEST_ARGS += nfstest_mnt=$(NFSTEST_MNT)

NFSTEST_REPO:=$(subst ",,$(CONFIG_NFSTEST_REPO))
NFSTEST_ARGS += nfstest_repo=$(NFSTEST_REPO)

NFSTEST_REPO_COMMIT:=$(subst ",,$(CONFIG_NFSTEST_REPO_COMMIT))
NFSTEST_ARGS += nfstest_repo_commit=$(NFSTEST_REPO_COMMIT)

ifeq (y,$(CONFIG_NFSTEST_TEST_GROUP_ALLOC))
NFSTEST_ENABLED_TEST_GROUPS += alloc
endif
ifeq (y,$(CONFIG_NFSTEST_TEST_GROUP_DIO))
NFSTEST_ENABLED_TEST_GROUPS += dio
endif
ifeq (y,$(CONFIG_NFSTEST_TEST_GROUP_INTEROP))
NFSTEST_ENABLED_TEST_GROUPS += interop
endif
ifeq (y,$(CONFIG_NFSTEST_TEST_GROUP_LOCK))
NFSTEST_ENABLED_TEST_GROUPS += lock
endif
ifeq (y,$(CONFIG_NFSTEST_TEST_GROUP_POSIX))
NFSTEST_ENABLED_TEST_GROUPS += posix
endif
ifeq (y,$(CONFIG_NFSTEST_TEST_GROUP_SPARSE))
NFSTEST_ENABLED_TEST_GROUPS += sparse
endif
ifeq (y,$(CONFIG_NFSTEST_TEST_GROUP_SSC))
NFSTEST_ENABLED_TEST_GROUPS += ssc
endif

WORKFLOW_ARGS += $(NFSTEST_ARGS)
WORKFLOW_ARGS_SEPARATED += nfstest_enabled_test_groups='$(subst $(space),+,$(NFSTEST_ENABLED_TEST_GROUPS))'


ifndef LAST_KERNEL
LAST_KERNEL := $(shell cat workflows/nfstest/results/last-kernel.txt 2>/dev/null)
endif

ifeq ($(LAST_KERNEL), $(shell cat workflows/nfstest/results/last-kernel.txt 2>/dev/null))
FIND_PATH := workflows/nfstest/results/last-run
else
FIND_PATH := workflows/nfstest/results/$(LAST_KERNEL)
endif

ifndef PATTERN
PATTERN := -name "*.log"
endif

ifndef XARGS_ARGS
XARGS_ARGS := -I {} bash -c 'echo "{}:"; cat {}; echo;'
endif

nfstest:
	$(Q)ansible-playbook \
		--limit 'baseline:dev' \
		--skip-tags run_tests,copy_results \
		$(KDEVOPS_PLAYBOOKS_DIR)/nfstest.yml

nfstest-baseline:
	$(Q)ansible-playbook \
		--limit 'baseline' \
		--tags vars,run_tests,copy_results \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/nfstest.yml


nfstest-dev-baseline:
	$(Q)ansible-playbook \
		--limit 'dev' \
		--tags vars,run_tests,copy_results \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/nfstest.yml


nfstest-dev-reset:
	$(Q)ansible-playbook \
		--limit 'dev' \
		--tags vars,reset \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/nfstest.yml

nfstest-show-results:
	@find $(FIND_PATH) -type f $(PATTERN) \
		| xargs $(XARGS_ARGS) \
		| sed '$${/^$$/d;}'

nfstest-help-menu:
	@echo "nfstest options:"
	@echo "nfstest                              - Git clone nfstest and install it"
	@echo "nfstest-{baseline,dev}               - Run selected nfstests on baseline or dev hosts and collect results"
	@echo "nfstests-results-visualize           - Generate HTML visualization of test results"
	@echo ""

HELP_TARGETS += nfstest-help-menu

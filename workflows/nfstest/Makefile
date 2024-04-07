ifeq (y,$(CONFIG_WORKFLOWS_DEDICATED_WORKFLOW))
export KDEVOPS_HOSTS_TEMPLATE := nfstest.j2
endif # CONFIG_WORKFLOWS_DEDICATED_WORKFLOW

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

NFSTEST_KERNEL_CI_LOOP := false
NFSTEST_KERNEL_CI_LOOP_KOTD := false

ifeq (y,$(CONFIG_KERNEL_CI))
NFSTEST_KERNEL_CI_LOOP      := scripts/workflows/nfstest/run_kernel_ci.sh
NFSTEST_KERNEL_CI_LOOP_KOTD := scripts/workflows/nfstest/run_kernel_ci_kotd.sh
endif # CONFIG_KERNEL_CI

nfstest:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) -l baseline,dev \
		-f 30 -i hosts playbooks/nfstest.yml \
		--skip-tags run_tests,copy_results

nfstest-baseline:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-f 30 -i hosts -l baseline playbooks/nfstest.yml \
		--tags vars,run_tests,copy_results \
		--extra-vars=@./extra_vars.yaml

nfstest-baseline-loop:
	$(Q)$(NFSTEST_KERNEL_CI_LOOP) baseline

nfstest-baseline-kernelci:
	$(Q)$(NFSTEST_KERNEL_CI_LOOP_KOTD) baseline

nfstest-dev-baseline:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-f 30 -i hosts -l dev playbooks/nfstest.yml \
		--tags vars,run_tests,copy_results \
		--extra-vars=@./extra_vars.yaml

nfstest-dev-loop:
	$(Q)$(NFSTEST_KERNEL_CI_LOOP) dev

nfstest-dev-kernelci:
	$(Q)$(NFSTEST_KERNEL_CI_LOOP_KOTD) dev

nfstest-dev-reset:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-f 30 -i hosts -l dev playbooks/nfstest.yml \
		--tags vars,reset \
		--extra-vars=@./extra_vars.yaml

nfstest-help-menu:
	@echo "nfstest options:"
	@echo "nfstest                              - Git clone nfstest and install it"
	@echo "nfstest-{baseline,dev}               - Run selected nfstests on baseline or dev hosts and collect results"
	@echo "nfstest-{baseline,dev}-loop"         - Run nfstest in a loop until error or steady state
	@echo "nfstest-{baseline,dev}-kernelci      - Run nfstest kernel-ci loop"
	@echo ""

HELP_TARGETS += nfstest-help-menu

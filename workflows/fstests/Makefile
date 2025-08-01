# SPDX-License-Identifier: copyleft-next-0.3.1

FSTESTS_ARGS	        :=
FSTESTS_ARGS_SEPARATED	:=
FSTESTS_ARGS_DIRECT :=

FSTESTS_BASELINE_EXTRA :=

export FSTYP:=$(subst ",,$(CONFIG_FSTESTS_FSTYP))

ifeq (y,$(CONFIG_WORKFLOWS_DEDICATED_WORKFLOW))
export KDEVOPS_HOSTS_TEMPLATE := fstests.j2
endif

FSTESTS_ARGS += fstests_fstyp='$(FSTYP)'
FS_CONFIG='$(FSTYP)/$(FSTYP).config'
FSTESTS_ARGS += fs_config_role_path='roles/fstests/templates/$(FS_CONFIG)'

ifeq (y,$(CONFIG_FSTESTS_TFB_COPY_ENABLE))
FSTESTS_ARGS += fstests_tfp_copy_enable='True'
endif

ifeq (y,$(CONFIG_FSTESTS_XFS))
include $(TOPDIR)/workflows/fstests/Makefile.xfs
endif

ifeq (y,$(CONFIG_FSTESTS_BTRFS))
include $(TOPDIR)/workflows/fstests/btrfs/Makefile
endif

ifeq (y,$(CONFIG_FSTESTS_NFS))
include $(TOPDIR)/workflows/fstests/nfs/Makefile
endif

ifeq (y,$(CONFIG_FSTESTS_CIFS))
include $(TOPDIR)/workflows/fstests/cifs/Makefile
endif

ifeq (y,$(CONFIG_FSTESTS_TMPFS))
include $(TOPDIR)/workflows/fstests/tmpfs/Makefile
endif

ifeq (y,$(CONFIG_QEMU_ENABLE_NVME_ZNS))
FSTESTS_ARGS += fstests_test_dev_zns='$(subst ",,$(CONFIG_FSTESTS_TEST_DEV_ZNS))'
FSTESTS_ARGS += fstests_zns_enabled='$(subst ",,$(CONFIG_QEMU_ENABLE_NVME_ZNS))'
endif

export FSTESTS_SPARSE_FILE_SIZE:=
export FSTESTS_TESTDEV_SPARSEFILE_GENERATION:=
export FSTESTS_SPARSE_FILE_PATH:=
export FSTESTS_SPARSE_FILENAME_PREFIX:=
export FSTESTS_SCRATCH_MNT:=
export FSTESTS_LOGWRITES_DEV:=

ifeq (y,$(CONFIG_CONFIG_BOOTLINUX))
TREE_REF:=$(subst ",,$(CONFIG_BOOTLINUX_TREE_REF))
FSTESTS_ARGS += fstests_perf_config='$(PROJECTRELEASE)-kernel-$(TREE_REF)'
endif
ifeq (,$(CONFIG_CONFIG_BOOTLINUX))
FSTESTS_ARGS += fstests_perf_config='$(PROJECTRELEASE)-kernel-distro'
endif

ifeq (y,$(CONFIG_FSTESTS_TESTDEV_SPARSEFILE_GENERATION))
include $(TOPDIR)/workflows/fstests/Makefile.sparsefiles
endif # CONFIG_FSTESTS_TESTDEV_SPARSEFILE_GENERATION == y

ifeq (y,$(CONFIG_QEMU_ENABLE_NVME_ZNS))
FSTESTS_SCRATCH_DEVPOOL_ZNS=$(subst ",,$(CONFIG_FSTESTS_SCRATCH_DEV_POOL_ZNS))
FSTESTS_ARGS_SEPARATED += fstests_scratch_devpool_zns='$(subst $(space),+,$(FSTESTS_SCRATCH_DEVPOOL_ZNS))'
endif # CONFIG_QEMU_ENABLE_NVME_ZNS

WORKFLOW_ARGS += $(FSTESTS_ARGS)
WORKFLOW_ARGS_SEPARATED += $(FSTESTS_ARGS_SEPARATED)
WORKFLOW_ARGS_DIRECT += $(FSTESTS_ARGS_DIRECT)

FSTEST_KERNEL_CI_LOOP := false
FSTEST_KERNEL_CI_LOOP_KOTD := false
ifeq (y,$(CONFIG_KERNEL_CI))
FSTEST_KERNEL_CI_LOOP := scripts/workflows/fstests/run_kernel_ci.sh
FSTEST_KERNEL_CI_LOOP_KOTD := scripts/workflows/fstests/run_kernel_ci_kotd.sh
endif # CONFIG_KERNEL_CI

FSTESTS_DYNAMIC_RUNTIME_VARS := "kdevops_run_fstests": True
ifneq (,$(RUN_FAILURES))
FSTESTS_DYNAMIC_RUNTIME_VARS += , "run_tests_on_failures": True
endif

ifneq (,$(SKIP_RUN))
FSTESTS_DYNAMIC_RUNTIME_VARS += , "fstests_skip_run": True
endif

ifeq (y,$(CONFIG_FSTESTS_ENABLE_JOURNAL))
FSTESTS_DYNAMIC_RUNTIME_VARS += , "fstests_journal": True
endif

ifneq (,$(INITIAL_BASELINE))
FSTESTS_DYNAMIC_RUNTIME_VARS += , "fstests_initial_baseline": True
endif

ifneq (,$(START_AFTER))
FSTESTS_DYNAMIC_RUNTIME_VARS += , "fstests_start_after": True
FSTESTS_DYNAMIC_RUNTIME_VARS += , "fstests_start_after_test": "$(START_AFTER)"
endif

ifneq (,$(SKIP_TESTS))
FSTESTS_DYNAMIC_RUNTIME_VARS += , "fstests_skip_tests_enable": True
FSTESTS_DYNAMIC_RUNTIME_VARS += , "fstests_skip_tests": "$(SKIP_TESTS)"
endif

ifeq (y,$(CONFIG_DEVCONFIG_ENABLE_SYSTEMD_JOURNAL_REMOTE))
FSTESTS_BASELINE_EXTRA += journal-ln
endif

ifneq (,$(COUNT))
FSTESTS_DYNAMIC_RUNTIME_VARS += , "oscheck_extra_args": "-I $(COUNT)"
endif

ifndef LAST_KERNEL
LAST_KERNEL := $(shell cat workflows/fstests/results/last-kernel.txt 2>/dev/null)
endif

ifeq ($(LAST_KERNEL), $(shell cat workflows/fstests/results/last-kernel.txt 2>/dev/null))
FIND_PATH := workflows/fstests/results/last-run
else
FIND_PATH := workflows/fstests/results/$(LAST_KERNEL)
endif

ifndef PATTERN
PATTERN := -name xunit_results.txt
endif

ifndef XARGS_ARGS
ifeq (-name xunit_results.txt,$(PATTERN))
XARGS_ARGS := cat
else
XARGS_ARGS := -I {} bash -c 'echo "{}:"; cat {}; echo;'
endif
endif

fstests: $(FSTESTS_BASELINE_EXTRA)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'localhost:baseline:dev' \
		playbooks/fstests.yml \
		--skip-tags run_tests,copy_results $(LIMIT_HOSTS)

fstests-kdevops-setup: $(KDEVOPS_EXTRA_VARS) $(FSTESTS_BASELINE_EXTRA)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/fstests.yml \
		--tags vars,kdevops_fstests_setup,gendisks \
		$(LIMIT_HOSTS)

fstests-baseline: $(FSTESTS_BASELINE_EXTRA)
	$(Q)PYTHONUNBUFFERED=1 ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline' \
		playbooks/fstests.yml \
		--tags vars,run_tests,copy_results \
		--extra-vars '{ $(FSTESTS_DYNAMIC_RUNTIME_VARS) }' \
		--extra-vars=@./extra_vars.yaml $(LIMIT_HOSTS)

fstests-baseline-loop: $(KDEVOPS_EXTRA_VARS)
	$(Q)$(FSTEST_KERNEL_CI_LOOP) baseline $(LIMIT_HOSTS)

fstests-baseline-kernelci: $(KDEVOPS_EXTRA_VARS)
	$(Q)$(FSTEST_KERNEL_CI_LOOP_KOTD) baseline $(LIMIT_HOSTS)

fstests-baseline-skip-kdevops-update: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline' \
		playbooks/fstests.yml \
		--tags run_tests,copy_results \
		--skip-tags git_update \
		--extra-vars \
		'{ $(FSTESTS_DYNAMIC_RUNTIME_VARS) }' \
		--extra-vars=@./extra_vars.yaml \
		$(LIMIT_HOSTS)

fstests-baseline-run-oscheck-only: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline' \
		playbooks/fstests.yml \
		--tags run_tests,copy_results \
		--skip-tags git_update,reboot,clean_results \
		--extra-vars \
		'{ $(FSTESTS_DYNAMIC_RUNTIME_VARS) }' \
		--extra-vars=@./extra_vars.yaml \
		$(LIMIT_HOSTS)

fstests-config: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline' \
		playbooks/fstests.yml \
		--tags vars,generate-fstests-config \
		--extra-vars=@./extra_vars.yaml \
		$(LIMIT_HOSTS)

fstests-config-debug: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/fstests.yml \
		-e 'fstests_debug_localhost=True' \
		--tags vars,generate-fstests-config \
		--extra-vars=@./extra_vars.yaml

fstests-dev: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'dev' \
		playbooks/fstests.yml \
		--tags vars,run_tests,copy_results \
		--extra-vars \
		'{ $(FSTESTS_DYNAMIC_RUNTIME_VARS) }' \
		--extra-vars=@./extra_vars.yaml $(LIMIT_HOSTS)

fstests-baseline-results-tfb-ls: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline' \
		playbooks/fstests.yml \
		--tags vars,tfb \
		--skip-tags copy_final \
		--extra-vars \
		'{ fstests_tfp_copy_enable_list: True }' \
		--extra-vars=@./extra_vars.yaml $(LIMIT_HOSTS)

fstests-baseline-results-tfb-trim: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline' \
		playbooks/fstests.yml \
		--tags vars,tfb \
		--skip-tags copy_final \
		--extra-vars \
		'{ fstests_tfp_copy_enable: True }' \
		--extra-vars=@./extra_vars.yaml $(LIMIT_HOSTS)

fstests-baseline-results: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline' \
		playbooks/fstests.yml \
		--tags copy_results,print_results,tfb \
		--extra-vars '{ kdevops_run_fstests: True }' \
		--extra-vars=@./extra_vars.yaml \
		$(LIMIT_HOSTS)

fstests-results: fstests-baseline-results

fstests-dev-results: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'dev' \
		playbooks/fstests.yml \
		--tags copy_results,print_results \
		--extra-vars '{ kdevops_run_fstests: True }' \
		--extra-vars=@./extra_vars.yaml \
		$(LIMIT_HOSTS)

fstests-show-results:
	@find $(FIND_PATH) -type f $(PATTERN) \
		| xargs $(XARGS_ARGS) \
		| sed '$${/^$$/d;}'

fstests-help-menu:
	@echo "fstests options:"
	@echo "fstests                                 - Git clones fstests, builds and install it"
	@echo "fstests-kdevops-setup                   - Install kdevops specific files, the fstests and running test targets also runs this"
	@echo "fstests-baseline                        - Run fstests on baseline hosts and collect results"
	@echo "fstests-dev                             - Run fstests on dev hosts and collect results"
	@echo ""
	@echo "fstests-config                          - Generates the filesystem configuration file only onto target systems"
	@echo "fstests-config-debug                    - Generates the filesystem configuration file locally, useful for debugging"
	@echo ""
	@echo "fstests-baseline-results-tfb-ls         - Only show a listing of TFB results files other than XML files which are TFB"
	@echo "fstests-baseline-results-tfb-trim       - Trim all TFB results file other than xml files"
	@echo "fstests-baseline-results                - Only collect results for baseline hosts"
	@echo "fstests-dev-results                     - Only collect results for dev hosts"
	@echo "fstests-baseline-skip-kdevops-update    - Run fstests but skip updating kdevops"
	@echo "fstests-baseline-run-oscheck-only       - Only run oscheck"
	@echo "fstests-baseline-loop                   - Run fstests in a loop until a failure is found or steady state is reached"
	@echo "fstests-baseline-kernelci               - Run fstests kernel-ci loop"
	@echo ""

HELP_TARGETS += fstests-help-menu

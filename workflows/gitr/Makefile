
GITR_MNT:=$(subst ",,$(CONFIG_GITR_MNT))
GITR_ARGS += gitr_mnt=$(GITR_MNT)

ifeq (y,$(CONFIG_GITR_XFS))
include $(TOPDIR)/workflows/gitr/xfs/Makefile
endif

ifeq (y,$(CONFIG_GITR_BTRFS))
include $(TOPDIR)/workflows/gitr/btrfs/Makefile
endif

ifeq (y,$(CONFIG_GITR_EXT4))
include $(TOPDIR)/workflows/gitr/ext4/Makefile
endif

ifeq (y,$(CONFIG_GITR_NFS))
include $(TOPDIR)/workflows/gitr/nfs/Makefile
endif

ifeq (y,$(CONFIG_GITR_TMPFS))
include $(TOPDIR)/workflows/gitr/tmpfs/Makefile
endif

GITR_REPO:=$(subst ",,$(CONFIG_GITR_REPO))
GITR_ARGS += gitr_repo=$(GITR_REPO)

GITR_REPO_COMMIT:=$(subst ",,$(CONFIG_GITR_REPO_COMMIT))
GITR_ARGS += gitr_repo_commit=$(GITR_REPO_COMMIT)

ifeq (y,$(CONFIG_GITR_ALL_TESTS))
GITR_PLAY_TAGS := vars,run_tests,copy_results
else
GITR_ARGS += gitr_test_list=$(subst ",,$(CONFIG_GITR_TEST_LIST))
GITR_PLAY_TAGS := vars,run_specific_tests,copy_results
endif

ifeq (y,$(CONFIG_GITR_THREAD_SINGLE))
GITR_ARGS += gitr_thread_single=True
endif

ifeq (y,$(CONFIG_GITR_THREAD_FAST))
GITR_ARGS += gitr_thread_fast=True
endif

ifeq (y,$(CONFIG_GITR_THREAD_STRESS))
GITR_ARGS += gitr_thread_stress=True
endif

ifeq (y,$(CONFIG_GITR_THREAD_CUSTOM))
GITR_THREAD_COUNT:=$(subst ",,$(CONFIG_GITR_THREAD_CUSTOM_COUNT))
GITR_ARGS += gitr_thread_count=$(GITR_THREAD_COUNT)
GITR_ARGS += gitr_thread_custom=True
endif

WORKFLOW_ARGS_DIRECT += $(GITR_ARGS)

ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_DEDICATE_GITR))
WORKFLOW_ARGS_SEPARATED += gitr_enabled_test_groups='$(subst $(space),+,$(GITR_ENABLED_TEST_GROUPS))'
endif


ifndef LAST_KERNEL
LAST_KERNEL := $(shell cat workflows/gitr/results/last-kernel.txt 2>/dev/null)
endif

ifeq ($(LAST_KERNEL), $(shell cat workflows/gitr/results/last-kernel.txt 2>/dev/null))
FIND_PATH := workflows/gitr/results/last-run
else
FIND_PATH := workflows/gitr/results/$(LAST_KERNEL)
endif

ifndef PATTERN
PATTERN := -name "*.summary"
endif

ifndef XARGS_ARGS
XARGS_ARGS := -I {} bash -c 'echo "{}:"; cat {}; echo;'
endif

gitr:
	$(Q)ansible-playbook \
		--limit 'baseline:dev' \
		--skip-tags run_tests,run_specific_tests,copy_results \
		$(KDEVOPS_PLAYBOOKS_DIR)/gitr.yml

gitr-baseline:
	$(Q)ansible-playbook \
		--limit 'baseline' \
		--tags $(GITR_PLAY_TAGS) \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/gitr.yml


gitr-dev-baseline:
	$(Q)ansible-playbook \
		--limit 'dev' \
		--tags $(GITR_PLAY_TAGS) \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/gitr.yml


gitr-dev-reset:
	$(Q)ansible-playbook \
		--limit 'dev' \
		--tags vars,reset \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/gitr.yml

gitr-show-results:
	@find $(FIND_PATH) -type f $(PATTERN) \
		| xargs $(XARGS_ARGS) \
		| sed '$${/^$$/d;}'

gitr-help-menu:
	@echo "gitr options:"
	@echo "gitr                              - Git clone git, build and install it"
	@echo "gitr-{baseline,dev}               - Run the gitr test on baseline or dev hosts and collect results"
	@echo ""

HELP_TARGETS += gitr-help-menu

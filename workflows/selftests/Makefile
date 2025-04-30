# SPDX-License-Identifier: copyleft-next-0.3.1

SELFTESTS_ARGS :=

ifeq (y,$(CONFIG_WORKFLOWS_DEDICATED_WORKFLOW))
export KDEVOPS_HOSTS_TEMPLATE := selftests.j2
endif

SELFTESTS_DYNAMIC_RUNTIME_VARS := "kdevops_run_selftests": True

ifneq (,$(SKIP_RUN))
SELFTESTS_DYNAMIC_RUNTIME_VARS += , "selftests_skip_run": True
endif

ifneq (,$(SKIP_REBOOT))
SELFTESTS_DYNAMIC_RUNTIME_VARS += , "selftests_skip_reboot": True
endif

SELFTESTS_HELP_TARGETS := selftests-help-main
SELFTESTS_LIMIT_TARGET :=
KDEVOPS_HOSTS_PREFIX:=$(subst ",,$(CONFIG_KDEVOPS_HOSTS_PREFIX))

ifeq (y,$(CONFIG_SELFTESTS_MANUAL_COVERAGE))
SELFTESTS_HELP_TARGETS += selftests-help-menu-targets
endif

include $(TOPDIR)/workflows/selftests/tests/Makefile.firmware
include $(TOPDIR)/workflows/selftests/tests/Makefile.module
include $(TOPDIR)/workflows/selftests/tests/Makefile.kmod
include $(TOPDIR)/workflows/selftests/tests/Makefile.maple
include $(TOPDIR)/workflows/selftests/tests/Makefile.sysctl
include $(TOPDIR)/workflows/selftests/tests/Makefile.xarray

selftests:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/selftests.yml \
		--skip-tags run_tests,copy_results,check_results \
		$(LIMIT_HOSTS)

selftests-baseline:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline' \
		playbooks/selftests.yml \
		--extra-vars '{ $(SELFTESTS_DYNAMIC_RUNTIME_VARS) }' \
		--tags vars,run_tests,copy_results,check_results $(LIMIT_HOSTS)

selftests-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline' \
		playbooks/selftests.yml \
		--tags vars,copy_results,check_results $(LIMIT_HOSTS)

selftests-check-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline' \
		playbooks/selftests.yml \
		--tags vars,check_results $(LIMIT_HOSTS)

selftests-help-main:
	@echo "Generic selftests options:"
	@echo "selftests                         - Build (can be local if using 9p) and then install target selftests (could be to target nodes)"
	@echo "selftests-baseline                - Runs selftests for all supported targets"
	@echo "selftests-results                 - Get results for all test runs"

selftests-help-menu: $(SELFTESTS_HELP_TARGETS)
	@echo ""

selftests-help-menu-targets:
	@echo ""
	@echo "Specific target selftests sections:"

PHONY += $(SELFTESTS_HELP_TARGETS)
HELP_TARGETS += selftests-help-menu
WORKFLOW_ARGS += $(SELFTESTS_ARGS)

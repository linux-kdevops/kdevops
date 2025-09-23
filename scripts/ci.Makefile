# SPDX-License-Identifier: copyleft-next-0.3.1

# Collection of CI build targets per kernel repo

CI_WORKFLOW ?=
ifeq (y,$(CONFIG_BOOTLINUX))

ifneq (y,$(CONFIG_WORKFLOW_LINUX_PACKAGED))

ifeq ($(strip $(CI_WORKFLOW)),)
CI_WORKFLOW_BASENAME := $(shell basename $(CONFIG_BOOTLINUX_TREE) | sed 's/\.git$$//')
else
# Map workflow names to their appropriate .ci basename
ifeq ($(findstring xfs,$(CI_WORKFLOW)),xfs)
CI_WORKFLOW_BASENAME := fstests
else ifeq ($(findstring btrfs,$(CI_WORKFLOW)),btrfs)
CI_WORKFLOW_BASENAME := fstests
else ifeq ($(findstring ext4,$(CI_WORKFLOW)),ext4)
CI_WORKFLOW_BASENAME := fstests
else ifeq ($(findstring tmpfs,$(CI_WORKFLOW)),tmpfs)
CI_WORKFLOW_BASENAME := fstests
else ifeq ($(findstring lbs-xfs,$(CI_WORKFLOW)),lbs-xfs)
CI_WORKFLOW_BASENAME := fstests
else
CI_WORKFLOW_BASENAME := $(shell basename $(CI_WORKFLOW))
endif
endif

ifneq ($(wildcard .ci/build-test/$(CI_WORKFLOW_BASENAME)),)
ifneq ($(wildcard .ci/test/$(CI_WORKFLOW_BASENAME)),)
ifneq ($(wildcard .ci/results/$(CI_WORKFLOW_BASENAME)),)

ci-build-test: ci-build-test-$(CI_WORKFLOW_BASENAME)

PHONY += build-test

ci-build-test-%::
	@set -e; \
		while IFS= read -r line || [ -n "$$line" ]; do \
		echo "Running: $$line"; \
		$$line; \
	  done < .ci/build-test/$(CI_WORKFLOW_BASENAME); \

ci-build-test-help-menu:
	@echo "kdevops built-in CI build tests for $(CI_WORKFLOW_BASENAME):"
	@echo "ci-build-test - Git clones a linux git tree, build Linux, installs and reboots into it"
	@while IFS= read -r line || [ -n "$$line" ]; do \
		echo -e "\t$$line"; \
		done < .ci/build-test/$(CI_WORKFLOW_BASENAME)
	@echo

HELP_TARGETS += ci-build-test-help-menu

ci-test: ci-test-$(CI_WORKFLOW_BASENAME)

ci-test-%::
	@set -e; \
		while IFS= read -r line || [ -n "$$line" ]; do \
		echo "Running: $$line"; \
		$$line; \
	  done < .ci/test/$(CI_WORKFLOW_BASENAME); \

ci-test-help-menu:
	@echo "kdevops built-in run time tests for $(CI_WORKFLOW_BASENAME):"
	@echo "ci-test       - Git clones a linux git tree, build Linux, installs and reboots into it"
	@while IFS= read -r line || [ -n "$$line" ]; do \
		echo -e "\t$$line"; \
		done < .ci/test/$(CI_WORKFLOW_BASENAME)
	@echo

HELP_TARGETS += ci-test-help-menu

ci-results: ci-results-$(CI_WORKFLOW_BASENAME)

ci-results-%::
	@set -e; \
		while IFS= read -r line || [ -n "$$line" ]; do \
		echo -e "$$line"; \
	done < .ci/results/$(CI_WORKFLOW_BASENAME)

ci-results-help-menu:
	@echo "kdevops built-in results tests for $(CI_WORKFLOW_BASENAME) can be found in directories:"
	@echo "ci-results    - List of directories where you can find test results"
	@while IFS= read -r line || [ -n "$$line" ]; do \
		echo -e "\t$$line"; \
		done < .ci/results/$(CI_WORKFLOW_BASENAME)
	@echo

HELP_TARGETS += ci-results-help-menu

endif # We have ci results entries
endif # We have ci tests entries
else
ci-results:
ci-test:
ci-build-test:
endif # We have ci build tests entries

else # CONFIG_WORKFLOW_LINUX_PACKAGED
ci-results:
ci-test:
ci-build-test:
endif # CONFIG_WORKFLOW_LINUX_PACKAGED

else # CONFIG_BOOTLINUX
ci-results:
ci-test:
ci-build-test:
endif

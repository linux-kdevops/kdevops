# SPDX-License-Identifier: copyleft-next-0.3.1

# Collection of CI build targets per kernel repo

ifeq (y,$(CONFIG_BOOTLINUX))
BOOTLINUX_BASENAME := $(shell basename $(CONFIG_BOOTLINUX_TREE))
ifneq ($(wildcard .ci/build-test/$(BOOTLINUX_BASENAME)),)
ifneq ($(wildcard .ci/test/$(BOOTLINUX_BASENAME)),)
ifneq ($(wildcard .ci/results/$(BOOTLINUX_BASENAME)),)

ci-build-test: build-test-$(BOOTLINUX_BASENAME)

PHONY += build-test

ci-build-test-%::
	@set -e; \
		while IFS= read -r line || [ -n "$$line" ]; do \
		echo "Running: $$line"; \
		$$line; \
	  done < .ci/build-test/$(BOOTLINUX_BASENAME); \

ci-build-test-help-menu:
	@echo "kdevops built-in CI build tests for $(BOOTLINUX_BASENAME):"
	@echo "ci-build-test - Git clones a linux git tree, build Linux, installs and reboots into it"
	@while IFS= read -r line || [ -n "$$line" ]; do \
		echo -e "\t$$line"; \
		done < .ci/build-test/$(BOOTLINUX_BASENAME)
	@echo

HELP_TARGETS += ci-build-test-help-menu

ci-test: ci-test-$(BOOTLINUX_BASENAME)

ci-test-%::
	@set -e; \
		while IFS= read -r line || [ -n "$$line" ]; do \
		echo "Running: $$line"; \
		$$line; \
	  done < .ci/test/$(BOOTLINUX_BASENAME); \

ci-test-help-menu:
	@echo "kdevops built-in run time tests for $(BOOTLINUX_BASENAME):"
	@echo "ci-test       - Git clones a linux git tree, build Linux, installs and reboots into it"
	@while IFS= read -r line || [ -n "$$line" ]; do \
		echo -e "\t$$line"; \
		done < .ci/test/$(BOOTLINUX_BASENAME)
	@echo

HELP_TARGETS += ci-test-help-menu

ci-results: ci-results-$(BOOTLINUX_BASENAME)

ci-results-%::
	@set -e; \
		while IFS= read -r line || [ -n "$$line" ]; do \
		echo -e "$$line"; \
	done < .ci/results/$(BOOTLINUX_BASENAME)

ci-results-help-menu:
	@echo "kdevops built-in results tests for $(BOOTLINUX_BASENAME) can be found in directories:"
	@echo "ci-results    - List of directories where you can find test results"
	@while IFS= read -r line || [ -n "$$line" ]; do \
		echo -e "\t$$line"; \
		done < .ci/results/$(BOOTLINUX_BASENAME)
	@echo

HELP_TARGETS += ci-results-help-menu

endif # We have ci results entries
endif # We have ci tests entries
endif # We have ci build tests entries
endif # CONFIG_BOOTLINUX

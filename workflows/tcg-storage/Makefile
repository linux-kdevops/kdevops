# TCG Storage workflow Makefile
#
# This Makefile provides targets for testing TCG Storage functionality
# using the go-tcg-storage test suite.

TCG_STORAGE_ARGS	:=

ifeq (y,$(CONFIG_KERNEL_CI))
TCG_STORAGE_KERNEL_CI_LOOP	:= scripts/workflows/tcg-storage/run_kernel_ci.sh
TCG_STORAGE_KERNEL_CI_LOOP_KOTD := scripts/workflows/tcg-storage/run_kernel_ci_kotd.sh
endif

TOPDIR_PATH ?= $(PWD)
TOPDIR_PATH_ESCAPED = $(shell echo $(TOPDIR_PATH) | sed 's/\//\\\//g')
TCG_STORAGE_RESULTS_DIR := $(TOPDIR_PATH)/workflows/tcg-storage/results

tcg-storage-help:
	@echo "TCG Storage testing options:"
	@echo "tcg-storage                 - Run TCG storage tests"
	@echo "tcg-storage-baseline        - Establish baseline for TCG storage tests"
	@echo "tcg-storage-dev             - Run tests on development kernel"
	@echo "tcg-storage-results         - Show test results"
	@echo "tcg-storage-results-full    - Show detailed test results"
	@echo "tcg-storage-clean           - Clean test results"
	@echo "tcg-storage-tools-info      - Show information about installed TCG tools"
	@echo "tcg-storage-device-info     - Show information about TCG devices"
	@echo ""
	@echo "TCG Storage test configuration:"
	@echo "tcg-storage-take-ownership  - Test taking ownership of TCG device"
	@echo "tcg-storage-locking-ranges  - Test locking range operations"
	@echo "tcg-storage-revert          - Test device revert operations"
	@echo ""

tcg-storage-menuconfig:
	@$(Q)make menuconfig
	@$(Q)echo "TCG Storage configuration saved"

tcg-storage-configure: tcg-storage-menuconfig

# Allow TCG_DEVICE override for declared hosts
ifdef TCG_DEVICE
TCG_STORAGE_TEST_ARGS += test_device=$(TCG_DEVICE)
else
TCG_STORAGE_TEST_ARGS += test_device=$(CONFIG_TCG_STORAGE_TEST_DEVICE)
endif

TCG_STORAGE_TEST_ARGS += test_device_type=$(CONFIG_TCG_STORAGE_TEST_DEVICE_TYPE)
TCG_STORAGE_TEST_ARGS += test_password=$(CONFIG_TCG_STORAGE_TEST_PASSWORD)

ifeq (y,$(CONFIG_TCG_STORAGE_USE_LOCAL))
TCG_STORAGE_TEST_ARGS += tcg_storage_use_local=true
TCG_STORAGE_TEST_ARGS += tcg_storage_local_path=$(CONFIG_TCG_STORAGE_LOCAL_PATH)
else
TCG_STORAGE_TEST_ARGS += tcg_storage_github_url=$(CONFIG_TCG_STORAGE_GITHUB_URL)
TCG_STORAGE_TEST_ARGS += tcg_storage_branch=$(CONFIG_TCG_STORAGE_BRANCH)
endif

ifeq (y,$(CONFIG_TCG_STORAGE_RUN_UNIT_TESTS))
TCG_STORAGE_TEST_ARGS += run_unit_tests=true
endif

ifeq (y,$(CONFIG_TCG_STORAGE_RUN_INTEGRATION_TESTS))
TCG_STORAGE_TEST_ARGS += run_integration_tests=true
endif

ifeq (y,$(CONFIG_TCG_STORAGE_TEST_TAKE_OWNERSHIP))
TCG_STORAGE_TEST_ARGS += test_take_ownership=true
endif

ifeq (y,$(CONFIG_TCG_STORAGE_TEST_LOCKING_RANGES))
TCG_STORAGE_TEST_ARGS += test_locking_ranges=true
endif

ifeq (y,$(CONFIG_TCG_STORAGE_TEST_REVERT))
TCG_STORAGE_TEST_ARGS += test_revert=true
endif

tcg-storage-build-tools:
	@echo "Building TCG storage tools..."
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-f 30 -i hosts playbooks/tcg-storage.yml \
		--tags build \
		--extra-vars=@extra_vars.yaml \
		--extra-vars="$(TCG_STORAGE_TEST_ARGS)"

tcg-storage:
	@echo "Installing dependencies and running TCG storage tests..."
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-f 30 -i hosts playbooks/tcg-storage.yml \
		--tags deps,build,run_tests \
		--extra-vars=@extra_vars.yaml \
		--extra-vars="$(TCG_STORAGE_TEST_ARGS)"

tcg-storage-baseline:
	@echo "Establishing TCG storage baseline..."
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-f 30 -i hosts playbooks/tcg-storage.yml \
		--tags baseline \
		--extra-vars=@extra_vars.yaml \
		--extra-vars="$(TCG_STORAGE_TEST_ARGS)" \
		--extra-vars="test_type=baseline"

tcg-storage-results:
	@echo "TCG Storage Test Results:"
	@echo "========================="
	@if [ -d "$(TCG_STORAGE_RESULTS_DIR)" ]; then \
		for file in $(TCG_STORAGE_RESULTS_DIR)/*.txt; do \
			if [ -f "$$file" ]; then \
				echo ""; \
				echo "=== $$(basename $$file) ==="; \
				head -20 "$$file"; \
			fi \
		done \
	else \
		echo "No results found. Run 'make tcg-storage' first."; \
	fi

tcg-storage-results-full:
	@echo "Full TCG Storage Test Results:"
	@echo "=============================="
	@if [ -d "$(TCG_STORAGE_RESULTS_DIR)" ]; then \
		for file in $(TCG_STORAGE_RESULTS_DIR)/*.txt; do \
			if [ -f "$$file" ]; then \
				echo ""; \
				echo "=== $$(basename $$file) ==="; \
				cat "$$file"; \
				echo ""; \
			fi \
		done \
	else \
		echo "No results found. Run 'make tcg-storage' first."; \
	fi

tcg-storage-dev: tcg-storage
	@echo "TCG storage development tests completed"

tcg-storage-clean:
	@echo "Cleaning TCG storage test results..."
	@rm -rf $(TCG_STORAGE_RESULTS_DIR)
	@echo "TCG storage test results cleaned"

tcg-storage-tools-info:
	@echo "Checking TCG storage tools..."
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-f 30 -i hosts playbooks/tcg-storage.yml \
		--tags tools_info \
		--extra-vars=@extra_vars.yaml

tcg-storage-device-info:
	@echo "Getting TCG device information..."
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-f 30 -i hosts playbooks/tcg-storage.yml \
		--tags device_info \
		--extra-vars=@extra_vars.yaml \
		--extra-vars="$(TCG_STORAGE_TEST_ARGS)"

tcg-storage-take-ownership:
	@echo "Testing TCG device ownership..."
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-f 30 -i hosts playbooks/tcg-storage.yml \
		--tags take_ownership \
		--extra-vars=@extra_vars.yaml \
		--extra-vars="$(TCG_STORAGE_TEST_ARGS) test_take_ownership=true"

tcg-storage-locking-ranges:
	@echo "Testing TCG locking ranges..."
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-f 30 -i hosts playbooks/tcg-storage.yml \
		--tags locking_ranges \
		--extra-vars=@extra_vars.yaml \
		--extra-vars="$(TCG_STORAGE_TEST_ARGS) test_locking_ranges=true"

tcg-storage-revert:
	@echo "Testing TCG device revert..."
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-f 30 -i hosts playbooks/tcg-storage.yml \
		--tags revert \
		--extra-vars=@extra_vars.yaml \
		--extra-vars="$(TCG_STORAGE_TEST_ARGS) test_revert=true"

ifeq (y,$(CONFIG_KERNEL_CI))
tcg-storage-kernel-ci-loop:
	$(Q)$(TCG_STORAGE_KERNEL_CI_LOOP) $(TCG_STORAGE_ARGS)

tcg-storage-kernel-ci-loop-kotd:
	$(Q)$(TCG_STORAGE_KERNEL_CI_LOOP_KOTD) $(TCG_STORAGE_ARGS)
endif # CONFIG_KERNEL_CI

PHONY += tcg-storage-help tcg-storage-menuconfig tcg-storage-configure
PHONY += tcg-storage tcg-storage-baseline tcg-storage-dev
PHONY += tcg-storage-results tcg-storage-results-full tcg-storage-clean
PHONY += tcg-storage-build-tools
PHONY += tcg-storage-tools-info tcg-storage-device-info
PHONY += tcg-storage-take-ownership tcg-storage-locking-ranges tcg-storage-revert

ifeq (y,$(CONFIG_KERNEL_CI))
PHONY += tcg-storage-kernel-ci-loop tcg-storage-kernel-ci-loop-kotd
endif

HELP_TARGETS += tcg-storage-help
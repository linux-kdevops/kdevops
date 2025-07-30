# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Linux A/B testing verification for kdevops
# Verifies that A/B testing ref configurations are correct

# Test scripts
LINUX_AB_TEST_SCRIPT_CONFIG :=	scripts/test-linux-ab-config.py
LINUX_AB_TEST_SCRIPT :=		scripts/test-linux-ab.sh

# Test verbosity
LINUX_AB_TEST_VERBOSE ?= 0

PHONY += check-linux-ab-help
check-linux-ab-help:
	@echo "Linux A/B testing verification:"
	@echo "check-linux-ab            - Run full A/B testing verification (all build methods)"
	@echo "check-linux-ab-config     - Quick check of current configuration only"
	@echo ""
	@echo "check-linux-ab runs the full test suite:"
	@echo "  - Tests all three build methods (target, 9p, builder)"
	@echo "  - Applies each defconfig and verifies settings"
	@echo "  - Checks that refs are different"
	@echo "  - Outputs results in TAP format"
	@echo "  - Returns error code on any failure"
	@echo ""
	@echo "check-linux-ab-config only verifies current config:"
	@echo "  - A/B testing is enabled in .config"
	@echo "  - target_linux_ref and target_linux_dev_ref are different"
	@echo "  - Both refs are valid (not empty or None)"
	@echo ""

# Main verification target - runs comprehensive tests
PHONY += check-linux-ab
check-linux-ab:
	@if [ ! -f $(LINUX_AB_TEST_SCRIPT) ]; then \
		echo "Error: Test script not found at $(LINUX_AB_TEST_SCRIPT)"; \
		exit 1; \
	fi
	$(LINUX_AB_TEST_SCRIPT)

# Quick verification - just checks current configuration
PHONY += check-linux-ab-config
check-linux-ab-config:
	@if [ ! -f $(LINUX_AB_TEST_SCRIPT_CONFIG) ]; then \
		echo "Error: Test script not found at $(LINUX_AB_TEST_SCRIPT_CONFIG)"; \
		exit 1; \
	fi
	@python3 $(LINUX_AB_TEST_SCRIPT_CONFIG)

# Add to help system
HELP_TARGETS += check-linux-ab-help

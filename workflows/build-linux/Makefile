PHONY += build-linux build-linux-baseline build-linux-dev
PHONY += build-linux-results build-linux-help-menu
PHONY += monitor-results

# Main build-linux workflow targets
build-linux: $(KDEVOPS_NODES) $(ANSIBLE_INVENTORY_FILE)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-i hosts \
		playbooks/build_linux.yml \
		-f 10 \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		$(LIMIT_HOSTS)

build-linux-baseline:
	$(Q)$(MAKE) build-linux HOSTS="baseline"

build-linux-dev:
	$(Q)$(MAKE) build-linux HOSTS="dev"

# Results collection target
build-linux-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-i hosts \
		playbooks/build_linux_results.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		$(LIMIT_HOSTS)

monitor-results: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/monitor-results.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS)

build-linux-help-menu:
	@echo "Build Linux workflow targets:"
	@echo ""
	@echo "Main targets:"
	@echo "  build-linux             - Build Linux kernel multiple times"
	@echo "  build-linux-baseline    - Build on baseline nodes only"
	@echo "  build-linux-dev         - Build on dev nodes only"
	@echo ""
	@echo "Results collection:"
	@echo "  build-linux-results     - Collect and analyze build statistics"
	@echo "  monitor-results         - Collect monitoring data"
	@echo ""
	@echo "Configuration:"
	@echo "  Repeat count: $(CONFIG_BUILD_LINUX_REPEAT_COUNT) builds"
	@echo "  Target: $(CONFIG_BUILD_LINUX_TARGET)"
	@echo "  Clean between: $(CONFIG_BUILD_LINUX_CLEAN_BETWEEN)"
	@echo ""

HELP_TARGETS += build-linux-help-menu

.PHONY: $(PHONY)

PHONY += build-linux build-linux-baseline build-linux-dev
PHONY += build-linux-results build-linux-visualize build-linux-help-menu
PHONY += monitor-results monitor-kill

# Main build-linux workflow targets
build-linux: $(KDEVOPS_NODES) $(ANSIBLE_INVENTORY_FILE)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-i hosts \
		playbooks/build_linux.yml \
		-f 10 \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		$(LIMIT_HOSTS)
	$(Q)echo "Build workflow completed. Collecting results..."
	$(Q)$(MAKE) build-linux-results
	$(Q)echo "Generating visualization..."
	$(Q)$(MAKE) build-linux-visualize

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

# Visualize collected results with graphs and HTML report
build-linux-visualize:
	$(Q)if [ ! -d workflows/build-linux/results ] || [ -z "$$(ls -A workflows/build-linux/results 2>/dev/null)" ]; then \
		echo "Error: No results found in workflows/build-linux/results/"; \
		echo ""; \
		echo "Did you run these commands first?"; \
		echo "  1. make build-linux        (to run the builds)"; \
		echo "  2. make build-linux-results (to collect results from nodes)"; \
		echo ""; \
		echo "To collect results now, run: make build-linux-results"; \
		exit 1; \
	fi
	$(Q)# Generate summary files if they don't exist
	$(Q)if [ -z "$$(ls workflows/build-linux/results/*_summary_*.json 2>/dev/null)" ]; then \
		echo "Generating summary files from build_times data..."; \
		python3 workflows/build-linux/scripts/generate_summaries.py \
			workflows/build-linux/results/ || \
			echo "Warning: Failed to generate summary files"; \
	fi
	$(Q)echo "Loading results..."
	$(Q)python3 workflows/build-linux/scripts/visualize_results.py \
		workflows/build-linux/results/ || \
		(echo ""; \
		echo "Error: Failed to generate visualizations."; \
		echo ""; \
		echo "This workflow requires matplotlib for visualization."; \
		echo "Please install the dependencies using:"; \
		echo "  make install-deps"; \
		echo ""; \
		echo "Or manually install matplotlib:"; \
		echo "  Debian/Ubuntu: sudo apt-get install python3-matplotlib python3-numpy"; \
		echo "  RHEL/Fedora: sudo dnf install python3-matplotlib python3-numpy"; \
		echo "  SUSE: sudo zypper install python3-matplotlib python3-numpy"; \
		exit 1)

monitor-results: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/monitor-results.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS)

monitor-kill: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-i hosts \
		playbooks/monitor-kill.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		$(LIMIT_HOSTS)

build-linux-help-menu:
	@echo "Build Linux workflow targets:"
	@echo ""
	@echo "Main targets:"
	@echo "  build-linux             - Build Linux kernel multiple times, collect results, and visualize"
	@echo "  build-linux-baseline    - Build on baseline nodes only (includes results + visualization)"
	@echo "  build-linux-dev         - Build on dev nodes only (includes results + visualization)"
	@echo ""
	@echo "Results collection (also run automatically by build-linux):"
	@echo "  build-linux-results     - Collect and analyze build statistics (standalone)"
	@echo "  build-linux-visualize   - Generate HTML report with performance graphs (standalone)"
	@echo "  monitor-results         - Collect monitoring data (requires CONFIG_ENABLE_MONITORING)"
	@echo "  monitor-kill            - Kill all monitoring processes and clean up data"
	@echo ""
	@echo "Configuration:"
	@echo "  Repeat count: $(CONFIG_BUILD_LINUX_REPEAT_COUNT) builds"
	@echo "  Target: $(CONFIG_BUILD_LINUX_TARGET)"
	@echo "  Clean between: $(CONFIG_BUILD_LINUX_CLEAN_BETWEEN)"
	@echo ""

HELP_TARGETS += build-linux-help-menu

.PHONY: $(PHONY)

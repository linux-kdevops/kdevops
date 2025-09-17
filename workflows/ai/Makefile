PHONY += ai ai-baseline ai-dev ai-results ai-results-baseline ai-results-dev
PHONY += ai-setup ai-uninstall ai-destroy ai-help-menu
PHONY += ai-tests ai-tests-baseline ai-tests-dev
PHONY += ai-tests-results


export AI_DATA_TARGET := $(subst ",,$(CONFIG_AI_BENCHMARK_RESULTS_DIR))
export AI_ARGS :=

AI_ARGS += ai_benchmark_results_dir='$(AI_DATA_TARGET)'

# Vector Database Configuration
ifeq (y,$(CONFIG_AI_TESTS_VECTOR_DATABASE))
AI_ARGS += ai_tests_vector_database=True
else
AI_ARGS += ai_tests_vector_database=False
endif

# Milvus-specific Configuration
ifeq (y,$(CONFIG_AI_VECTOR_DB_MILVUS))
AI_ARGS += ai_vector_db_milvus_enable=True
AI_ARGS += ai_vector_db_milvus_docker=True
else
AI_ARGS += ai_vector_db_milvus_enable=False
endif

AI_MANUAL_ARGS :=

export AI_ARGS_SEPARATED := $(subst $(space),$(comma),$(AI_ARGS))

# Main AI workflow targets
ai: $(KDEVOPS_NODES) $(ANSIBLE_INVENTORY_FILE)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/ai.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--extra-vars="$(AI_ARGS) $(AI_MANUAL_ARGS)" \
		$(LIMIT_HOSTS)

ai-baseline:
	$(Q)$(MAKE) ai HOSTS="baseline"

ai-dev:
	$(Q)$(MAKE) ai HOSTS="dev"

# AI Testing/Benchmark targets
ai-tests: $(KDEVOPS_NODES) $(ANSIBLE_INVENTORY_FILE)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/ai_tests.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--extra-vars="$(AI_ARGS) $(AI_MANUAL_ARGS)" \
		$(LIMIT_HOSTS)
	$(Q)$(MAKE) ai-results

ai-tests-baseline: $(KDEVOPS_NODES) $(ANSIBLE_INVENTORY_FILE)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-l baseline \
		playbooks/ai_tests.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--extra-vars="$(AI_ARGS) $(AI_MANUAL_ARGS)"
	$(Q)$(MAKE) ai-results-baseline

ai-tests-dev: $(KDEVOPS_NODES) $(ANSIBLE_INVENTORY_FILE)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-l dev \
		playbooks/ai_tests.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--extra-vars="$(AI_ARGS) $(AI_MANUAL_ARGS)"
	$(Q)$(MAKE) ai-results-dev

# Target to only run results analysis and graph generation
ai-tests-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/ai_tests.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--extra-vars="$(AI_ARGS) $(AI_MANUAL_ARGS)" \
		--tags="results" \
		$(LIMIT_HOSTS)

# Results collection targets
ai-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/ai_results.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--extra-vars="$(AI_ARGS) $(AI_MANUAL_ARGS)" \
		$(LIMIT_HOSTS)

ai-results-baseline:
	$(Q)$(MAKE) ai-results HOSTS="baseline"

ai-results-dev:
	$(Q)$(MAKE) ai-results HOSTS="dev"

ai-setup:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/ai_setup.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--extra-vars="$(AI_ARGS) $(AI_MANUAL_ARGS)" \
		$(LIMIT_HOSTS)

ai-uninstall:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/ai_uninstall.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--extra-vars="$(AI_ARGS) $(AI_MANUAL_ARGS)" \
		$(LIMIT_HOSTS)

ai-destroy:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/ai_destroy.yml \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--extra-vars="$(AI_ARGS) $(AI_MANUAL_ARGS)" \
		$(LIMIT_HOSTS)

ai-help-menu:
	@echo "AI workflow targets:"
	@echo ""
	@echo "Setup targets:"
	@echo "  ai                     - Setup AI infrastructure (installs and starts services)"
	@echo "  ai-baseline            - Setup AI infrastructure on baseline nodes only"
	@echo "  ai-dev                 - Setup AI infrastructure on dev nodes only"
	@echo ""
	@echo "Testing/Benchmark targets:"
	@echo "  ai-tests               - Run AI benchmarks on all nodes"
	@echo "  ai-tests-baseline      - Run AI benchmarks on baseline nodes only"
	@echo "  ai-tests-dev           - Run AI benchmarks on dev nodes only"
	@echo "  ai-tests-results       - Only run results analysis and graph generation"
	@echo ""
	@echo "Results collection:"
	@echo "  ai-results             - Collect and analyze AI benchmark results"
	@echo "  ai-results-baseline    - Collect results from baseline nodes only"
	@echo "  ai-results-dev         - Collect results from dev nodes only"
	@echo ""
	@echo "Other targets:"
	@echo "  ai-setup               - Legacy target (use 'make ai' instead)"
	@echo "  ai-uninstall           - Uninstall AI benchmark components"
	@echo "  ai-destroy             - Destroy AI benchmark environment"
	@echo ""

HELP_TARGETS += ai-help-menu

EXTRA_VAR_INPUTS += AI_ARGS_SEPARATED

.PHONY: $(PHONY)

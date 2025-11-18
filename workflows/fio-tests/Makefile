fio-tests:
	$(Q)ansible-playbook \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests.yml

fio-tests-baseline:
	$(Q)ansible-playbook \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-baseline.yml

fio-tests-results:
	$(Q)ansible-playbook \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-results.yml

fio-tests-graph:
	$(Q)ansible-playbook \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-graph.yml

fio-tests-compare:
	$(Q)ansible-playbook \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-compare.yml

fio-tests-trend-analysis:
	$(Q)ansible-playbook \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-trend-analysis.yml

fio-tests-multi-fs-compare:
	$(Q)ansible-playbook \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-multi-fs-compare.yml

fio-tests-clean-results:
	@echo "Cleaning fio-tests results directory..."
	$(Q)rm -rf $(TOPDIR)/workflows/fio-tests/results/
	@echo "fio-tests results directory cleaned"

# Add results cleanup to destroy dependencies when fio-tests workflow is enabled
ifeq (y,$(CONFIG_KDEVOPS_WORKFLOW_ENABLE_FIO_TESTS))
KDEVOPS_DESTROY_DEPS += fio-tests-clean-results
endif

fio-tests-help-menu:
	@echo "fio-tests options:"
	@echo "fio-tests                    - run fio performance tests"
	@echo "fio-tests-baseline           - establish baseline results"
	@echo "fio-tests-results            - collect and analyze results"
	@echo "fio-tests-graph              - generate performance graphs"
	@echo "fio-tests-compare            - compare baseline vs dev results"
	@echo "fio-tests-trend-analysis     - analyze performance trends"
	@echo "fio-tests-multi-fs-compare   - compare results across multiple filesystems"
	@echo "fio-tests-clean-results      - clean results directory"
	@echo ""

HELP_TARGETS += fio-tests-help-menu

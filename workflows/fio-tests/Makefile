fio-tests:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory $(KDEVOPS_HOSTFILE) \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests.yml

fio-tests-baseline:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory $(KDEVOPS_HOSTFILE) \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-baseline.yml

fio-tests-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory $(KDEVOPS_HOSTFILE) \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-results.yml

fio-tests-graph:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory $(KDEVOPS_HOSTFILE) \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-graph.yml

fio-tests-compare:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory $(KDEVOPS_HOSTFILE) \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-compare.yml

fio-tests-trend-analysis:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory $(KDEVOPS_HOSTFILE) \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-trend-analysis.yml

fio-tests-help-menu:
	@echo "fio-tests options:"
	@echo "fio-tests                 - run fio performance tests"
	@echo "fio-tests-baseline        - establish baseline results"
	@echo "fio-tests-results         - collect and analyze results"
	@echo "fio-tests-graph           - generate performance graphs"
	@echo "fio-tests-compare         - compare baseline vs dev results"
	@echo "fio-tests-trend-analysis  - analyze performance trends"
	@echo ""

HELP_TARGETS += fio-tests-help-menu

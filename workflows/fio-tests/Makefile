ifeq (y,$(CONFIG_WORKFLOWS_DEDICATED_WORKFLOW))
export KDEVOPS_HOSTS_TEMPLATE := fio-tests.j2
endif

fio-tests:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory hosts \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests.yml

fio-tests-baseline:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory hosts \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-baseline.yml

fio-tests-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory hosts \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests.yml \
		--tags results

fio-tests-graph:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory hosts \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-graph.yml

fio-tests-compare:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory hosts \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-compare.yml

fio-tests-trend-analysis:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory hosts \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-trend-analysis.yml

fio-tests-help-menu:
	@echo "fio-tests options:"
	@echo "fio-tests                 - run fio performance tests"
	@echo "fio-tests-baseline        - establish baseline results"
	@echo "fio-tests-results         - collect results from target nodes to localhost"
	@echo "fio-tests-graph           - generate performance graphs on localhost"
	@echo "fio-tests-compare         - compare baseline vs dev results"
	@echo "fio-tests-trend-analysis  - analyze performance trends"
	@echo ""

HELP_TARGETS += fio-tests-help-menu

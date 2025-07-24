ifeq (y,$(CONFIG_WORKFLOWS_DEDICATED_WORKFLOW))
export KDEVOPS_HOSTS_TEMPLATE := fio-tests.j2
endif

fio-tests:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory hosts \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests.yml \
		$(LIMIT_HOSTS)

fio-tests-baseline:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory hosts \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-baseline.yml \
		$(LIMIT_HOSTS)

fio-tests-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory hosts \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests.yml \
		--tags results \
		$(LIMIT_HOSTS)

fio-tests-graph:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory hosts \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-graph.yml \
		$(LIMIT_HOSTS)

fio-tests-compare:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory hosts \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-compare.yml \
		$(LIMIT_HOSTS)

fio-tests-trend-analysis:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--connection=ssh \
		--inventory hosts \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		playbooks/fio-tests-trend-analysis.yml \
		$(LIMIT_HOSTS)

fio-tests-estimate:
	$(Q)python3 scripts/workflows/fio-tests/estimate-runtime.py

fio-tests-help-menu:
	@echo "fio-tests options:"
	@echo "fio-tests                 - run fio performance tests"
	@echo "fio-tests-baseline        - establish baseline results"
	@echo "fio-tests-results         - collect results from target nodes to localhost"
	@echo "fio-tests-graph           - generate performance graphs on localhost"
	@echo "fio-tests-compare         - compare baseline vs dev results"
	@echo "fio-tests-trend-analysis  - analyze performance trends"
	@echo "fio-tests-estimate        - estimate runtime for current configuration"
	@echo ""

HELP_TARGETS += fio-tests-help-menu

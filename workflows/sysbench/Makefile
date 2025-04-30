PHONY += sysbench sysbench-test sysbench-telemetry sysbench-help-menu

ifeq (y,$(CONFIG_WORKFLOWS_DEDICATED_WORKFLOW))
export KDEVOPS_HOSTS_TEMPLATE := sysbench.j2
endif

TAGS_SYSBENCH_RUN := db_start
TAGS_SYSBENCH_RUN += db_test_connection
TAGS_SYSBENCH_RUN += post_entrypoint
TAGS_SYSBENCH_RUN += populate_sbtest
TAGS_SYSBENCH_RUN += run_sysbench
TAGS_SYSBENCH_RUN += telemetry
TAGS_SYSBENCH_RUN += logs
TAGS_SYSBENCH_RUN += results
TAGS_SYSBENCH_RUN += plot

# Tags for running sysbench tests
TAGS_SYSBENCH_TEST := vars
TAGS_SYSBENCH_TEST += $(TAGS_SYSBENCH_RUN)

# Tags for collecting telemetry only
TAGS_SYSBENCH_TELEMETRY := vars
TAGS_SYSBENCH_TELEMETRY += telemetry

# Tags for collecting results only
TAGS_SYSBENCH_RESULTS := vars
TAGS_SYSBENCH_RESULTS += results

# Target to set up sysbench (MySQL or PostgreSQL)
sysbench:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/sysbench.yml \
		--skip-tags $(subst $(space),$(comma),$(TAGS_SYSBENCH_RUN))

# Target to run sysbench tests (including telemetry)
sysbench-test:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/sysbench.yml \
		--tags $(subst $(space),$(comma),$(TAGS_SYSBENCH_TEST))

# Optional target to collect telemetry
sysbench-telemetry:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/sysbench.yml \
		--tags $(subst $(space),$(comma),$(TAGS_SYSBENCH_TELEMETRY))

# Optional target to collect all results
sysbench-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/sysbench.yml \
		--tags $(subst $(space),$(comma),$(TAGS_SYSBENCH_RESULTS))

sysbench-clean:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/sysbench.yml \
		--tags vars,clean

# Optional in case you want to improve graphing
sysbench-plot:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/sysbench.yml \
		--tags vars,plot

# Help target to show available options
sysbench-help-menu:
	@echo "Sysbench options:"
	@echo "sysbench                          - Set up sysbench (MySQL or PostgreSQL)"
	@echo "sysbench-test                     - Run sysbench tests and collect results (with telemetry)"
	@echo "sysbench-telemetry                - Gather sysbench telemetry data on each node"
	@echo "sysbench-results                  - Collect all sysbench results onto local host"
	@echo "sysbench-clean                    - Remove any previous results on node and host"
	@echo ""

HELP_TARGETS += sysbench-help-menu

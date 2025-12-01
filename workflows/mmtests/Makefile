MMTESTS_ARGS	:=


mmtests:
	$(Q)ansible-playbook \
		playbooks/mmtests.yml \
		--extra-vars=@./extra_vars.yaml  \
		--tags deps,setup
		$(MMTESTS_ARGS)

mmtests-baseline:
	$(Q)ansible-playbook \
		-l 'mmtests:&baseline' playbooks/mmtests.yml \
		--extra-vars=@./extra_vars.yaml  \
		--tags run_tests \
		$(MMTESTS_ARGS)

mmtests-dev:
	$(Q)ansible-playbook \
		-l 'mmtests:&dev' playbooks/mmtests.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags run_tests \
		$(MMTESTS_ARGS)

mmtests-tests:
	$(Q)ansible-playbook \
		playbooks/mmtests.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags run_tests,results \
		$(MMTESTS_ARGS)

mmtests-results:
	$(Q)ansible-playbook \
		playbooks/mmtests.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags results \
		$(MMTESTS_ARGS)

mmtests-compare:
	$(Q)ansible-playbook \
		playbooks/mmtests-compare.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags deps,compare \
		$(MMTESTS_ARGS)

monitor-results: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		playbooks/monitor-results.yml \
		--extra-vars=@./extra_vars.yaml \
		$(MMTESTS_ARGS)

mmtests-clean:
	$(Q)ansible-playbook \
		playbooks/mmtests.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags clean \
		$(MMTESTS_ARGS)

mmtests-help:
	@echo "mmtests targets:"
	@echo "mmtests                       : Setup and install mmtests"
	@echo "mmtests-baseline             : Setup mmtests with baseline configuration"
	@echo "mmtests-dev                  : Setup mmtests with dev configuration"
	@echo "mmtests-tests                : Run mmtests tests"
	@echo "mmtests-results              : Copy results from guests"
	@echo "mmtests-compare              : Compare baseline and dev results (AB testing)"
	@echo "monitor-results              : Collect interim monitoring data without stopping monitoring"
	@echo "mmtests-clean                : Clean up mmtests installation"
	@echo ""

HELP_TARGETS += mmtests-help

PHONY +: mmtests
PHONY +: mmtests-baseline
PHONY +: mmtests-dev
PHONY +: mmtests-tests
PHONY +: mmtests-results
PHONY +: mmtests-compare
PHONY +: monitor-results
PHONY +: mmtests-clean
PHONY +: mmtests-help
.PHONY: $(PHONY)

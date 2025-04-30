MMTESTS_ARGS	:=

ifeq (y,$(CONFIG_WORKFLOWS_DEDICATED_WORKFLOW))
export KDEVOPS_HOSTS_TEMPLATE := mmtests.j2
endif

mmtests:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/mmtests.yml \
		--extra-vars=@./extra_vars.yaml  \
		--tags deps,setup
		$(MMTESTS_ARGS)

mmtests-baseline:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-l baseline playbooks/mmtests.yml
		--extra-vars=@./extra_vars.yaml  \
		--tags run_tests \
		$(MMTESTS_ARGS)

mmtests-dev:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		-l dev playbooks/mmtests.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags run_tests \
		$(MMTESTS_ARGS)

mmtests-test: mmtests
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/mmtests.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags run_tests,results \
		$(MMTESTS_ARGS)

mmtests-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/mmtests.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags results \
		$(MMTESTS_ARGS)

mmtests-clean:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/mmtests.yml \
		--extra-vars=@./extra_vars.yaml \
		--tags clean \
		$(MMTESTS_ARGS)

mmtests-help:
	@echo "mmtests targets:"
	@echo "mmtests                       : Setup and install mmtests"
	@echo "mmtests-baseline             : Setup mmtests with baseline configuration"
	@echo "mmtests-dev                  : Setup mmtests with dev configuration"
	@echo "mmtests-test                 : Run mmtests tests"
	@echo "mmtests-results              : Copy results from guests"
	@echo "mmtests-clean                : Clean up mmtests installation"
	@echo ""

HELP_TARGETS += mmtests-help

PHONY +: mmtests
PHONY +: mmtests-baseline
PHONY +: mmtests-dev
PHONY +: mmtests-test
PHONY +: mmtests-results
PHONY +: mmtests-clean
PHONY +: mmtests-help
.PHONY: $(PHONY)

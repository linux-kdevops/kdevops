PHONY += steady-state
PHONY += steady-state-files
PHONY += steady-state-prefill
PHONY += steady-state-run
PHONY += steady-state-help-menu

SSD_STEADY_STATE_DYNAMIC_RUNTIME_VARS := "kdevops_run_ssd_steady_state": True

steady-state-files:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
	playbooks/steady_state.yml \
	--extra-vars=@./extra_vars.yaml --tags vars,setup $(LIMIT_HOSTS)

steady-state-prefill:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
	playbooks/steady_state.yml \
	--extra-vars=@./extra_vars.yaml --tags vars,prefill $(LIMIT_HOSTS)

steady-state-run:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
	playbooks/steady_state.yml \
	--extra-vars=@./extra_vars.yaml --tags vars,steady_state $(LIMIT_HOSTS)

steady-state:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
	playbooks/steady_state.yml \
	--extra-vars '{ $(SSD_STEADY_STATE_DYNAMIC_RUNTIME_VARS) }' $(LIMIT_HOSTS)

steady-state-help-menu:
	@echo "steady-state-files                - Install steady state template files only"
	@echo "steady-state-prefill              - Run prefill operations only"
	@echo "steady-state-run                  - Run fio steady state tests only"
	@echo "steady-state                      - Prefill and run fio steady state"
	@echo ""

HELP_TARGETS += steady-state-help-menu

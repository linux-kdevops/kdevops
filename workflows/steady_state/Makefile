PHONY += steady-state steady-state-help-menu

SSD_STEADY_STATE_DYNAMIC_RUNTIME_VARS := "kdevops_run_ssd_steady_state": True

steady-state:
$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
-i $(KDEVOPS_HOSTFILE) playbooks/steady_state.yml \
--extra-vars '{ $(SSD_STEADY_STATE_DYNAMIC_RUNTIME_VARS) }' $(LIMIT_HOSTS)

steady-state-help-menu:
@echo "steady-state                      - Prefill and run fio steady state"
@echo ""

HELP_TARGETS += steady-state-help-menu

PHONY += fio-tests fio-tests-help-menu

ifeq (y,$(CONFIG_WORKFLOWS_DEDICATED_WORKFLOW))
export KDEVOPS_HOSTS_TEMPLATE := fio_tests.j2
endif

fio-tests:
$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
-i $(KDEVOPS_HOSTFILE) playbooks/fio_tests.yml

fio-tests-help-menu:
@echo "fio-tests                        - Run fio-tests workflow"
@echo ""

HELP_TARGETS += fio-tests-help-menu

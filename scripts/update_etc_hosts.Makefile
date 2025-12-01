update_etc_hosts:
	$(Q)ansible-playbook \
		playbooks/update_etc_hosts.yml

KDEVOPS_BRING_UP_DEPS_EARLY += update_etc_hosts

PHONY += update_etc_hosts

update_etc_hosts:
	$(Q)ansible-playbook \
		playbooks/update_etc_hosts.yml

# Skip update_etc_hosts on the qsu path. NixOS manages /etc/hosts
# declaratively through networking.hosts; ansible edits on the
# imageless guest would be overwritten on the next boot anyway.
ifneq (y,$(CONFIG_QEMU_SYSTEM_UNITS))
KDEVOPS_BRING_UP_DEPS_EARLY += update_etc_hosts
endif

PHONY += update_etc_hosts

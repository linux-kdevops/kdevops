ifeq (y,$(CONFIG_KDEVOPS_SETUP_RDMA_SIW))

siw:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) --extra-vars=@./extra_vars.yaml \
		-f 30 -i hosts playbooks/siw.yml

KDEVOPS_BRING_UP_DEPS += siw

PHONY += siw

endif

ifeq (y,$(CONFIG_KDEVOPS_SETUP_RDMA_RXE))

rxe:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) --extra-vars=@./extra_vars.yaml \
		-f 30 -i hosts playbooks/rxe.yml

KDEVOPS_BRING_UP_DEPS += rxe

PHONY += rxe

endif

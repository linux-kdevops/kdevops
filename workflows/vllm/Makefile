# vLLM Production Stack workflow

HELP_TARGETS += vllm-help-menu

vllm:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/vllm.yml \
		--tags data_partition,vars,deps,docker-config,vllm-deploy \
		--extra-vars=@./extra_vars.yaml

vllm-deploy:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/vllm.yml \
		--tags data_partition,vars,deps,docker-config,vllm-deploy \
		--extra-vars=@./extra_vars.yaml

vllm-benchmark:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/vllm.yml \
		--tags vars,vllm-benchmark \
		--extra-vars=@./extra_vars.yaml

vllm-monitor:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/vllm.yml \
		--tags vars,vllm-monitor \
		--extra-vars=@./extra_vars.yaml

vllm-teardown:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/vllm.yml \
		--tags vars,vllm-teardown \
		--extra-vars=@./extra_vars.yaml

vllm-cleanup:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/vllm.yml \
		--tags vars,vllm-cleanup \
		--extra-vars=@./extra_vars.yaml

vllm-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/vllm.yml \
		--tags vars,vllm-results \
		--extra-vars=@./extra_vars.yaml

vllm-visualize-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/vllm.yml \
		--tags vars,vllm-visualize \
		--extra-vars=@./extra_vars.yaml

vllm-help-menu:
	@echo "vLLM Production Stack options:"
	@echo "vllm                      - Deploy vLLM stack to Kubernetes"
	@echo "vllm-deploy               - Deploy vLLM stack to Kubernetes (same as vllm)"
	@echo "vllm-benchmark            - Run performance benchmarks and collect results"
	@echo "vllm-monitor              - Display monitoring dashboard URLs"
	@echo "vllm-teardown             - Gracefully remove vLLM deployment"
	@echo "vllm-cleanup              - Force delete all vLLM resources (use when stuck)"
	@echo "vllm-results              - Display benchmark results"
	@echo "vllm-visualize-results    - Generate HTML visualization of benchmark results"
	@echo ""

.PHONY: vllm vllm-deploy vllm-benchmark vllm-monitor vllm-teardown vllm-cleanup vllm-results vllm-visualize-results vllm-help-menu

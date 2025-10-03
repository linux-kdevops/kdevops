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

vllm-cleanup-full:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/vllm.yml \
		--tags vars,vllm-cleanup \
		--extra-vars=@./extra_vars.yaml \
		--extra-vars='{"vllm_cleanup_remove_binaries": true}'

vllm-cleanup-purge:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/vllm.yml \
		--tags vars,vllm-cleanup \
		--extra-vars=@./extra_vars.yaml \
		--extra-vars='{"vllm_cleanup_remove_binaries": true, "vllm_cleanup_remove_data": true}'

vllm-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/vllm.yml \
		--tags vars,vllm-results,vllm-visualize \
		--extra-vars=@./extra_vars.yaml

vllm-visualize-results:
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline:dev' \
		playbooks/vllm.yml \
		--tags vars,vllm-visualize \
		--extra-vars=@./extra_vars.yaml

vllm-status:
	@echo "=========================================="
	@echo "vLLM Deployment Status (Detailed)"
	@echo "=========================================="
	@echo ""
	@echo "--- Ansible Process ---"
	@ps aux | grep -E "ansible.*vllm" | grep -v grep || echo "No Ansible process running"
	@echo ""
	@echo "--- Helm Deployment (on nodes) ---"
	@ansible all -i hosts -m shell -a "ps aux | grep -E 'helm.*vllm' | grep -v grep || echo 'No helm process running'" 2>/dev/null || echo "Unable to check helm status"
	@echo ""
	@echo "--- Kubernetes Cluster Status ---"
	@ansible all -i hosts -m shell -a "kubectl cluster-info 2>&1 | head -5 || minikube status 2>&1 || echo 'Kubernetes not ready'" 2>/dev/null || echo "Unable to check k8s status"
	@echo ""
	@echo "--- Kubernetes Pods ---"
	@ansible all -i hosts -m shell -a "KUBECONFIG=/root/.kube/config kubectl get pods -A 2>&1 | head -20 || echo 'Cannot get pods'" -b 2>/dev/null || echo "Unable to check pods"
	@echo ""
	@echo "--- Helm Releases ---"
	@ansible all -i hosts -m shell -a "KUBECONFIG=/root/.kube/config helm list -A 2>&1 || echo 'No helm releases'" -b 2>/dev/null || echo "Unable to check helm releases"
	@echo ""
	@echo "--- Kubernetes Services ---"
	@ansible all -i hosts -m shell -a "KUBECONFIG=/root/.kube/config kubectl get svc -n vllm-system 2>&1 | head -10 || echo 'No services found'" -b 2>/dev/null || echo "Unable to check services"
	@echo ""
	@echo "--- Docker Containers ---"
	@ansible all -i hosts -m shell -a "docker ps 2>&1 | head -15 || echo 'Cannot get containers'" 2>/dev/null || echo "Unable to check docker containers"
	@echo ""
	@echo "--- Docker Mirror 9P Mount ---"
	@ansible all -i hosts -m shell -a "mount | grep 9p || echo 'No 9P mounts found'" 2>/dev/null || echo "Unable to check 9P mounts"
	@echo ""
	@echo "--- Docker Images (vLLM related) ---"
	@ansible all -i hosts -m shell -a "docker images | grep -E 'REPOSITORY|vllm|openeuler' | head -20 || echo 'No vLLM images found'" 2>/dev/null || echo "Unable to check docker images"
	@echo ""
	@echo "--- Helm Values (Image Configuration) ---"
	@ansible all -i hosts -m shell -a "grep -E 'repository:|tag:|modelURL:' /data/vllm/prod-stack-values.yaml 2>/dev/null | head -10 || echo 'Values file not found'" 2>/dev/null || echo "Unable to check helm values"
	@echo ""

vllm-status-simplified:
	@$(MAKE) -s vllm-status 2>&1 | python3 scripts/vllm-status-summary.py

vllm-quick-test:
	$(Q)bash scripts/vllm-quick-test.sh

vllm-help-menu:
	@echo "vLLM Production Stack options:"
	@echo "vllm                      - Deploy vLLM stack"
	@echo "vllm-deploy               - Deploy vLLM stack (same as vllm)"
	@echo "vllm-benchmark            - Run performance benchmarks and collect results"
	@echo "vllm-monitor              - Display monitoring dashboard URLs"
	@echo "vllm-status               - Check detailed deployment status (verbose)"
	@echo "vllm-status-simplified    - Check deployment status (clean summary)"
	@echo "vllm-quick-test           - Quick API test (baseline + dev if enabled)"
	@echo "vllm-teardown             - Gracefully remove vLLM deployment"
	@echo "vllm-cleanup              - Remove vLLM containers/services (keep binaries & data)"
	@echo "vllm-cleanup-full         - Remove everything including binaries (kubectl, helm, minikube)"
	@echo "vllm-cleanup-purge        - PURGE ALL: Remove binaries + all data directories"
	@echo "vllm-results              - Collect and visualize benchmark results"
	@echo "vllm-visualize-results    - Generate HTML visualization of benchmark results"
	@echo ""

.PHONY: vllm vllm-deploy vllm-benchmark vllm-monitor vllm-status vllm-status-simplified vllm-quick-test vllm-teardown vllm-cleanup vllm-cleanup-full vllm-cleanup-purge vllm-results vllm-visualize-results vllm-help-menu

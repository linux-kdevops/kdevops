MINIO_DATA_TARGET			:= minio
MINIO_DATA_TARGET_INSTALL		:= minio-install
MINIO_DATA_TARGET_UNINSTALL		:= minio-uninstall
MINIO_DATA_TARGET_DESTROY		:= minio-destroy
MINIO_DATA_TARGET_RUN			:= minio-warp
MINIO_DATA_TARGET_RESULTS		:= minio-results

MINIO_PLAYBOOK		:= playbooks/minio.yml

HELP_TARGETS += minio-help

$(MINIO_DATA_TARGET): $(ANSIBLE_INVENTORY_FILE)
	$(Q)$(MAKE) $(MINIO_DATA_TARGET_INSTALL)

$(MINIO_DATA_TARGET_INSTALL): $(ANSIBLE_INVENTORY_FILE)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		$(MINIO_PLAYBOOK) \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--tags vars,minio_install

$(MINIO_DATA_TARGET_UNINSTALL): $(ANSIBLE_INVENTORY_FILE)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		$(MINIO_PLAYBOOK) \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--tags vars,minio_uninstall

$(MINIO_DATA_TARGET_DESTROY): $(ANSIBLE_INVENTORY_FILE)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		$(MINIO_PLAYBOOK) \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--tags vars,minio_destroy

$(MINIO_DATA_TARGET_RUN): $(ANSIBLE_INVENTORY_FILE)
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		$(MINIO_PLAYBOOK) \
		--extra-vars=@$(KDEVOPS_EXTRA_VARS) \
		--tags vars,minio_warp

$(MINIO_DATA_TARGET_RESULTS):
	$(Q)if [ -d workflows/minio/results ]; then \
		python3 workflows/minio/scripts/generate_warp_report.py workflows/minio/results/ && \
		echo "" && \
		echo "📊 MinIO Warp Analysis Complete!" && \
		echo "Results available in workflows/minio/results/" && \
		echo "  - warp_benchmark_report.html (open in browser)" && \
		echo "  - PNG charts for performance visualization" && \
		ls -lh workflows/minio/results/*.png 2>/dev/null | tail -5; \
	else \
		echo "No results directory found. Run 'make minio-warp' first."; \
	fi

minio-help:
	@echo "MinIO Warp S3 benchmarking targets:"
	@echo ""
	@echo "minio                   - Install and setup MinIO server"
	@echo "minio-install           - Install and setup MinIO server"
	@echo "minio-uninstall         - Stop and remove MinIO containers"
	@echo "minio-destroy           - Remove MinIO containers and clean up data"
	@echo "minio-warp              - Run MinIO Warp benchmarks"
	@echo "minio-results           - Collect and analyze benchmark results"
	@echo ""
	@echo "Example usage:"
	@echo "  make defconfig-minio-warp    # Configure for Warp benchmarking"
	@echo "  make bringup                 # Setup test nodes"
	@echo "  make minio                   # Install MinIO server"
	@echo "  make minio-warp              # Run benchmarks"
	@echo "  make minio-results           # Generate analysis and visualizations"
	@echo ""
	@echo "Visualization options:"
	@echo "  - Enable MINIO_WARP_ENABLE_WEB_UI in menuconfig for real-time monitoring"
	@echo "  - Access web UI at http://node-ip:7762 during benchmarks"
	@echo "  - View HTML report: workflows/minio/results/warp_benchmark_report.html"

.PHONY: $(MINIO_DATA_TARGET) $(MINIO_DATA_TARGET_INSTALL) $(MINIO_DATA_TARGET_UNINSTALL)
.PHONY: $(MINIO_DATA_TARGET_DESTROY) $(MINIO_DATA_TARGET_RUN) $(MINIO_DATA_TARGET_RESULTS)
.PHONY: minio-help

# SPDX-License-Identifier: copyleft-next-0.3.1

PCIE_UIO_QEMU_DEP :=
ifeq (y,$(CONFIG_QEMU))
PCIE_UIO_QEMU_DEP := qemu
endif

pcie-uio-deps: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/pcie_uio.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,pcie_uio_deps
PHONY += pcie-uio-deps

pcie-uio-fetch: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/pcie_uio.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,pcie_uio_fetch
PHONY += pcie-uio-fetch

pcie-uio-kernel: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/pcie_uio.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,pcie_uio_kernel
PHONY += pcie-uio-kernel

pcie-uio-image: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/pcie_uio.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,pcie_uio_image
PHONY += pcie-uio-image

pcie-uio-check: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/pcie_uio.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,pcie_uio_check
PHONY += pcie-uio-check

pcie-uio-run: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/pcie_uio.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,pcie_uio_run
PHONY += pcie-uio-run

pcie-uio-results: $(KDEVOPS_EXTRA_VARS)
	$(Q)ansible-playbook \
		$(KDEVOPS_PLAYBOOKS_DIR)/pcie_uio.yml \
		--extra-vars=@./extra_vars.yaml --tags vars,pcie_uio_results
PHONY += pcie-uio-results

pcie-uio: $(PCIE_UIO_QEMU_DEP) pcie-uio-fetch pcie-uio-kernel pcie-uio-image pcie-uio-check pcie-uio-run
PHONY += pcie-uio

pcie-uio-help-menu:
	@echo "pcie-uio: PCIe Unordered I/O control-plane tests (localhost, no bringup):"
	@echo "pcie-uio-deps        - Install kernel-build and libguestfs deps (one-time, may sudo)"
	@echo "pcie-uio             - Build QEMU + kernel + guest image, then run all suites"
	@echo "pcie-uio-fetch       - Clone the PCIe UIO kernel tree and the uio-tests harness"
	@echo "pcie-uio-kernel      - Configure and build the PCIe UIO bzImage"
	@echo "pcie-uio-image       - Download and customize the guest qcow2 image"
	@echo "pcie-uio-check       - Verify KVM access and the QEMU UIO device knobs"
	@echo "pcie-uio-run         - Run the uio-tests suites, collect TAP + dmesg"
	@echo "pcie-uio-results     - Summarize per-suite TAP pass/fail counts"
	@echo ""

HELP_TARGETS += pcie-uio-help-menu

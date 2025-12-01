
PYNFS_GIT:=$(subst ",,$(CONFIG_PYNFS_GIT))
PYNFS_ARGS += pynfs_git=$(PYNFS_GIT)

PYNFS_GIT_TAG:=$(subst ",,$(CONFIG_PYNFS_GIT_TAG))
PYNFS_ARGS += pynfs_git_tag=$(PYNFS_GIT_TAG)

ifeq (y,$(CONFIG_PYNFS_PNFS_BLOCK))
PYNFS_ARGS += pynfs_pnfs_block='True'
endif # CONFIG_PYNFS_PNFS_BLOCK

WORKFLOW_ARGS += $(PYNFS_ARGS)


ifndef LAST_KERNEL
LAST_KERNEL := $(shell cat workflows/pynfs/results/last-kernel.txt 2>/dev/null || ls -1dt workflows/pynfs/results/*/ 2>/dev/null | grep -v "last-run" | head -1 | xargs -r basename)
endif

ifeq ($(LAST_KERNEL), $(shell cat workflows/pynfs/results/last-kernel.txt 2>/dev/null))
FIND_PATH := workflows/pynfs/results/last-run
else
FIND_PATH := workflows/pynfs/results/$(LAST_KERNEL)
endif

ifndef PATTERN
PATTERN := -name "*.json"
endif

ifndef XARGS_ARGS
XARGS_ARGS := -I {} bash -c 'echo "{}:"; cat {}; echo;'
endif

# Makefile for pynfs targets
pynfs:
	$(Q)ansible-playbook \
		--limit 'baseline:dev' \
		--skip-tags run_tests,copy_results,clean_local_results \
		$(KDEVOPS_PLAYBOOKS_DIR)/pynfs.yml

pynfs-baseline:
	$(Q)ansible-playbook \
		--limit 'baseline' \
		--tags vars,first_run,reset \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/pynfs.yml
	$(Q)ansible-playbook \
		--limit 'baseline' \
		--tags vars,run_tests,copy_results \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/pynfs.yml


# Below are the corresponding dev targets
pynfs-dev-baseline:
	$(Q)ansible-playbook \
		--limit 'dev' \
		--tags vars,first_run,reset \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/pynfs.yml
	$(Q)ansible-playbook \
		--limit 'dev' \
		--tags vars,run_tests,copy_results \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/pynfs.yml


pynfs-dev-reset:
	$(Q)ansible-playbook \
		--limit 'dev' \
		--tags vars,reset \
		--extra-vars=@./extra_vars.yaml \
		$(KDEVOPS_PLAYBOOKS_DIR)/pynfs.yml

pynfs-show-results:
	@find $(FIND_PATH) -type f $(PATTERN) \
		| xargs $(XARGS_ARGS) \
		| sed '$${/^$$/d;}'

pynfs-visualize:
	$(Q)if [ ! -d "workflows/pynfs/results/$(LAST_KERNEL)" ]; then \
		echo "Error: No results found for kernel $(LAST_KERNEL)"; \
		echo "Available kernels:"; \
		ls -1 workflows/pynfs/results/ | grep -v last; \
		exit 1; \
	fi
	$(Q)echo "Generating HTML visualization for kernel $(LAST_KERNEL)..."
	$(Q)python3 scripts/workflows/pynfs/visualize_results.py \
		workflows/pynfs/results/$(LAST_KERNEL) \
		$(LAST_KERNEL) \
		--output workflows/pynfs/results/$(LAST_KERNEL)/html/index.html
	$(Q)echo "✅ Visualization complete: workflows/pynfs/results/$(LAST_KERNEL)/html/index.html"

pynfs-help-menu:
	@echo "pynfs options:"
	@echo "pynfs                             - Git clone pynfs, build and install it"
	@echo "pynfs-{baseline,dev}              - Run the pynfs test on baseline  or dev hosts and collect results"
	@echo "pynfs-visualize                   - Generate HTML visualization of test results"
	@echo ""

HELP_TARGETS += pynfs-help-menu

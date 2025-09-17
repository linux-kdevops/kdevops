# SPDX-License-Identifier: copyleft-next-0.3.1
# Dynamic cloud provider Kconfig generation

DYNAMIC_CLOUD_KCONFIG :=
DYNAMIC_CLOUD_KCONFIG_ARGS :=

# Lambda Labs dynamic configuration
LAMBDALABS_KCONFIG_DIR := terraform/lambdalabs/kconfigs
LAMBDALABS_KCONFIG_COMPUTE := $(LAMBDALABS_KCONFIG_DIR)/Kconfig.compute.generated
LAMBDALABS_KCONFIG_LOCATION := $(LAMBDALABS_KCONFIG_DIR)/Kconfig.location.generated
LAMBDALABS_KCONFIG_IMAGES := $(LAMBDALABS_KCONFIG_DIR)/Kconfig.images.generated

LAMBDALABS_KCONFIGS := $(LAMBDALABS_KCONFIG_COMPUTE) $(LAMBDALABS_KCONFIG_LOCATION) $(LAMBDALABS_KCONFIG_IMAGES)

# AWS dynamic configuration
AWS_KCONFIG_DIR := terraform/aws/kconfigs
AWS_KCONFIG_COMPUTE := $(AWS_KCONFIG_DIR)/Kconfig.compute.generated
AWS_KCONFIG_LOCATION := $(AWS_KCONFIG_DIR)/Kconfig.location.generated
AWS_KCONFIG_GPU_AMIS := $(AWS_KCONFIG_DIR)/Kconfig.gpu-amis.generated
AWS_KCONFIG_INSTANCE_TYPES_DIR := $(AWS_KCONFIG_DIR)/instance-types

# Note: Instance type files are generated dynamically, so we just track the main ones
AWS_KCONFIGS := $(AWS_KCONFIG_COMPUTE) $(AWS_KCONFIG_LOCATION) $(AWS_KCONFIG_GPU_AMIS)

# Add generated files to mrproper clean list
KDEVOPS_MRPROPER += $(LAMBDALABS_KCONFIGS) $(AWS_KCONFIGS)

# Touch Lambda Labs generated files so Kconfig can source them
# This ensures the files exist (even if empty) before Kconfig runs
dynamic_lambdalabs_kconfig_touch:
	$(Q)touch $(LAMBDALABS_KCONFIGS)

DYNAMIC_KCONFIG += dynamic_lambdalabs_kconfig_touch

# Touch AWS generated files so Kconfig can source them
dynamic_aws_kconfig_touch:
	$(Q)mkdir -p $(AWS_KCONFIG_INSTANCE_TYPES_DIR)
	$(Q)touch $(AWS_KCONFIGS)

DYNAMIC_KCONFIG += dynamic_aws_kconfig_touch

# Individual Lambda Labs targets are now handled by generate_cloud_configs.py
cloud-config-lambdalabs:
	$(Q)python3 scripts/generate_cloud_configs.py

# AWS targets using Chuck's scripts with caching
cloud-config-aws:
	$(Q)python3 terraform/aws/scripts/generate_aws_kconfig.py

# AWS cache refresh (clears cache and regenerates)
cloud-update-aws:
	$(Q)python3 terraform/aws/scripts/generate_aws_kconfig.py clear-cache
	$(Q)python3 terraform/aws/scripts/generate_aws_kconfig.py

# Clean Lambda Labs generated files
clean-cloud-config-lambdalabs:
	$(Q)rm -f $(LAMBDALABS_KCONFIGS)

# Clean AWS generated files
clean-cloud-config-aws:
	$(Q)rm -f $(AWS_KCONFIGS)
	$(Q)rm -rf $(AWS_KCONFIG_INSTANCE_TYPES_DIR)

DYNAMIC_CLOUD_KCONFIG += cloud-config-lambdalabs cloud-config-aws

cloud-config-help:
	@echo "Cloud-specific dynamic kconfig targets:"
	@echo "cloud-config            - generates all cloud provider dynamic kconfig content"
	@echo "cloud-config-lambdalabs - generates Lambda Labs dynamic kconfig content"
	@echo "cloud-config-aws        - generates AWS dynamic kconfig content"
	@echo "cloud-update            - refreshes cloud provider data (clears cache)"
	@echo "cloud-update-aws        - refreshes AWS data (clears cache and regenerates)"
	@echo "clean-cloud-config      - removes all generated cloud kconfig files"
	@echo "cloud-list-all          - list all cloud instances for configured provider"
	@echo "cloud-bill              - show current month's cloud provider costs"
	@echo "cloud-bill-aws          - show AWS costs for current month"

HELP_TARGETS += cloud-config-help

cloud-config:
	$(Q)python3 scripts/generate_cloud_configs.py

cloud-update: cloud-update-aws
	$(Q)echo "Updated cloud provider configurations."

clean-cloud-config: clean-cloud-config-lambdalabs clean-cloud-config-aws
	$(Q)echo "Cleaned all cloud provider dynamic Kconfig files."

cloud-list-all:
	$(Q)chmod +x scripts/cloud_list_all.sh
	$(Q)scripts/cloud_list_all.sh

# Cloud billing targets
cloud-bill-aws:
	$(Q)chmod +x scripts/aws-costs.sh
	$(Q)scripts/aws-costs.sh

cloud-bill: cloud-bill-aws
	$(Q)echo ""
	$(Q)echo "Note: Only AWS billing is currently supported"

PHONY += cloud-config cloud-config-lambdalabs cloud-config-aws cloud-update cloud-update-aws
PHONY += clean-cloud-config clean-cloud-config-lambdalabs clean-cloud-config-aws
PHONY += cloud-config-help cloud-list-all cloud-bill cloud-bill-aws

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

# Individual Lambda Labs targets are now handled by generate_cloud_configs.py
cloud-config-lambdalabs:
	$(Q)python3 scripts/generate_cloud_configs.py

# Clean Lambda Labs generated files
clean-cloud-config-lambdalabs:
	$(Q)rm -f $(LAMBDALABS_KCONFIGS)

DYNAMIC_CLOUD_KCONFIG += cloud-config-lambdalabs

cloud-config-help:
	@echo "Cloud-specific dynamic kconfig targets:"
	@echo "cloud-config            - generates all cloud provider dynamic kconfig content"
	@echo "cloud-config-lambdalabs - generates Lambda Labs dynamic kconfig content"
	@echo "clean-cloud-config      - removes all generated cloud kconfig files"
	@echo "cloud-list-all          - list all cloud instances for configured provider"

HELP_TARGETS += cloud-config-help

cloud-config:
	$(Q)python3 scripts/generate_cloud_configs.py

clean-cloud-config: clean-cloud-config-lambdalabs
	$(Q)echo "Cleaned all cloud provider dynamic Kconfig files."

cloud-list-all:
	$(Q)chmod +x scripts/cloud_list_all.sh
	$(Q)scripts/cloud_list_all.sh

PHONY += cloud-config cloud-config-lambdalabs clean-cloud-config clean-cloud-config-lambdalabs cloud-config-help cloud-list-all

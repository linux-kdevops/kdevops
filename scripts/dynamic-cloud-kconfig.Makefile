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
AWS_KCONFIG_AMI := $(AWS_KCONFIG_DIR)/Kconfig.ami.generated
AWS_KCONFIG_INSTANCE := $(AWS_KCONFIG_DIR)/Kconfig.instance.generated
AWS_KCONFIG_LOCATION := $(AWS_KCONFIG_DIR)/Kconfig.location.generated

AWS_KCONFIGS := $(AWS_KCONFIG_AMI) $(AWS_KCONFIG_INSTANCE) $(AWS_KCONFIG_LOCATION)

# OCI dynamic configuration
OCI_KCONFIG_DIR := terraform/oci/kconfigs
OCI_KCONFIG_LOCATION := $(OCI_KCONFIG_DIR)/Kconfig.location.generated
OCI_KCONFIG_SHAPE := $(OCI_KCONFIG_DIR)/Kconfig.shape.generated

OCI_KCONFIGS := $(OCI_KCONFIG_LOCATION) $(OCI_KCONFIG_SHAPE)

# Add generated files to mrproper clean list
KDEVOPS_MRPROPER += $(LAMBDALABS_KCONFIGS) $(AWS_KCONFIGS) $(OCI_KCONFIGS)

# Touch Lambda Labs generated files so Kconfig can source them
# This ensures the files exist (even if empty) before Kconfig runs
dynamic_lambdalabs_kconfig_touch:
	$(Q)touch $(LAMBDALABS_KCONFIGS)

# Touch AWS generated files so Kconfig can source them
dynamic_aws_kconfig_touch:
	$(Q)touch $(AWS_KCONFIGS)

# Touch OCI generated files so Kconfig can source them
dynamic_oci_kconfig_touch:
	$(Q)touch $(OCI_KCONFIGS)

DYNAMIC_KCONFIG += dynamic_lambdalabs_kconfig_touch dynamic_aws_kconfig_touch dynamic_oci_kconfig_touch

# Lambda Labs targets use --provider argument for efficiency
cloud-config-lambdalabs:
	$(Q)python3 scripts/generate_cloud_configs.py --provider lambdalabs

# AWS targets use --provider argument for efficiency
cloud-config-aws:
	$(Q)python3 scripts/generate_cloud_configs.py --provider aws

# OCI targets use --provider argument for efficiency
cloud-config-oci:
	$(Q)python3 scripts/generate_cloud_configs.py --provider oci

# Clean Lambda Labs generated files
clean-cloud-config-lambdalabs:
	$(Q)rm -f $(LAMBDALABS_KCONFIGS)

# Clean AWS generated files
clean-cloud-config-aws:
	$(Q)rm -f $(AWS_KCONFIGS)

# Clean OCI generated files
clean-cloud-config-oci:
	$(Q)rm -f $(OCI_KCONFIGS)

DYNAMIC_CLOUD_KCONFIG += cloud-config-lambdalabs cloud-config-aws cloud-config-oci

cloud-config-help:
	@echo "Cloud-specific dynamic kconfig targets:"
	@echo "cloud-config            - generates all cloud provider dynamic kconfig content"
	@echo "cloud-config-lambdalabs - generates Lambda Labs dynamic kconfig content"
	@echo "cloud-config-aws        - generates AWS dynamic kconfig content"
	@echo "clean-cloud-config      - removes all generated cloud kconfig files"
	@echo "cloud-list-all          - list all cloud instances for configured provider"

HELP_TARGETS += cloud-config-help

cloud-config:
	$(Q)python3 scripts/generate_cloud_configs.py

clean-cloud-config: clean-cloud-config-lambdalabs clean-cloud-config-aws
	$(Q)echo "Cleaned all cloud provider dynamic Kconfig files."

cloud-list-all:
	$(Q)chmod +x scripts/cloud_list_all.sh
	$(Q)scripts/cloud_list_all.sh

PHONY += cloud-config clean-cloud-config cloud-config-help cloud-list-all
PHONY += cloud-config-aws clean-cloud-config-aws
PHONY += cloud-config-lambdalabs clean-cloud-config-lambdalabs
PHONY += cloud-config-oci clean-cloud-config-oci

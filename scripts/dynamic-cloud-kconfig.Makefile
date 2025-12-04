# SPDX-License-Identifier: copyleft-next-0.3.1
# Dynamic cloud provider Kconfig generation

DYNAMIC_CLOUD_KCONFIG :=
DYNAMIC_CLOUD_KCONFIG_ARGS :=

# Lambda Labs dynamic configuration
LAMBDALABS_KCONFIG_DIR := terraform/lambdalabs/kconfigs
LAMBDALABS_KCONFIG_COMPUTE := $(LAMBDALABS_KCONFIG_DIR)/Kconfig.compute.generated
LAMBDALABS_KCONFIG_LOCATION := $(LAMBDALABS_KCONFIG_DIR)/Kconfig.location.generated
LAMBDALABS_KCONFIG_IMAGES := $(LAMBDALABS_KCONFIG_DIR)/Kconfig.images.generated

# Lambda Labs default files (tracked in git, provide sensible defaults)
LAMBDALABS_KCONFIG_COMPUTE_DEFAULT := $(LAMBDALABS_KCONFIG_DIR)/Kconfig.compute.default
LAMBDALABS_KCONFIG_LOCATION_DEFAULT := $(LAMBDALABS_KCONFIG_DIR)/Kconfig.location.default
LAMBDALABS_KCONFIG_IMAGES_DEFAULT := $(LAMBDALABS_KCONFIG_DIR)/Kconfig.images.default

LAMBDALABS_KCONFIGS := $(LAMBDALABS_KCONFIG_COMPUTE) $(LAMBDALABS_KCONFIG_LOCATION) $(LAMBDALABS_KCONFIG_IMAGES)

# AWS dynamic configuration
AWS_KCONFIG_DIR := terraform/aws/kconfigs
AWS_KCONFIG_AMI := $(AWS_KCONFIG_DIR)/Kconfig.ami.generated
AWS_KCONFIG_INSTANCE := $(AWS_KCONFIG_DIR)/Kconfig.instance.generated
AWS_KCONFIG_LOCATION := $(AWS_KCONFIG_DIR)/Kconfig.location.generated

# AWS default files (tracked in git, provide sensible defaults)
AWS_KCONFIG_AMI_DEFAULT := $(AWS_KCONFIG_DIR)/Kconfig.ami.default
AWS_KCONFIG_INSTANCE_DEFAULT := $(AWS_KCONFIG_DIR)/Kconfig.instance.default
AWS_KCONFIG_LOCATION_DEFAULT := $(AWS_KCONFIG_DIR)/Kconfig.location.default

AWS_KCONFIGS := $(AWS_KCONFIG_AMI) $(AWS_KCONFIG_INSTANCE) $(AWS_KCONFIG_LOCATION)

# Azure dynamic configuration
AZURE_KCONFIG_DIR := terraform/azure/kconfigs
AZURE_KCONFIG_IMAGE := $(AZURE_KCONFIG_DIR)/Kconfig.image.generated
AZURE_KCONFIG_LOCATION := $(AZURE_KCONFIG_DIR)/Kconfig.location.generated
AZURE_KCONFIG_SIZE := $(AZURE_KCONFIG_DIR)/Kconfig.size.generated

# Azure default files (tracked in git, provide sensible defaults)
AZURE_KCONFIG_IMAGE_DEFAULT := $(AZURE_KCONFIG_DIR)/Kconfig.image.default
AZURE_KCONFIG_LOCATION_DEFAULT := $(AZURE_KCONFIG_DIR)/Kconfig.location.default
AZURE_KCONFIG_SIZE_DEFAULT := $(AZURE_KCONFIG_DIR)/Kconfig.size.default

AZURE_KCONFIGS := $(AZURE_KCONFIG_LOCATION) $(AZURE_KCONFIG_SIZE) $(AZURE_KCONFIG_IMAGE)

# GCE dynamic configuration
GCE_KCONFIG_DIR := terraform/gce/kconfigs
GCE_KCONFIG_IMAGE := $(GCE_KCONFIG_DIR)/Kconfig.image.generated
GCE_KCONFIG_LOCATION := $(GCE_KCONFIG_DIR)/Kconfig.location.generated
GCE_KCONFIG_MACHINE := $(GCE_KCONFIG_DIR)/Kconfig.machine.generated

# GCE default files (tracked in git, provide sensible defaults)
GCE_KCONFIG_IMAGE_DEFAULT := $(GCE_KCONFIG_DIR)/Kconfig.image.default
GCE_KCONFIG_LOCATION_DEFAULT := $(GCE_KCONFIG_DIR)/Kconfig.location.default
GCE_KCONFIG_MACHINE_DEFAULT := $(GCE_KCONFIG_DIR)/Kconfig.machine.default

GCE_KCONFIGS := $(GCE_KCONFIG_IMAGE) $(GCE_KCONFIG_LOCATION) $(GCE_KCONFIG_MACHINE)

# OCI dynamic configuration
OCI_KCONFIG_DIR := terraform/oci/kconfigs
OCI_KCONFIG_IMAGE := $(OCI_KCONFIG_DIR)/Kconfig.image.generated
OCI_KCONFIG_LOCATION := $(OCI_KCONFIG_DIR)/Kconfig.location.generated
OCI_KCONFIG_SHAPE := $(OCI_KCONFIG_DIR)/Kconfig.shape.generated

# OCI default files (tracked in git, provide sensible defaults)
OCI_KCONFIG_IMAGE_DEFAULT := $(OCI_KCONFIG_DIR)/Kconfig.image.default
OCI_KCONFIG_LOCATION_DEFAULT := $(OCI_KCONFIG_DIR)/Kconfig.location.default
OCI_KCONFIG_SHAPE_DEFAULT := $(OCI_KCONFIG_DIR)/Kconfig.shape.default

OCI_KCONFIGS := $(OCI_KCONFIG_IMAGE) $(OCI_KCONFIG_LOCATION) $(OCI_KCONFIG_SHAPE)

# DataCrunch dynamic configuration
DATACRUNCH_KCONFIG_DIR := terraform/datacrunch/kconfigs
DATACRUNCH_KCONFIG_COMPUTE := $(DATACRUNCH_KCONFIG_DIR)/Kconfig.compute.generated
DATACRUNCH_KCONFIG_IMAGES := $(DATACRUNCH_KCONFIG_DIR)/Kconfig.images.generated
DATACRUNCH_KCONFIG_LOCATION := $(DATACRUNCH_KCONFIG_DIR)/Kconfig.location.generated

# DataCrunch default files (tracked in git, provide sensible defaults)
DATACRUNCH_KCONFIG_COMPUTE_DEFAULT := $(DATACRUNCH_KCONFIG_DIR)/Kconfig.compute.default
DATACRUNCH_KCONFIG_IMAGES_DEFAULT := $(DATACRUNCH_KCONFIG_DIR)/Kconfig.images.default
DATACRUNCH_KCONFIG_LOCATION_DEFAULT := $(DATACRUNCH_KCONFIG_DIR)/Kconfig.location.default

DATACRUNCH_KCONFIGS := $(DATACRUNCH_KCONFIG_COMPUTE) $(DATACRUNCH_KCONFIG_IMAGES) $(DATACRUNCH_KCONFIG_LOCATION)

# Add generated files to mrproper clean list
KDEVOPS_MRPROPER += $(LAMBDALABS_KCONFIGS) $(AWS_KCONFIGS) $(AZURE_KCONFIGS) $(GCE_KCONFIGS) $(OCI_KCONFIGS) $(DATACRUNCH_KCONFIGS)

# Ensure Lambda Labs generated files exist with sensible defaults
# Copies from .default files if .generated files don't exist
dynamic_lambdalabs_kconfig_touch:
	$(Q)test -f $(LAMBDALABS_KCONFIG_COMPUTE) || cp $(LAMBDALABS_KCONFIG_COMPUTE_DEFAULT) $(LAMBDALABS_KCONFIG_COMPUTE)
	$(Q)test -f $(LAMBDALABS_KCONFIG_LOCATION) || cp $(LAMBDALABS_KCONFIG_LOCATION_DEFAULT) $(LAMBDALABS_KCONFIG_LOCATION)
	$(Q)test -f $(LAMBDALABS_KCONFIG_IMAGES) || cp $(LAMBDALABS_KCONFIG_IMAGES_DEFAULT) $(LAMBDALABS_KCONFIG_IMAGES)

# Ensure AWS generated files exist with sensible defaults
# Copies from .default files if .generated files don't exist
dynamic_aws_kconfig_touch:
	$(Q)test -f $(AWS_KCONFIG_AMI) || cp $(AWS_KCONFIG_AMI_DEFAULT) $(AWS_KCONFIG_AMI)
	$(Q)test -f $(AWS_KCONFIG_INSTANCE) || cp $(AWS_KCONFIG_INSTANCE_DEFAULT) $(AWS_KCONFIG_INSTANCE)
	$(Q)test -f $(AWS_KCONFIG_LOCATION) || cp $(AWS_KCONFIG_LOCATION_DEFAULT) $(AWS_KCONFIG_LOCATION)

# Ensure Azure generated files exist with sensible defaults
# Copies from .default files if .generated files don't exist
dynamic_azure_kconfig_touch:
	$(Q)test -f $(AZURE_KCONFIG_IMAGE) || cp $(AZURE_KCONFIG_IMAGE_DEFAULT) $(AZURE_KCONFIG_IMAGE)
	$(Q)test -f $(AZURE_KCONFIG_LOCATION) || cp $(AZURE_KCONFIG_LOCATION_DEFAULT) $(AZURE_KCONFIG_LOCATION)
	$(Q)test -f $(AZURE_KCONFIG_SIZE) || cp $(AZURE_KCONFIG_SIZE_DEFAULT) $(AZURE_KCONFIG_SIZE)

# Ensure GCE generated files exist with sensible defaults
# Copies from .default files if .generated files don't exist
dynamic_gce_kconfig_touch:
	$(Q)test -f $(GCE_KCONFIG_IMAGE) || cp $(GCE_KCONFIG_IMAGE_DEFAULT) $(GCE_KCONFIG_IMAGE)
	$(Q)test -f $(GCE_KCONFIG_LOCATION) || cp $(GCE_KCONFIG_LOCATION_DEFAULT) $(GCE_KCONFIG_LOCATION)
	$(Q)test -f $(GCE_KCONFIG_MACHINE) || cp $(GCE_KCONFIG_MACHINE_DEFAULT) $(GCE_KCONFIG_MACHINE)

# Ensure OCI generated files exist with sensible defaults
# Copies from .default files if .generated files don't exist
dynamic_oci_kconfig_touch:
	$(Q)test -f $(OCI_KCONFIG_IMAGE) || cp $(OCI_KCONFIG_IMAGE_DEFAULT) $(OCI_KCONFIG_IMAGE)
	$(Q)test -f $(OCI_KCONFIG_LOCATION) || cp $(OCI_KCONFIG_LOCATION_DEFAULT) $(OCI_KCONFIG_LOCATION)
	$(Q)test -f $(OCI_KCONFIG_SHAPE) || cp $(OCI_KCONFIG_SHAPE_DEFAULT) $(OCI_KCONFIG_SHAPE)

# Ensure DataCrunch generated files exist with sensible defaults
# Copies from .default files if .generated files don't exist
dynamic_datacrunch_kconfig_touch:
	$(Q)test -f $(DATACRUNCH_KCONFIG_COMPUTE) || cp $(DATACRUNCH_KCONFIG_COMPUTE_DEFAULT) $(DATACRUNCH_KCONFIG_COMPUTE)
	$(Q)test -f $(DATACRUNCH_KCONFIG_IMAGES) || cp $(DATACRUNCH_KCONFIG_IMAGES_DEFAULT) $(DATACRUNCH_KCONFIG_IMAGES)
	$(Q)test -f $(DATACRUNCH_KCONFIG_LOCATION) || cp $(DATACRUNCH_KCONFIG_LOCATION_DEFAULT) $(DATACRUNCH_KCONFIG_LOCATION)

DYNAMIC_KCONFIG += dynamic_lambdalabs_kconfig_touch dynamic_aws_kconfig_touch dynamic_azure_kconfig_touch dynamic_gce_kconfig_touch dynamic_oci_kconfig_touch dynamic_datacrunch_kconfig_touch

# User-facing target to populate cloud kconfigs with defaults
# This is called automatically before menuconfig, but can be run manually
default-cloud-kconfigs: dynamic_lambdalabs_kconfig_touch dynamic_aws_kconfig_touch dynamic_azure_kconfig_touch dynamic_gce_kconfig_touch dynamic_oci_kconfig_touch dynamic_datacrunch_kconfig_touch

# Lambda Labs targets use --provider argument for efficiency
cloud-config-lambdalabs:
	$(Q)python3 scripts/generate_cloud_configs.py --provider lambdalabs

# AWS targets use --provider argument for efficiency
cloud-config-aws:
	$(Q)python3 scripts/generate_cloud_configs.py --provider aws

# Azure targets use --provider argument for efficiency
cloud-config-azure:
	$(Q)python3 scripts/generate_cloud_configs.py --provider azure

# GCE targets use --provider argument for efficiency
cloud-config-gce:
	$(Q)python3 scripts/generate_cloud_configs.py --provider gce

# OCI targets use --provider argument for efficiency
cloud-config-oci:
	$(Q)python3 scripts/generate_cloud_configs.py --provider oci

# DataCrunch targets use --provider argument for efficiency
cloud-config-datacrunch:
	$(Q)python3 scripts/generate_cloud_configs.py --provider datacrunch

# Clean Lambda Labs generated files
clean-cloud-config-lambdalabs:
	$(Q)rm -f $(LAMBDALABS_KCONFIGS)

# Clean AWS generated files
clean-cloud-config-aws:
	$(Q)rm -f $(AWS_KCONFIGS)

# Clean Azure generated files
clean-cloud-config-azure:
	$(Q)rm -f $(AZURE_KCONFIGS)

# Clean GCE generated files
clean-cloud-config-gce:
	$(Q)rm -f $(GCE_KCONFIGS)

# Clean OCI generated files
clean-cloud-config-oci:
	$(Q)rm -f $(OCI_KCONFIGS)

# Clean DataCrunch generated files
clean-cloud-config-datacrunch:
	$(Q)rm -f $(DATACRUNCH_KCONFIGS)

DYNAMIC_CLOUD_KCONFIG += cloud-config-lambdalabs cloud-config-aws cloud-config-azure cloud-config-gce cloud-config-oci cloud-config-datacrunch

cloud-config-help:
	@echo "Cloud-specific dynamic kconfig targets:"
	@echo "default-cloud-kconfigs   - populate cloud kconfigs with defaults (auto-runs before menuconfig)"
	@echo "cloud-config             - regenerate cloud kconfigs from live API data"
	@echo "cloud-config-lambdalabs  - generates Lambda Labs dynamic kconfig content"
	@echo "cloud-config-aws         - generates AWS dynamic kconfig content"
	@echo "cloud-config-azure       - generates Azure dynamic kconfig content"
	@echo "cloud-config-gce         - generates GCE dynamic kconfig content"
	@echo "cloud-config-oci         - generates OCI dynamic kconfig content"
	@echo "cloud-config-datacrunch  - generates DataCrunch dynamic kconfig content"
	@echo "clean-cloud-config       - removes all generated cloud kconfig files"
	@echo "cloud-list-all           - list all cloud instances for configured provider"

HELP_TARGETS += cloud-config-help

cloud-config:
	$(Q)python3 scripts/generate_cloud_configs.py

clean-cloud-config: clean-cloud-config-lambdalabs clean-cloud-config-aws clean-cloud-config-azure clean-cloud-config-gce clean-cloud-config-oci clean-cloud-config-datacrunch
	$(Q)echo "Cleaned all cloud provider dynamic Kconfig files."

cloud-list-all:
	$(Q)chmod +x scripts/cloud_list_all.sh
	$(Q)scripts/cloud_list_all.sh

PHONY += cloud-config clean-cloud-config cloud-config-help cloud-list-all default-cloud-kconfigs
PHONY += cloud-config-aws clean-cloud-config-aws
PHONY += cloud-config-azure clean-cloud-config-azure
PHONY += cloud-config-gce clean-cloud-config-gce
PHONY += cloud-config-datacrunch clean-cloud-config-datacrunch
PHONY += cloud-config-lambdalabs clean-cloud-config-lambdalabs
PHONY += cloud-config-oci clean-cloud-config-oci

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
AWS_INSTANCE_TYPES_DIR := $(AWS_KCONFIG_DIR)/instance-types

# List of AWS instance type family files that will be generated
AWS_INSTANCE_TYPE_FAMILIES := m5 m7a t3 t3a c5 c7a i4i is4gen im4gn
AWS_INSTANCE_TYPE_KCONFIGS := $(foreach family,$(AWS_INSTANCE_TYPE_FAMILIES),$(AWS_INSTANCE_TYPES_DIR)/Kconfig.$(family).generated)

AWS_KCONFIGS := $(AWS_KCONFIG_COMPUTE) $(AWS_KCONFIG_LOCATION) $(AWS_INSTANCE_TYPE_KCONFIGS)

# Add Lambda Labs generated files to mrproper clean list
KDEVOPS_MRPROPER += $(LAMBDALABS_KCONFIGS)

# Add AWS generated files to mrproper clean list
KDEVOPS_MRPROPER += $(AWS_KCONFIGS)

# Touch Lambda Labs generated files so Kconfig can source them
# This ensures the files exist (even if empty) before Kconfig runs
dynamic_lambdalabs_kconfig_touch:
	$(Q)touch $(LAMBDALABS_KCONFIGS)

DYNAMIC_KCONFIG += dynamic_lambdalabs_kconfig_touch

# Touch AWS generated files so Kconfig can source them
# This ensures the files exist (even if empty) before Kconfig runs
dynamic_aws_kconfig_touch:
	$(Q)mkdir -p $(AWS_INSTANCE_TYPES_DIR)
	$(Q)touch $(AWS_KCONFIG_COMPUTE) $(AWS_KCONFIG_LOCATION)
	$(Q)touch $(AWS_KCONFIG_DIR)/Kconfig.gpu-amis.generated
	$(Q)for family in $(AWS_INSTANCE_TYPE_FAMILIES); do \
		touch $(AWS_INSTANCE_TYPES_DIR)/Kconfig.$$family.generated; \
	done
	# Touch all existing generated files
	$(Q)for file in $(AWS_INSTANCE_TYPES_DIR)/Kconfig.*.generated; do \
		if [ -f "$$file" ]; then \
			touch "$$file"; \
		fi; \
	done

DYNAMIC_KCONFIG += dynamic_aws_kconfig_touch

# Individual Lambda Labs targets are now handled by generate_cloud_configs.py
cloud-config-lambdalabs:
	$(Q)python3 scripts/generate_cloud_configs.py

# Individual AWS targets are now handled by generate_cloud_configs.py
cloud-config-aws:
	$(Q)python3 scripts/generate_cloud_configs.py

# Clean Lambda Labs generated files
clean-cloud-config-lambdalabs:
	$(Q)rm -f $(LAMBDALABS_KCONFIGS)

# Clean AWS generated files
clean-cloud-config-aws:
	$(Q)rm -f $(AWS_KCONFIGS)

DYNAMIC_CLOUD_KCONFIG += cloud-config-lambdalabs cloud-config-aws

cloud-config-help:
	@echo "Cloud-specific dynamic kconfig targets:"
	@echo "cloud-config            - generates all cloud provider dynamic kconfig content"
	@echo "cloud-config-lambdalabs - generates Lambda Labs dynamic kconfig content"
	@echo "cloud-config-aws        - generates AWS dynamic kconfig content"
	@echo "cloud-update            - converts generated cloud configs to static (for committing)"
	@echo "clean-cloud-config      - removes all generated cloud kconfig files"
	@echo "cloud-list-all          - list all cloud instances for configured provider"

HELP_TARGETS += cloud-config-help

cloud-config:
	$(Q)python3 scripts/generate_cloud_configs.py

clean-cloud-config: clean-cloud-config-lambdalabs clean-cloud-config-aws
	$(Q)rm -f .cloud.initialized
	$(Q)echo "Cleaned all cloud provider dynamic Kconfig files."

cloud-list-all:
	$(Q)chmod +x scripts/cloud_list_all.sh
	$(Q)scripts/cloud_list_all.sh

# Convert dynamically generated cloud configs to static versions for git commits
# This allows admins to generate configs once and commit them for regular users
cloud-update:
	@echo "Converting generated cloud configs to static versions..."
	# AWS configs
	$(Q)if [ -f $(AWS_KCONFIG_COMPUTE) ]; then \
		cp $(AWS_KCONFIG_COMPUTE) $(AWS_KCONFIG_DIR)/Kconfig.compute.static; \
		sed -i 's/Kconfig\.\([^.]*\)\.generated/Kconfig.\1.static/g' $(AWS_KCONFIG_DIR)/Kconfig.compute.static; \
		echo "  Created $(AWS_KCONFIG_DIR)/Kconfig.compute.static"; \
	fi
	$(Q)if [ -f $(AWS_KCONFIG_LOCATION) ]; then \
		cp $(AWS_KCONFIG_LOCATION) $(AWS_KCONFIG_DIR)/Kconfig.location.static; \
		sed -i 's/Kconfig\.\([^.]*\)\.generated/Kconfig.\1.static/g' $(AWS_KCONFIG_DIR)/Kconfig.location.static; \
		echo "  Created $(AWS_KCONFIG_DIR)/Kconfig.location.static"; \
	fi
	# AWS instance type families
	$(Q)for file in $(AWS_INSTANCE_TYPES_DIR)/Kconfig.*.generated; do \
		if [ -f "$$file" ]; then \
			static_file=$$(echo "$$file" | sed 's/\.generated$$/\.static/'); \
			cp "$$file" "$$static_file"; \
			echo "  Created $$static_file"; \
		fi; \
	done
	# Lambda Labs configs
	$(Q)if [ -f $(LAMBDALABS_KCONFIG_COMPUTE) ]; then \
		cp $(LAMBDALABS_KCONFIG_COMPUTE) $(LAMBDALABS_KCONFIG_DIR)/Kconfig.compute.static; \
		echo "  Created $(LAMBDALABS_KCONFIG_DIR)/Kconfig.compute.static"; \
	fi
	$(Q)if [ -f $(LAMBDALABS_KCONFIG_LOCATION) ]; then \
		cp $(LAMBDALABS_KCONFIG_LOCATION) $(LAMBDALABS_KCONFIG_DIR)/Kconfig.location.static; \
		echo "  Created $(LAMBDALABS_KCONFIG_DIR)/Kconfig.location.static"; \
	fi
	$(Q)if [ -f $(LAMBDALABS_KCONFIG_IMAGES) ]; then \
		cp $(LAMBDALABS_KCONFIG_IMAGES) $(LAMBDALABS_KCONFIG_DIR)/Kconfig.images.static; \
		echo "  Created $(LAMBDALABS_KCONFIG_DIR)/Kconfig.images.static"; \
	fi
	@echo "Static cloud configs created. You can now commit these .static files to git."

PHONY += cloud-config cloud-config-lambdalabs cloud-config-aws clean-cloud-config clean-cloud-config-lambdalabs clean-cloud-config-aws cloud-config-help cloud-list-all cloud-update

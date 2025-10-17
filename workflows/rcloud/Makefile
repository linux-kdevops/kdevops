RCLOUD_WORKFLOW := workflows/rcloud

# Check if rcloud is enabled
ifeq (y,$(CONFIG_RCLOUD))

# Extract port from bind address, removing quotes
RCLOUD_PORT := $(shell echo $(CONFIG_RCLOUD_SERVER_BIND) | sed -e 's/.*://' -e 's/"//g')

RCLOUD_DEPS :=

# Add rcloud-build to default dependencies so 'make' builds rcloud
DEFAULT_DEPS += rcloud-build

# Check build prerequisites
rcloud-check-deps:
	@echo "Checking rcloud build dependencies..."
	@command -v cargo >/dev/null 2>&1 || \
		{ echo "ERROR: cargo not found. Install dependencies with 'make rcloud-deps' or install cargo package."; exit 1; }
	@command -v rustc >/dev/null 2>&1 || \
		{ echo "ERROR: rustc not found. Install dependencies with 'make rcloud-deps' or install rustc package."; exit 1; }
	@command -v pkg-config >/dev/null 2>&1 || \
		{ echo "ERROR: pkg-config not found. Install pkg-config package."; exit 1; }
	@pkg-config --exists libvirt 2>/dev/null || \
		{ echo "ERROR: libvirt development libraries not found. Install libvirt-dev (Debian) or libvirt-devel (RPM) package."; exit 1; }
	@echo "All build dependencies satisfied"

# Build rcloud Rust binary
$(RCLOUD_WORKFLOW)/target/release/rcloud: rcloud-check-deps $(RCLOUD_DEPS) FORCE
	@echo "Building rcloud REST API server..."
	$(Q)cd $(RCLOUD_WORKFLOW) && cargo build --release
	@echo "rcloud binary built at $(RCLOUD_WORKFLOW)/target/release/rcloud"

# Build Terraform provider if enabled
ifeq (y,$(CONFIG_RCLOUD_ENABLE_TERRAFORM_PROVIDER))
# Check Go is available for Terraform provider build
rcloud-check-go-deps:
	@echo "Checking Go build dependencies..."
	@command -v go >/dev/null 2>&1 || \
		{ echo "ERROR: go not found. Install dependencies with 'make rcloud-deps' or install golang package."; exit 1; }
	@echo "Go dependencies satisfied"

terraform-provider-rcloud/terraform-provider-rcloud: rcloud-check-go-deps FORCE
	@echo "Building Terraform provider for rcloud..."
	$(Q)cd terraform-provider-rcloud && go build
	@echo "Terraform provider built at terraform-provider-rcloud/terraform-provider-rcloud"

RCLOUD_DEPS += terraform-provider-rcloud/terraform-provider-rcloud
endif

# Default target: build rcloud and dependencies
rcloud-build: $(RCLOUD_WORKFLOW)/target/release/rcloud $(RCLOUD_DEPS)
	@echo "rcloud build complete"

# Create base images with proper customization (networking, SSH, users, etc.)
rcloud-base-images:
	@echo "Creating base images with virt-builder customization..."
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'localhost' \
		--extra-vars=@./extra_vars.yaml \
		--tags network,pool,base_image \
		playbooks/guestfs.yml
	@echo "Base images created and customized"

# Install rcloud (copy binary, setup systemd service, install Terraform provider)
rcloud: rcloud-build rcloud-base-images
	@echo "Installing rcloud..."
	$(Q)ansible-playbook $(ANSIBLE_VERBOSE) \
		--extra-vars=@./extra_vars.yaml  \
		-i inventory/hosts \
		playbooks/rcloud.yml
ifeq (y,$(CONFIG_RCLOUD_ENABLE_TERRAFORM_PROVIDER))
	@echo "Installing Terraform provider to local plugin directory..."
	$(Q)mkdir -p ~/.terraform.d/plugins/registry.terraform.io/kdevops/rcloud/0.1.0/linux_amd64
	$(Q)cp terraform-provider-rcloud/terraform-provider-rcloud \
		~/.terraform.d/plugins/registry.terraform.io/kdevops/rcloud/0.1.0/linux_amd64/
	@echo "Terraform provider installed to ~/.terraform.d/"
endif
	@echo "rcloud installed and configured"
	@echo ""
	@echo "Starting rcloud service..."
	$(Q)sudo systemctl start rcloud
	@echo ""
	@echo "Checking rcloud service status..."
	$(Q)sudo systemctl status rcloud --no-pager || true
	@echo ""
	@echo "rcloud service started successfully"
	@echo ""
	$(Q)$(RCLOUD_WORKFLOW)/scripts/check-health.py http://localhost:$(RCLOUD_PORT)

# Check rcloud service health and status
rcloud-status:
	@echo "Checking rcloud service health..."
	@echo ""
	$(Q)$(RCLOUD_WORKFLOW)/scripts/check-health.py http://localhost:$(RCLOUD_PORT)

# Install Terraform provider to local development directory
rcloud-terraform-install: terraform-provider-rcloud/terraform-provider-rcloud
	@echo "Installing Terraform provider to local plugin directory..."
	$(Q)mkdir -p ~/.terraform.d/plugins/registry.terraform.io/kdevops/rcloud/0.1.0/linux_amd64
	$(Q)cp terraform-provider-rcloud/terraform-provider-rcloud \
		~/.terraform.d/plugins/registry.terraform.io/kdevops/rcloud/0.1.0/linux_amd64/
	@echo "Terraform provider installed"
	@echo ""
	@echo "You can now use it in Terraform configurations:"
	@echo "  terraform {"
	@echo "    required_providers {"
	@echo "      rcloud = {"
	@echo "        source = \"kdevops/rcloud\""
	@echo "      }"
	@echo "    }"
	@echo "  }"

# Clean build artifacts
rcloud-clean:
	@echo "Cleaning rcloud build artifacts..."
	$(Q)cd $(RCLOUD_WORKFLOW) && cargo clean
ifeq (y,$(CONFIG_RCLOUD_ENABLE_TERRAFORM_PROVIDER))
	$(Q)cd terraform-provider-rcloud && rm -f terraform-provider-rcloud
endif
	@echo "rcloud clean complete"

# Help target
rcloud-help:
	@echo "rcloud targets:"
	@echo "  rcloud-build              - Build rcloud server and Terraform provider"
	@echo "  rcloud-base-images        - Create base images with virt-builder customization"
	@echo "  rcloud                    - Install and configure rcloud (runs rcloud-build and rcloud-base-images)"
	@echo "  rcloud-status             - Check rcloud health and explain status"
	@echo "  rcloud-terraform-install  - Install Terraform provider to ~/.terraform.d/"
	@echo "  rcloud-clean              - Clean build artifacts"
	@echo ""
	@echo "Configuration:"
	@echo "  RCLOUD_SERVER_BIND=$(CONFIG_RCLOUD_SERVER_BIND)"
	@echo "  RCLOUD_WORKERS=$(CONFIG_RCLOUD_WORKERS)"
	@echo ""
	@echo "See workflows/rcloud/DESIGN.md for architecture details"

HELP_TARGETS += rcloud-help
PHONY += rcloud rcloud-build rcloud-base-images rcloud-status rcloud-clean rcloud-help rcloud-terraform-install
PHONY += rcloud-check-deps rcloud-check-go-deps

else
# rcloud not enabled - provide no-op targets
rcloud rcloud-build rcloud-base-images rcloud-status rcloud-clean rcloud-help rcloud-terraform-install:
	$(Q)echo "rcloud is not enabled. Enable it with 'make menuconfig'"
endif

FORCE:
.PHONY: $(PHONY) FORCE

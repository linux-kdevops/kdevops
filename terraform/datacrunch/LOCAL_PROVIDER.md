# Using Local DataCrunch Provider Build

This directory uses the DataCrunch Terraform provider version 0.0.2, which includes
resources and data sources that are not yet published to the Terraform registry.

## Prerequisites

You must build and install the provider locally from the terraform-provider-datacrunch repository:

### 1. Build the Provider

```bash
cd /path/to/terraform-provider-datacrunch
go build -o terraform-provider-datacrunch
```

### 2. Install Locally

Create the plugin directory and copy the binary:

```bash
mkdir -p ~/.terraform.d/plugins/registry.terraform.io/linux-kdevops/datacrunch/0.0.2/linux_amd64/
cp terraform-provider-datacrunch ~/.terraform.d/plugins/registry.terraform.io/linux-kdevops/datacrunch/0.0.2/linux_amd64/terraform-provider-datacrunch_v0.0.2
```

Note: Adjust `linux_amd64` for your platform (e.g., `darwin_amd64`, `darwin_arm64`).

### 3. Configure Development Overrides

Create or edit `~/.terraformrc`:

```hcl
provider_installation {
  dev_overrides {
    "linux-kdevops/datacrunch" = "/home/YOUR_USERNAME/.terraform.d/plugins/registry.terraform.io/linux-kdevops/datacrunch/0.0.2/linux_amd64"
  }
  direct {}
}
```

Replace `YOUR_USERNAME` with your actual username.

## Using with kdevops

Once the local provider is installed, you can use kdevops normally:

```bash
make menuconfig  # Select DataCrunch provider
make bringup     # Provision DataCrunch instances
```

The `make bringup` target will automatically use the locally installed provider
due to the dev_overrides configuration.

## Important Notes

- Skip `terraform init` when using dev overrides - it may error unexpectedly
- The OpenTofu/Terraform CLI will show a warning about dev overrides being active
- The provider will load directly from your local filesystem
- Changes to the provider require rebuilding and reinstalling the binary

## Available Resources

The local v0.0.2 provider includes:

**Resources:**
- `datacrunch_instance` - Manage GPU instances
- `datacrunch_ssh_key` - Manage SSH keys

**Data Sources:**
- `datacrunch_instance_types` - Query available instance types
- `datacrunch_images` - Query available OS images
- `datacrunch_locations` - Query datacenter locations

## Troubleshooting

If you see errors about provider not found:

1. Verify the binary exists:
   ```bash
   ls -la ~/.terraform.d/plugins/registry.terraform.io/linux-kdevops/datacrunch/0.0.2/*/terraform-provider-datacrunch_v0.0.2
   ```

2. Verify ~/.terraformrc has correct path (use absolute path, no ~)

3. Check OpenTofu recognizes the override:
   ```bash
   cd terraform/datacrunch
   terraform plan  # Should show dev override warning
   ```

For more details, see the provider's DEVELOPMENT.md in the terraform-provider-datacrunch repository.

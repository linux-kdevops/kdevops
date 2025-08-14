#!/bin/bash
# List instances from terraform state
# This works even when API access is limited

set -e

# Function to detect terraform directory based on cloud provider
get_terraform_dir() {
    if [ -f .config ]; then
        if grep -q "CONFIG_TERRAFORM_LAMBDALABS=y" .config 2>/dev/null; then
            echo "terraform/lambdalabs"
        elif grep -q "CONFIG_TERRAFORM_AWS=y" .config 2>/dev/null; then
            echo "terraform/aws"
        elif grep -q "CONFIG_TERRAFORM_GCE=y" .config 2>/dev/null; then
            echo "terraform/gce"
        elif grep -q "CONFIG_TERRAFORM_AZURE=y" .config 2>/dev/null; then
            echo "terraform/azure"
        elif grep -q "CONFIG_TERRAFORM_OCI=y" .config 2>/dev/null; then
            echo "terraform/oci"
        elif grep -q "CONFIG_TERRAFORM_OPENSTACK=y" .config 2>/dev/null; then
            echo "terraform/openstack"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Get terraform directory
TERRAFORM_DIR=$(get_terraform_dir)

if [ -z "$TERRAFORM_DIR" ]; then
    echo "No terraform provider configured"
    exit 1
fi

if [ ! -d "$TERRAFORM_DIR" ]; then
    echo "Terraform directory $TERRAFORM_DIR does not exist"
    exit 1
fi

cd "$TERRAFORM_DIR"

# Check if terraform is initialized
if [ ! -d ".terraform" ]; then
    echo "Terraform not initialized. Run 'make' first."
    exit 1
fi

# Check if we have state
if [ ! -f "terraform.tfstate" ]; then
    echo "No terraform state file found. No instances deployed."
    exit 0
fi

echo "Terraform Managed Instances:"
echo "============================"
echo

# Try to get instances from state
terraform state list 2>/dev/null | grep -E "instance|vm" | while read resource; do
    echo "Resource: $resource"
    terraform state show "$resource" 2>/dev/null | grep -E "^\s*(name|ip|ip_address|public_ip|instance_type|region|status|hostname)" | sed 's/^/  /'
    echo
done

# If no instances found
if ! terraform state list 2>/dev/null | grep -qE "instance|vm"; then
    echo "No instances found in terraform state"
    echo
    echo "To deploy instances, run: make bringup"
fi

# Show outputs if available
echo
echo "Terraform Outputs:"
echo "-----------------"
terraform output 2>/dev/null || echo "No outputs defined"

#!/bin/bash

echo "Lambda Labs Instance Availability Update"
echo "========================================"
echo
echo "The configured instance type 'gpu_1x_a10' is currently unavailable."
echo
echo "Available options:"
echo
echo "1. Use gpu_1x_a100_sxm4 in us-east-1 (Virginia) - $1.29/hr"
echo "   To use this, run:"
echo "   make menuconfig"
echo "   Then navigate to:"
echo "   - Terraform -> Lambda Labs cloud provider"
echo "   - Change 'Lambda Labs region' to 'us-east-1'"
echo "   - Change 'Lambda Labs instance type' to 'gpu_1x_a100_sxm4'"
echo
echo "2. Use gpu_8x_a100 in us-west-1 (California) - $10.32/hr"
echo "   To use this, run:"
echo "   make menuconfig"
echo "   Then navigate to:"
echo "   - Terraform -> Lambda Labs cloud provider"
echo "   - Change 'Lambda Labs instance type' to 'gpu_8x_a100'"
echo
echo "3. Wait for gpu_1x_a10 to become available"
echo "   Check availability at: https://cloud.lambdalabs.com/"
echo
echo "Current configuration:"
grep "CONFIG_TERRAFORM_LAMBDALABS_REGION\|CONFIG_TERRAFORM_LAMBDALABS_INSTANCE_TYPE" .config 2>/dev/null || echo "  Configuration not found"

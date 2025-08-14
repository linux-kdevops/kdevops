#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

# Setup Lambda Labs environment for kdevops
# This scriptcan be used to test the Lambda Labs credentials are properly
# configured

echo "Lambda Labs Environment Setup"
echo "=============================="

# Get API key from credentials file
API_KEY=$(python3 $(dirname "$0")/lambdalabs_credentials.py get 2>/dev/null)

if [ -z "$API_KEY" ]; then
    echo "❌ Lambda Labs API key not found in credentials file"
    echo "   Please configure it with: python3 scripts/lambdalabs_credentials.py set 'your-api-key'"
    exit 1
else
    echo "✓ Lambda Labs API key loaded from credentials file"
    echo "  Key starts with: ${API_KEY:0:10}..."
    echo "  Key length: ${#API_KEY} characters"
fi

# Test API key validity
echo ""
echo "Testing API key validity..."
response=$(curl -s -H "Authorization: Bearer $API_KEY" https://cloud.lambdalabs.com/api/v1/instance-types 2>&1)

if echo "$response" | grep -q '"data"'; then
    echo "✓ API key is valid and working"
else
    echo "❌ API key appears to be invalid"
    echo "   Response: $(echo "$response" | head -3)"
    exit 1
fi

# Show current configuration
echo ""
echo "Current Configuration:"
echo "----------------------"
if [ -f terraform/lambdalabs/terraform.tfvars ]; then
    grep -E "^(lambdalabs_region|lambdalabs_instance_type|lambdalabs_ssh_key_name)" terraform/lambdalabs/terraform.tfvars | sed 's/^/  /'
fi

echo ""
echo "Environment ready! You can now run:"
echo "  make bringup"
echo ""
echo "Lambda Labs API key is stored in: ~/.lambdalabs/credentials"
echo "To update it, run: python3 scripts/lambdalabs_credentials.py set 'new-api-key'"

#!/bin/bash
# SPDX-License-Identifier: MIT
# List all cloud instances across supported providers
# Currently supports: Lambda Labs

set -e

PROVIDER=""

# Detect which cloud provider is configured
if [ -f .config ]; then
    if grep -q "CONFIG_TERRAFORM_LAMBDALABS=y" .config 2>/dev/null; then
        PROVIDER="lambdalabs"
    elif grep -q "CONFIG_TERRAFORM_AWS=y" .config 2>/dev/null; then
        PROVIDER="aws"
    elif grep -q "CONFIG_TERRAFORM_GCE=y" .config 2>/dev/null; then
        PROVIDER="gce"
    elif grep -q "CONFIG_TERRAFORM_AZURE=y" .config 2>/dev/null; then
        PROVIDER="azure"
    elif grep -q "CONFIG_TERRAFORM_OCI=y" .config 2>/dev/null; then
        PROVIDER="oci"
    fi
fi

if [ -z "$PROVIDER" ]; then
    echo "No cloud provider configured or .config file not found"
    exit 1
fi

echo "Cloud Provider: $PROVIDER"
echo

case "$PROVIDER" in
    lambdalabs)
        # Get API key from credentials file
        API_KEY=$(python3 $(dirname "$0")/lambdalabs_credentials.py get 2>/dev/null)
        if [ -z "$API_KEY" ]; then
            echo "Error: Lambda Labs API key not found"
            echo "Please configure it with: python3 scripts/lambdalabs_credentials.py set 'your-api-key'"
            exit 1
        fi

        # Try to list instances using curl
        echo "Fetching Lambda Labs instances..."
        response=$(curl -s -H "Authorization: Bearer $API_KEY" \
            https://cloud.lambdalabs.com/api/v1/instances 2>&1)

        # Check if we got an error
        if echo "$response" | grep -q '"error"'; then
            echo "Error accessing Lambda Labs API:"
            echo "$response" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'error' in data:
        err = data['error']
        print(f\"  {err.get('message', 'Unknown error')}\")
        if 'suggestion' in err:
            print(f\"  Suggestion: {err['suggestion']}\")
except:
    print('  Unable to parse error response')
"
            exit 1
        fi

        # Parse and display instances
        echo "$response" | python3 -c '
import sys, json
from datetime import datetime

def format_uptime(created_at):
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(created.tzinfo)
        delta = now - created

        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except:
        return "unknown"

data = json.load(sys.stdin)
instances = data.get("data", [])

if not instances:
    print("No Lambda Labs instances currently running")
else:
    print("Lambda Labs Instances:")
    print("=" * 80)
    headers = f"{'Name':<20} {'Type':<20} {'IP':<15} {'Region':<15} {'Status':<10}"
    print(headers)
    print("-" * 80)

    total_cost = 0
    for inst in instances:
        name = inst.get("name", "unnamed")
        inst_type = inst.get("instance_type", {}).get("name", "unknown")
        ip = inst.get("ip", "pending")
        region = inst.get("region", {}).get("name", "unknown")
        status = inst.get("status", "unknown")

        # Highlight kdevops instances
        if "cgpu" in name or "kdevops" in name.lower():
            name = f"→ {name}"

        row = f"{name:<20} {inst_type:<20} {ip:<15} {region:<15} {status:<10}"
        print(row)

        price_cents = inst.get("instance_type", {}).get("price_cents_per_hour", 0)
        total_cost += price_cents / 100

    print("-" * 80)
    print(f"Total instances: {len(instances)}")
    if total_cost > 0:
        print(f"Total hourly cost: ${total_cost:.2f}/hr")
        print(f"Daily cost estimate: ${total_cost * 24:.2f}/day")
'
        ;;

    aws)
        echo "AWS cloud listing not yet implemented"
        echo "You can use: aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,PublicIpAddress,State.Name,Tags[?Key==\`Name\`]|[0].Value]' --output table"
        ;;

    gce)
        echo "Google Cloud listing not yet implemented"
        echo "You can use: gcloud compute instances list"
        ;;

    azure)
        echo "Azure cloud listing not yet implemented"
        echo "You can use: az vm list --output table"
        ;;

    oci)
        echo "Oracle Cloud listing not yet implemented"
        echo "You can use: oci compute instance list --compartment-id <compartment-ocid>"
        ;;

    *)
        echo "Cloud provider '$PROVIDER' not supported for listing"
        exit 1
        ;;
esac

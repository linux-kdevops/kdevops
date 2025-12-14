#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# DataCrunch terraform apply wrapper with volume cache support
#
# This script wraps terraform apply to:
# 1. Load cached volume IDs before applying (for future volume reuse)
# 2. Save volume IDs after successful apply (when KEEP=1)
#
# Usage: ./apply_wrapper.sh [terraform apply args...]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TERRAFORM_DIR="$(dirname "$SCRIPT_DIR")"
VOLUME_CACHE="$SCRIPT_DIR/volume_cache.py"
KDEVOPS_ROOT="$(cd "$TERRAFORM_DIR/../.." && pwd)"

# Source configuration
if [ ! -f "$KDEVOPS_ROOT/.config" ]; then
	echo "Error: No .config file found. Run 'make menuconfig' first."
	exit 1
fi

# Get configuration values
KEEP_VOLUMES=$(grep -E "^CONFIG_TERRAFORM_DATACRUNCH_KEEP_VOLUMES=y" "$KDEVOPS_ROOT/.config" >/dev/null 2>&1 && echo "yes" || echo "no")
HOST_PREFIX=$(grep "^CONFIG_KDEVOPS_HOSTS_PREFIX=" "$KDEVOPS_ROOT/.config" | cut -d'"' -f2)

if [ -z "$HOST_PREFIX" ]; then
	echo "Error: Could not determine KDEVOPS_HOSTS_PREFIX from .config"
	exit 1
fi

echo "DataCrunch terraform apply wrapper"
echo "  Host prefix: $HOST_PREFIX"
echo "  Keep volumes: $KEEP_VOLUMES"
echo ""

# Run terraform apply
cd "$TERRAFORM_DIR"
terraform apply "$@"
apply_status=$?

# If apply succeeded and KEEP=1, save volume IDs to cache
if [ $apply_status -eq 0 ] && [ "$KEEP_VOLUMES" = "yes" ]; then
	echo ""
	echo "Saving volume IDs to cache..."

	# Get terraform output
	if ! terraform_output=$(terraform output -json 2>&1); then
		echo "Warning: Could not get terraform output to cache volume IDs"
		echo "  $terraform_output" >&2
	else
		# Extract and save volume IDs
		echo "$terraform_output" | python3 -c "
import sys
import json
import subprocess

output = json.load(sys.stdin)
if 'instance_details' not in output or 'value' not in output['instance_details']:
    sys.exit(0)

instances = output['instance_details']['value']
for hostname, details in instances.items():
    if 'os_volume_id' in details and details['os_volume_id']:
        volume_id = details['os_volume_id']
        cmd = ['python3', '$VOLUME_CACHE', 'save', '$HOST_PREFIX', hostname, volume_id]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f'  Saved: {hostname} -> {volume_id}')
        else:
            print(f'  Warning: Failed to save {hostname}: {result.stderr}', file=sys.stderr)
"
		echo "Volume cache updated successfully"
	fi
fi

exit $apply_status

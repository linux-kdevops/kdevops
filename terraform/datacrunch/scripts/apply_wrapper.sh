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

# shellcheck source=/dev/null
source "$KDEVOPS_ROOT/.config"

# Get configuration values
if [ "${CONFIG_TERRAFORM_DATACRUNCH_KEEP_VOLUMES:-n}" = "y" ]; then
	KEEP_VOLUMES="yes"
else
	KEEP_VOLUMES="no"
fi
HOST_PREFIX="${CONFIG_KDEVOPS_HOSTS_PREFIX:-}"

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
		exit $apply_status
	fi

	# Extract volume IDs from terraform output
	volume_data=$(echo "$terraform_output" | python3 -c "
import sys
import json

output = json.load(sys.stdin)
if 'instance_details' not in output or 'value' not in output['instance_details']:
    sys.exit(0)

instances = output['instance_details']['value']
for hostname, details in instances.items():
    if 'os_volume_id' in details and details['os_volume_id']:
        volume_id = details['os_volume_id']
        print(f'{hostname}\t{volume_id}')
")

	# Save each volume ID using properly quoted shell arguments
	if [ -n "$volume_data" ]; then
		echo "$volume_data" | while IFS=$'\t' read -r hostname volume_id; do
			if python3 "$VOLUME_CACHE" save "$HOST_PREFIX" "$hostname" "$volume_id"; then
				echo "  Saved: $hostname -> $volume_id"
			else
				echo "  Warning: Failed to save $hostname" >&2
			fi
		done
	fi
	echo "Volume cache updated successfully"
fi

exit $apply_status

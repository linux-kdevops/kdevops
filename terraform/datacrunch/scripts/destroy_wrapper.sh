#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# DataCrunch terraform destroy wrapper with volume management
#
# This script wraps terraform destroy to handle volume lifecycle:
# 1. When KEEP=1: Preserves volume cache for future reuse
# 2. When KEEP!=1: Deletes volume cache and attempts to delete volumes
#
# Note: DataCrunch automatically deletes OS-NVMe volumes when instances
# are destroyed unless they are explicitly detached first. This script
# manages the cache state to reflect the expected volume lifecycle.
#
# Usage: ./destroy_wrapper.sh [terraform destroy args...]

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

echo "DataCrunch terraform destroy wrapper"
echo "  Host prefix: $HOST_PREFIX"
echo "  Keep volumes: $KEEP_VOLUMES"
echo ""

# If KEEP!=1, show warning about volume deletion
if [ "$KEEP_VOLUMES" != "yes" ]; then
	echo "WARNING: KEEP_VOLUMES is disabled"
	echo "  - Instances and volumes will be destroyed"
	echo "  - Volume cache will be cleared"
	echo "  - Next bringup will require full OS installation (~5-10 minutes)"
	echo ""
	echo "To enable volume caching for faster reprovisioning:"
	echo "  make defconfig-datacrunch-a100 KEEP=1"
	echo ""
fi

# Get list of instances before destroying
cd "$TERRAFORM_DIR"
if terraform_output=$(terraform output -json 2>/dev/null); then
	instance_list=$(echo "$terraform_output" | python3 -c "
import sys
import json
output = json.load(sys.stdin)
if 'instance_details' in output and 'value' in output['instance_details']:
    instances = output['instance_details']['value']
    print(' '.join(instances.keys()))
" 2>/dev/null)
fi

# Run terraform destroy
terraform destroy "$@"
destroy_status=$?

# Handle volume cache based on KEEP setting
if [ $destroy_status -eq 0 ]; then
	if [ "$KEEP_VOLUMES" = "yes" ]; then
		echo ""
		echo "KEEP_VOLUMES=yes: Volume cache preserved for faster reprovisioning"
		echo "  Cached volumes will incur storage charges (~\$10/month)"
		echo "  Next bringup will reuse existing volumes (seconds vs minutes)"
		echo ""
		echo "Current cache:"
		python3 "$VOLUME_CACHE" list "$HOST_PREFIX"
	else
		echo ""
		echo "KEEP_VOLUMES=no: Clearing volume cache"
		if [ -n "$instance_list" ]; then
			for hostname in $instance_list; do
				python3 "$VOLUME_CACHE" delete "$HOST_PREFIX" "$hostname" 2>/dev/null || true
			done
		fi
		echo "  Volume cache cleared"
		echo "  No ongoing storage charges"
	fi
fi

exit $destroy_status

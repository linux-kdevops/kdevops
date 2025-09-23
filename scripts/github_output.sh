#!/usr/bin/env bash
#
# Usage: ./github_output.sh key value
set -euxo pipefail

key="$1"
value="$2"

echo "$key=$value" >> "$GITHUB_OUTPUT"

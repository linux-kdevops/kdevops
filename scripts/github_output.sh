#!/usr/bin/env bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Usage: ./github_output.sh key value
set -euxo pipefail

key="$1"
value="$2"

echo "$key=$value" >> "$GITHUB_OUTPUT"

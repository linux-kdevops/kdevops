#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# AWS cost tracking script - quick hack to check AWS spending
# This queries AWS Cost Explorer to get current month's costs

set -e

# Get the first and last day of the current month
FIRST_DAY=$(date +%Y-%m-01)
LAST_DAY=$(date -d "$FIRST_DAY +1 month -1 day" +%Y-%m-%d)
TODAY=$(date +%Y-%m-%d)

# If we're still in the current month, use today as the end date
if [[ "$TODAY" < "$LAST_DAY" ]]; then
    END_DATE="$TODAY"
else
    END_DATE="$LAST_DAY"
fi

echo "Fetching AWS costs from $FIRST_DAY to $END_DATE..." >&2

# Query AWS Cost Explorer
aws ce get-cost-and-usage \
    --time-period Start=$FIRST_DAY,End=$END_DATE \
    --granularity MONTHLY \
    --metrics UnblendedCost \
    --group-by Type=DIMENSION,Key=SERVICE \
    --output json > cost.json

# Parse and display the results
if [ -f cost.json ]; then
    echo "Cost data saved to cost.json" >&2
    echo "Parsing costs..." >&2
    python3 scripts/aws-parse-costs.py cost.json
else
    echo "Error: Failed to retrieve cost data" >&2
    exit 1
fi
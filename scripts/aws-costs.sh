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

# Query AWS Cost Explorer for actual costs by service
aws ce get-cost-and-usage \
    --time-period Start=$FIRST_DAY,End=$END_DATE \
    --granularity MONTHLY \
    --metrics UnblendedCost \
    --group-by Type=DIMENSION,Key=SERVICE \
    --output json > cost.json

# Also get breakdown by record type (Usage, Tax, Credit)
aws ce get-cost-and-usage \
    --time-period Start=$FIRST_DAY,End=$END_DATE \
    --granularity MONTHLY \
    --metrics UnblendedCost \
    --group-by Type=DIMENSION,Key=RECORD_TYPE \
    --output json > cost_breakdown.json

# Get forecast for the rest of the month if we're still in the current month
if [[ "$TODAY" < "$LAST_DAY" ]]; then
    TOMORROW=$(date -d "$TODAY +1 day" +%Y-%m-%d)
    echo "Fetching forecast from $TOMORROW to $LAST_DAY..." >&2
    aws ce get-cost-forecast \
        --time-period Start=$TOMORROW,End=$LAST_DAY \
        --metric UNBLENDED_COST \
        --granularity MONTHLY \
        --output json > forecast.json
fi

# Parse and display the results
if [ -f cost.json ]; then
    echo "Cost data saved to cost.json" >&2
    if [ -f forecast.json ]; then
        echo "Forecast data saved to forecast.json" >&2
    fi
    echo "Parsing costs..." >&2
    python3 scripts/aws-parse-costs.py cost.json forecast.json cost_breakdown.json
else
    echo "Error: Failed to retrieve cost data" >&2
    exit 1
fi

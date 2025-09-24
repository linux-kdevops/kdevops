#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Send AWS billing notifications to Slack
# This script is called by systemd timer to send periodic billing reports
# and immediate alerts when thresholds are exceeded

set -e

# Source configuration from kdevops
KDEVOPS_DIR="${KDEVOPS_DIR:-/data/cloud/gpt2/kdevops}"
CONFIG_FILE="${KDEVOPS_DIR}/extra_vars.yaml"

# Parse configuration from extra_vars.yaml
if [ -f "$CONFIG_FILE" ]; then
    SLACK_ENABLED=$(grep "^enable_slack_notifications:" "$CONFIG_FILE" | awk '{print $2}')
    SLACK_WEBHOOK=$(grep "^slack_webhook:" "$CONFIG_FILE" | awk '{print $2}')
    SLACK_WEBHOOK_URL=$(grep "^slack_webhook_url:" "$CONFIG_FILE" | awk '{print $2}')
    SLACK_AWS_CHATBOT=$(grep "^slack_aws_chatbot:" "$CONFIG_FILE" | awk '{print $2}')
    SLACK_AWS_CHATBOT_ARN=$(grep "^slack_aws_chatbot_arn:" "$CONFIG_FILE" | awk '{print $2}')
    SLACK_CHANNEL=$(grep "^slack_channel_name:" "$CONFIG_FILE" | awk '{print $2}')
    SLACK_THRESHOLD=$(grep "^slack_billing_threshold:" "$CONFIG_FILE" | awk '{print $2}')
    SLACK_FORECAST_ALERT=$(grep "^slack_billing_forecast_alert:" "$CONFIG_FILE" | awk '{print $2}')
else
    echo "Error: Configuration file not found: $CONFIG_FILE" >&2
    exit 1
fi

# Check if Slack notifications are enabled
if [ "$SLACK_ENABLED" != "true" ]; then
    echo "Slack notifications are not enabled in configuration" >&2
    exit 0
fi

# Function to send Slack webhook message
send_slack_webhook() {
    local message="$1"
    local alert_type="${2:-info}"

    # Determine color based on alert type
    local color="good"
    case "$alert_type" in
        warning)
            color="warning"
            ;;
        danger|alert)
            color="danger"
            ;;
        info|*)
            color="good"
            ;;
    esac

    # Create JSON payload
    local payload=$(cat <<EOF
{
    "channel": "${SLACK_CHANNEL}",
    "username": "AWS Billing Bot",
    "icon_emoji": ":moneybag:",
    "attachments": [
        {
            "color": "${color}",
            "title": "AWS Billing Report",
            "text": "${message}",
            "footer": "kdevops cloud billing monitor",
            "ts": $(date +%s)
        }
    ]
}
EOF
)

    # Send to Slack
    curl -X POST -H 'Content-type: application/json' \
        --data "${payload}" \
        "${SLACK_WEBHOOK_URL}" 2>/dev/null
}

# Function to send via AWS Chatbot
send_aws_chatbot() {
    local message="$1"
    local alert_type="${2:-info}"

    # AWS Chatbot requires SNS topic
    # This would need to be configured separately
    echo "AWS Chatbot integration not yet implemented" >&2
    return 1
}

# Main execution
cd "$KDEVOPS_DIR"

# Run the cloud-bill command and capture output
echo "Fetching AWS billing data..." >&2
BILLING_OUTPUT=$(mktemp)
trap "rm -f $BILLING_OUTPUT" EXIT

if ! make cloud-bill > "$BILLING_OUTPUT" 2>&1; then
    echo "Error: Failed to fetch billing data" >&2
    cat "$BILLING_OUTPUT" >&2

    # Send error notification
    if [ "$SLACK_WEBHOOK" = "true" ] && [ -n "$SLACK_WEBHOOK_URL" ]; then
        send_slack_webhook "Failed to fetch AWS billing data. Check system logs for details." "danger"
    fi
    exit 1
fi

# Parse the billing output
CURRENT_COST=$(grep "Total Cost:" "$BILLING_OUTPUT" | awk '{print $3}' | sed 's/\$//')
FORECAST_COST=$(grep "Total Projected Month Cost:" "$BILLING_OUTPUT" | awk '{print $5}' | sed 's/\$//')
DAILY_AVERAGE=$(grep "Daily Average:" "$BILLING_OUTPUT" | awk '{print $3}' | sed 's/\$//')

# Extract service breakdown (top 5 services)
SERVICE_BREAKDOWN=$(awk '/Costs by Service:/,/^-{40}/' "$BILLING_OUTPUT" | \
    grep -E '^\s+[A-Za-z]' | head -5 | \
    sed 's/^[[:space:]]*/• /')

# Check if current cost exceeds threshold
ALERT_TYPE="info"
ALERT_MESSAGE=""

if [ -n "$SLACK_THRESHOLD" ] && [ "$SLACK_THRESHOLD" -gt 0 ]; then
    # Convert costs to integers for comparison
    CURRENT_COST_INT=$(echo "$CURRENT_COST" | cut -d. -f1)

    if [ "$CURRENT_COST_INT" -ge "$SLACK_THRESHOLD" ]; then
        ALERT_TYPE="danger"
        ALERT_MESSAGE=":warning: *ALERT: Monthly cost has exceeded threshold of \$${SLACK_THRESHOLD}* :warning:\n"
    fi

    # Check forecast if enabled
    if [ "$SLACK_FORECAST_ALERT" = "true" ] && [ -n "$FORECAST_COST" ]; then
        FORECAST_COST_INT=$(echo "$FORECAST_COST" | cut -d. -f1)
        if [ "$FORECAST_COST_INT" -ge "$SLACK_THRESHOLD" ]; then
            if [ "$ALERT_TYPE" != "danger" ]; then
                ALERT_TYPE="warning"
                ALERT_MESSAGE=":chart_with_upwards_trend: *WARNING: Forecasted cost will exceed threshold of \$${SLACK_THRESHOLD}* :chart_with_upwards_trend:\n"
            fi
        fi
    fi
fi

# Format the message
MESSAGE="${ALERT_MESSAGE}*AWS Billing Summary*\n"
MESSAGE="${MESSAGE}Current Month Cost: *\$${CURRENT_COST}*\n"

if [ -n "$DAILY_AVERAGE" ]; then
    MESSAGE="${MESSAGE}Daily Average: \$${DAILY_AVERAGE}\n"
fi

if [ -n "$FORECAST_COST" ]; then
    MESSAGE="${MESSAGE}Projected Month Total: *\$${FORECAST_COST}*\n"
fi

if [ -n "$SERVICE_BREAKDOWN" ]; then
    MESSAGE="${MESSAGE}\n*Top Services:*\n${SERVICE_BREAKDOWN}"
fi

MESSAGE="${MESSAGE}\n\n_Report generated at $(date '+%Y-%m-%d %H:%M:%S %Z')_"

# Send the notification
if [ "$SLACK_WEBHOOK" = "true" ] && [ -n "$SLACK_WEBHOOK_URL" ]; then
    echo "Sending notification via Slack webhook..." >&2
    if send_slack_webhook "$MESSAGE" "$ALERT_TYPE"; then
        echo "Notification sent successfully" >&2
    else
        echo "Failed to send notification" >&2
        exit 1
    fi
elif [ "$SLACK_AWS_CHATBOT" = "true" ] && [ -n "$SLACK_AWS_CHATBOT_ARN" ]; then
    echo "Sending notification via AWS Chatbot..." >&2
    if send_aws_chatbot "$MESSAGE" "$ALERT_TYPE"; then
        echo "Notification sent successfully" >&2
    else
        echo "Failed to send notification" >&2
        exit 1
    fi
else
    echo "Error: No valid Slack integration method configured" >&2
    exit 1
fi

# Save the last notification timestamp
echo "$(date +%s)" > "${KDEVOPS_DIR}/.last_slack_billing_notification"

exit 0

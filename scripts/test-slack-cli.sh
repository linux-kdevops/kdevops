#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Test script for Slack billing CLI configuration
# This script verifies that CLI variables are properly passed and configured

set -e

echo "Testing Slack billing CLI configuration..."
echo "========================================="

# Test variables
TEST_WEBHOOK="https://hooks.slack.com/services/TEST/TEST/TEST"
TEST_CHANNEL="#test-channel"
TEST_THRESHOLD="250"
TEST_SCHEDULE="Mon *-*-* 09:00:00"

# Clean up any existing config
if [ -f .config ]; then
    echo "Backing up existing .config to .config.bak"
    mv .config .config.bak
fi

echo ""
echo "Test 1: Basic webhook configuration"
echo "-----------------------------------"
SLACK_WEBHOOK_URL="$TEST_WEBHOOK" make defconfig-cloud-bill-slack > /dev/null 2>&1

if grep -q "CONFIG_SLACK_WEBHOOK_URL=\"$TEST_WEBHOOK\"" .config; then
    echo "✓ Webhook URL set correctly"
else
    echo "✗ Webhook URL not set correctly"
    grep "CONFIG_SLACK_WEBHOOK_URL" .config || echo "Not found in config"
fi

if grep -q "CONFIG_ENABLE_SLACK_NOTIFICATIONS=y" .config; then
    echo "✓ Slack notifications enabled"
else
    echo "✗ Slack notifications not enabled"
fi

echo ""
echo "Test 2: Full configuration with all variables"
echo "---------------------------------------------"
rm -f .config
SLACK_WEBHOOK_URL="$TEST_WEBHOOK" \
SLACK_CHANNEL="$TEST_CHANNEL" \
SLACK_THRESHOLD="$TEST_THRESHOLD" \
SLACK_SCHEDULE="$TEST_SCHEDULE" \
make defconfig-cloud-bill-slack > /dev/null 2>&1

echo "Checking configuration values:"
if grep -q "CONFIG_SLACK_WEBHOOK_URL=\"$TEST_WEBHOOK\"" .config; then
    echo "✓ Webhook URL: $TEST_WEBHOOK"
else
    echo "✗ Webhook URL not set"
fi

if grep -q "CONFIG_SLACK_CHANNEL_NAME=\"$TEST_CHANNEL\"" .config; then
    echo "✓ Channel: $TEST_CHANNEL"
else
    echo "✗ Channel not set correctly"
    grep "CONFIG_SLACK_CHANNEL_NAME" .config || echo "Not found"
fi

if grep -q "CONFIG_SLACK_BILLING_THRESHOLD=$TEST_THRESHOLD" .config; then
    echo "✓ Threshold: $TEST_THRESHOLD"
else
    echo "✗ Threshold not set correctly"
    grep "CONFIG_SLACK_BILLING_THRESHOLD" .config || echo "Not found"
fi

if grep -q "CONFIG_SLACK_BILLING_SCHEDULE=\"$TEST_SCHEDULE\"" .config; then
    echo "✓ Schedule: $TEST_SCHEDULE"
else
    echo "✗ Schedule not set correctly"
    grep "CONFIG_SLACK_BILLING_SCHEDULE" .config || echo "Not found"
fi

echo ""
echo "Test 3: Verify defconfig files exist"
echo "------------------------------------"
if [ -f defconfigs/cloud-bill-slack ]; then
    echo "✓ defconfigs/cloud-bill-slack exists"
else
    echo "✗ defconfigs/cloud-bill-slack missing"
fi

if [ -f defconfigs/cloud-bill-slack-aws ]; then
    echo "✓ defconfigs/cloud-bill-slack-aws exists"
else
    echo "✗ defconfigs/cloud-bill-slack-aws missing"
fi

# Restore original config if it existed
if [ -f .config.bak ]; then
    echo ""
    echo "Restoring original .config"
    mv .config.bak .config
else
    rm -f .config
fi

echo ""
echo "Testing complete!"
echo ""
echo "To use in production:"
echo "  make defconfig-cloud-bill-slack SLACK_WEBHOOK_URL=\"your-real-webhook-url\""
echo "  make"
echo "  make slack-billing-setup"
echo "  make slack-billing-test"

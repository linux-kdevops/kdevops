# Slack Billing Integration for AWS

kdevops now supports optional Slack notifications for AWS cloud billing, allowing you to receive periodic cost reports and threshold alerts directly in your Slack channels.

## Quick Start (CLI Method)

The fastest way to set up Slack billing notifications is using the CLI method with defconfigs:

```bash
# One-line setup with webhook URL
make defconfig-cloud-bill-slack SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T00/B00/XXX"
make
make slack-billing-setup
make slack-billing-test  # Send test notification

# With custom settings
make defconfig-cloud-bill-slack \
  SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T00/B00/XXX" \
  SLACK_CHANNEL="#cloud-costs" \
  SLACK_THRESHOLD=500 \
  SLACK_SCHEDULE="*-*-* 09:00:00"
```

## Features

- **Periodic Billing Reports**: Automatically send AWS cost summaries to Slack on a configurable schedule
- **Threshold Alerts**: Get immediate notifications when costs exceed defined limits
- **Forecast Alerts**: Receive warnings when projected monthly costs will exceed thresholds
- **Service Breakdown**: See top AWS services contributing to costs
- **Flexible Scheduling**: Use systemd timer syntax for custom notification schedules
- **Multiple Integration Methods**: Support for both Slack webhooks and AWS Chatbot

## Prerequisites

### 1. AWS CLI Setup

The AWS CLI must be installed and configured with credentials that have billing access:

```bash
# Install AWS CLI (if not already installed)
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure AWS credentials
aws configure
# Enter your AWS Access Key ID, Secret Access Key, region, and output format

# Verify credentials work and have billing access
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

**Note**: Having `~/.aws/credentials` is sufficient. The Ansible role will copy these credentials to the kdevops service user automatically.

### 2. Obtaining a Slack Webhook URL

To get a Slack webhook URL:

1. **Sign in to your Slack workspace** at https://slack.com

2. **Create an Incoming Webhook**:
   - Go to https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - Name your app (e.g., "AWS Billing Bot")
   - Select your workspace

3. **Enable Incoming Webhooks**:
   - In your app settings, click "Incoming Webhooks" in the left sidebar
   - Toggle "Activate Incoming Webhooks" to ON
   - Click "Add New Webhook to Workspace"
   - Select the channel where notifications should be posted
   - Click "Allow"

4. **Copy the Webhook URL**:
   - You'll see a webhook URL like:
     ```
     https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXX
     ```
   - Copy this entire URL - you'll need it for configuration

5. **Test the webhook** (optional):
   ```bash
   curl -X POST -H 'Content-type: application/json' \
     --data '{"text":"Test message from kdevops"}' \
     YOUR_WEBHOOK_URL
   ```

### 3. System Requirements

- systemd-based Linux system (for timer/service management)
- Python 3.x (for cost parsing)
- curl (for sending Slack notifications)

## Configuration Methods

### Method 1: CLI Variables (Recommended)

The easiest way to configure Slack notifications is using CLI variables with the provided defconfigs:

#### Available Defconfigs

1. **cloud-bill-slack** - Localhost-only setup (no VMs created)
   ```bash
   make defconfig-cloud-bill-slack SLACK_WEBHOOK_URL="..."
   ```

2. **cloud-bill-slack-aws** - AWS-specific configuration
   ```bash
   make defconfig-cloud-bill-slack-aws SLACK_WEBHOOK_URL="..."
   ```

#### CLI Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `SLACK_WEBHOOK_URL` | Slack webhook URL (required) | none | `https://hooks.slack.com/services/...` |
| `SLACK_CHANNEL` | Target Slack channel | `#aws-billing` | `#cloud-costs` |
| `SLACK_THRESHOLD` | Alert threshold (USD) | `100` | `500` |
| `SLACK_SCHEDULE` | systemd timer schedule | `daily` | `*-*-* 09:00:00` |

#### Examples

```bash
# Basic setup
make defconfig-cloud-bill-slack \
  SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T00/B00/XXX"

# Custom channel and threshold
make defconfig-cloud-bill-slack \
  SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T00/B00/XXX" \
  SLACK_CHANNEL="#devops-alerts" \
  SLACK_THRESHOLD=250

# Weekly reports on Mondays at 9 AM
make defconfig-cloud-bill-slack \
  SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T00/B00/XXX" \
  SLACK_SCHEDULE="Mon *-*-* 09:00:00"

# Complete setup and test
make defconfig-cloud-bill-slack \
  SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T00/B00/XXX" && \
  make && \
  make slack-billing-setup && \
  make slack-billing-test
```

### Method 2: Interactive Configuration (menuconfig)

For more control, use the interactive menu configuration:

#### 1. Enable Slack Notifications

Run `make menuconfig` and navigate to:
```
Monitors → Enable Slack notifications for cloud billing
```

#### 2. Configure Integration Method

Choose between:

#### Slack Webhook (Simpler)
1. Create an Incoming Webhook in your Slack workspace
2. Configure the webhook URL in kdevops
3. Specify the target Slack channel

#### AWS Chatbot (Advanced)
1. Set up AWS Chatbot in your AWS account
2. Configure the Chatbot channel ARN
3. Connect to your Slack workspace

### 3. Set Notification Schedule

The schedule uses systemd timer format. Common examples:
- `daily` - Once per day at midnight
- `weekly` - Once per week on Monday
- `monthly` - Once per month on the 1st
- `*-*-* 09:00:00` - Every day at 9 AM
- `Mon,Wed,Fri *-*-* 09:00:00` - Monday, Wednesday, Friday at 9 AM

### 4. Configure Thresholds

- **Cost Threshold**: Set a USD amount to trigger immediate alerts
- **Forecast Alerts**: Enable/disable projected cost warnings

## Deployment

### Initial Setup

1. Configure your options in `make menuconfig`
2. Deploy the Slack integration:
   ```bash
   make slack-billing-setup
   ```

### Testing

Test the notification system:
```bash
make slack-billing-test
```

This will:
- Run `make cloud-bill` to fetch current AWS costs
- Format the billing report
- Send a test notification to your configured Slack channel

### Check Status

View the status of the systemd timer:
```bash
make slack-billing-status
```

Or directly with systemctl:
```bash
systemctl status kdevops-slack-billing.timer
systemctl list-timers kdevops-slack-billing.timer
```

## Message Format

Slack notifications include:
- Current month-to-date costs
- Daily average spending
- Projected monthly total
- Top 5 AWS services by cost
- Alert indicators when thresholds are exceeded

Example message:
```
AWS Billing Summary
Current Month Cost: $145.32
Daily Average: $14.53
Projected Month Total: $450.43

Top Services:
• EC2-Instances             $98.45
• EC2-Other                 $25.67
• S3                        $12.34
• RDS                       $8.90
• Lambda                    $0.96

Report generated at 2025-09-23 09:00:00 UTC
```

## Threshold Alerts

When costs exceed configured thresholds, messages include prominent warnings:

- **Current Cost Alert**: ⚠️ ALERT: Monthly cost has exceeded threshold of $100 ⚠️
- **Forecast Alert**: 📈 WARNING: Forecasted cost will exceed threshold of $100 📈

## Troubleshooting

### Common Setup Issues

#### 1. "Slack webhook URL must be configured"
```bash
# Ensure you're providing the webhook URL correctly
make defconfig-cloud-bill-slack SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."

# Check if the URL was set in config
grep SLACK_WEBHOOK_URL .config
```

#### 2. "AWS CLI is not installed"
```bash
# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

#### 3. "AWS CLI is not configured"
```bash
# Configure AWS credentials
aws configure

# Or manually create credentials file
mkdir -p ~/.aws
cat > ~/.aws/credentials << EOF
[default]
aws_access_key_id = YOUR_KEY_ID
aws_secret_access_key = YOUR_SECRET_KEY
EOF

# Test credentials
aws sts get-caller-identity
```

#### 4. "Error: Unable to locate credentials"
```bash
# Check if credentials file exists
ls -la ~/.aws/credentials

# Verify the Ansible role copied credentials
sudo ls -la /var/lib/kdevops/.aws/

# Manually copy if needed
sudo mkdir -p /var/lib/kdevops/.aws
sudo cp ~/.aws/credentials /var/lib/kdevops/.aws/
sudo chown -R kdevops:kdevops /var/lib/kdevops/.aws/
sudo chmod 600 /var/lib/kdevops/.aws/credentials
```

### Notifications Not Sending

#### Check Webhook URL
```bash
# Verify webhook URL in configuration
grep slack_webhook_url extra_vars.yaml

# Test webhook directly
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test from kdevops"}' \
  "YOUR_WEBHOOK_URL"

# Expected response: "ok"
```

#### Check Systemd Service
```bash
# Check timer status
systemctl status kdevops-slack-billing.timer
systemctl list-timers kdevops-slack-billing.timer

# Check service logs
journalctl -u kdevops-slack-billing.service -n 50

# Run service manually
sudo systemctl start kdevops-slack-billing.service

# Follow logs in real-time
journalctl -u kdevops-slack-billing.service -f
```

#### Debug the Script
```bash
# Run the notification script directly
sudo -u kdevops bash /data/cloud/gpt2/kdevops/scripts/slack-billing-notify.sh

# Run with debug output
sudo -u kdevops bash -x /data/cloud/gpt2/kdevops/scripts/slack-billing-notify.sh
```

### AWS Billing Access Issues

#### "AccessDeniedException: User is not authorized"
Your AWS user needs billing access permissions:

1. **For root account**: Billing access is automatic

2. **For IAM users**:
   - Enable "IAM user and role access to billing" in root account settings
   - Attach the `AWSBillingReadOnlyAccess` policy or create custom policy

3. **Test access**:
   ```bash
   aws ce get-cost-and-usage \
     --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
     --granularity MONTHLY \
     --metrics UnblendedCost
   ```

#### No Cost Data Available
```bash
# Check if you're in the correct AWS account
aws sts get-caller-identity

# Ensure billing data exists (may take 24h for new accounts)
aws ce get-cost-and-usage \
  --time-period Start=$(date -d "1 month ago" +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost
```

### Permission Issues

#### Service User Issues
```bash
# Verify kdevops user exists
id kdevops

# Check service user can access credentials
sudo -u kdevops aws sts get-caller-identity

# Fix permissions if needed
sudo chown -R kdevops:kdevops /var/lib/kdevops
sudo chmod 700 /var/lib/kdevops/.aws
sudo chmod 600 /var/lib/kdevops/.aws/credentials
```

#### Systemd Service Fails to Start
```bash
# Check service status
systemctl status kdevops-slack-billing.service

# View detailed error
journalctl -xe -u kdevops-slack-billing.service

# Common fixes:
# 1. Fix script permissions
sudo chmod 755 /data/cloud/gpt2/kdevops/scripts/slack-billing-notify.sh

# 2. Ensure working directory exists
sudo mkdir -p /data/cloud/gpt2/kdevops
sudo chown kdevops:kdevops /data/cloud/gpt2/kdevops
```

### Webhook Issues

#### "Invalid_webhook" or 404 Error
- The webhook URL may be incorrect or revoked
- Regenerate webhook in Slack app settings
- Update configuration with new URL

#### No Messages in Slack
- Check if the bot has permission to post to the channel
- Verify channel name matches configuration (include # prefix)
- Check if webhook is active in Slack app settings

### Quick Diagnostics Script

Create and run this diagnostic script:
```bash
cat > /tmp/slack-billing-diagnose.sh << 'EOF'
#!/bin/bash
echo "=== Slack Billing Diagnostics ==="
echo
echo "1. Checking AWS CLI:"
which aws && aws --version || echo "❌ AWS CLI not found"
echo
echo "2. Checking AWS credentials:"
aws sts get-caller-identity || echo "❌ AWS credentials not configured"
echo
echo "3. Checking billing access:"
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --output text | head -n 1 || echo "❌ No billing access"
echo
echo "4. Checking kdevops user:"
id kdevops || echo "❌ kdevops user not found"
echo
echo "5. Checking systemd timer:"
systemctl is-active kdevops-slack-billing.timer || echo "❌ Timer not active"
echo
echo "6. Checking webhook URL configured:"
grep -q SLACK_WEBHOOK_URL .config && echo "✓ Webhook URL configured" || echo "❌ No webhook URL"
EOF

bash /tmp/slack-billing-diagnose.sh
```

## AWS Credentials Configuration

### Using Existing AWS Credentials

If you already have AWS CLI configured:

```bash
# Check current configuration
aws sts get-caller-identity

# Verify billing access
aws ce get-cost-and-usage --help
```

Your existing `~/.aws/credentials` file should look like:
```ini
[default]
aws_access_key_id = AKIAXXXXXXXXXXXXXXXX
aws_secret_access_key = XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
region = us-east-1
```

**Important**: The Ansible role automatically copies your AWS credentials to the kdevops service user during `make slack-billing-setup`.

### Creating IAM User for Billing Access

If you need to create dedicated credentials for billing:

1. **Create an IAM user** in AWS Console:
   - Go to IAM → Users → Add User
   - Username: `kdevops-billing-reader`
   - Access type: Programmatic access

2. **Attach the policy** (see minimum permissions below)

3. **Save the credentials** and configure:
   ```bash
   aws configure --profile billing
   # Or add to ~/.aws/credentials manually
   ```

### Minimum Required IAM Permissions

Create a custom IAM policy with these permissions:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ce:GetCostAndUsage",
                "ce:GetCostForecast",
                "ce:GetCostAndUsageWithResources"
            ],
            "Resource": "*"
        }
    ]
}
```

**Note**: These are read-only permissions that only allow viewing cost data.

## Security Considerations

### Slack Webhook Security
- **Keep webhook URLs secret** - treat them like passwords
- Don't commit webhook URLs to git repositories
- Rotate webhooks periodically
- Use environment variables or secrets management for production

### AWS Credentials Security
- Use IAM roles with minimal permissions
- Enable MFA for AWS accounts with billing access
- Rotate access keys regularly
- Consider using AWS SSO or temporary credentials for enhanced security

### System Security
- The systemd service runs as a dedicated `kdevops` user with limited privileges
- Service uses `ProtectSystem=strict` and other hardening options
- Credentials are stored with 0600 permissions

## Uninstalling

To remove the Slack billing integration:

1. Disable in configuration:
   ```bash
   make menuconfig
   # Disable: Monitors → Enable Slack notifications for cloud billing
   ```

2. Re-run the setup to remove:
   ```bash
   make slack-billing-setup
   ```

This will stop and remove the systemd timer and service.

## Integration with CI/CD

The Slack billing notifications can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Check AWS Costs
  run: |
    make cloud-bill
    make slack-billing-test
```

## Future Enhancements

Planned improvements include:
- Full AWS Chatbot integration with SNS topics
- Support for other cloud providers (Azure, GCP)
- Cost breakdown by tags/projects
- Historical cost trend graphs
- Multi-channel notifications
- Cost anomaly detection

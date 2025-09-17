#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Parse AWS Cost Explorer JSON output and display costs

import json
import sys
from datetime import datetime


def parse_costs(filename):
    """Parse AWS Cost Explorer JSON output."""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File {filename} not found", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Extract time period
    if 'ResultsByTime' in data and data['ResultsByTime']:
        result = data['ResultsByTime'][0]
        time_period = result.get('TimePeriod', {})
        start = time_period.get('Start', 'Unknown')
        end = time_period.get('End', 'Unknown')

        print(f"\nAWS Cost Report")
        print(f"Period: {start} to {end}")
        print("=" * 60)

        # Get total cost
        total = result.get('Total', {})
        if 'UnblendedCost' in total:
            total_amount = float(total['UnblendedCost'].get('Amount', 0))
            currency = total['UnblendedCost'].get('Unit', 'USD')
            print(f"\nTotal Cost: ${total_amount:.2f} {currency}")

        # Get costs by service
        groups = result.get('Groups', [])
        if groups:
            print("\nCosts by Service:")
            print("-" * 40)

            # Sort by cost (descending)
            sorted_groups = sorted(groups,
                                   key=lambda x: float(x['Metrics']['UnblendedCost']['Amount']),
                                   reverse=True)

            for group in sorted_groups:
                service = group['Keys'][0] if group.get('Keys') else 'Unknown'
                metrics = group.get('Metrics', {})
                if 'UnblendedCost' in metrics:
                    amount = float(metrics['UnblendedCost'].get('Amount', 0))
                    if amount > 0.01:  # Only show services with costs > $0.01
                        print(f"  {service:30} ${amount:10.2f}")

            # Show total at the bottom
            print("-" * 40)
            if 'UnblendedCost' in total:
                print(f"  {'TOTAL':30} ${total_amount:10.2f}")

        # Calculate daily average
        try:
            start_date = datetime.strptime(start, '%Y-%m-%d')
            end_date = datetime.strptime(end, '%Y-%m-%d')
            days = (end_date - start_date).days
            if days > 0 and 'UnblendedCost' in total:
                daily_avg = total_amount / days
                print(f"\nDaily Average: ${daily_avg:.2f}")

                # Project monthly cost if we're mid-month
                today = datetime.now()
                if end_date.date() == today.date() and start_date.day == 1:
                    days_in_month = 30  # Approximate
                    projected = daily_avg * days_in_month
                    print(f"Projected Monthly: ${projected:.2f}")
        except ValueError:
            pass

    else:
        print("No cost data available in the response", file=sys.stderr)
        sys.exit(1)


def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: aws-parse-costs.py <cost.json>", file=sys.stderr)
        sys.exit(1)

    parse_costs(sys.argv[1])


if __name__ == "__main__":
    main()
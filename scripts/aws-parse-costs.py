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
        total_amount = 0
        currency = 'USD'

        # If Total is provided, use it
        if 'UnblendedCost' in total:
            total_amount = float(total['UnblendedCost'].get('Amount', 0))
            currency = total['UnblendedCost'].get('Unit', 'USD')
        # Otherwise calculate from groups
        else:
            groups = result.get('Groups', [])
            for group in groups:
                metrics = group.get('Metrics', {})
                if 'UnblendedCost' in metrics:
                    total_amount += float(metrics['UnblendedCost'].get('Amount', 0))

        if total_amount > 0:
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


def parse_forecast(filename):
    """Parse AWS Cost Forecast JSON output."""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

    if 'Total' in data:
        amount = float(data['Total'].get('Amount', 0))
        return amount
    return None


def parse_breakdown(filename):
    """Parse cost breakdown by record type."""
    try:
        with open(filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None

    breakdown = {'Usage': 0, 'Tax': 0, 'Credit': 0}
    if 'ResultsByTime' in data and data['ResultsByTime']:
        result = data['ResultsByTime'][0]
        groups = result.get('Groups', [])
        for group in groups:
            record_type = group['Keys'][0] if group.get('Keys') else 'Unknown'
            metrics = group.get('Metrics', {})
            if 'UnblendedCost' in metrics:
                amount = float(metrics['UnblendedCost'].get('Amount', 0))
                if record_type in breakdown:
                    breakdown[record_type] = amount
    return breakdown


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: aws-parse-costs.py <cost.json> [forecast.json] [cost_breakdown.json]", file=sys.stderr)
        sys.exit(1)

    # Parse breakdown if provided
    breakdown = None
    if len(sys.argv) > 3:
        breakdown = parse_breakdown(sys.argv[3])
        if breakdown:
            print(f"\nCost Breakdown:")
            print("=" * 60)
            print(f"Usage Costs:    ${breakdown['Usage']:.2f}")
            if breakdown['Credit'] != 0:
                print(f"Credits:        ${breakdown['Credit']:.2f}")
            if breakdown['Tax'] != 0:
                print(f"Tax:            ${breakdown['Tax']:.2f}")
            net_total = breakdown['Usage'] + breakdown['Credit'] + breakdown['Tax']
            print(f"Net Total:      ${net_total:.2f}")
            print("=" * 60)

    parse_costs(sys.argv[1])

    # Parse forecast if provided
    if len(sys.argv) > 2:
        forecast_amount = parse_forecast(sys.argv[2])
        if forecast_amount is not None:
            print(f"\n{'=' * 60}")
            print(f"Forecast for remainder of month: ${forecast_amount:.2f}")

            # Calculate total projected
            actual_amount = 0
            if breakdown:
                # Use net total from breakdown
                actual_amount = breakdown['Usage'] + breakdown['Credit'] + breakdown['Tax']
            else:
                # Fall back to calculation from service costs
                with open(sys.argv[1], 'r') as f:
                    data = json.load(f)
                if 'ResultsByTime' in data and data['ResultsByTime']:
                    result = data['ResultsByTime'][0]
                    total = result.get('Total', {})

                    # If Total is provided, use it
                    if 'UnblendedCost' in total:
                        actual_amount = float(total['UnblendedCost'].get('Amount', 0))
                    # Otherwise calculate from groups
                    else:
                        groups = result.get('Groups', [])
                        for group in groups:
                            metrics = group.get('Metrics', {})
                            if 'UnblendedCost' in metrics:
                                actual_amount += float(metrics['UnblendedCost'].get('Amount', 0))

            if actual_amount != 0:
                total_projected = actual_amount + forecast_amount
                print(f"Total Projected Month Cost: ${total_projected:.2f}")

                # If we have breakdown, also show projected without credits
                if breakdown and breakdown['Credit'] < 0:
                    total_usage_projected = breakdown['Usage'] + forecast_amount
                    print(f"Projected Usage (before credits): ${total_usage_projected:.2f}")
                print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
List all Lambda Labs instances for the current account.
Part of kdevops cloud management utilities.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
import lambdalabs_credentials


def format_uptime(created_at):
    """Convert timestamp to human-readable uptime."""
    try:
        created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        now = datetime.now(created.tzinfo)
        delta = now - created

        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"
    except:
        return "unknown"


def list_instances():
    """List all Lambda Labs instances."""
    # Get API key from credentials
    api_key = lambdalabs_credentials.get_api_key()
    if not api_key:
        print("Error: Lambda Labs API key not found in credentials file", file=sys.stderr)
        print(
            "Please configure it with: python3 scripts/lambdalabs_credentials.py set 'your-api-key'",
            file=sys.stderr,
        )
        return 1

    url = "https://cloud.lambdalabs.com/api/v1/instances"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())

            if "data" not in data:
                print("No instances found or unexpected API response")
                return 0

            instances = data["data"]

            if not instances:
                print("No Lambda Labs instances currently running")
                return 0

            # Print header
            print("\nLambda Labs Instances:")
            print("=" * 80)
            print(
                f"{'Name':<20} {'Type':<20} {'IP':<15} {'Region':<15} {'Uptime':<10} {'Status'}"
            )
            print("-" * 80)

            # Print each instance
            for instance in instances:
                name = instance.get("name", "unnamed")
                instance_type = instance.get("instance_type", {}).get("name", "unknown")
                ip = instance.get("ip", "pending")
                region = instance.get("region", {}).get("name", "unknown")
                status = instance.get("status", "unknown")
                created_at = instance.get("created", "")
                uptime = format_uptime(created_at)

                # Highlight kdevops instances
                if "cgpu" in name or "kdevops" in name.lower():
                    name = f"→ {name}"

                print(
                    f"{name:<20} {instance_type:<20} {ip:<15} {region:<15} {uptime:<10} {status}"
                )

            print("-" * 80)
            print(f"Total instances: {len(instances)}")

            # Calculate total cost
            total_cost = 0
            for instance in instances:
                price_cents = instance.get("instance_type", {}).get(
                    "price_cents_per_hour", 0
                )
                total_cost += price_cents / 100

            if total_cost > 0:
                print(f"Total hourly cost: ${total_cost:.2f}/hr")
                print(f"Daily cost estimate: ${total_cost * 24:.2f}/day")

            print()

            return 0

    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"Error: HTTP {e.code} - {e.reason}", file=sys.stderr)
        if error_body:
            try:
                error_data = json.loads(error_body)
                if "error" in error_data:
                    err = error_data["error"]
                    print(f"  {err.get('message', 'Unknown error')}", file=sys.stderr)
                    if "suggestion" in err:
                        print(f"  Suggestion: {err['suggestion']}", file=sys.stderr)
            except:
                print(f"  Response: {error_body}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main():
    """Main entry point."""
    # Support JSON output flag
    if len(sys.argv) > 1 and sys.argv[1] == "--json":
        # For future: output raw JSON
        # Get API key from credentials
        api_key = lambdalabs_credentials.get_api_key()
        if not api_key:
            print(json.dumps({"error": "Lambda Labs API key not found in credentials file"}))
            return 1

        url = "https://cloud.lambdalabs.com/api/v1/instances"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                print(response.read().decode())
                return 0
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            return 1
    else:
        return list_instances()


if __name__ == "__main__":
    sys.exit(main())

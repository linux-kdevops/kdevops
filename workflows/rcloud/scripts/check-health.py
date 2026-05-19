#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
"""
rcloud Health Check Script

This script queries the rcloud REST API health endpoint and provides
a human-readable explanation of the service status.
"""

import json
import sys
import urllib.request
import urllib.error


def check_health(endpoint="http://localhost:8765"):
    """
    Check the health of the rcloud API server.

    Args:
        endpoint: The base URL of the rcloud API server

    Returns:
        Tuple of (success: bool, data: dict, message: str)
    """
    health_url = f"{endpoint}/api/v1/health"

    try:
        with urllib.request.urlopen(health_url, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                return True, data, None
            else:
                return False, None, f"HTTP {response.status}: {response.reason}"

    except urllib.error.URLError as e:
        return False, None, f"Connection failed: {e.reason}"
    except urllib.error.HTTPError as e:
        return False, None, f"HTTP error: {e.code} {e.reason}"
    except json.JSONDecodeError as e:
        return False, None, f"Invalid JSON response: {e}"
    except Exception as e:
        return False, None, f"Unexpected error: {e}"


def explain_health_status(data):
    """
    Explain the health check response in human language.

    Args:
        data: The parsed JSON health check response

    Returns:
        List of explanation strings
    """
    explanations = []

    # Explain overall status
    status = data.get("status", "unknown")
    if status == "healthy":
        explanations.append(
            "✅ SERVICE STATUS: The rcloud REST API server is running and healthy."
        )
        explanations.append(
            "   This means the service is accepting connections and ready to handle requests."
        )
    elif status == "degraded":
        explanations.append("⚠️  SERVICE STATUS: The service is running but degraded.")
        explanations.append(
            "   Some functionality may be limited or experiencing issues."
        )
    elif status == "unhealthy":
        explanations.append("❌ SERVICE STATUS: The service is unhealthy.")
        explanations.append("   Critical issues are preventing normal operation.")
    else:
        explanations.append(f"❓ SERVICE STATUS: Unknown status '{status}'")

    # Explain version
    version = data.get("version", "unknown")
    explanations.append("")
    explanations.append(f"📦 VERSION: rcloud {version}")
    explanations.append(
        "   This is the version of the rcloud server currently running."
    )

    # Explain what this means for operations
    explanations.append("")
    explanations.append("🔧 WHAT YOU CAN DO:")
    if status == "healthy":
        explanations.append("   • Create new virtual machines via the API")
        explanations.append("   • List and manage existing VMs")
        explanations.append("   • Use Terraform to provision infrastructure")
        explanations.append("   • Query available base images")
    else:
        explanations.append("   • Check service logs: sudo journalctl -u rcloud -n 50")
        explanations.append(
            "   • Verify libvirt is running: sudo systemctl status libvirtd"
        )
        explanations.append("   • Check system resources: df -h, free -h")

    return explanations


def main():
    """Main entry point for the health check script."""

    # Allow custom endpoint as command line argument
    endpoint = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765"

    print("=" * 70)
    print("rcloud Health Check")
    print("=" * 70)
    print(f"\nQuerying: {endpoint}/api/v1/health\n")

    # Perform health check
    success, data, error_msg = check_health(endpoint)

    if not success:
        print("❌ HEALTH CHECK FAILED")
        print(f"\nError: {error_msg}\n")
        print("Troubleshooting steps:")
        print("  1. Verify the service is running:")
        print("     sudo systemctl status rcloud")
        print("  2. Check if the correct port is being used:")
        print("     sudo ss -tlnp | grep rcloud")
        print("  3. Review service logs:")
        print("     sudo journalctl -u rcloud -n 50")
        print("  4. Ensure you're using the correct endpoint URL")
        print()
        return 1

    # Show raw JSON response
    print("📄 RAW API RESPONSE:")
    print("-" * 70)
    print(json.dumps(data, indent=2))
    print("-" * 70)
    print()

    # Show human-friendly explanation
    print("📖 EXPLANATION:")
    print("-" * 70)
    for line in explain_health_status(data):
        print(line)
    print("-" * 70)
    print()

    # Show next steps
    print("🔗 TRY THESE ENDPOINTS:")
    print(f"  • List VMs:        curl {endpoint}/api/v1/vms")
    print(f"  • List images:     curl {endpoint}/api/v1/images")
    print(f"  • System status:   curl {endpoint}/api/v1/status")
    print(f"  • Metrics:         curl {endpoint}/metrics")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())

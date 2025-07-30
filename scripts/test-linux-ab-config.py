#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1
"""
Linux A/B testing verification for kdevops
Verifies that A/B testing ref configurations are set correctly
"""

import os
import sys
import re
import subprocess
from pathlib import Path


class LinuxABTester:
    """Test runner for Linux A/B testing configurations"""

    def __init__(self):
        self.failed_checks = []

    def check_config_file(self):
        """Check if .config exists and has A/B testing enabled"""
        if not os.path.exists(".config"):
            print(
                "❌ No .config file found - run 'make menuconfig' or apply a defconfig first"
            )
            return False

        with open(".config", "r") as f:
            config = f.read()

        # Check if A/B testing is enabled
        if "CONFIG_KDEVOPS_BASELINE_AND_DEV=y" not in config:
            print("❌ A/B testing not enabled (CONFIG_KDEVOPS_BASELINE_AND_DEV=y)")
            return False

        if "CONFIG_BOOTLINUX_AB_DIFFERENT_REF=y" not in config:
            print("❌ Different refs not enabled (CONFIG_BOOTLINUX_AB_DIFFERENT_REF=y)")
            return False

        print("✓ A/B testing configuration enabled")
        return True

    def check_extra_vars(self):
        """Check if extra_vars.yaml has been generated"""
        if not os.path.exists("extra_vars.yaml"):
            print("❌ No extra_vars.yaml found - run 'make' to generate it")
            return False
        return True

    def verify_refs(self):
        """Extract and verify kernel references are different"""
        print("\nChecking kernel references...")

        with open("extra_vars.yaml", "r") as f:
            content = f.read()

        # Extract refs
        baseline_match = re.search(r"^target_linux_ref:\s*(.+)$", content, re.MULTILINE)
        dev_match = re.search(r"^target_linux_dev_ref:\s*(.+)$", content, re.MULTILINE)

        if not baseline_match:
            print("❌ Could not find target_linux_ref in extra_vars.yaml")
            self.failed_checks.append("missing-baseline-ref")
            return False

        if not dev_match:
            print("❌ Could not find target_linux_dev_ref in extra_vars.yaml")
            self.failed_checks.append("missing-dev-ref")
            return False

        baseline_ref = baseline_match.group(1).strip()
        dev_ref = dev_match.group(1).strip()

        print(f"  Baseline ref: {baseline_ref}")
        print(f"  Dev ref: {dev_ref}")

        if baseline_ref == dev_ref:
            print("❌ ERROR: Baseline and dev refs are the same!")
            print("  This defeats the purpose of A/B testing")
            self.failed_checks.append("refs-identical")
            return False

        # Check if refs look valid
        if not baseline_ref or baseline_ref == "None":
            print("❌ Baseline ref is empty or None")
            self.failed_checks.append("invalid-baseline-ref")
            return False

        if not dev_ref or dev_ref == "None":
            print("❌ Dev ref is empty or None")
            self.failed_checks.append("invalid-dev-ref")
            return False

        print("✓ Refs are different and valid")
        return True

    def check_makefile_structure(self):
        """Verify the Makefile has proper A/B testing targets"""
        print("\nChecking Makefile structure...")

        makefile_path = "workflows/linux/Makefile"
        if not os.path.exists(makefile_path):
            print(f"⚠️  Cannot verify - {makefile_path} not found")
            return True  # Don't fail if file doesn't exist

        with open(makefile_path, "r") as f:
            content = f.read()

        # Check for A/B testing targets
        has_baseline_target = bool(
            re.search(r"^linux-baseline:", content, re.MULTILINE)
        )
        has_dev_target = bool(re.search(r"^linux-dev:", content, re.MULTILINE))

        if not has_baseline_target:
            print("⚠️  Missing linux-baseline target in Makefile")

        if not has_dev_target:
            print("⚠️  Missing linux-dev target in Makefile")

        if has_baseline_target and has_dev_target:
            print("✓ Makefile has A/B testing targets")

        return True

    def run_checks(self):
        """Run all verification checks"""
        print("Linux A/B Testing Reference Verification")
        print("=" * 50)

        # Check .config
        if not self.check_config_file():
            return False

        # Check extra_vars.yaml
        if not self.check_extra_vars():
            return False

        # Verify refs are different
        if not self.verify_refs():
            return False

        # Check Makefile (informational only)
        self.check_makefile_structure()

        print("\n" + "=" * 50)
        if self.failed_checks:
            print(f"❌ Verification failed: {', '.join(self.failed_checks)}")
            return False
        else:
            print("✅ A/B testing refs verified successfully!")
            return True


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify Linux A/B testing ref configurations",
        epilog="This tool only checks configurations, it does not run any builds or tests.",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Quick check for current directory
    if not os.path.exists("Kconfig"):
        print("❌ Error: Must be run from kdevops root directory")
        sys.exit(1)

    tester = LinuxABTester()
    success = tester.run_checks()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

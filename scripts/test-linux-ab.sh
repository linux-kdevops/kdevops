#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Test A/B configuration locally of all Linux AB configurations possible.
# The goal is to verify your extra_vars.yaml ends up with different kernel
# target refs for A and B group hosts. It does so also by checking that
# ansible will use these. No real bringup or live test is done.
#
# Note: Originally this script ran full 'make' for each build method, but
# GitHub Actions containers lack systemd and infrastructure dependencies
# that kdevops requires. Since we only need to verify configuration
# generation (not infrastructure setup), we run 'make extra_vars.yaml'
# which generates the ansible variables needed for A/B validation while
# skipping systemd services and other GitHub-incompatible components.
#
# Outputs TAP (Test Anything Protocol) format results

set -e
set -o pipefail

# Colors for output (disabled if not a terminal or if NO_COLOR is set)
if [ -t 1 ] && [ -z "${NO_COLOR}" ] && [ "${TERM}" != "dumb" ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m' # No Color
else
    RED=''
    GREEN=''
    YELLOW=''
    NC=''
fi

# TAP counters
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
declare -a FAILED_DETAILS

# Function to output TAP result
tap_result() {
    local result=$1
    local test_name=$2
    local details=$3

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    if [ "$result" = "ok" ]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo "ok $TOTAL_TESTS - $test_name"
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "not ok $TOTAL_TESTS - $test_name"
        if [ -n "$details" ]; then
            echo "  ---"
            echo "  message: $details"
            echo "  ..."
            FAILED_DETAILS+=("$test_name: $details")
        fi
    fi
}

# Function to check condition and output TAP
check_condition() {
    local condition=$1
    local test_name=$2
    local error_msg=${3:-"Condition failed"}

    if eval "$condition"; then
        tap_result "ok" "$test_name"
        return 0
    else
        tap_result "not ok" "$test_name" "$error_msg"
        return 1
    fi
}

echo "# Testing Linux A/B configuration locally"
echo "# This script tests the configuration without requiring Docker"
echo "TAP version 13"
echo ""

# Save current state
if [ -f .config ]; then
    cp .config .config.backup.$$
    tap_result "ok" "Backup current .config to .config.backup.$$"
else
    tap_result "ok" "No existing .config to backup"
fi

# Function to restore state
restore_state() {
    if [ -f .config.backup.$$ ]; then
        mv .config.backup.$$ .config >/dev/null 2>&1
        echo "# Restored original .config"
    fi
}

# Set trap to restore on exit
trap restore_state EXIT

# Test each build method
BUILD_METHODS="target 9p builder"
echo "1..18" # We expect 18 tests total (6 per build method x 3 methods)

for method in $BUILD_METHODS; do
    echo ""
    echo "# Testing $method build method"

    # Clean and apply defconfig
    if make mrproper >/dev/null 2>&1; then
        tap_result "ok" "$method: Clean environment (make mrproper)"
    else
        tap_result "not ok" "$method: Clean environment (make mrproper)" "Failed to run make mrproper"
    fi

    # Apply defconfig
    if make defconfig-linux-ab-testing-$method >/dev/null 2>&1; then
        tap_result "ok" "$method: Apply defconfig-linux-ab-testing-$method"
    else
        tap_result "not ok" "$method: Apply defconfig-linux-ab-testing-$method" "Failed to apply defconfig"
        continue
    fi

    # Generate configuration (container-safe)
    if make extra_vars.yaml >/dev/null 2>&1; then
        tap_result "ok" "$method: Generate configuration (extra_vars.yaml)"
    else
        tap_result "not ok" "$method: Generate configuration (extra_vars.yaml)" "Failed to generate extra_vars.yaml"
        continue
    fi

    # Verify A/B testing is enabled
    check_condition "grep -q 'CONFIG_KDEVOPS_BASELINE_AND_DEV=y' .config" \
        "$method: A/B testing enabled (CONFIG_KDEVOPS_BASELINE_AND_DEV=y)" \
        "A/B testing not enabled in .config"

    # Verify different refs enabled
    check_condition "grep -q 'CONFIG_BOOTLINUX_AB_DIFFERENT_REF=y' .config" \
        "$method: Different refs enabled (CONFIG_BOOTLINUX_AB_DIFFERENT_REF=y)" \
        "Different refs not enabled in .config"

    # Verify build method specific config
    case "$method" in
        target)
            check_condition "grep -q 'CONFIG_BOOTLINUX_TARGETS=y' .config" \
                "$method: Target build enabled (CONFIG_BOOTLINUX_TARGETS=y)" \
                "Target build not enabled"
            ;;
        9p)
            check_condition "grep -q 'CONFIG_BOOTLINUX_9P=y' .config" \
                "$method: 9P build enabled (CONFIG_BOOTLINUX_9P=y)" \
                "9P build not enabled"
            ;;
        builder)
            check_condition "grep -q 'CONFIG_BOOTLINUX_BUILDER=y' .config" \
                "$method: Builder build enabled (CONFIG_BOOTLINUX_BUILDER=y)" \
                "Builder build not enabled"
            ;;
    esac
done

# Additional tests for ref extraction
echo ""
echo "# Testing ref extraction from final configuration"

# Check if extra_vars.yaml was generated
if [ -f extra_vars.yaml ]; then
    tap_result "ok" "extra_vars.yaml exists"

    # Extract refs with new variable names
    BASELINE_REF=$(grep "^target_linux_ref:" extra_vars.yaml 2>/dev/null | awk '{print $2}')
    DEV_REF=$(grep "^target_linux_dev_ref:" extra_vars.yaml 2>/dev/null | awk '{print $2}')

    # Check baseline ref
    if [ -n "$BASELINE_REF" ]; then
        tap_result "ok" "Baseline ref found: $BASELINE_REF"
    else
        tap_result "not ok" "Baseline ref not found" "Could not find target_linux_ref in extra_vars.yaml"
    fi

    # Check dev ref
    if [ -n "$DEV_REF" ]; then
        tap_result "ok" "Dev ref found: $DEV_REF"
    else
        tap_result "not ok" "Dev ref not found" "Could not find target_linux_dev_ref in extra_vars.yaml"
    fi

    # Check refs are different
    if [ -n "$BASELINE_REF" ] && [ -n "$DEV_REF" ] && [ "$BASELINE_REF" != "$DEV_REF" ]; then
        tap_result "ok" "Refs are different (baseline: $BASELINE_REF, dev: $DEV_REF)"
    else
        tap_result "not ok" "Refs are not different" "Baseline and dev refs should be different for A/B testing"
    fi
else
    tap_result "not ok" "extra_vars.yaml exists" "File not found"
fi

# Summary
echo ""
echo "# Test Summary"
echo "# ============"
echo "# Total tests: $TOTAL_TESTS"
printf "# Passed: ${GREEN}%d${NC}\n" "$PASSED_TESTS"
printf "# Failed: ${RED}%d${NC}\n" "$FAILED_TESTS"

if [ $FAILED_TESTS -gt 0 ]; then
    echo ""
    printf "${RED}# Failed tests:${NC}\n"
    for failure in "${FAILED_DETAILS[@]}"; do
        printf "${RED}#   - %s${NC}\n" "$failure"
    done
    echo ""
    printf "${RED}# FAIL: A/B testing verification failed${NC}\n"
    exit 1
else
    echo ""
    printf "${GREEN}# PASS: All A/B testing verifications passed!${NC}\n"
    exit 0
fi

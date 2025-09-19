#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1
# TCG Storage kernel CI test runner for Kernel of the Day (KOTD)

# This script runs TCG storage tests against the latest kernel

set -e

TOPDIR="${TOPDIR:-$(git rev-parse --show-toplevel)}"
RESULTS_DIR="${TOPDIR}/workflows/tcg-storage/results"

# Source common CI functions if available
if [ -f "${TOPDIR}/scripts/workflows/common/kernel_ci.sh" ]; then
    source "${TOPDIR}/scripts/workflows/common/kernel_ci.sh"
fi

echo "Starting TCG Storage Kernel CI testing with KOTD..."
echo "Results will be stored in: ${RESULTS_DIR}"

# Create results directory if it doesn't exist
mkdir -p "${RESULTS_DIR}"

# Update to latest kernel
echo "Updating to kernel of the day..."
make linux

# Run the TCG storage tests
echo "Running TCG storage tests on KOTD..."
make tcg-storage

# Check test results
if [ -f "${RESULTS_DIR}/summary.txt" ]; then
    echo "Test summary:"
    cat "${RESULTS_DIR}/summary.txt"
fi

# Exit with proper status
if grep -q "FAILED" "${RESULTS_DIR}/summary.txt" 2>/dev/null; then
    echo "TCG Storage tests on KOTD FAILED"
    exit 1
else
    echo "TCG Storage tests on KOTD PASSED"
    exit 0
fi
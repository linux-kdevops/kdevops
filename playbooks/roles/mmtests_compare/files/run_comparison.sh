#!/bin/bash
# Script to run mmtests comparison with proper error handling

set -e

TOPDIR="$1"
BENCHMARK="$2"
BASELINE_NAME="$3"
DEV_NAME="$4"
OUTPUT_DIR="$5"

cd "$TOPDIR/tmp/mmtests"

# First, verify the script exists and is executable
if [ ! -f ./bin/compare-mmtests.pl ]; then
    echo "ERROR: compare-mmtests.pl not found"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Run the comparison with error checking for HTML output
echo "Running HTML comparison for $BASELINE_NAME vs $DEV_NAME"
./bin/compare-mmtests.pl \
    --directory work/log/ \
    --benchmark "$BENCHMARK" \
    --names "$BASELINE_NAME,$DEV_NAME" \
    --format html > "$OUTPUT_DIR/comparison.html" 2>&1

# Check if the output file was created and has content
if [ ! -s "$OUTPUT_DIR/comparison.html" ]; then
    echo "WARNING: comparison.html is empty or not created"
    # Check for the specific error we're trying to fix
    if grep -q "Can't use an undefined value as an ARRAY reference" "$OUTPUT_DIR/comparison.html" 2>/dev/null; then
        echo "ERROR: The patch to fix undefined array reference was not applied correctly"
        exit 1
    fi
else
    echo "HTML comparison completed successfully"
fi

# Run text comparison
echo "Running text comparison for $BASELINE_NAME vs $DEV_NAME"
./bin/compare-mmtests.pl \
    --directory work/log/ \
    --benchmark "$BENCHMARK" \
    --names "$BASELINE_NAME,$DEV_NAME" \
    > "$OUTPUT_DIR/comparison.txt" 2>&1

# Verify the text output was created
if [ ! -s "$OUTPUT_DIR/comparison.txt" ]; then
    echo "WARNING: comparison.txt is empty or not created"
else
    echo "Text comparison completed successfully"
fi

exit 0

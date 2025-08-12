#!/bin/bash
# Script to generate HTML report with embedded graphs using compare-kernels.sh

set -e

TOPDIR="$1"
BENCHMARK="$2"
BASELINE_NAME="$3"
DEV_NAME="$4"
OUTPUT_DIR="$5"

cd "$TOPDIR/tmp/mmtests/work/log"

echo "Generating HTML report with embedded graphs using compare-kernels.sh"

# Ensure output directory is absolute path
if [[ "$OUTPUT_DIR" != /* ]]; then
    OUTPUT_DIR="$TOPDIR/$OUTPUT_DIR"
fi

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Check if compare-kernels.sh exists
if [ ! -f ../../compare-kernels.sh ]; then
    echo "ERROR: compare-kernels.sh not found"
    exit 1
fi

# Generate the HTML report with graphs
echo "Running compare-kernels.sh for $BASELINE_NAME vs $DEV_NAME"

# Export R_TMPDIR for caching R objects (performance optimization)
export R_TMPDIR="$TOPDIR/tmp/mmtests_r_tmp"
mkdir -p "$R_TMPDIR"

# Suppress package installation prompts by pre-answering
export MMTESTS_AUTO_PACKAGE_INSTALL=never

# Run compare-kernels.sh with HTML format
# The HTML output goes to stdout, graphs go to output-dir
echo "Generating graphs and HTML report..."
../../compare-kernels.sh \
    --baseline "$BASELINE_NAME" \
    --compare "$DEV_NAME" \
    --format html \
    --output-dir "$OUTPUT_DIR" \
    --report-title "$BENCHMARK Performance Comparison" \
    > "$OUTPUT_DIR/comparison.html" 2> "$OUTPUT_DIR/compare-kernels.log"

# Check if the HTML was created
if [ -f "$OUTPUT_DIR/comparison.html" ] && [ -s "$OUTPUT_DIR/comparison.html" ]; then
    echo "HTML report with graphs created: $OUTPUT_DIR/comparison.html"

    # Clean up any package installation artifacts from the HTML
    # Remove lines about package installation
    sed -i '/MMTests needs to install/d' "$OUTPUT_DIR/comparison.html"
    sed -i '/dpkg-query: no packages found/d' "$OUTPUT_DIR/comparison.html"
    sed -i '/E: Unable to locate package/d' "$OUTPUT_DIR/comparison.html"
    sed -i '/WARNING: Failed to cleanly install/d' "$OUTPUT_DIR/comparison.html"
    sed -i '/Reading package lists/d' "$OUTPUT_DIR/comparison.html"
    sed -i '/Building dependency tree/d' "$OUTPUT_DIR/comparison.html"
    sed -i '/Reading state information/d' "$OUTPUT_DIR/comparison.html"
    sed -i '/Installed perl-File-Which/d' "$OUTPUT_DIR/comparison.html"
    sed -i '/Unrecognised argument:/d' "$OUTPUT_DIR/comparison.html"
else
    echo "ERROR: Failed to generate HTML report"
    echo "Check $OUTPUT_DIR/compare-kernels.log for errors"
    exit 1
fi

# Count generated graphs
PNG_COUNT=$(ls -1 "$OUTPUT_DIR"/*.png 2>/dev/null | wc -l)
echo "Generated $PNG_COUNT graph files"

# List all generated files
echo ""
echo "Generated files:"
ls -la "$OUTPUT_DIR"/*.html 2>/dev/null | head -5
echo "..."
ls -la "$OUTPUT_DIR"/*.png 2>/dev/null | head -10

# Clean up R temp directory
rm -rf "$R_TMPDIR"

echo ""
echo "HTML report generation complete"
echo "Main report: $OUTPUT_DIR/comparison.html"
exit 0

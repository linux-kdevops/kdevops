#!/bin/bash
# Visualize NFS test results

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
KDEVOPS_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
RESULTS_DIR="${1:-$KDEVOPS_DIR/workflows/nfstest/results/last-run}"
HTML_OUTPUT_DIR="$KDEVOPS_DIR/workflows/nfstest/results/html"

# Check if results directory exists
if [ ! -d "$RESULTS_DIR" ]; then
    echo "Error: Results directory '$RESULTS_DIR' does not exist"
    echo "Please run 'make nfstest-baseline' or 'make nfstest-dev' first to generate test results"
    exit 1
fi

# Check if there are any log files
LOG_COUNT=$(find "$RESULTS_DIR" -name "*.log" 2>/dev/null | wc -l)
if [ "$LOG_COUNT" -eq 0 ]; then
    echo "Error: No test log files found in '$RESULTS_DIR'"
    echo "Please run NFS tests first to generate results"
    exit 1
fi

echo "Processing NFS test results from: $RESULTS_DIR"

# Parse the results
echo "Step 1: Parsing test results..."
python3 "$SCRIPT_DIR/parse_nfstest_results.py" "$RESULTS_DIR"
if [ $? -ne 0 ]; then
    echo "Error: Failed to parse test results"
    exit 1
fi

# Generate HTML visualization
echo "Step 2: Generating HTML visualization..."
python3 "$SCRIPT_DIR/generate_nfstest_html.py" "$RESULTS_DIR"
if [ $? -ne 0 ]; then
    echo "Warning: HTML generation completed with warnings"
fi

# Check if HTML was generated
if [ -f "$HTML_OUTPUT_DIR/index.html" ]; then
    echo ""
    echo "✓ Visualization complete!"
    echo ""
    echo "Results available in: $HTML_OUTPUT_DIR/"
    echo ""
    echo "To view locally:"
    echo "  open $HTML_OUTPUT_DIR/index.html"
    echo ""
    echo "To copy to remote system:"
    echo "  scp -r $HTML_OUTPUT_DIR/ user@remote:/path/to/destination/"
    echo ""

    # List generated files
    echo "Generated files:"
    ls -lh "$HTML_OUTPUT_DIR/"
else
    echo "Error: HTML generation failed - no index.html created"
    exit 1
fi

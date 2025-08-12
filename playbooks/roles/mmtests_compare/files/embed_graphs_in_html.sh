#!/bin/bash
# Script to embed graphs in the comparison HTML

COMPARISON_HTML="$1"
COMPARE_DIR="$2"

# Check if comparison.html exists
if [ ! -f "$COMPARISON_HTML" ]; then
    echo "ERROR: $COMPARISON_HTML not found"
    exit 1
fi

# Create a backup of the original
cp "$COMPARISON_HTML" "${COMPARISON_HTML}.bak"

# Create new HTML with embedded graphs
{
    echo '<!DOCTYPE html>'
    echo '<html><head>'
    echo '<title>mmtests Comparison with Graphs</title>'
    echo '<style>'
    echo 'body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }'
    echo '.container { max-width: 1400px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }'
    echo '.resultsTable { border-collapse: collapse; width: 100%; margin: 20px 0; }'
    echo '.resultsTable th { background-color: #3498db; color: white; padding: 10px; text-align: center; font-weight: bold; }'
    echo '.resultsTable td { padding: 8px; text-align: right; font-family: monospace; border-bottom: 1px solid #ddd; }'
    echo '.resultsTable tr:nth-child(odd) { background: #f9f9f9; }'
    echo '.graph-section { background: #ecf0f1; padding: 20px; border-radius: 10px; margin: 20px 0; }'
    echo '.graph-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(500px, 1fr)); gap: 20px; }'
    echo '.graph-item { text-align: center; }'
    echo '.graph-item img { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }'
    echo 'h1 { color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 10px; }'
    echo 'h2 { color: #34495e; border-left: 4px solid #3498db; padding-left: 15px; }'
    echo 'h3 { color: #34495e; font-size: 1.1em; }'
    echo '</style>'
    echo '</head><body>'
    echo '<div class="container">'
    echo '<h1>mmtests Performance Comparison</h1>'

    # Add graphs section if any graphs exist
    if ls "$COMPARE_DIR"/*.png >/dev/null 2>&1; then
        echo '<div class="graph-section">'
        echo '<h2>Performance Graphs</h2>'
        echo '<div class="graph-grid">'

        # Main benchmark graph first
        for graph in "$COMPARE_DIR"/graph-*compact.png; do
            if [ -f "$graph" ] && [[ ! "$graph" =~ -sorted|-smooth ]]; then
                echo '<div class="graph-item">'
                echo '<h3>Main Performance Comparison</h3>'
                echo "<img src='$(basename "$graph")' alt='Main Performance'>"
                echo '</div>'
            fi
        done

        # Sorted graph
        if [ -f "$COMPARE_DIR/graph-thpcompact-sorted.png" ]; then
            echo '<div class="graph-item">'
            echo '<h3>Sorted Samples</h3>'
            echo '<img src="graph-thpcompact-sorted.png" alt="Sorted Samples">'
            echo '</div>'
        fi

        # Smooth graph
        if [ -f "$COMPARE_DIR/graph-thpcompact-smooth.png" ]; then
            echo '<div class="graph-item">'
            echo '<h3>Smoothed Trend</h3>'
            echo '<img src="graph-thpcompact-smooth.png" alt="Smoothed Trend">'
            echo '</div>'
        fi

        # Any monitor graphs
        for graph in "$COMPARE_DIR"/graph-vmstat.png "$COMPARE_DIR"/graph-proc-vmstat.png "$COMPARE_DIR"/graph-mpstat.png; do
            if [ -f "$graph" ]; then
                graphname=$(basename "$graph" .png | sed 's/graph-//')
                echo '<div class="graph-item">'
                echo "<h3>${graphname^^} Monitor</h3>"
                echo "<img src='$(basename "$graph")' alt='$graphname'>"
                echo '</div>'
            fi
        done

        echo '</div>'
        echo '</div>'
    fi

    # Add the original comparison table
    echo '<div class="graph-section">'
    echo '<h2>Detailed Comparison Table</h2>'
    cat "$COMPARISON_HTML"
    echo '</div>'

    echo '</div></body></html>'
} > "${COMPARISON_HTML}.new"

# Replace the original with the new version
mv "${COMPARISON_HTML}.new" "$COMPARISON_HTML"

echo "Graphs embedded in $COMPARISON_HTML"
exit 0

#!/bin/bash
# Script to generate mmtests graphs with proper error handling

set -e

TOPDIR="$1"
BENCHMARK="$2"
BASELINE_NAME="$3"
DEV_NAME="$4"
OUTPUT_DIR="$5"

cd "$TOPDIR/tmp/mmtests"

echo "Generating graphs for $BENCHMARK comparison"

# Create output directory if it doesn't exist
mkdir -p "$OUTPUT_DIR"

# Set up kernel list for graph generation
KERNEL_LIST="$BASELINE_NAME,$DEV_NAME"

# Check if we have the required tools
if [ ! -f ./bin/graph-mmtests.sh ]; then
    echo "ERROR: graph-mmtests.sh not found"
    exit 1
fi

if [ ! -f ./bin/extract-mmtests.pl ]; then
    echo "ERROR: extract-mmtests.pl not found"
    exit 1
fi

# Generate the main benchmark comparison graph
echo "Generating main benchmark graph..."
./bin/graph-mmtests.sh \
    -d work/log/ \
    -b "$BENCHMARK" \
    -n "$KERNEL_LIST" \
    --format png \
    --output "$OUTPUT_DIR/graph-$BENCHMARK" \
    --title "$BENCHMARK Performance Comparison" 2>&1 | tee "$OUTPUT_DIR/graph-generation.log"

# Check if the graph was created
if [ -f "$OUTPUT_DIR/graph-$BENCHMARK.png" ]; then
    echo "Main benchmark graph created: graph-$BENCHMARK.png"
else
    echo "WARNING: Main benchmark graph was not created"
fi

# Generate sorted sample graphs
echo "Generating sorted sample graph..."
./bin/graph-mmtests.sh \
    -d work/log/ \
    -b "$BENCHMARK" \
    -n "$KERNEL_LIST" \
    --format png \
    --output "$OUTPUT_DIR/graph-$BENCHMARK-sorted" \
    --title "$BENCHMARK Performance (Sorted)" \
    --sort-samples-reverse \
    --x-label "Sorted samples" 2>&1 | tee -a "$OUTPUT_DIR/graph-generation.log"

# Generate smooth curve graphs
echo "Generating smooth curve graph..."
./bin/graph-mmtests.sh \
    -d work/log/ \
    -b "$BENCHMARK" \
    -n "$KERNEL_LIST" \
    --format png \
    --output "$OUTPUT_DIR/graph-$BENCHMARK-smooth" \
    --title "$BENCHMARK Performance (Smoothed)" \
    --with-smooth 2>&1 | tee -a "$OUTPUT_DIR/graph-generation.log"

# Generate monitor graphs if data is available
echo "Checking for monitor data..."

# Function to generate monitor graph
generate_monitor_graph() {
    local monitor_type="$1"
    local title="$2"

    # Check if monitor data exists for any of the kernels
    for kernel in $BASELINE_NAME $DEV_NAME; do
        if [ -f "work/log/$kernel/$monitor_type-$BENCHMARK.gz" ] || [ -f "work/log/$kernel/$monitor_type.gz" ]; then
            echo "Generating $monitor_type graph..."
            ./bin/graph-mmtests.sh \
                -d work/log/ \
                -b "$BENCHMARK" \
                -n "$KERNEL_LIST" \
                --format png \
                --output "$OUTPUT_DIR/graph-$monitor_type" \
                --title "$title" \
                --print-monitor "$monitor_type" 2>&1 | tee -a "$OUTPUT_DIR/graph-generation.log"

            if [ -f "$OUTPUT_DIR/graph-$monitor_type.png" ]; then
                echo "Monitor graph created: graph-$monitor_type.png"
            fi
            break
        fi
    done
}

# Generate various monitor graphs
generate_monitor_graph "vmstat" "VM Statistics"
generate_monitor_graph "proc-vmstat" "Process VM Statistics"
generate_monitor_graph "mpstat" "CPU Statistics"
generate_monitor_graph "proc-buddyinfo" "Buddy Info"
generate_monitor_graph "proc-pagetypeinfo" "Page Type Info"

# List all generated graphs
echo ""
echo "Generated graphs:"
ls -la "$OUTPUT_DIR"/*.png 2>/dev/null || echo "No PNG files generated"

# Create an HTML file that embeds all the graphs
cat > "$OUTPUT_DIR/graphs.html" << 'EOF'
<!DOCTYPE html>
<html><head>
<title>mmtests Graphs</title>
<style>
body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
.container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 20px rgba(0,0,0,0.1); }
h1 { color: #2c3e50; text-align: center; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
h2 { color: #34495e; border-left: 4px solid #3498db; padding-left: 15px; }
.graph { margin: 20px 0; text-align: center; }
.graph img { max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
.description { background: #e8f8f5; border-left: 4px solid #2ecc71; padding: 15px; margin: 15px 0; }
</style>
</head>
<body>
<div class="container">
<h1>mmtests Performance Graphs</h1>
EOF

# Add each graph to the HTML file
for graph in "$OUTPUT_DIR"/*.png; do
    if [ -f "$graph" ]; then
        graphname=$(basename "$graph" .png)
        echo "<div class='graph'>" >> "$OUTPUT_DIR/graphs.html"
        echo "<h2>$graphname</h2>" >> "$OUTPUT_DIR/graphs.html"
        echo "<img src='$(basename $graph)' alt='$graphname'>" >> "$OUTPUT_DIR/graphs.html"
        echo "</div>" >> "$OUTPUT_DIR/graphs.html"
    fi
done

echo "</div></body></html>" >> "$OUTPUT_DIR/graphs.html"

echo "Graph generation complete. HTML summary: $OUTPUT_DIR/graphs.html"
exit 0

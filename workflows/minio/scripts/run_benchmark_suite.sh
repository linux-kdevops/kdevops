#!/bin/bash
# Run comprehensive MinIO Warp benchmark suite

MINIO_HOST="${1:-localhost:9000}"
ACCESS_KEY="${2:-minioadmin}"
SECRET_KEY="${3:-minioadmin}"
TOTAL_DURATION="${4:-30m}"
RESULTS_DIR="/tmp/warp-results"
TIMESTAMP=$(date +%s)

# Parse duration to seconds for calculation
parse_duration_to_seconds() {
    local duration="$1"
    local value="${duration//[^0-9]/}"
    local unit="${duration//[0-9]/}"
    
    case "$unit" in
        s) echo "$value" ;;
        m) echo $((value * 60)) ;;
        h) echo $((value * 3600)) ;;
        *) echo "1800" ;;  # Default 30 minutes
    esac
}

TOTAL_SECONDS=$(parse_duration_to_seconds "$TOTAL_DURATION")
# Distribute time across 8 benchmark types (reserving some buffer)
PER_TEST_SECONDS=$((TOTAL_SECONDS / 10))  # Divide by 10 to leave buffer
if [ $PER_TEST_SECONDS -lt 30 ]; then
    PER_TEST_SECONDS=30  # Minimum 30 seconds per test
fi

# Convert back to duration string
if [ $PER_TEST_SECONDS -ge 3600 ]; then
    PER_TEST_DURATION="$((PER_TEST_SECONDS / 3600))h"
elif [ $PER_TEST_SECONDS -ge 60 ]; then
    PER_TEST_DURATION="$((PER_TEST_SECONDS / 60))m"
else
    PER_TEST_DURATION="${PER_TEST_SECONDS}s"
fi

echo "🚀 MinIO Warp Comprehensive Benchmark Suite"
echo "==========================================="
echo "Target: $MINIO_HOST"
echo "Total Duration: $TOTAL_DURATION ($TOTAL_SECONDS seconds)"
echo "Per Test Duration: $PER_TEST_DURATION"
echo "Results: $RESULTS_DIR"
echo ""

# Ensure results directory exists
mkdir -p "$RESULTS_DIR"

# Function to run a benchmark
run_benchmark() {
    local test_type=$1
    local duration=$2
    local concurrent=$3
    local obj_size=$4

    echo "Running $test_type benchmark..."
    echo "  Duration: $duration, Concurrent: $concurrent, Size: $obj_size"

    OUTPUT_FILE="${RESULTS_DIR}/warp_${test_type}_${TIMESTAMP}.json"

    # Don't use --autoterm or --objects for duration-based tests
    warp "$test_type" \
        --host="$MINIO_HOST" \
        --access-key="$ACCESS_KEY" \
        --secret-key="$SECRET_KEY" \
        --bucket="warp-bench-${test_type}" \
        --duration="$duration" \
        --concurrent="$concurrent" \
        --obj.size="$obj_size" \
        --noclear \
        --json > "$OUTPUT_FILE" 2>&1

    if [ $? -eq 0 ]; then
        echo "✅ $test_type completed successfully"
    else
        echo "❌ $test_type failed"
    fi
    echo ""
}

# Run comprehensive test suite
echo "📊 Starting Comprehensive Benchmark Suite"
echo "-----------------------------------------"

# 1. Mixed workload (simulates real-world usage)
run_benchmark "mixed" "$PER_TEST_DURATION" "10" "1MB"

# 2. GET performance (read-heavy workload)
run_benchmark "get" "$PER_TEST_DURATION" "20" "1MB"

# 3. PUT performance (write-heavy workload)
run_benchmark "put" "$PER_TEST_DURATION" "10" "10MB"

# 4. DELETE performance
run_benchmark "delete" "$PER_TEST_DURATION" "5" "1MB"

# 5. LIST operations (metadata operations)
run_benchmark "list" "$PER_TEST_DURATION" "5" "1KB"

# 6. Small object performance
run_benchmark "mixed" "$PER_TEST_DURATION" "10" "1KB"

# 7. Large object performance
run_benchmark "mixed" "$PER_TEST_DURATION" "5" "100MB"

# 8. High concurrency test
run_benchmark "mixed" "$PER_TEST_DURATION" "50" "1MB"

echo "==========================================="
echo "✅ Benchmark Suite Complete!"
echo ""
echo "Results saved in: $RESULTS_DIR"
echo "Run 'make minio-results' to generate analysis"

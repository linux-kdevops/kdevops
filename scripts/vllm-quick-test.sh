#!/bin/bash
# Quick test script for vLLM deployment
# Tests both baseline and dev nodes, measures response time, and validates output

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOPDIR="${SCRIPT_DIR}/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
PROMPT="kdevops is"
MAX_TOKENS=30
TIMEOUT=30

# Load configuration
if [[ ! -f "${TOPDIR}/.config" ]]; then
    echo -e "${RED}Error: No .config found. Run 'make menuconfig' first.${NC}"
    exit 1
fi

# Check if baseline and dev are enabled
BASELINE_AND_DEV=$(grep "^CONFIG_KDEVOPS_BASELINE_AND_DEV=y" "${TOPDIR}/.config" || true)

# Get node names from extra_vars.yaml
if [[ ! -f "${TOPDIR}/extra_vars.yaml" ]]; then
    echo -e "${RED}Error: extra_vars.yaml not found. Run 'make' first.${NC}"
    exit 1
fi

KDEVOPS_HOST_PREFIX=$(grep "^kdevops_host_prefix:" "${TOPDIR}/extra_vars.yaml" | awk '{print $2}' | tr -d '"')
if [[ -z "$KDEVOPS_HOST_PREFIX" ]]; then
    echo -e "${RED}Error: Could not determine host prefix from extra_vars.yaml${NC}"
    exit 1
fi

# Determine nodes to test
NODES=("${KDEVOPS_HOST_PREFIX}-vllm")
if [[ -n "$BASELINE_AND_DEV" ]]; then
    NODES+=("${KDEVOPS_HOST_PREFIX}-vllm-dev")
fi

# Function to test a single node
test_node() {
    local node=$1
    local node_type=$2
    local exit_code=0

    echo ""
    echo "Testing ${node_type} node: ${node}"
    echo "----------------------------------------"

    # Get node IP
    local node_ip=$(ansible "${node}" -i "${TOPDIR}/hosts" -m shell -a "hostname -I | awk '{print \$1}'" 2>/dev/null | grep -A1 "${node} |" | tail -1 | xargs)

    if [[ -z "$node_ip" ]]; then
        echo -e "${RED}✗ Failed to get IP for ${node}${NC}"
        return 1
    fi

    echo "Node IP: ${node_ip}"

    # Check if port-forward is running
    local pf_running=$(ssh "${node}" "ps aux | grep 'kubectl port-forward' | grep 8000 | grep -v grep" 2>/dev/null || true)

    if [[ -z "$pf_running" ]]; then
        echo "Starting kubectl port-forward..."
        ssh "${node}" "sudo nohup kubectl --kubeconfig=/root/.kube/config port-forward -n vllm-system svc/vllm-prod-${node}-router-service 8000:80 --address=0.0.0.0 > /tmp/pf.log 2>&1 &" 2>/dev/null || true
        sleep 2
    else
        echo "kubectl port-forward already running"
    fi

    # Prepare JSON payload
    local json_payload=$(cat <<EOF
{
  "model": "facebook/opt-125m",
  "prompt": "${PROMPT}",
  "max_tokens": ${MAX_TOKENS}
}
EOF
)

    # Test the endpoint with timing
    echo "Sending request: \"${PROMPT}\""
    local start_time=$(date +%s.%N)

    local response=$(curl -s -m "${TIMEOUT}" \
        "http://${node_ip}:8000/v1/completions" \
        -H 'Content-Type: application/json' \
        -d "${json_payload}" 2>&1)

    local curl_exit=$?
    local end_time=$(date +%s.%N)
    local duration=$(echo "$end_time - $start_time" | bc)

    if [[ $curl_exit -ne 0 ]]; then
        echo -e "${RED}✗ Request failed (curl exit code: ${curl_exit})${NC}"
        echo "Response: ${response}"
        return 1
    fi

    # Check if response is valid JSON
    if ! echo "${response}" | python3 -m json.tool > /dev/null 2>&1; then
        echo -e "${RED}✗ Invalid JSON response${NC}"
        echo "Response: ${response}"
        return 1
    fi

    # Extract completion text
    local completion=$(echo "${response}" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('choices', [{}])[0].get('text', 'N/A').strip())" 2>/dev/null || echo "ERROR")

    if [[ "$completion" == "ERROR" ]] || [[ "$completion" == "N/A" ]]; then
        echo -e "${RED}✗ Failed to extract completion from response${NC}"
        echo "Response: ${response}"
        return 1
    fi

    # Check for error in response
    local error_msg=$(echo "${response}" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('message', ''))" 2>/dev/null || echo "")

    if [[ -n "$error_msg" ]] && [[ "$error_msg" != "" ]]; then
        echo -e "${RED}✗ API returned error: ${error_msg}${NC}"
        return 1
    fi

    # Success!
    echo -e "${GREEN}✓ Success!${NC}"
    echo "Duration: ${duration}s"
    echo "Full response: \"${PROMPT}${completion}\""
    echo ""

    # Pretty print full JSON response
    echo "Full JSON response:"
    echo "${response}" | python3 -m json.tool | head -30

    return 0
}

# Main execution
echo "========================================"
echo "vLLM Quick Test"
echo "========================================"
echo "Prompt: \"${PROMPT}\""
echo "Max tokens: ${MAX_TOKENS}"
echo "Nodes to test: ${#NODES[@]}"

overall_exit=0

for i in "${!NODES[@]}"; do
    node="${NODES[$i]}"
    if [[ $i -eq 0 ]]; then
        node_type="Baseline"
    else
        node_type="Development"
    fi

    if ! test_node "$node" "$node_type"; then
        overall_exit=1
        echo -e "${RED}✗ Test failed for ${node}${NC}"
    fi
done

echo ""
echo "========================================"
if [[ $overall_exit -eq 0 ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
else
    echo -e "${RED}Some tests failed!${NC}"
fi
echo "========================================"

exit $overall_exit

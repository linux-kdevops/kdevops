#!/bin/bash
# Demo script showing the complete AI results pipeline with graphs and HTML report

echo "=== AI Benchmark Results Pipeline Demo ==="
echo

# Step 1: Generate test results on all hosts
echo "1. Generating test results on all AI hosts..."
ansible -i hosts ai -b -m shell -a '
mkdir -p /data/ai-benchmark/
chmod 777 /data/ai-benchmark/
HOSTNAME=$(hostname)
echo "{
  \"test\": \"benchmark\",
  \"timestamp\": \"$(date -Iseconds)\",
  \"host\": \"${HOSTNAME}\",
  \"filesystem\": \"$(echo ${HOSTNAME} | cut -d- -f3)\",
  \"performance\": {
    \"insert_qps\": $((RANDOM % 5000 + 1000)),
    \"query_qps\": $((RANDOM % 10000 + 5000))
  }
}" > /data/ai-benchmark/results_${HOSTNAME}_1.json
chmod 644 /data/ai-benchmark/results_${HOSTNAME}_1.json
'

echo
echo "2. Creating results directories..."
mkdir -p workflows/ai/results/collected
mkdir -p workflows/ai/results/graphs

echo
echo "3. Collecting results from all hosts..."
for host in $(ansible -i hosts ai --list-hosts | grep -v "hosts" | sed 's/^[[:space:]]*//')
do
    echo "   Collecting from $host..."
    ansible -i hosts $host -m fetch -a "src=/data/ai-benchmark/results_${host}_1.json dest=workflows/ai/results/collected/ flat=yes" 2>/dev/null || true
done

echo
echo "4. Generating performance graphs..."
python3 playbooks/roles/ai_collect_results/files/generate_graphs.py \
    workflows/ai/results/collected \
    workflows/ai/results/graphs

echo
echo "5. Generating HTML report..."
python3 playbooks/roles/ai_collect_results/files/generate_html_report.py \
    workflows/ai/results/collected \
    workflows/ai/results/graphs \
    workflows/ai/results/benchmark_report.html

echo
echo "=== Pipeline Complete! ==="
echo
echo "Results available at:"
echo "  - Raw data: workflows/ai/results/collected/"
echo "  - Graphs: workflows/ai/results/graphs/"
echo "  - HTML Report: workflows/ai/results/benchmark_report.html"
echo
echo "To view the HTML report, open it in a web browser:"
echo "  firefox workflows/ai/results/benchmark_report.html"
echo

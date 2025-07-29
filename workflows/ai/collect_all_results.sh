#!/bin/bash
# Collect results from all AI hosts (both baseline and dev)

echo "Collecting results from all AI hosts..."

# Create local results directory
mkdir -p workflows/ai/results/collected

# First, list what files exist
echo "Checking for results files on hosts..."
ansible -i hosts ai -m shell -a "ls -la /data/ai-benchmark/results_*.json 2>/dev/null || echo 'No results'"

# Collect each file individually
for host in $(ansible -i hosts ai --list-hosts | grep -v "hosts" | sed 's/^[[:space:]]*//')
do
    echo "Collecting from $host..."
    ansible -i hosts $host -m fetch -a "src=/data/ai-benchmark/results_${host}_1.json dest=workflows/ai/results/collected/ flat=yes" 2>/dev/null || true
done

echo "Results collected to: workflows/ai/results/collected/"
ls -la workflows/ai/results/collected/

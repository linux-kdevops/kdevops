#!/bin/bash
# Simple test script to generate dummy results for testing ai-results collection

# Create results on all AI hosts
ansible -i hosts ai -b -m shell -a '
mkdir -p /data/ai-benchmark/
chmod 777 /data/ai-benchmark/
HOSTNAME=$(hostname)
echo "{
  \"test\": \"dummy\",
  \"timestamp\": \"$(date -Iseconds)\",
  \"host\": \"${HOSTNAME}\",
  \"performance\": {
    \"insert_qps\": 1000,
    \"query_qps\": 5000
  }
}" > /data/ai-benchmark/results_${HOSTNAME}_1.json
chmod 644 /data/ai-benchmark/results_${HOSTNAME}_1.json
'

echo "Test results created. Now run 'make ai-results' to collect them."

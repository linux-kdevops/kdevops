#!/bin/bash
# blk_iobuf_pool A/B for the kvio KV-cache-offload passthrough workload.
#
# kvio issues LLM KV-cache-offload store/load I/O through LMCache's raw_block
# io_uring_cmd NVMe passthrough engine, sized from REAL model geometry (fake KV
# bytes -- storage geometry is content-independent). Passthrough bios bounce
# through blk_iobuf_pool folios, so this exercises the pool on the passthrough
# path (distinct from run_sweep.sh's io_uring fixed buffers and run_iomap.sh's
# iomap DIO bounce).
#
# Run once per boot state (pool on vs. booted blk_iobuf.iobuf_pool_max_order=0),
# passing a matching LABEL. Captures per-model store/load latency + the
# iobuf_pool_allocs delta (engagement) so the A/B is attributable.
#
# Prereqs in the guest (built by the kvio setup step, not here):
#   - LMCache `kvio` branch at $KVIO_SRC with the rust raw_block ext built
#   - examples/kv_cache_offload_io/run_kv_offload_io.py (real-geometry generator)
#   - a Python venv on PATH with torch (CPU is fine) + lmcache importable
set -u
NGDEV=${1:-/dev/ng0n1}          # NVMe char device (io_uring_cmd passthrough)
LABEL=${2:-poolon}              # poolon | pooloff (matches the booted state)
OUT=${3:-/tmp/kvio_${LABEL}.jsonl}
HDR=${4:-/tmp/kvio_env_${LABEL}.txt}

KVIO_SRC=${KVIO_SRC:-$HOME/lmcache-src}
EX="$KVIO_SRC/examples/kv_cache_offload_io"
MODELS=${MODELS:-"meta-llama/Llama-3.1-8B-Instruct Qwen/Qwen3-32B mistralai/Mistral-7B-Instruct-v0.2"}
DTYPE=${DTYPE:-bfloat16}
CHUNK=${CHUNK:-256}
NCHUNKS=${NCHUNKS:-8}
ITERS=${ITERS:-10}
WARMUP=${WARMUP:-3}

# Resolve the block device behind the ng char device for sysfs pool counters
# (/dev/ngXnY -> /dev/nvmeXnY -> /sys/block/nvmeXnY/queue/iobuf_pool_*).
blk=$(basename "$NGDEV" | sed 's/^ng/nvme/')
q=/sys/block/$blk/queue

: > "$OUT"
{
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "kernel=$(uname -r)"
  echo "label=$LABEL ngdev=$NGDEV blkdev=/dev/$blk"
  echo "dtype=$DTYPE chunk_tokens=$CHUNK num_chunks=$NCHUNKS iters=$ITERS warmup=$WARMUP"
  echo "logical_block_size=$(cat $q/logical_block_size 2>/dev/null)"
  echo "pool_enabled=$(cat $q/iobuf_pool_enabled 2>/dev/null)"
  echo "pool_order=$(cat $q/iobuf_pool_order 2>/dev/null)"
  echo "pool_folio_size=$(cat $q/iobuf_pool_folio_size 2>/dev/null)"
  echo "pool_reasons=$(cat $q/iobuf_pool_reasons 2>/dev/null)"
  echo "max_order=$(cat /sys/module/blk_iobuf/parameters/iobuf_pool_max_order 2>/dev/null)"
  echo "nproc=$(nproc)"
} > "$HDR"

for model in $MODELS; do
  a0=$(cat $q/iobuf_pool_allocs 2>/dev/null || echo 0)
  # run_kv_offload_io.py prints "store/load: p50 X ms  p99 Y ms | Z MB/s | ..."
  log=$(sudo -E env PYTHONPATH="$EX:$KVIO_SRC" \
        python "$EX/run_kv_offload_io.py" \
        --model "$model" --dtype "$DTYPE" --chunk-tokens "$CHUNK" \
        --num-chunks "$NCHUNKS" --device "$NGDEV" --engine uring_cmd \
        --iters "$ITERS" --warmup "$WARMUP" 2>/dev/null)
  a1=$(cat $q/iobuf_pool_allocs 2>/dev/null || echo 0)

  block=$(echo "$log" | awk -F'= ' '/KV block/{print $2}' | awk '{print $1}')
  s_p50=$(echo "$log" | awk '/^  store:/{print $3}')
  s_p99=$(echo "$log" | awk '/^  store:/{print $6}')
  l_p50=$(echo "$log" | awk '/^  load :/{print $3}')
  l_p99=$(echo "$log" | awk '/^  load :/{print $6}')

  printf '{"label":"%s","model":"%s","block_bytes":%s,"pool_allocs_delta":%s,' \
    "$LABEL" "$model" "${block:-0}" "$((a1 - a0))" >> "$OUT"
  printf '"store_p50_ms":%s,"store_p99_ms":%s,"load_p50_ms":%s,"load_p99_ms":%s}\n' \
    "${s_p50:-null}" "${s_p99:-null}" "${l_p50:-null}" "${l_p99:-null}" >> "$OUT"
  echo "  $model: block=${block:-?}B pool_allocs_delta=$((a1 - a0)) store_p50=${s_p50:-?}ms load_p50=${l_p50:-?}ms"
done
echo "DONE $LABEL -> $OUT"

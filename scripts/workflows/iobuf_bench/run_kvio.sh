#!/bin/bash
# blk_iobuf_pool A/B for the kvio KV-cache-offload passthrough workload.
#
# Test setup, findings, and the matched op-38 A/B: see kvio-results.md in this
# directory. kvio docs (how it works / deps / how to run):
#   https://htmlpreview.github.io/?https://github.com/SamsungDS/ebpf-syscall/blob/ebpf-fixes/docs/kvio.html
#
# kvio issues LLM KV-cache-offload store/load I/O through LMCache's raw_block
# io_uring_cmd NVMe passthrough engine, sized from REAL model geometry (fake KV
# bytes -- storage geometry is content-independent). Passthrough bios bounce
# through blk_iobuf_pool folios, so this exercises the pool on the passthrough
# path (distinct from run_sweep.sh's io_uring fixed buffers and run_iomap.sh's
# iomap DIO bounce).
#
# Pool creation is gated by nvme_core.iobuf_pool={0 off,1 auto,2 force} AND by
# blk_iobuf_choose_order(): a pool is only created when device geometry supplies
# a reason (io_min>PAGE, seg_geom>PAGE, or io_opt>=PAGE with prefer_io_opt on).
# "force" only warns-on-failure -- it does NOT bypass a zero-order decision, so
# on a plain 4 KiB-IU drive force alone still creates nothing. To engage the pool
# on a regular drive (the "large folios in general" flavor) boot with:
#   nvme_core.iobuf_pool=1 blk_iobuf.iobuf_pool_prefer_io_opt=1
# and confirm the drive advertises optimal_io_size>=4096 (IO_OPT reason 0x4).
#
# Run once per boot state (pool on vs. nvme_core.iobuf_pool=0), passing a
# matching LABEL. Captures per-model store/load latency + the iobuf_pool_allocs
# delta (engagement) so the A/B is attributable.
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
  echo "optimal_io_size=$(cat $q/optimal_io_size 2>/dev/null)"
  echo "nvme_iobuf_pool_mode=$(cat /sys/module/nvme_core/parameters/iobuf_pool 2>/dev/null)"
  echo "prefer_io_opt=$(cat /sys/module/blk_iobuf/parameters/iobuf_pool_prefer_io_opt 2>/dev/null)"
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

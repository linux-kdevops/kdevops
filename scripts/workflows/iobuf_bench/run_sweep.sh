#!/bin/bash
# blk_iobuf_pool A/B sweep: pool vs malloc(THP) vs mallocnh(4K) fixed buffers.
# CPU-bound regime: small cache-resident span on writeback-cached virtual NVMe,
# isolating per-I/O software cost (bio segments / buffer import).
set -u
DEV=${1:-/dev/nvme1n1}
OUT=${2:-/tmp/iobuf_results.jsonl}
HDR=${3:-/tmp/iobuf_env.txt}
SPAN=${SPAN:-1024}        # MiB working set (cache-resident)
SECS=${SECS:-5}
ITERS=${ITERS:-5}
BENCH=/tmp/iobuf_bench
dn=$(basename "$DEV")

: > "$OUT"
{
  echo "date_utc=$(date -u +%FT%TZ)"
  echo "kernel=$(uname -r)"
  echo "dev=$DEV span_mb=$SPAN secs=$SECS iters=$ITERS"
  echo "logical_block_size=$(cat /sys/block/$dn/queue/logical_block_size)"
  echo "pool_enabled=$(cat /sys/block/$dn/queue/iobuf_pool_enabled)"
  echo "pool_order=$(cat /sys/block/$dn/queue/iobuf_pool_order)"
  echo "pool_folio_size=$(cat /sys/block/$dn/queue/iobuf_pool_folio_size)"
  echo "pool_reasons=$(cat /sys/block/$dn/queue/iobuf_pool_reasons)"
  echo "nproc=$(nproc)"
  echo "mem_kb=$(awk '/MemTotal/{print $2}' /proc/meminfo)"
  echo "cache_mode=writeback(qemu_default)"
  echo "thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled)"
} > "$HDR"

# Allocate + warm the working span (defeat sparse-zero shortcut, fill host cache)
sudo dd if=/dev/zero of="$DEV" bs=16M count=$((SPAN/16 + 8)) oflag=direct status=none
sudo dd if="$DEV" of=/dev/null bs=16M count=$((SPAN/16 + 8)) iflag=direct status=none

emit() {  # $1=iter ; reads a bench JSON line on stdin, injects iter + counters
  local iter=$1 a m fb line
  a=$(cat /sys/block/$dn/queue/iobuf_pool_allocs)
  fb=$(cat /sys/block/$dn/queue/iobuf_pool_fallbacks)
  m=$(cat /sys/block/$dn/queue/iobuf_pool_misses)
  read -r line
  [ -z "$line" ] && return
  echo "{\"iter\":$iter,\"pool_allocs\":$a,\"pool_fallbacks\":$fb,\"pool_misses\":$m,${line:1}" >> "$OUT"
}

total=0
for rw in randread randwrite; do
 for bs in 16384 32768 65536 131072; do
  for qd in 1 8 32; do
   for iter in $(seq 1 $ITERS); do
    # interleave the 3 modes within each iteration so they see identical conditions
    for mode in pool malloc mallocnh; do
      sudo taskset -c 0 $BENCH "$DEV" $mode $rw $bs $qd $SECS $SPAN | emit $iter
      total=$((total+1))
    done
   done
  done
 done
done
echo "DONE total_runs=$total -> $OUT"

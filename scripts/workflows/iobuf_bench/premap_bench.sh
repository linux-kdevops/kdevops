#!/bin/bash
# premap_bench.sh -- per-command host CPU for three buffer/mapping strategies at
# one NVMe command size, on the raw passthrough path (/dev/ngXnY):
#
#   page-granular : ordinary 4 KiB-page user buffer (mapped per IO)
#   huge page     : huge-page user buffer -- contiguous, still mapped per IO
#   premap        : blk_iobuf_pool buffer -- contiguous AND mapped once (dma_iova)
#
# Emits CSV the plot script consumes: arm,cyc_per_cmd,note
#
# Requires the tool `nvme_uring_cmd_smoke` built from the ebpf-syscall tree with
# its --premap / --hugepage flags:
#   git clone https://github.com/SamsungDS/ebpf-syscall && cd ebpf-syscall
#   make nvme_uring_cmd_smoke      # needs liburing-dev
# and, for --premap, the pool provisioned + multipath off on the kernel cmdline:
#   nvme_core.multipath=N nvme_core.iobuf_pool_folios=32 nvme_core.iobuf_pool_order=10
# and huge pages reserved for the huge-page arm:
#   echo 200 | sudo tee /proc/sys/vm/nr_hugepages
#
# Usage: premap_bench.sh <ngdev> [len-bytes] [tool-path] [out.csv]
set -u
NG=$1; LEN=${2:-2097152}; TOOL=${3:-./nvme_uring_cmd_smoke}; CSV=${4:-ace.csv}
LBA=${LBA:-512}; QD=${QD:-32}; CNT=${CNT:-30000}; REP=${REP:-3}
PERF=$(ls /usr/lib/linux-tools/*/perf 2>/dev/null | head -1); [ -z "$PERF" ] && PERF=$(command -v perf)
getcyc(){ awk '/cycles/{gsub(/,/,"",$1);print $1;exit}' "$1"; }

echo "arm,cyc_per_cmd,note" > "$CSV"
echo "ng=$NG len=$LEN qd=$QD count=$CNT rep=$REP tool=$TOOL"
run(){
  local arm=$1 flag=$2 note=$3 vals="" ok=1
  for r in $(seq 1 "$REP"); do
    sudo "$PERF" stat -a -e cycles -o /tmp/pm_pf -- \
      "$TOOL" --dev "$NG" --len "$LEN" --lba-size "$LBA" --qd "$QD" --count "$CNT" $flag \
      > /tmp/pm.out 2>&1
    if grep -qE "errors=$CNT|ALLOC_IOBUF|MAP_FAILED|cannot|Invalid" /tmp/pm.out; then ok=0; break; fi
    vals="$vals $(python3 -c "print($(getcyc /tmp/pm_pf)/$CNT)")"
  done
  if [ "$ok" = 0 ]; then
    echo "$arm,,${note}; could not issue: $(tail -1 /tmp/pm.out)" | tee -a "$CSV"
  else
    local med; med=$(python3 -c "v=sorted([${vals// /,}]); print(f'{v[len(v)//2]:.0f}')")
    echo "$arm,$med,$note" | tee -a "$CSV"
  fi
}
run "page-granular" ""          "ordinary 4 KiB pages; mapped per IO"
run "huge page"     "--hugepage" "contiguous (1 segment); mapped per IO"
run "premap"        "--premap"   "contiguous (1 segment); mapped once (dma_iova)"
echo "wrote $CSV"

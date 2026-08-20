#!/bin/bash
# ublk_bench.sh -- place ublk (copy vs optimized batch+zero-copy) on the same
# IOPS/core axes as SPDK / premap / stock io_uring_cmd. kublk loop target over
# /dev/nvme0n1 (io_uring O_DIRECT backend), host-bound (device not the limit).
# Accounts TOTAL system CPU (fio + ublk server + backend), since ublk inherently
# uses a separate server thread. Emits results.jsonl rows: impl,size,qd,rep,...
set -u
KUBLK=$HOME/linux-premap/tools/testing/selftests/ublk/kublk
BLK=/dev/nvme0n1; DEVN=/dev/ublkb0
OUT=${OUT:-$HOME/ublk_out}; mkdir -p "$OUT"; JSONL="$OUT/results.jsonl"; : > "$JSONL"
SIZES=(${SIZES:-4096 16384 65536 131072}); QDS=(${QDS:-8 32 128})
REPS=${REPS:-2}; RUNT=${RUNT:-12}; FIOCORE=${FIOCORE:-10}
busy(){ awk '/^cpu /{i=$5+$6;t=0;for(k=2;k<=NF;k++)t+=$k;print t-i}' /proc/stat; }
log(){ echo "[$(date -u +%T)] $*" >&2; }

run_mode(){ # $1=impl-label  $2="kublk flags"
  local impl=$1 flags=$2
  sudo $KUBLK del -a >/dev/null 2>&1; sleep 1
  sudo $KUBLK add -t loop $flags -q 1 -d 128 $BLK >/tmp/ublk_$impl.log 2>&1; sleep 1
  [ -e $DEVN ] || { log "$impl device FAILED"; return; }
  for size in "${SIZES[@]}"; do for qd in "${QDS[@]}"; do for rep in $(seq 1 $REPS); do
    local c0=$(busy)
    sudo taskset -c $FIOCORE fio --name=u --filename=$DEVN --ioengine=io_uring --direct=1 \
      --rw=randread --bs=$size --iodepth=$qd --size=6000G --time_based --runtime=$RUNT \
      --ramp_time=3 --group_reporting --output-format=json >/tmp/ub_fio.json 2>/dev/null
    local c1=$(busy)
    python3 -c "
import json
d=json.load(open('/tmp/ub_fio.json'))['jobs'][0]['read']
cores=($c1-$c0)/100/$RUNT
iops=d['iops']; p=d['clat_ns']['percentile']
r={'impl':'$impl','size':$size,'qd':$qd,'rep':$rep,'iops':round(iops),
   'core_util':round(cores,3),'iops_per_core':round(iops/cores) if cores>0 else 0,
   'p99_us':round(p['99.000000']/1000,1),'p999_us':round(p['99.900000']/1000,1),
   'bw_mbps':round(d['bw']/1024)}
print(json.dumps(r))
" | tee -a "$JSONL" >/dev/null
    log "$impl s=$size qd=$qd r=$rep"
  done; done; done
  sudo $KUBLK del -a >/dev/null 2>&1; sleep 1
}

run_mode ublk_copy    ""
run_mode ublk_batchzc "-b -z"
echo "UBLK_DONE -> $JSONL ($(wc -l < $JSONL) rows)"

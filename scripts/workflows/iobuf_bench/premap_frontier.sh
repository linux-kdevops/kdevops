#!/bin/bash
# premap_frontier.sh -- the kernel PREMAP arm for the local crossover: the
# io_uring_cmd map-once path (smoke --premap), interrupt-driven, across block
# sizes at pinned core counts. Same metric/columns as frontier_local.sh so the
# rows drop straight onto the crossover figure. Needs the premap kernel (pool +
# clamp lift). Emits: arm,bs,cores,iops,bw_mbps,p99_us,busy_cores
set -u
SMOKE=${SMOKE:-$HOME/smoke}
CSV=${CSV:-$HOME/premap_frontier.csv}
NGS=(/dev/ng0n1 /dev/ng1n1 /dev/ng2n1 /dev/ng3n1)
CORES=(${CORES:-1 2 4})
QD=${QD:-128}; LBA=512
declare -A LEN=( [4k]=4096 [16k]=16384 [128k]=131072 [512k]=524288 )
declare -A CNT=( [4k]=1500000 [16k]=700000 [128k]=150000 [512k]=120000 )
BSES=(${BSES:-4k 16k 128k 512k})
busy(){ awk '/^cpu /{idle=$5+$6;t=0;for(k=2;k<=NF;k++)t+=$k;print t-idle}' /proc/stat; }
echo "arm,bs,cores,iops,bw_mbps,p99_us,busy_cores" > "$CSV"
sudo sysctl -q -w vm.nr_hugepages=1024

for bs in "${BSES[@]}"; do
  len=${LEN[$bs]}; cnt=${CNT[$bs]}
  for c in "${CORES[@]}"; do
    c0=$(busy); t0=$(date +%s.%N)
    for ng in "${NGS[@]}"; do
      sudo taskset -c 0-$((c-1)) "$SMOKE" --dev "$ng" --count $cnt --qd $QD \
        --len $len --lba-size $LBA --cmds-per-obj 1 --premap >/tmp/pf_$(basename $ng).json 2>&1 &
    done
    wait
    t1=$(date +%s.%N); c1=$(busy)
    python3 -c "
import json,glob
wall=$t1-$t0
iops=0.0; byps=0.0; p99=0.0
for f in glob.glob('/tmp/pf_ng*.json'):
    try:
        line=[L for L in open(f) if L.lstrip().startswith('{')][-1]
        d=json.loads(line)
        iops+=d.get('iops',0.0); byps+=d.get('bytes_per_second',0.0)
        p99=max(p99, d.get('latency_ns',{}).get('p99',0)/1000.0)
    except Exception: pass
bw=byps/1e6  # MB/s
bc=($c1-$c0)/100/wall
print(f'kernel_premap,$bs,$c,{iops:.0f},{bw:.0f},{p99:.0f},{bc:.2f}')
" | tee -a "$CSV"
    sleep 2
  done
done
echo "PREMAP_FRONTIER_DONE -> $CSV"

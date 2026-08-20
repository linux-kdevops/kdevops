#!/bin/bash
# two_box.sh -- CLEAN NVMe-oF/TCP target comparison across two boxes.
# Target box runs ONLY the target, so its whole-system CPU IS the pure target
# cost (no initiator contamination -- the flaw that sank the loopback run).
# Initiator box drives fio over the wire; we sample target-box CPU during each
# run. Sweeps SPDK reactor count {2,4,8} to build SPDK's IOPS-vs-target-cores
# curve against kernel nvmet. Emits: arm,bs,qd,iops,bw_mbps,p99_us,tgt_cores
set -u
SP=/tmp/claude-1000/-home-mcgrof-devel-ebpf-syscall/3336ad37-4446-4ae8-9316-ce54f6ca078c/scratchpad
TSSH="$SP/ssh.sh"; ISSH="$SP/ssh_init.sh"
TGT_IP=69.67.151.123
DEVS="/dev/nvme0n1 /dev/nvme1n1 /dev/nvme2n1 /dev/nvme3n1"
BDFS="0000:c1:00.0 0000:c3:00.0 0000:c5:00.0 0000:c7:00.0"
CSV="$SP/two_box.csv"
BSES="4k 128k"; QDS="8 32 128"; JPD=4; T=12; RANGE=100G
echo "arm,bs,qd,iops,bw_mbps,p99_us,tgt_cores" > "$CSV"

tbusy(){ $TSSH "awk '/^cpu /{idle=\$5+\$6;t=0;for(k=2;k<=NF;k++)t+=\$k;print t-idle}' /proc/stat" 2>/dev/null; }
fabdevs(){ $ISSH 'out=""; for n in /sys/class/nvme/nvme*; do [ "$(cat $n/transport 2>/dev/null)" = tcp ] || continue; b=$(basename $n); for ns in /dev/${b}n*; do [ -e "$ns" ] && out="$out $ns"; done; done; echo $out' 2>/dev/null; }

connect(){ local pfx=$1; $ISSH "sudo modprobe nvme-tcp; for i in 0 1 2 3; do sudo nvme connect -t tcp -a $TGT_IP -s 4420 -n ${pfx}\$i >/dev/null 2>&1; done; sleep 3"; }
disconnect(){ $ISSH 'sudo nvme disconnect-all >/dev/null 2>&1'; sleep 2; }

sweep(){ # $1=armlabel  $2=fabdevs
  local arm=$1 fdevs="$2" bs qd jobs c0 c1
  for bs in $BSES; do for qd in $QDS; do
    jobs=""; for d in $fdevs; do jobs="$jobs --name=$(basename $d) --filename=$d --numjobs=$JPD"; done
    c0=$(tbusy)
    $ISSH "sudo fio --ioengine=io_uring --direct=1 --rw=randread --bs=$bs --iodepth=$qd \
      --size=$RANGE --time_based --runtime=$T --ramp_time=3 --group_reporting \
      --output-format=json $jobs 2>/dev/null" > "$SP/tb_fio.json" 2>/dev/null
    c1=$(tbusy)
    python3 -c "
import json
d=json.load(open('$SP/tb_fio.json'))
iops=sum(j['read']['iops'] for j in d['jobs'])
bw=sum(j['read']['bw'] for j in d['jobs'])/1024
p99=max(j['read']['clat_ns']['percentile']['99.000000'] for j in d['jobs'])/1000
tc=($c1-$c0)/100/$T
print(f'$arm,$bs,$qd,{iops:.0f},{bw:.0f},{p99:.0f},{tc:.2f}')
" | tee -a "$CSV"
  done; done
}

# ---- kernel nvmet ----
echo "### nvmet ###"
$TSSH "LISTEN_IP=$TGT_IP bash \$HOME/nvmet_setup.sh $DEVS" >/dev/null 2>&1
connect "nvmet-bench-"
FAB=$(fabdevs); echo "fab: $FAB"
sweep nvmet "$FAB"
disconnect
$TSSH "sudo bash \$HOME/nvmet_teardown.sh" >/dev/null 2>&1
sleep 3

# ---- SPDK nvmf, reactor sweep ----
for R in 2 4 8; do
  mask=$(printf '0x%x' $(( (1<<R)-1 )))
  echo "### spdk r=$R ($mask) ###"
  $TSSH "LISTEN_IP=$TGT_IP REACTOR_MASK=$mask SPDK=\$HOME/spdk bash \$HOME/spdk_nvmf_setup.sh $BDFS" >/dev/null 2>&1
  connect "nqn.2026-08.io.spdk:bench-"
  FAB=$(fabdevs); echo "fab: $FAB"
  sweep "spdk_r$R" "$FAB"
  disconnect
  $TSSH "[ -f /tmp/nvmf_tgt.pid ] && sudo kill \$(cat /tmp/nvmf_tgt.pid) 2>/dev/null; sleep 2; sudo PCI_ALLOWED=\"$BDFS\" \$HOME/spdk/scripts/setup.sh reset >/dev/null 2>&1; sleep 3"
done
echo "TWO_BOX_DONE -> $CSV"
column -t -s, "$CSV"

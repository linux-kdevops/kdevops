#!/bin/bash
# spdk_gbps_per_core.sh -- storage throughput PER CPU CORE for a large-object
# NVMe read workload, three paths: stock io_uring_cmd (hugepage fixed buffers),
# premap (blk_iobuf_pool map-once), and SPDK spdk_nvme_perf (VFIO polling).
#
# The point (per the premap-vs-SPDK design): NOT peak GB/s, but GB/s per CPU
# core. The kernel path is interrupt-driven so CPU scales with load; SPDK burns
# a full polling core regardless. On large objects the kernel path wins the
# efficiency metric. Emits CSV: arm,drives,gbps,busy_cores,gbps_per_core.
#
# SAFETY: the SPDK arm binds ONLY the drives you pass to vfio-pci; SPDK's
# setup.sh additionally refuses any drive with an active mount/md holder, so a
# root-mirror member is never bound. Always pass FREE namespaces.
#
# Requires: fio, a premap-capable nvme_uring_cmd_smoke (--premap), a built SPDK
# (build/bin/spdk_nvme_perf), reserved huge pages, and a kernel booted with the
# pool + lift + multipath=N (see iobuf-premap-tlb-baremetal / PREMAP-TLB-README).
#
# Usage: spdk_gbps_per_core.sh "<ng1> [<ng2> ...]" "<bdf1> [<bdf2> ...]" \
#          <smoke-tool> <spdk_nvme_perf> [out.csv]
#   ng devices and PCI BDFs must be the SAME free drives, in the same order.
set -u
NGS=($1); BDFS=($2); SMOKE=$3; SPDK_PERF=$4; CSV=${5:-spdk_gbps.csv}
BS=${BS:-2M}; QD=${QD:-64}; T=${T:-15}; LBA=${LBA:-512}
N=${#NGS[@]}
busy(){ awk '/^cpu /{i=$5+$6;t=0;for(k=2;k<=NF;k++)t+=$k;print t-i}' /proc/stat; }
[ -f "$CSV" ] || echo "arm,drives,gbps,busy_cores,gbps_per_core" > "$CSV"
sudo sysctl -q -w vm.nr_hugepages="$(( N*128 + 128 ))"

# --- stock io_uring_cmd, hugepage fixed buffers (one fio job per drive) ---
jobs=""; for ng in "${NGS[@]}"; do jobs="$jobs --name=$(basename $ng) --filename=$ng"; done
c0=$(busy)
sudo fio --ioengine=io_uring_cmd --cmd_type=nvme --rw=read --bs="$BS" --iodepth="$QD" \
  --fixedbufs --iomem=mmaphuge --runtime="$T" --time_based --group_reporting \
  --output-format=json $jobs > /tmp/sg_fio.json 2>/dev/null
c1=$(busy)
python3 -c "import json;d=json.load(open('/tmp/sg_fio.json'));bw=sum(j['read']['bw'] for j in d['jobs'])/1024/1024;bc=($c1-$c0)/100/$T;print(f'stock_iouring_cmd,$N,{bw:.2f},{bc:.3f},{bw/bc:.0f}')" | tee -a "$CSV"

# --- premap (map-once), one smoke instance per drive ---
sleep 2; c0=$(busy); t0=$(date +%s.%N)
for ng in "${NGS[@]}"; do
  sudo "$SMOKE" --dev "$ng" --count 60000 --qd "$QD" --len 2097152 --lba-size "$LBA" \
    --cmds-per-obj 8 --premap >/dev/null 2>&1 &
done; wait
t1=$(date +%s.%N); c1=$(busy)
python3 -c "wall=$t1-$t0;gib=$N*60000*2097152/1073741824;gbs=gib/wall;bc=($c1-$c0)/100/wall;print(f'premap_map_once,$N,{gbs:.2f},{bc:.3f},{gbs/bc:.0f}')" | tee -a "$CSV"

# --- SPDK spdk_nvme_perf (VFIO): bind ONLY these BDFs, run, reset ---
SPDK_DIR=$(dirname "$(dirname "$(dirname "$SPDK_PERF")")")
ALLOW=$(IFS=" "; echo "${BDFS[*]}")
sudo PCI_ALLOWED="$ALLOW" HUGEMEM=$(( N*3072 + 2048 )) "$SPDK_DIR/scripts/setup.sh" >/tmp/sg_setup.log 2>&1
# refuse to proceed if any requested BDF did NOT bind to vfio (e.g. it had a holder)
for b in "${BDFS[@]}"; do
  drv=$(basename "$(readlink -f /sys/bus/pci/devices/$b/driver 2>/dev/null)" 2>/dev/null)
  [ "$drv" = vfio-pci ] || { echo "SPDK: $b not bound to vfio ($drv) -- skipping SPDK arm" | tee -a "$CSV"; drv=BAD; break; }
done
if [ "${drv:-}" = vfio-pci ]; then
  c0=$(busy)
  sudo "$SPDK_PERF" -q "$QD" -o 2097152 -w read -t "$T" -c "$(printf '0x%x' $(( (1<<N)-1 )) )" > /tmp/sg_spdk.log 2>&1
  c1=$(busy)
  bw=$(awk '/^Total/{print $3}' /tmp/sg_spdk.log)   # MiB/s
  python3 -c "bw=$bw/1024;bc=($c1-$c0)/100/$T;print(f'spdk_nvme_perf,$N,{bw:.2f},{bc:.3f},{bw/bc:.0f}')" | tee -a "$CSV"
fi
sudo PCI_ALLOWED="$ALLOW" "$SPDK_DIR/scripts/setup.sh" reset >/dev/null 2>&1
echo "wrote $CSV"

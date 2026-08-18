#!/bin/bash
# scale_sweep.sh -- storage GB/s PER CPU CORE vs NVMe drive count, three paths:
#   stock io_uring_cmd (hugepage fixed bufs), premap (blk_iobuf_pool map-once),
#   SPDK spdk_nvme_perf (VFIO poller). Sweeps drive count 1,2,4 to show whether
#   the kernel's interrupt-driven efficiency edge over SPDK's dedicated poller
#   holds as you add drives. Emits CSV: arm,drives,rep,gbps,busy_cores,gbps_per_core.
#
# Must run ON the custom premap kernel (nvme.lift_dma_opt_clamp=1) so 2 MiB
# io_uring_cmd passthrough is legal. Kernel arms use the nvme driver; the SPDK
# arm binds ONLY the passed BDFs to vfio-pci, runs, then rebinds to nvme.
set -u
SMOKE=${SMOKE:-/tmp/smoke}
SPDK_PERF=${SPDK_PERF:-$HOME/spdk/build/bin/spdk_nvme_perf}
SPDK_DIR=$(dirname "$(dirname "$(dirname "$SPDK_PERF")")")
CSV=${CSV:-/tmp/scale.csv}
BS=2M; QD=${QD:-64}; T=${T:-12}; LBA=512; OBJ=2097152; REPS=${REPS:-3}
# Discover the free drives at runtime: Samsung 7TB namespaces with NO holder
# (root lives on the Micron md0 mirror). Build matched ng + BDF arrays, BDF-sorted.
ALL_NG=(); ALL_BDF=()
while read -r dev; do
  n=${dev%n1}                       # nvmeX
  [ -e "/dev/${dev}" ] || continue
  # skip anything with a partition / md holder
  holders=$(lsblk -no NAME "/dev/${dev}" | tail -n +2)
  [ -n "$holders" ] && continue
  model=$(cat /sys/class/nvme/${n}/model 2>/dev/null)
  echo "$model" | grep -qi samsung || continue
  bdf=$(basename "$(readlink -f /sys/class/nvme/${n}/device)")
  ng="/dev/ng${dev#nvme}"           # ngXn1
  [ -e "$ng" ] || continue
  ALL_BDF+=("$bdf"); ALL_NG+=("$ng")
done < <(ls /dev | grep -E '^nvme[0-9]+n1$')
# sort both arrays by BDF for stable order
paired=$(for i in "${!ALL_BDF[@]}"; do echo "${ALL_BDF[$i]} ${ALL_NG[$i]}"; done | sort)
ALL_BDF=($(echo "$paired" | awk '{print $1}'))
ALL_NG=($(echo "$paired" | awk '{print $2}'))
echo "free drives: ${#ALL_NG[@]} -> ${ALL_NG[*]} @ ${ALL_BDF[*]}"
COUNTS=(1 2 4)

busy(){ awk '/^cpu /{idle=$5+$6;t=0;for(k=2;k<=NF;k++)t+=$k;print t-idle}' /proc/stat; }
echo "arm,drives,rep,gbps,busy_cores,gbps_per_core" > "$CSV"
sudo sysctl -q -w vm.nr_hugepages=$(( 4*160 + 256 ))

run_stock(){ # $1=N
  local N=$1 jobs="" ng
  for ng in "${ALL_NG[@]:0:$N}"; do jobs="$jobs --name=$(basename $ng) --filename=$ng"; done
  for r in $(seq 1 $REPS); do
    local c0=$(busy)
    sudo fio --ioengine=io_uring_cmd --cmd_type=nvme --rw=read --bs=$BS --iodepth=$QD \
      --fixedbufs --iomem=mmaphuge --runtime=$T --time_based --group_reporting \
      --output-format=json $jobs >/tmp/ss_fio.json 2>/dev/null
    local c1=$(busy)
    python3 -c "import json;d=json.load(open('/tmp/ss_fio.json'));bw=sum(j['read']['bw'] for j in d['jobs'])/1024/1024;bc=($c1-$c0)/100/$T;print(f'stock_iouring_cmd,$N,$r,{bw:.2f},{bc:.3f},{bw/bc:.0f}')" | tee -a "$CSV"
    sleep 2
  done
}

run_premap(){ # $1=N
  local N=$1 ng
  for r in $(seq 1 $REPS); do
    local c0=$(busy); local t0=$(date +%s.%N)
    for ng in "${ALL_NG[@]:0:$N}"; do
      sudo "$SMOKE" --dev "$ng" --count 40000 --qd $QD --len $OBJ --lba-size $LBA \
        --cmds-per-obj 8 --premap >/dev/null 2>&1 &
    done; wait
    local t1=$(date +%s.%N); local c1=$(busy)
    python3 -c "wall=$t1-$t0;gib=$N*40000*$OBJ/1073741824;gbs=gib/wall;bc=($c1-$c0)/100/wall;print(f'premap_map_once,$N,$r,{gbs:.2f},{bc:.3f},{gbs/bc:.0f}')" | tee -a "$CSV"
    sleep 2
  done
}

run_spdk(){ # $1=N ; binds only these BDFs
  local N=$1; local allow=$(IFS=" "; echo "${ALL_BDF[*]:0:$N}")
  sudo PCI_ALLOWED="$allow" HUGEMEM=$(( N*4096 + 4096 )) "$SPDK_DIR/scripts/setup.sh" >/tmp/ss_setup.log 2>&1
  local b drv=missing
  for b in "${ALL_BDF[@]:0:$N}"; do
    drv=$(basename "$(readlink -f /sys/bus/pci/devices/$b/driver 2>/dev/null)" 2>/dev/null)
    [ "$drv" = vfio-pci ] || { echo "spdk,$N,-,BIND_FAIL_$b($drv),,"| tee -a "$CSV"; drv=BAD; break; }
  done
  if [ "$drv" = vfio-pci ]; then
    local coremask=$(printf '0x%x' $(( (1<<N)-1 )))   # N poller cores
    for r in $(seq 1 $REPS); do
      local c0=$(busy)
      sudo "$SPDK_PERF" -q $QD -o $OBJ -w read -t $T -c "$coremask" >/tmp/ss_spdk.log 2>&1
      local c1=$(busy)
      local mib=$(awk '/^Total/{print $4}' /tmp/ss_spdk.log)   # $1=Total $2=: $3=IOPS $4=MiB/s
      python3 -c "bw=${mib:-0}/1024;bc=($c1-$c0)/100/$T;print(f'spdk_nvme_perf,$N,$r,{bw:.2f},{bc:.3f},{(bw/bc) if bc>0 else 0:.0f}')" | tee -a "$CSV"
      sleep 2
    done
  fi
  sudo PCI_ALLOWED="$allow" "$SPDK_DIR/scripts/setup.sh" reset >/tmp/ss_reset.log 2>&1
  sleep 3  # let nvme re-enumerate
}

echo "### kernel arms (drives on nvme driver) ###"
for N in "${COUNTS[@]}"; do run_stock $N; run_premap $N; done
echo "### SPDK arm (VFIO, per drive count) ###"
for N in "${COUNTS[@]}"; do run_spdk $N; done
echo "SWEEP_DONE -> $CSV"
column -t -s, "$CSV"

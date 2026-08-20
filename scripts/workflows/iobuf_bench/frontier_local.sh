#!/bin/bash
# frontier_local.sh -- local storage frontier: SPDK vs the kernel's OWN polling
# path, across block sizes, to find the crossover. Gives the kernel its best
# foot forward (io_uring + IOPOLL/--hipri + registered files + fixed buffers +
# O_DIRECT + NVMe poll queues) -- the architectural analog of SPDK that stays in
# the kernel. Both arms poll, both pinned to N cores; we compare IOPS (small BS)
# and GB/s (large BS) per core at matched core count.
#   arm,bs,cores,iops,bw_mbps,p99_us,busy_cores
#
# Needs: SPDK built; booted with nvme.poll_queues>=cores (kernel arm). Drives on
# the kernel for the kernel arm; bound to VFIO for the SPDK arm.
set -u
SPDK=${SPDK:-$HOME/spdk}
SPDK_PERF=$SPDK/build/bin/spdk_nvme_perf
CSV=${CSV:-$HOME/frontier.csv}
BSES=(${BSES:-4k 16k 128k 2m})
CORES=(${CORES:-1 2 4})
QD=${QD:-128}; RUNT=${RUNT:-12}; RANGE=${RANGE:-128G}

# free drives (7TB, no holder) -> DEVS + BDFS
DEVS=(); BDFS=()
while read -r dev; do
  n=${dev%n1}; [ -e "/dev/$dev" ] || continue
  [ -n "$(lsblk -no NAME /dev/$dev | tail -n +2)" ] && continue
  sz=$(cat /sys/class/nvme/$n/${dev}/size 2>/dev/null); [ "${sz:-0}" -lt 1000000000 ] && continue
  DEVS+=("/dev/$dev"); BDFS+=("$(basename $(readlink -f /sys/class/nvme/$n/device))")
done < <(ls /dev | grep -E '^nvme[0-9]+n1$' | sort)
echo "free drives: ${DEVS[*]} @ ${BDFS[*]}"
NDRV=${#DEVS[@]}
busy(){ awk '/^cpu /{idle=$5+$6;t=0;for(k=2;k<=NF;k++)t+=$k;print t-idle}' /proc/stat; }
echo "arm,bs,cores,iops,bw_mbps,p99_us,busy_cores" > "$CSV"

# ---- kernel arm: io_uring block + IOPOLL(--hipri) + fixed bufs + regfiles ----
kernel_arm(){
  local bs c i files
  sudo sysctl -q -w vm.nr_hugepages=$(( NDRV*160 + 256 ))
  for bs in "${BSES[@]}"; do
    for c in "${CORES[@]}"; do
      # spread c jobs across the c*? ... one job per drive, capped by cores
      files=""; for d in "${DEVS[@]}"; do files="$files --name=$(basename $d) --filename=$d"; done
      local c0=$(busy)
      sudo taskset -c 0-$((c-1)) fio --ioengine=io_uring --direct=1 --rw=randread --bs=$bs \
        --iodepth=$QD --hipri --fixedbufs --registerfiles --iomem=mmaphuge \
        --cpus_allowed=0-$((c-1)) --cpus_allowed_policy=shared \
        --size=$RANGE --time_based --runtime=$RUNT --ramp_time=3 \
        --group_reporting --output-format=json $files >/tmp/fr_fio.json 2>/dev/null
      local c1=$(busy)
      python3 -c "
import json
d=json.load(open('/tmp/fr_fio.json'))
iops=sum(j['read']['iops'] for j in d['jobs'])
bw=sum(j['read']['bw'] for j in d['jobs'])/1024
p99=max(j['read']['clat_ns']['percentile']['99.000000'] for j in d['jobs'])/1000
bc=($c1-$c0)/100/$RUNT
print(f'kernel_iopoll,$bs,$c,{iops:.0f},{bw:.0f},{p99:.0f},{bc:.2f}')
" | tee -a "$CSV"
    done
  done
}

# ---- SPDK arm: spdk_nvme_perf (VFIO), c reactor cores ----
spdk_arm(){
  local allow=$(IFS=' '; echo "${BDFS[*]}")
  sudo PCI_ALLOWED="$allow" HUGEMEM=$(( NDRV*3072 + 4096 )) "$SPDK/scripts/setup.sh" >/tmp/fr_setup.log 2>&1
  local bs c b drv=ok
  for b in "${BDFS[@]}"; do drv=$(basename "$(readlink -f /sys/bus/pci/devices/$b/driver 2>/dev/null)"); [ "$drv" = vfio-pci ] || { echo "SPDK bind fail $b ($drv)"; return 1; }; done
  local bdfargs=""; for b in "${BDFS[@]}"; do bdfargs="$bdfargs -r 'trtype:PCIe traddr:$b'"; done
  for bs in "${BSES[@]}"; do
    local o=$(numfmt --from=iec ${bs^^} 2>/dev/null || echo $bs)
    for c in "${CORES[@]}"; do
      local mask=$(printf '0x%x' $(( (1<<c)-1 )))
      local c0=$(busy)
      eval sudo "$SPDK_PERF" -q $QD -o $o -w randread -t $RUNT -c "$mask" $bdfargs >/tmp/fr_spdk.log 2>&1
      local c1=$(busy)
      local mib=$(awk '/^Total/{print $4}' /tmp/fr_spdk.log)
      local iops=$(awk '/^Total/{print $3}' /tmp/fr_spdk.log)
      python3 -c "bc=($c1-$c0)/100/$RUNT;print(f'spdk_nvme_perf,$bs,$c,{${iops:-0}:.0f},{${mib:-0}:.0f},0,{bc:.2f}')" | tee -a "$CSV"
    done
  done
  sudo PCI_ALLOWED="$allow" "$SPDK/scripts/setup.sh" reset >/tmp/fr_reset.log 2>&1; sleep 3
}

echo "### kernel IOPOLL arm ###"; kernel_arm
echo "### SPDK arm ###"; spdk_arm
echo "FRONTIER_DONE -> $CSV"

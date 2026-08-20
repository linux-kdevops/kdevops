#!/bin/bash
# iops_core_bench.sh -- IOPS/core + cycles/IO for premap vs stock Linux vs SPDK
# on ONE NVMe namespace, ONE core, random reads. Primary metric is cycles/IO and
# IOPS/core, weighted toward low QD. All Linux arms polled (IOPOLL) to match
# SPDK; interrupt arms are secondary. Emits results.jsonl (one row/point) + env.
#
# Impls: stock (smoke --hugepage --fixed --poll), premap (smoke --premap --poll),
#        spdk (spdk_nvme_perf), fio_ref (fio io_uring_cmd --hipri, the stock tool).
set -u
NG=${NG:-/dev/ng0n1}; BLK=${BLK:-/dev/nvme0n1}; BDF=${BDF:-0000:c1:00.0}
CORE=${CORE:-10}                      # app core (NUMA0, avoid SMT sibling + core0)
SIZES=(${SIZES:-4096 8192 16384 32768 65536 131072})
QDS=(${QDS:-1 4 8 16 32 128})
REPS=${REPS:-3}; WINDOW=${WINDOW:-25}; RANGE_GIB=${RANGE_GIB:-32}
SMOKE=${SMOKE:-$HOME/smoke}; SPDK=${SPDK:-$HOME/spdk}
SPDK_PERF=$SPDK/build/bin/spdk_nvme_perf
PERF=${PERF:-/usr/lib/linux-tools/6.8.0-138-generic/perf}
OUT=${OUT:-$HOME/iops_core_out}; mkdir -p "$OUT"
JSONL="$OUT/results.jsonl"; : > "$JSONL"
PEV=cycles,instructions,task-clock,context-switches,cpu-migrations,cache-references,cache-misses
LBA=$(sudo nvme id-ns "$BLK" 2>/dev/null | awk '/in use/{for(i=1;i<=NF;i++)if($i ~ /lbads/){split($i,a,":");print 2^a[2]}}'); LBA=${LBA:-512}
COREMASK=$(printf '0x%x' $((1<<CORE)))

log(){ echo "[$(date -u +%T)] $*" >&2; }

# --- environment capture (spec: record everything) ---
env_capture(){
  local e="$OUT/env.txt"
  { echo "=== date/host ==="; date -u; uname -a; echo "core=$CORE lba=$LBA ng=$NG bdf=$BDF"
    echo "=== cmdline ==="; cat /proc/cmdline
    echo "=== governor ==="; cat /sys/devices/system/cpu/cpu$CORE/cpufreq/scaling_governor 2>/dev/null
    echo "=== numa ==="; numactl -H; echo "dev numa: $(cat /sys/bus/pci/devices/$BDF/numa_node)"
    echo "=== lscpu -e ==="; lscpu -e
    echo "=== queue ==="; for f in /sys/block/$(basename $BLK)/queue/*; do echo "$f = $(cat $f 2>/dev/null)"; done
    echo "=== io_poll ==="; cat /sys/block/$(basename $BLK)/queue/io_poll
    echo "=== poll_queues ==="; cat /sys/module/nvme/parameters/poll_queues 2>/dev/null
    echo "=== nvme id-ctrl (mdts,vid) ==="; sudo nvme id-ctrl $BLK 2>/dev/null | grep -iE "^mdts|^vid|^mn|^fr"
    echo "=== nvme id-ns ==="; sudo nvme id-ns $BLK 2>/dev/null | grep -iE "lbaf|in use|nsze"
    echo "=== premap params ==="; for p in lift_dma_opt_clamp; do echo "nvme.$p=$(cat /sys/module/nvme/parameters/$p)"; done
    for p in iobuf_pool_folios iobuf_pool_order multipath; do echo "nvme_core.$p=$(cat /sys/module/nvme_core/parameters/$p)"; done
  } > "$e"
  log "env -> $e"
}

# --- controls: perf governor, pin NVMe IRQs of the device to CORE ---
setup_controls(){
  sudo cpupower frequency-set -g performance >/dev/null 2>&1 || \
    echo performance | sudo tee /sys/devices/system/cpu/cpu$CORE/cpufreq/scaling_governor >/dev/null 2>&1
  # move this device's NVMe IRQs onto CORE so interrupt-mode completion CPU is counted there
  for irq in $(grep -iE "nvme.*$(echo $BDF|sed 's/0000://')" /proc/interrupts 2>/dev/null | awk -F: '{print $1}'); do
    echo $CORE | sudo tee /proc/irq/$irq/smp_affinity_list >/dev/null 2>&1
  done
  sudo sysctl -q -w vm.nr_hugepages=1024
}

# parse perf -x, output; echo "cycles instructions taskclock_ms ctxsw migr cref cmiss"
parse_perf(){
  awk -F, '
    /cycles/{c=$1} /instructions/{i=$1} /task-clock/{t=$1}
    /context-switches/{x=$1} /cpu-migrations/{m=$1}
    /cache-references/{cr=$1} /cache-misses/{cm=$1}
    END{gsub(/[^0-9.]/,"",c);gsub(/[^0-9.]/,"",i);gsub(/[^0-9.]/,"",t);
        print c+0, i+0, t+0, x+0, m+0, cr+0, cm+0}' "$1"
}

emit(){ echo "$1" >> "$JSONL"; }

# --- smoke-based arm (stock or premap), polled, pinned to CORE ---
run_smoke(){ # $1=impl-label  $2="extra flags"  $3=size  $4=qd  $5=rep
  local impl=$1 flags=$2 size=$3 qd=$4 rep=$5
  local slots=$qd; [ $slots -gt 80 ] && slots=80    # pool has 80 folios
  local effqd=$qd; [ $effqd -gt 80 ] && effqd=80
  # calibrate count for ~WINDOW s: probe scales with qd
  local probe=$(( effqd*20000 )); [ $probe -lt 50000 ] && probe=50000; [ $probe -gt 3000000 ] && probe=3000000
  local pj=$(sudo taskset -c $CORE $SMOKE --dev $NG --count $probe --qd $effqd --slots $slots \
      --len $size --lba-size $LBA --cmds-per-obj 1 --random --range-gib $RANGE_GIB $flags 2>&1 | grep '^{')
  local piops=$(echo "$pj" | python3 -c "import json,sys;print(int(json.load(sys.stdin).get('iops',0)))" 2>/dev/null || echo 0)
  [ "${piops:-0}" -lt 1 ] && { emit "{\"impl\":\"$impl\",\"size\":$size,\"qd\":$qd,\"rep\":$rep,\"error\":\"probe_zero\"}"; return; }
  local cnt=$(( piops*WINDOW )); local cap=$((1<<27)); [ $cnt -gt $cap ] && cnt=$cap; [ $cnt -lt 50000 ] && cnt=50000
  # measured run under perf
  local pf="$OUT/perf_${impl}_${size}_${qd}_${rep}.txt"
  local js=$(sudo $PERF stat -C $CORE -e $PEV -x, -o "$pf" -- \
      taskset -c $CORE $SMOKE --dev $NG --count $cnt --qd $effqd --slots $slots \
      --len $size --lba-size $LBA --cmds-per-obj 1 --random --range-gib $RANGE_GIB $flags 2>&1 | grep '^{')
  [ -z "$js" ] && { emit "{\"impl\":\"$impl\",\"size\":$size,\"qd\":$qd,\"rep\":$rep,\"error\":\"run_nojson\"}"; return; }
  read cyc ins tclk ctx migr cref cmiss < <(parse_perf "$pf")
  python3 -c "
import json
d=json.loads('''$js''')
ios=d.get('successful_commands',0); el=d.get('elapsed_ns',1)/1e9
lat=d.get('latency_ns',{})
cyc,ins,tclk=$cyc,$ins,$tclk
iops=ios/el if el>0 else 0
core_util=(tclk/1000.0)/el if el>0 else 0            # fraction of the 1 core used
r={'impl':'$impl','size':$size,'qd':$qd,'rep':$rep,'ios':ios,'elapsed_s':round(el,3),
   'iops':round(iops),'cycles_per_io':round(cyc/ios,1) if ios else 0,
   'instr_per_io':round(ins/ios,1) if ios else 0,'core_util':round(core_util,3),
   'iops_per_core':round(iops/core_util) if core_util>0 else 0,
   'cpu_s_per_Mio':round((tclk/1000.0)/(ios/1e6),3) if ios else 0,
   'p50_us':round(lat.get('p50',0)/1000,1),'p95_us':round(lat.get('p95',0)/1000,1),
   'p99_us':round(lat.get('p99',0)/1000,1),'max_us':round(lat.get('max',0)/1000,1),
   'ctxsw':$ctx,'cache_miss':$cmiss}
print(json.dumps(r))
" | tee -a "$JSONL" >/dev/null
}

# --- SPDK arm (bind to VFIO, run nvme_perf on CORE) ---
run_spdk(){ # $1=size $2=qd $3=rep
  local size=$1 qd=$2 rep=$3
  local pf="$OUT/perf_spdk_${size}_${qd}_${rep}.txt"
  sudo $PERF stat -C $CORE -e $PEV -x, -o "$pf" -- \
    taskset -c $CORE $SPDK_PERF -q $qd -o $size -w randread -t $WINDOW -c $COREMASK \
      -r "trtype:PCIe traddr:$BDF" >"$OUT/spdk_${size}_${qd}_${rep}.log" 2>&1
  local mib=$(awk '/^Total/{print $4}' "$OUT/spdk_${size}_${qd}_${rep}.log")
  local iops=$(awk '/^Total/{print $3}' "$OUT/spdk_${size}_${qd}_${rep}.log")
  local p99=$(awk '/^Total/{print $7}' "$OUT/spdk_${size}_${qd}_${rep}.log")  # us
  read cyc ins tclk ctx migr cref cmiss < <(parse_perf "$pf")
  python3 -c "
iops=${iops:-0}; cyc,ins,tclk=$cyc,$ins,$tclk
el=$WINDOW; ios=iops*el
core_util=(tclk/1000.0)/el if el>0 else 0
import json
r={'impl':'spdk','size':$size,'qd':$qd,'rep':$rep,'ios':int(ios),'elapsed_s':el,
   'iops':round(iops),'cycles_per_io':round(cyc/ios,1) if ios else 0,
   'instr_per_io':round(ins/ios,1) if ios else 0,'core_util':round(core_util,3),
   'iops_per_core':round(iops/core_util) if core_util>0 else 0,
   'cpu_s_per_Mio':round((tclk/1000.0)/(ios/1e6),3) if ios else 0,
   'p99_us':${p99:-0},'ctxsw':$ctx,'cache_miss':$cmiss}
print(json.dumps(r))
" | tee -a "$JSONL" >/dev/null
}

spdk_bind(){ sudo PCI_ALLOWED="$BDF" HUGEMEM=4096 "$SPDK/scripts/setup.sh" >/tmp/spdk_setup.log 2>&1; }
spdk_reset(){ sudo PCI_ALLOWED="$BDF" "$SPDK/scripts/setup.sh" reset >/tmp/spdk_reset.log 2>&1; sleep 3; }

# --- premap validation: IOMMU maps per IO must be ~0 for premap, ~1 for stock ---
dma_validate(){
  local v="$OUT/dma_validation.txt"; : > "$v"
  for size in 4096 131072; do
    for a in "--fixed:stock" "--premap:premap"; do
      local flags=${a%:*} name=${a#*:}
      sudo $PERF stat -a -e iommu:map,iommu:unmap -o /tmp/dv.txt -- \
        taskset -c $CORE $SMOKE --dev $NG --count 800000 --qd 32 --len $size --lba-size $LBA \
          --cmds-per-obj 1 --random --range-gib $RANGE_GIB $flags >/dev/null 2>/tmp/dv.json
      local ios=$(grep '^{' /tmp/dv.json | python3 -c "import json,sys;print(json.load(sys.stdin).get('successful_commands',0))" 2>/dev/null)
      local maps=$(grep 'iommu:map' /tmp/dv.txt | awk '{gsub(/,/,"",$1);print $1}')
      echo "$name size=$size ios=$ios iommu_maps=$maps maps_per_io=$(python3 -c "print(round(${maps:-0}/${ios:-1},6))" 2>/dev/null)" | tee -a "$v"
    done
  done
  log "premap validation -> $v"
}

# ================= main =================
env_capture; setup_controls; dma_validate
log "LBA=$LBA sizes=${SIZES[*]} qds=${QDS[*]} reps=$REPS window=${WINDOW}s core=$CORE"

# Linux arms first (drive on kernel)
for rep in $(seq 1 $REPS); do
  for size in "${SIZES[@]}"; do
    [ $((size % LBA)) -ne 0 ] && continue
    for qd in "${QDS[@]}"; do
      # polled arms: the IOPS/core-vs-SPDK comparison (matches SPDK's model)
      log "stock  s=$size qd=$qd r=$rep"; run_smoke stock  "--fixed --poll"   $size $qd $rep
      log "premap s=$size qd=$qd r=$rep"; run_smoke premap "--premap --poll"  $size $qd $rep
      # interrupt arms: the true cycles/IO (per-IO work) -- no polling spin to
      # mask premap's map-once saving. IRQ is pinned to CORE so it is counted.
      log "stock_irq  s=$size qd=$qd r=$rep"; run_smoke stock_irq  "--fixed"   $size $qd $rep
      log "premap_irq s=$size qd=$qd r=$rep"; run_smoke premap_irq "--premap"  $size $qd $rep
    done
  done
done

# SPDK arm (VFIO)
spdk_bind
if [ "$(basename $(readlink -f /sys/bus/pci/devices/$BDF/driver 2>/dev/null))" = vfio-pci ]; then
  for rep in $(seq 1 $REPS); do
    for size in "${SIZES[@]}"; do
      [ $((size % LBA)) -ne 0 ] && continue
      for qd in "${QDS[@]}"; do log "spdk   s=$size qd=$qd r=$rep"; run_spdk $size $qd $rep; done
    done
  done
else
  log "SPDK bind FAILED — skipping spdk arm"
fi
spdk_reset
log "IOPS_CORE_DONE -> $JSONL ($(wc -l < $JSONL) rows)"

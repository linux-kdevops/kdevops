#!/bin/bash
# cpu_sweep.sh -- host CPU cycles per GiB vs NVMe command size (reads, O_DIRECT).
#
# Drives a drive at a FIXED data rate so every command size moves the same data,
# and measures host CPU with perf hardware cycle counters (immune to the
# /proc/stat idle-jiffies noise a % measure suffers on a many-core idle box).
# Median of REP runs per size. Sizes above 1 MiB use a huge-page buffer because
# a page-granular buffer is capped at ~1 MiB by the 256-segment limit.
#
# Emits CSV the plot script consumes: drive,size_kb,cmds_per_gib,mcyc_per_gib,buffer
#
# Requires: fio, perf (linux-tools), python3, and (for >1 MiB) reserved huge
# pages: echo 6144 | sudo tee /proc/sys/vm/nr_hugepages
# The kernel must be built with CONFIG_NVME_LIFT_DMA_OPT_CLAMP=y (the
# iobuf-clamp-lift-* defconfig) or max_sectors_kb cannot exceed 128.
#
# Usage: cpu_sweep.sh <blockdev> [drive-label] [out.csv]
set -u
DEV=$1; LABEL=${2:-$(basename "$1")}; CSV=${3:-sweep.csv}
BN=$(basename "$DEV"); Q=/sys/block/$BN/queue
MAXHW=$(cat "$Q/max_hw_sectors_kb")
PERF=$(ls /usr/lib/linux-tools/*/perf 2>/dev/null | head -1); [ -z "$PERF" ] && PERF=$(command -v perf)
RATE=${RATE:-4000m}; T=${T:-15}; QD=${QD:-32}; REP=${REP:-3}
getcyc(){ awk '/cycles/{gsub(/,/,"",$1);print $1;exit}' "$1"; }

[ -f "$CSV" ] || echo "drive,size_kb,cmds_per_gib,mcyc_per_gib,buffer" > "$CSV"
sudo "$PERF" stat -a -e cycles -o /tmp/cs_base -- sleep "$T" 2>/dev/null
BASE=$(getcyc /tmp/cs_base)
echo "device=$DEV label=$LABEL max_hw_sectors_kb=$MAXHW rate=$RATE t=${T}s rep=$REP"

for kb in 128 256 512 1024 2048 4096 8192; do
  [ "$kb" -gt "$MAXHW" ] && continue
  echo "$kb" | sudo tee "$Q/max_sectors_kb" >/dev/null
  mem=""; buf=pages; [ "$kb" -gt 1024 ] && { mem="--iomem=mmaphuge"; buf=huge; }
  vals=""
  for r in $(seq 1 "$REP"); do
    sync; sleep 1
    sudo "$PERF" stat -a -e cycles -o /tmp/cs_pf -- \
      fio --name=s --filename="$DEV" --rw=read --bs=${kb}k --iodepth="$QD" \
          --ioengine=io_uring --direct=1 --runtime="$T" --time_based --rate="$RATE" \
          $mem --group_reporting --output-format=json > /tmp/cs_fio.json 2>/dev/null
    cyc=$(getcyc /tmp/cs_pf)
    gib=$(python3 -c "import json;print(json.load(open('/tmp/cs_fio.json'))['jobs'][0]['read']['io_bytes']/1073741824)")
    vals="$vals $(python3 -c "print(($cyc-$BASE)/1e6/$gib)")"
  done
  med=$(python3 -c "v=sorted([${vals// /,}]); print(f'{v[len(v)//2]:.1f}')")
  cmds=$(python3 -c "print(int(1073741824/($kb*1024)))")
  echo "$LABEL,$kb,$cmds,$med,$buf" | tee -a "$CSV"
done
echo "wrote $CSV"

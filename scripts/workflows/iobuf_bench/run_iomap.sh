#!/bin/bash
# iomap DIO-bounce A/B: aligned O_DIRECT writes to XFS on a 16K-LBS NVMe.
# With the pool, iomap_dio_write_iobuf() bounces each aligned 16K write through a
# single pool folio (1 memcpy, single-segment bio) instead of the user pages.
# Run once per boot state (pool on/off). Captures fio iops/bw/cpu + pool-counter
# deltas (engagement). 64K control should NOT bounce (allocs delta ~0).
set -u
DEV=${1:-/dev/nvme1n1}
LABEL=${2:-poolon}
OUT=${3:-/tmp/iomap_${LABEL}.jsonl}
MNT=/mnt/iobuf_xfs
SIZE=${SIZE:-4G}; SECS=${SECS:-15}; QD=${QD:-32}; ITERS=${ITERS:-3}
dn=$(basename "$DEV")
: > "$OUT"
command -v fio >/dev/null || { echo "fio missing"; exit 5; }

sudo umount "$MNT" 2>/dev/null
sudo mkfs.xfs -f -b size=16384 "$DEV" >/dev/null 2>&1 || { echo "mkfs failed"; exit 6; }
sudo mkdir -p "$MNT"; sudo mount "$DEV" "$MNT" || { echo "mount failed"; exit 7; }
sudo chmod 777 "$MNT"
# pre-fill the target file with real extents so allocation isn't measured
sudo dd if=/dev/zero of=$MNT/tf bs=16M count=$(( ${SIZE%G}*1024/16 )) oflag=direct status=none
pool_en=$(cat /sys/block/$dn/queue/iobuf_pool_enabled 2>/dev/null)

run() {  # $1=rw $2=bs
  local rw=$1 bs=$2 it a0 a1 fb0 fb1 j
  for it in $(seq 1 $ITERS); do
    a0=$(cat /sys/block/$dn/queue/iobuf_pool_allocs 2>/dev/null || echo 0)
    fb0=$(cat /sys/block/$dn/queue/iobuf_pool_fallbacks 2>/dev/null || echo 0)
    j=$(sudo fio --name=io --filename=$MNT/tf --ioengine=io_uring --direct=1 \
        --rw=$rw --bs=$bs --io_size=$SIZE --runtime=$SECS --time_based \
        --iodepth=$QD --numjobs=1 --group_reporting --output-format=json 2>/dev/null)
    a1=$(cat /sys/block/$dn/queue/iobuf_pool_allocs 2>/dev/null || echo 0)
    fb1=$(cat /sys/block/$dn/queue/iobuf_pool_fallbacks 2>/dev/null || echo 0)
    echo "$j" > /tmp/fio_out.json
    python3 - "$LABEL" "$pool_en" "$rw" "$bs" "$it" \
        "$((a1-a0))" "$((fb1-fb0))" /tmp/fio_out.json >> "$OUT" <<'PY'
import json,sys
lbl,en,rw,bs,it,da,dfb,fpath=sys.argv[1:9]
try: d=json.load(open(fpath))
except Exception: print('{"error":"no fio json","rw":"%s","bs":"%s"}'%(rw,bs)); sys.exit()
j=d["jobs"][0]; side=j["write"] if "write" in rw else j["read"]
print(json.dumps({"label":lbl,"pool_enabled":int(en),"rw":rw,"bs":bs,"iter":int(it),
  "iops":round(side["iops"],1),"bw_mb_s":round(side["bw"]/1024,1),
  "clat_p50_us":round(side["clat_ns"]["percentile"].get("50.000000",0)/1000,1),
  "clat_p99_us":round(side["clat_ns"]["percentile"].get("99.000000",0)/1000,1),
  "usr_cpu":j.get("usr_cpu",0),"sys_cpu":j.get("sys_cpu",0),
  "pool_allocs_delta":int(da),"pool_fallbacks_delta":int(dfb)}))
PY
  done
}

run randwrite 16k
run randwrite 64k
run randwrite 256k
run randwrite 1024k
sudo umount "$MNT"
echo "DONE label=$LABEL pool_enabled=$pool_en -> $OUT"

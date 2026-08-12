#!/bin/bash
# Premap large-command proof + geometry on a large-MDTS NVMe (real OR QEMU-emulated).
#
# Run this ON the target after booting the blk-iobuf-pool-v5-premap-iova kernel
# (see PREMAP-README.md). It drives the kernel's own premap selftest
# (tools/testing/selftests/blk-iobuf/iobuf-fixed-test.c) across a command-size
# sweep on the /dev/ng passthrough path, records the LARGEST single premapped
# command the drive accepts (the headline a large-MDTS drive uniquely proves --
# a 128 KiB-clamped host cannot), captures all geometry, and tars the results.
#
#   sudo ./run_premap.sh /dev/ng0n1 /dev/nvme0n1 [kernel_source_dir]
#
# Sends back one file: premap-results-<host>-<ts>.tar.gz
set -u
NG=${1:?usage: run_premap.sh /dev/ngXnY /dev/nvmeXnY [kernel_src_dir]}
BLK=${2:?need the matching /dev/nvmeXnY block device}
SRC=${3:-}
[ "$(id -u)" = 0 ] || { echo "run as root (sudo)"; exit 1; }
dn=$(basename "$BLK")
ts=$(date -u +%Y%m%dT%H%M%SZ)
OUT="premap-results-$(hostname -s)-$ts"
mkdir -p "$OUT"

# ---- locate the kernel selftest source (from `make linux`, or pass arg3) ------
if [ -z "$SRC" ]; then
  for c in "$HOME/linux" /lib/modules/"$(uname -r)"/build /usr/src/linux* "$PWD/linux" ../linux; do
    [ -f "$c/tools/testing/selftests/blk-iobuf/iobuf-fixed-test.c" ] && SRC="$c" && break
  done
fi
[ -n "$SRC" ] && [ -f "$SRC/tools/testing/selftests/blk-iobuf/iobuf-fixed-test.c" ] || {
  echo "ERROR: kernel source with tools/testing/selftests/blk-iobuf not found; pass it as arg3"; exit 2; }

# ---- geometry + prereqs -------------------------------------------------------
{
  echo "host=$(hostname)  date_utc=$ts  kernel=$(uname -r)"
  echo "block_dev=$BLK  ng_dev=$NG"
  echo "--- clamp / geometry (block queue sysfs) ---"
  for f in max_hw_sectors_kb max_sectors_kb logical_block_size max_hw_premapped_sectors; do
    printf '%s=%s\n' "$f" "$(cat /sys/block/$dn/queue/$f 2>/dev/null || echo '(n/a)')"
  done
  echo "--- pool (this branch: nvme module params + dmesg, NOT per-queue sysfs) ---"
  printf 'iobuf_pool_order=%s  iobuf_pool_folios=%s\n' \
    "$(cat /sys/module/nvme_core/parameters/iobuf_pool_order 2>/dev/null || echo '(n/a)')" \
    "$(cat /sys/module/nvme_core/parameters/iobuf_pool_folios 2>/dev/null || echo '(n/a)')"
  echo "pool_dmesg: $(dmesg 2>/dev/null | grep 'iobuf_pool:' | tail -1 || echo '(no iobuf_pool line)')"
  echo "--- device MDTS (nvme id-ctrl) ---"
  nvme id-ctrl "$BLK" 2>/dev/null | grep -iE '^mdts' || echo "mdts: (nvme-cli missing?)"
  echo "--- IOMMU ---"
  echo "iommu_groups=$(ls /sys/kernel/iommu_groups 2>/dev/null | wc -l)"
  echo "cmdline=$(cat /proc/cmdline)"
} | tee "$OUT/env.txt"

# ---- prereq gate --------------------------------------------------------------
# This branch has NO per-queue iobuf_pool sysfs; the pool is provisioned via nvme
# module params + a dmesg line ("iobuf_pool: N folios of order M ... on <dn>").
pord=$(cat /sys/module/nvme_core/parameters/iobuf_pool_order 2>/dev/null || echo 0)
pfol=$(cat /sys/module/nvme_core/parameters/iobuf_pool_folios 2>/dev/null || echo 0)
pmsg=$(dmesg 2>/dev/null | grep "iobuf_pool:.*folios of order.* $dn$" | tail -1)
grp=$(ls /sys/kernel/iommu_groups 2>/dev/null | wc -l)
fail=0
if [ -z "$pmsg" ] && { [ "$pord" = 0 ] || [ "$pfol" = 0 ]; }; then
  echo "PREREQ FAIL: iobuf pool not provisioned for $dn"
  echo "  module params: order=$pord folios=$pfol ; no 'iobuf_pool: ... on $dn' in dmesg"
  fail=1
elif [ -z "$pmsg" ]; then
  echo "NOTE: params set (order=$pord folios=$pfol) but no dmesg pool line names $dn — is the pool on a different namespace? check: dmesg | grep iobuf_pool:"
fi
[ "$grp" -gt 0 ] || { echo "PREREQ FAIL: no IOMMU groups — need a translating IOMMU"; fail=1; }
[ -e "$NG" ] || { echo "PREREQ FAIL: $NG missing"; fail=1; }
if [ "$fail" = 1 ]; then
  echo "Fix by booting with: iommu.passthrough=0 nvme_core.iobuf_pool=1 nvme_core.iobuf_pool_order=10 nvme_core.iobuf_pool_folios=32"
  echo "(add intel_iommu=on or amd_iommu=on if the IOMMU is not already up translating). See PREMAP-README.md."
  exit 3
fi

# ---- build the selftest (needs the branch's uapi headers) ---------------------
( cd "$SRC" && make headers_install >/dev/null 2>&1 )
make -C "$SRC/tools/testing/selftests/blk-iobuf" >/dev/null 2>"$OUT/build.err" && \
  TEST="$SRC/tools/testing/selftests/blk-iobuf/iobuf-fixed-test"
if [ ! -x "${TEST:-}" ]; then
  cc -O2 -I"$SRC/usr/include" -o "$OUT/iobuf-fixed-test" \
     "$SRC/tools/testing/selftests/blk-iobuf/iobuf-fixed-test.c" -luring 2>>"$OUT/build.err" \
     && TEST="$OUT/iobuf-fixed-test"
fi
[ -x "${TEST:-}" ] || { echo "ERROR: could not build iobuf-fixed-test (see $OUT/build.err)"; exit 4; }

# ---- command-size sweep: the headline result ---------------------------------
# Each PASS means the premap path issued a single command of that size on the
# /dev/ng passthrough leg. The largest PASS = the drive's real premapped ceiling.
lba=$(cat /sys/block/$dn/queue/logical_block_size)
clamp=$(cat /sys/block/$dn/queue/max_hw_sectors_kb)
echo "size_kib,size_bytes,result" > "$OUT/premap_sizes.csv"
maxok=0
for kb in 128 256 512 1024 2048 4096 8192; do
  len=$((kb * 1024))
  if timeout 60 "$TEST" -b "$BLK" -n "$NG" -l "$len" -L "$lba" >"$OUT/size_${kb}k.log" 2>&1; then
    echo "$kb,$len,PASS" | tee -a "$OUT/premap_sizes.csv"; maxok=$kb
  else
    echo "$kb,$len,FAIL" | tee -a "$OUT/premap_sizes.csv"; break
  fi
done

# decode the real MDTS (2^mdts * min-page; assume 4 KiB MPSMIN) and detect a
# multipath head, which is the usual reason premap silently caps at the clamp.
mdts=$(nvme id-ctrl "$BLK" 2>/dev/null | awk '/^mdts/{print $3}')
mdts_kib=""; [ -n "$mdts" ] && mdts_kib=$(( (1 << mdts) * 4 ))
pooldev=$(dmesg 2>/dev/null | sed -n 's/.*iobuf_pool:.* on \([a-z0-9]*\).*/\1/p' | tail -1)
mp_note=""
case "$pooldev" in *c[0-9]*n[0-9]*)
  mp_note="  <-- pool is on multipath PATH device '$pooldev'; you passed the HEAD ($NG). Premap is REFUSED on the head (commit 912328a). Re-run against the fixed path char (e.g. /dev/ng${pooldev#nvme}) or boot nvme_core.multipath=N." ;;
esac

{
  echo "=== premap large-command proof ==="
  echo "ordinary path clamp (max_hw_sectors_kb) : ${clamp} KiB"
  echo "device MDTS (decoded)                   : ${mdts_kib:-?} KiB  (mdts=${mdts:-?})"
  echo "pool provisioned on                     : ${pooldev:-?}"
  echo "largest premapped single command        : ${maxok} KiB"
  echo "premap beats the clamp by               : $(( maxok / (clamp==0?1:clamp) ))x"
  echo
  if [ -n "$mdts_kib" ] && [ "$maxok" -le "$clamp" ] && [ "$mdts_kib" -gt "$clamp" ]; then
    echo "VERDICT: PREMAP DID NOT ENGAGE. The drive MDTS is ${mdts_kib} KiB but premap"
    echo "only reached the ${clamp} KiB clamp -- so the premapped ceiling was not applied.${mp_note}"
  elif [ -n "$mdts_kib" ] && [ "$maxok" -ge "$mdts_kib" ]; then
    echo "VERDICT: PREMAP ENGAGED and reached the device MDTS (${maxok} KiB), while the"
    echo "ordinary path is pinned at ${clamp} KiB -- a ${maxok}/${clamp} = $((maxok/clamp))x lift by allocating"
    echo "zero per-I/O IOVA."
  else
    echo "Interpretation: ordinary NVMe commands cap at ${clamp} KiB (the dma_opt clamp);"
    echo "the premapped pool buffer reached ${maxok} KiB with zero per-I/O IOVA."
  fi
} | tee "$OUT/summary.txt"

tar czf "$OUT.tar.gz" "$OUT"
echo
echo "DONE -> $OUT.tar.gz   (send this file back)"

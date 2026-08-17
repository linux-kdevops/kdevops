#!/bin/bash
# premap_tlb_smoke.sh -- tightened per-command CPU: huge page vs premap vs strict
# premap, at one command size, on the NVMe passthrough path (/dev/ngXnY).
#
# This is the reconciling workload for "how much less host CPU does premap use
# than huge pages": perf -r REPS (default 10) with a discarded warmup pass. It
# reproduces the huge-page/premap/strict arms Codex used, on our clamp-lift
# (module param) kernel. Reads only, so a read-only drive is fine.
#
# Emits CSV: boot,arm,cyc_per_cmd,reps
#   boot = huge-on | huge-off   (auto-detected from amd_iommu=...nohugepages)
#   arm  = hugepage | premap | strict-premap
# In the huge-off boot the strict-premap arm is EXPECTED to fail (no 2 MiB
# IOMMU leaves), and is recorded as such.
#
# Requires: the nvme_uring_cmd_smoke tool built with --hugepage/--premap/
# --strict-premap (ebpf-syscall), perf (linux-tools), reserved huge pages, and
# a pool-provisioned, multipath=N, lift-enabled boot:
#   nvme_core.multipath=N nvme_core.iobuf_pool_order=9 \
#   nvme_core.iobuf_pool_folios=256 nvme.lift_dma_opt_clamp=1
#   (huge-off arm additionally: amd_iommu=pgtbl_v1,nohugepages)
#
# Usage: premap_tlb_smoke.sh <ngdev> <smoke-tool> [out.csv]
set -u
NG=$1; SM=$2; CSV=${3:-premap_tlb_smoke.csv}
LEN=${LEN:-2097152}; QD=${QD:-32}; COUNT=${COUNT:-30000}; LBA=${LBA:-512}; REPS=${REPS:-10}
PERF=$(ls /usr/lib/linux-tools/*/perf 2>/dev/null | head -1); [ -z "$PERF" ] && PERF=$(command -v perf)
getcyc(){ awk -F, '/cycles/{print $1}' "$1"; }
BOOT=huge-on; grep -q nohugepages /proc/cmdline && BOOT=huge-off
echo "boot=$BOOT ng=$NG len=$LEN qd=$QD count=$COUNT reps=$REPS"
[ -f "$CSV" ] || echo "boot,arm,cyc_per_cmd,reps" > "$CSV"
sudo sysctl -q -w vm.nr_hugepages="$(( QD > 300 ? QD : 300 ))"

run(){
  local arm=$1 flag=$2
  # discard a warmup pass, then perf -r REPS.
  sudo "$SM" --dev "$NG" --count "$COUNT" --qd "$QD" --len "$LEN" --lba-size "$LBA" \
    --cmds-per-obj 8 $flag >/dev/null 2>/tmp/pt_w_$arm || {
      echo "$BOOT,$arm,,${REPS}  # FAILED: $(tail -1 /tmp/pt_w_$arm)" | tee -a "$CSV"; return; }
  sudo "$PERF" stat -x, -r "$REPS" -o /tmp/pt_c_$arm.csv -e cycles -- \
    "$SM" --dev "$NG" --count "$COUNT" --qd "$QD" --len "$LEN" --lba-size "$LBA" \
    --cmds-per-obj 8 $flag >/dev/null 2>/tmp/pt_e_$arm
  local c; c=$(getcyc /tmp/pt_c_$arm.csv)
  printf '%s,%s,%.1f,%s\n' "$BOOT" "$arm" "$(python3 -c "print($c/$COUNT)")" "$REPS" | tee -a "$CSV"
}
run hugepage --hugepage
run premap --premap
run strict-premap --strict-premap
echo "wrote $CSV"

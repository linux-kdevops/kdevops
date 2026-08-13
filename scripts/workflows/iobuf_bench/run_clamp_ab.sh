#!/bin/bash
# run_clamp_ab.sh -- A/B for the dma_opt max-transfer clamp (CONFIG_NVME_LIFT_DMA_OPT_CLAMP).
#
# Shows the effect the clamp lift buys: at a fixed data rate, how many device
# commands and NVMe interrupts it takes to move a GiB when the request size is
# capped at the 128 KiB dma_opt clamp (A) vs lifted to the drive's MDTS (B).
# The two arms are selected at runtime on ONE kernel via max_sectors_kb, so this
# works whether the clamp was lifted at build time (option on, max_hw_sectors is
# the true MDTS) or you are simply comparing 128 KiB vs a larger request size.
#
# Hardware-agnostic: the achievable large command is the drive's MDTS, which the
# script decodes and prints -- 512 KiB on a Micron 7450, 2 MiB on a Samsung
# PM9A3, 8 MiB on a QEMU device built with CONFIG_QSU_NVME_MDTS="11". Run it on
# an emulated device (kdevops, any host) or on bare metal; the numbers scale with
# the MDTS/128 KiB ratio either way.
#
# Usage: run_clamp_ab.sh [blockdev]     (default: first non-root nvme namespace)
# READ-ONLY on the target; safe on an unmounted data namespace.
set -eu

DEV="${1:-}"
if [ -z "$DEV" ]; then
	ROOT=$(findmnt -no SOURCE / | sed 's|p[0-9]*$||;s|[0-9]*$||' 2>/dev/null || true)
	for d in /dev/nvme*n1; do
		[ -b "$d" ] || continue
		case "$d" in "$ROOT"*) continue;; esac
		DEV="$d"; break
	done
fi
[ -n "$DEV" ] && [ -b "$DEV" ] || { echo "no usable nvme block device; pass one explicitly"; exit 1; }
BN=$(basename "$DEV"); Q="/sys/block/$BN/queue"; STAT="/sys/block/$BN/stat"
CTRL="/dev/${BN%n*}"

# Decode MDTS (do not assume it). max_hw_sectors_kb already folds in the driver
# ceiling AND, when the option is enabled, the lifted dma_max_mapping_size.
MDTS_RAW=$(sudo nvme id-ctrl "$CTRL" 2>/dev/null | awk '/^mdts/{print $3}')
MAXHW=$(cat "$Q/max_hw_sectors_kb")
LBS=$(cat "$Q/logical_block_size")
# The largest single command this kernel will issue on this drive:
BIG_KB=$MAXHW
[ "$BIG_KB" -gt 4096 ] && BIG_KB=4096   # cap fio buffer at 4 MiB for portability
echo "device=$DEV  mdts=$MDTS_RAW  max_hw_sectors_kb=$MAXHW  logical_block_size=$LBS"
echo "large command under test: ${BIG_KB} KiB (vs the 128 KiB clamp)"
if [ "$MAXHW" -le 128 ]; then
	echo "WARNING: max_hw_sectors_kb=$MAXHW -- the clamp is NOT lifted on this kernel"
	echo "         (build with CONFIG_NVME_LIFT_DMA_OPT_CLAMP=y, or this is a 128 KiB-MDTS drive)."
fi

nvme_irq(){ awk '/nvme/{for(k=2;k<=NF-2;k++)s+=$k} END{print s+0}' /proc/interrupts; }
RATE="${RATE:-2000m}"; RUNTIME="${RUNTIME:-20}"; QD="${QD:-16}"

run(){
	local name="$1" mss="$2"
	echo "$mss" | sudo tee "$Q/max_sectors_kb" >/dev/null
	local eff; eff=$(cat "$Q/max_sectors_kb")
	local i0 r0; i0=$(nvme_irq); r0=$(awk '{print $1}' "$STAT")
	local j; j=$(sudo fio --name="$name" --filename="$DEV" --rw=read --bs="${BIG_KB}k" \
		--iodepth="$QD" --ioengine=io_uring --direct=1 --runtime="$RUNTIME" \
		--time_based --rate="$RATE" --group_reporting --output-format=json 2>/dev/null)
	local i1 r1; i1=$(nvme_irq); r1=$(awk '{print $1}' "$STAT")
	python3 - "$j" "$eff" "$name" "$((r1-r0))" "$((i1-i0))" <<'PY'
import json,sys
j=json.loads(sys.argv[1]); eff,name,cmds,irqs=sys.argv[2],sys.argv[3],int(sys.argv[4]),int(sys.argv[5])
r=j["jobs"][0]["read"]; gib=r["io_bytes"]/1073741824 or 1; bw=r["bw"]/1024/1024
print(f"{name:<9} max_sectors_kb={eff:<5} | BW={bw:.2f} GB/s moved={gib:.1f} GiB | "
      f"dev_cmds/GiB={cmds/gib:.0f} nvme_irqs/GiB={irqs/gib:.0f}")
PY
}

echo "=== A/B at a fixed ${RATE}B/s, ${BIG_KB}k sequential reads, QD${QD} ==="
run "A-clamped" 128
sleep 3
run "B-lifted"  "$BIG_KB"
echo "Expect the clamped arm to issue ~$((BIG_KB/128))x the commands and interrupts"
echo "per GiB (each ${BIG_KB} KiB request splits into $((BIG_KB/128)) x 128 KiB commands)."

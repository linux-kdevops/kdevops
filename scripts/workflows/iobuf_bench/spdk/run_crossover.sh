#!/bin/bash
# run_crossover.sh -- reproduce THE result: premap io_uring_cmd crosses above
# spdk_nvme_perf in GB/s-per-core at large objects.
#
# Sweeps block size on the free NVMe drives, one pinned CPU core, three arms:
#   spdk         spdk_nvme_perf (VFIO poller) -- the kernel-bypass reference
#   kernel_poll  fio io_uring + IOPOLL (--hipri) -- generic kernel, best foot
#   kernel_premap smoke --premap (io_uring_cmd map-once) -- the feature
#
# The point: at small blocks SPDK's userspace poller wins; as the object grows
# the drive becomes bandwidth-bound, SPDK's MANDATORY busy-poll wastes a whole
# core sitting there, and interrupt-driven premap spends almost none -- so premap
# crosses above SPDK around 64K and runs several-fold past it at the MDTS ceiling.
#
# Requires: the iobuf-premap-vs-spdk kernel booted (pool + clamp lift + poll
# queues; see the defconfig), and spdk/provision.sh already run.
#
# Env: PREFIX (default $HOME), CORE (pinned core), QD (default 64),
#      BSES (default "4k 16k 64k 128k 512k"), REPS, RUNT.
set -u
D=$(dirname "$(readlink -f "$0")")
PREFIX=${PREFIX:-$HOME}
SPDK=${SPDK:-$PREFIX/spdk}; SPDK_PERF=$SPDK/build/bin/spdk_nvme_perf
SMOKE=${SMOKE:-$PREFIX/smoke}
CORE=${CORE:-4}; QD=${QD:-64}; REPS=${REPS:-3}; RUNT=${RUNT:-12}
BSES=(${BSES:-4k 16k 64k 128k 512k})
OUT=${OUT:-$PREFIX/crossover_out}; mkdir -p "$OUT"; CSV="$OUT/crossover.csv"
echo "arm,bs,cores,iops,bw_mbps,busy_cores" > "$CSV"

# --- preflight: the premap kernel must actually be configured ---
clamp=$(cat /sys/module/nvme/parameters/lift_dma_opt_clamp 2>/dev/null || echo '?')
folios=$(cat /sys/module/nvme_core/parameters/iobuf_pool_folios 2>/dev/null || echo 0)
[ "$clamp" = Y ] || { echo "PREFLIGHT FAIL: nvme.lift_dma_opt_clamp!=Y (boot the iobuf-premap-vs-spdk kernel)"; exit 1; }
[ "${folios:-0}" -ge "$QD" ] || { echo "PREFLIGHT FAIL: iobuf_pool_folios=$folios < QD=$QD"; exit 1; }
[ -x "$SPDK_PERF" ] && [ -x "$SMOKE" ] || { echo "PREFLIGHT FAIL: run spdk/provision.sh first"; exit 1; }

# --- discover free drives (7TB-ish, no holder): ng + BDF, matched, BDF-sorted ---
NGS=(); BDFS=()
while read -r dev; do
	n=${dev%n1}; [ -e "/dev/$dev" ] || continue
	[ -n "$(lsblk -no NAME /dev/$dev | tail -n +2)" ] && continue
	sz=$(cat /sys/class/nvme/$n/${dev}/size 2>/dev/null); [ "${sz:-0}" -lt 1000000000 ] && continue
	NGS+=("/dev/ng${dev#nvme}"); BDFS+=("$(basename $(readlink -f /sys/class/nvme/$n/device))")
done < <(ls /dev | grep -E '^nvme[0-9]+n1$' | sort)
paired=$(for i in "${!BDFS[@]}"; do echo "${BDFS[$i]} ${NGS[$i]}"; done | sort)
BDFS=($(echo "$paired" | awk '{print $1}')); NGS=($(echo "$paired" | awk '{print $2}'))
N=${#NGS[@]}
[ "$N" -ge 1 ] || { echo "no free NVMe namespaces found"; exit 1; }
echo "free drives: $N -> ${NGS[*]} @ ${BDFS[*]}  core=$CORE qd=$QD"
sudo sysctl -q -w vm.nr_hugepages=$(( N*160 + 256 ))
busy(){ awk '/^cpu /{i=$5+$6;t=0;for(k=2;k<=NF;k++)t+=$k;print t-i}' /proc/stat; }
bytes(){ numfmt --from=iec "${1^^}"; }

# --- kernel_poll: fio io_uring block + IOPOLL, drives on the kernel ---
kernel_poll(){ local bs; local files=""; local d
	for d in "${NGS[@]}"; do files="$files --name=$(basename ${d/ng/nvme}) --filename=${d/ng/nvme}"; done
	for bs in "${BSES[@]}"; do for r in $(seq 1 $REPS); do
		c0=$(busy)
		sudo taskset -c $CORE fio --ioengine=io_uring --direct=1 --rw=randread --bs=$bs \
			--iodepth=$QD --hipri --fixedbufs --registerfiles --iomem=mmaphuge \
			--cpus_allowed=$CORE --size=100G --time_based --runtime=$RUNT --ramp_time=3 \
			--group_reporting --output-format=json $files >/tmp/cx_fio.json 2>/dev/null
		c1=$(busy)
		python3 -c "import json;d=json.load(open('/tmp/cx_fio.json'));bw=sum(j['read']['bw'] for j in d['jobs'])/1024;io=sum(j['read']['iops'] for j in d['jobs']);bc=($c1-$c0)/100/$RUNT;print(f'kernel_poll,$bs,1,{io:.0f},{bw:.0f},{bc:.3f}')" | tee -a "$CSV"
	done; done
}
# --- kernel_premap: smoke --premap, one instance per drive, pinned to CORE ---
kernel_premap(){ local bs len d
	for bs in "${BSES[@]}"; do len=$(bytes $bs); for r in $(seq 1 $REPS); do
		c0=$(busy); t0=$(date +%s.%N)
		for d in "${NGS[@]}"; do
			sudo taskset -c $CORE "$SMOKE" --dev "$d" --count 40000 --qd $QD --len $len \
				--lba-size 512 --cmds-per-obj 1 --premap >/dev/null 2>&1 &
		done; wait
		t1=$(date +%s.%N); c1=$(busy)
		python3 -c "wall=$t1-$t0;gib=$N*40000*$len/1073741824;gbs=gib/wall;io=$N*40000/wall;bc=($c1-$c0)/100/wall;print(f'kernel_premap,$bs,1,{io:.0f},{gbs*1024:.0f},{bc:.3f}')" | tee -a "$CSV"
	done; done
}
# --- spdk: bind free BDFs to VFIO, run nvme_perf on CORE, rebind ---
spdk_arm(){ local bs o
	"$D/vfio.sh" bind "$SPDK" "${BDFS[*]}" || { echo "spdk arm skipped (bind failed)"; return; }
	local rargs=""; for b in "${BDFS[@]}"; do rargs="$rargs -r 'trtype:PCIe traddr:$b'"; done
	for bs in "${BSES[@]}"; do o=$(bytes $bs); for r in $(seq 1 $REPS); do
		c0=$(busy)
		eval sudo taskset -c $CORE "$SPDK_PERF" -q $QD -o $o -w randread -t $RUNT \
			-c "$(printf '0x%x' $((1<<CORE)))" $rargs >/tmp/cx_spdk.log 2>&1
		c1=$(busy)
		mib=$(awk '/^Total/{print $4}' /tmp/cx_spdk.log); io=$(awk '/^Total/{print $3}' /tmp/cx_spdk.log)
		python3 -c "bc=($c1-$c0)/100/$RUNT;print(f'spdk,$bs,1,${io:-0},${mib:-0},{bc:.3f}')" | tee -a "$CSV"
	done; done
	"$D/vfio.sh" reset "$SPDK" "${BDFS[*]}"
}

echo "### kernel_poll ###";   kernel_poll
echo "### kernel_premap ###"; kernel_premap
echo "### spdk ###";          spdk_arm
echo "CROSSOVER_DONE -> $CSV"
python3 "$D/../plot_crossover3.py" "$OUT" "$CSV" 2>/dev/null && echo "figure -> $OUT/fig_crossover_3arm.png" || \
	echo "(plot_crossover3.py expects columns arm,bs,cores,iops,bw_mbps,busy_cores)"

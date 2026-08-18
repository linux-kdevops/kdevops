#!/bin/bash
# kernpath_sweep.sh -- ISOLATE the kernel buffer path: same userspace tool
# (the smoke loop), same 2 MiB reads, differing ONLY in buffer mode:
#   stock-buffer  = --hugepage --fixed  (ordinary hugepage fixed buffer, mapped
#                   per command through the normal block/nvme path)
#   premap        = --premap            (blk_iobuf_pool, mapped once, reused)
# This removes the fio-vs-smoke confound in scale_sweep.sh, so the CPU delta is
# the kernel per-command mapping/descriptor work alone. Sweeps drives 1,2,4.
set -u
SMOKE=${SMOKE:-$HOME/smoke}
CSV=${CSV:-$HOME/kernpath.csv}
QD=${QD:-64}; LBA=512; OBJ=2097152; REPS=${REPS:-3}; COUNT=${COUNT:-40000}

ALL_NG=()
while read -r dev; do
  n=${dev%n1}
  [ -e "/dev/${dev}" ] || continue
  [ -n "$(lsblk -no NAME "/dev/${dev}" | tail -n +2)" ] && continue
  cat /sys/class/nvme/${n}/model 2>/dev/null | grep -qi samsung || continue
  ng="/dev/ng${dev#nvme}"; [ -e "$ng" ] && ALL_NG+=("$ng")
done < <(ls /dev | grep -E '^nvme[0-9]+n1$' | sort)
echo "free drives: ${#ALL_NG[@]} -> ${ALL_NG[*]}"

busy(){ awk '/^cpu /{idle=$5+$6;t=0;for(k=2;k<=NF;k++)t+=$k;print t-idle}' /proc/stat; }
echo "arm,drives,rep,gbps,busy_cores,gbps_per_core" > "$CSV"
sudo sysctl -q -w vm.nr_hugepages=$(( 4*160 + 256 ))

run(){ # $1=arm-label  $2=extra smoke flags  $3=N
  local arm=$1 flags=$2 N=$3 ng r
  for r in $(seq 1 $REPS); do
    local c0=$(busy); local t0=$(date +%s.%N)
    for ng in "${ALL_NG[@]:0:$N}"; do
      sudo "$SMOKE" --dev "$ng" --count $COUNT --qd $QD --len $OBJ --lba-size $LBA \
        --cmds-per-obj 8 $flags >/dev/null 2>&1 &
    done; wait
    local t1=$(date +%s.%N); local c1=$(busy)
    python3 -c "wall=$t1-$t0;gib=$N*$COUNT*$OBJ/1073741824;gbs=gib/wall;bc=($c1-$c0)/100/wall;print(f'$arm,$N,$r,{gbs:.2f},{bc:.3f},{(gbs/bc) if bc>0 else 0:.0f}')" | tee -a "$CSV"
    sleep 2
  done
}

for N in 1 2 4; do
  run stock_buffer "--hugepage --fixed" $N
  run premap       "--premap"           $N
done
echo "KERNPATH_DONE -> $CSV"
column -t -s, "$CSV"

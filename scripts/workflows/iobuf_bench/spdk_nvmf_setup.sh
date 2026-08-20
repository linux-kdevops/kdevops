#!/bin/bash
# spdk_nvmf_setup.sh -- start an SPDK NVMe-oF/TCP target exporting the given PCI
# NVMe drives, one subsystem per drive, on 127.0.0.1:4420. Reactors pinned by
# REACTOR_MASK (default 0xF = 4 cores). Binds the drives to SPDK (vfio/uio).
# Usage: REACTOR_MASK=0xF spdk_nvmf_setup.sh <bdf1> <bdf2> ...
set -e
SPDK=${SPDK:-$HOME/spdk}
RPC="sudo $SPDK/scripts/rpc.py"
MASK=${REACTOR_MASK:-0xF}
IP=${LISTEN_IP:-127.0.0.1}; SVC=4420
# bind ONLY these drives to SPDK
ALLOW=$(IFS=" "; echo "$*")
sudo PCI_ALLOWED="$ALLOW" HUGEMEM=8192 "$SPDK/scripts/setup.sh" >/tmp/spdk_setup.log 2>&1
# start the target
sudo "$SPDK/build/bin/nvmf_tgt" -m "$MASK" >/tmp/nvmf_tgt.log 2>&1 &
echo $! > /tmp/nvmf_tgt.pid
# wait for RPC socket
for i in $(seq 1 30); do $RPC framework_get_config >/dev/null 2>&1 && break; sleep 0.5; done
$RPC nvmf_create_transport -t TCP -u 131072 >/dev/null
i=0
for bdf in "$@"; do
  nqn="nqn.2026-08.io.spdk:bench-$i"
  $RPC bdev_nvme_attach_controller -b "Nvme$i" -t PCIe -a "$bdf" >/dev/null
  $RPC nvmf_create_subsystem "$nqn" -a -s "SPDKBENCH$i" >/dev/null
  $RPC nvmf_subsystem_add_ns "$nqn" "Nvme${i}n1" >/dev/null
  $RPC nvmf_subsystem_add_listener "$nqn" -t tcp -a $IP -s $SVC >/dev/null
  echo "SPDK exported $bdf as $nqn"
  i=$((i+1))
done
echo "spdk nvmf_tgt up on $IP:$SVC, reactors=$MASK, $i subsystems"

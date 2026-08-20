#!/bin/bash
# nvmet_setup.sh -- bring up an in-kernel NVMe-oF/TCP target exporting the free
# NVMe namespaces, one subsystem per drive, on 127.0.0.1:4420 (loopback).
# Usage: nvmet_setup.sh /dev/nvme0n1 /dev/nvme1n1 ...
set -e
CFG=/sys/kernel/config/nvmet
PORT=$CFG/ports/1
IP=${LISTEN_IP:-127.0.0.1}; SVC=4420
sudo modprobe nvmet nvmet-tcp
# port
[ -d $PORT ] || sudo mkdir -p $PORT
echo ipv4 | sudo tee $PORT/addr_adrfam >/dev/null
echo tcp  | sudo tee $PORT/addr_trtype >/dev/null
echo $IP  | sudo tee $PORT/addr_traddr >/dev/null
echo $SVC | sudo tee $PORT/addr_trsvcid >/dev/null
i=0
for dev in "$@"; do
  nqn="nvmet-bench-$i"
  sub=$CFG/subsystems/$nqn
  sudo mkdir -p $sub
  echo 1 | sudo tee $sub/attr_allow_any_host >/dev/null
  sudo mkdir -p $sub/namespaces/1
  echo -n $dev | sudo tee $sub/namespaces/1/device_path >/dev/null
  echo 1 | sudo tee $sub/namespaces/1/enable >/dev/null
  sudo ln -sf $sub $PORT/subsystems/$nqn
  echo "exported $dev as $nqn"
  i=$((i+1))
done
echo "nvmet-tcp up on $IP:$SVC with $i subsystems"

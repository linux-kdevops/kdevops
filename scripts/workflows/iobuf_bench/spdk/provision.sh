#!/bin/bash
# provision.sh -- reproducibly build SPDK and the premap smoke tool on the target.
#
# This is the piece kdevops was missing: SPDK as a pinned, built dependency
# rather than a hand-made artifact. Run once on the box the premap kernel booted
# on (the iobuf-premap-vs-spdk defconfig put it there). Records the exact SPDK
# commit it built to spdk/PROVENANCE so a run is reproducible even if the tag
# moves.
#
# Env:
#   SPDK_REF     SPDK git ref to build (default: a pinned tag; override to bump)
#   PREFIX       where to put spdk + smoke (default: $HOME)
#   SMOKE_URL    git repo carrying nvme_uring_cmd_smoke.c (the premap benchmark
#                client); default is the ebpf-syscall tree.
#   SMOKE_REF    ref within SMOKE_URL (default: main)
set -e
SPDK_REF=${SPDK_REF:-v25.01}
PREFIX=${PREFIX:-$HOME}
SMOKE_URL=${SMOKE_URL:-https://github.com/mcgrof/ebpf-syscall.git}
SMOKE_REF=${SMOKE_REF:-main}

echo "== provisioning SPDK ($SPDK_REF) and smoke tool into $PREFIX =="

# --- SPDK ---
cd "$PREFIX"
if [ ! -d spdk/.git ]; then
	git clone https://github.com/spdk/spdk.git spdk
fi
cd "$PREFIX/spdk"
git fetch --tags --depth 1 origin "$SPDK_REF" 2>/dev/null || git fetch --tags origin
git checkout "$SPDK_REF"
sudo scripts/pkgdep.sh
git submodule update --init --depth 1
./configure
make -j"$(nproc)"
SPDK_COMMIT=$(git rev-parse --short HEAD)
[ -x build/bin/spdk_nvme_perf ] || { echo "ERROR: spdk_nvme_perf did not build"; exit 1; }

# --- smoke tool (the premap io_uring_cmd benchmark client) ---
cd "$PREFIX"
if [ ! -d ebpf-syscall/.git ]; then
	git clone --depth 1 -b "$SMOKE_REF" "$SMOKE_URL" ebpf-syscall
fi
cd "$PREFIX/ebpf-syscall"
gcc -O2 -o "$PREFIX/smoke" nvme_uring_cmd_smoke.c -luring
SMOKE_COMMIT=$(git rev-parse --short HEAD)
[ -x "$PREFIX/smoke" ] || { echo "ERROR: smoke did not build"; exit 1; }

# --- provenance ---
D=$(dirname "$(readlink -f "$0")")
{
	echo "date=$(date -u +%FT%TZ)"
	echo "host=$(uname -n) kernel=$(uname -r)"
	echo "spdk_ref=$SPDK_REF spdk_commit=$SPDK_COMMIT spdk_bin=$PREFIX/spdk/build/bin/spdk_nvme_perf"
	echo "smoke_url=$SMOKE_URL smoke_ref=$SMOKE_REF smoke_commit=$SMOKE_COMMIT smoke_bin=$PREFIX/smoke"
} | tee "$D/PROVENANCE"
echo "== provisioned OK =="

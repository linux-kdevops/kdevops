# premap vs SPDK — reproducible crossover, and a home for SPDK analysis

This directory adds **SPDK support to kdevops** so the one result that proves the
premap thesis is `make`-and-a-script reproducible, and so there is a place to
grow SPDK analysis instead of hand-building SPDK each time.

## The thesis this reproduces

On a NVMe drive, `premap` (the `blk_iobuf_pool` map-once `io_uring_cmd` path)
issues a command whose buffer is DMA-mapped **once** and reused, and it is
**interrupt-driven**. SPDK's userspace driver is a **busy-poll** loop that owns a
whole CPU core. So:

- **Small blocks (≤16K):** SPDK wins. Its lockless userspace submission (no
  `blk_mq` request, no tag, no `io_kiocb`) is simply leaner per I/O.
- **Large blocks (≥~64K):** the drive is **bandwidth-bound**, so SPDK's *mandatory*
  poll core spins doing nothing useful, while interrupt-driven premap spends
  almost no CPU. premap **crosses above SPDK around 64K** and runs several-fold
  past it at the drive's MDTS ceiling (measured 6× at 512K on a Micron 7450).

GB/s **per CPU core** is the metric — not peak GB/s — because the question is how
many cores storage steals from the application. Full analysis + figures live in
`knlp-key-results/spdk-vs-linux-grounded-20260819` and
`premap-spdk-multidrive-20260818`.

## Reproduce it

1. **Boot the premap kernel** (pool + clamp lift + poll queues) on a bare-metal
   host with a **translating IOMMU** and free NVMe namespaces:

   ```
   make defconfig-iobuf-premap-vs-spdk-baremetal DECLARE_HOSTS=<ip-or-host>
   make -j$(nproc) && make bringup && make linux
   ```

   That builds `blk-iobuf-pool-v5-premap-iova-pgsize-clamp-param-test` from
   kernel.org with `CONFIG_BLK_IOBUF_POOL=y`, and boots it with:

   ```
   nvme.lift_dma_opt_clamp=1 nvme_core.multipath=0 \
   nvme_core.iobuf_pool_folios=80 nvme_core.iobuf_pool_order=9 nvme.poll_queues=8
   ```

   (`order=9` = 2 MiB pool folios; `folios≥QD`; see the defconfig header.)

2. **Provision SPDK + the smoke client** (the missing kdevops piece — pinned,
   built, recorded):

   ```
   ssh <host> 'bash /path/to/spdk/provision.sh'   # writes spdk/PROVENANCE
   ```

3. **Run the crossover** (three arms, block-size sweep, one pinned core):

   ```
   ssh <host> 'CORE=4 QD=64 bash /path/to/spdk/run_crossover.sh'
   # -> crossover_out/crossover.csv and fig_crossover_3arm.png
   ```

   `run_crossover.sh` preflights the kernel (clamp lifted, pool sized), discovers
   the free drives, runs **spdk** (`spdk_nvme_perf`, VFIO), **kernel_poll** (fio
   `io_uring`+IOPOLL — generic kernel best-foot), and **kernel_premap** (the
   feature), then plots GB/s-per-core vs block size. You should see premap cross
   above SPDK around 64K.

## What's here

- `provision.sh` — clone+build a pinned SPDK and the smoke client; record commits.
- `vfio.sh` — safe VFIO bind/reset: binds **only** the BDFs you pass, fails closed
  if a drive has a holder, rebinds to `nvme` after.
- `run_crossover.sh` — the end-to-end reproducer above.
- `../plot_crossover3.py` — GB/s-per-core vs block-size figure.

## A home to grow SPDK analysis

These already exist in the parent dir and reuse `provision.sh`/`vfio.sh` — the
expansion surface:

- `../scale_sweep.sh` — premap vs stock vs SPDK across **1/2/4 drives** (shows
  SPDK's poll-core-per-drive tax scaling vs premap's flat CPU).
- `../two_box.sh` (+ `nvmet_setup.sh`, `spdk_nvmf_setup.sh`) — SPDK **nvmf_tgt**
  vs kernel **nvmet** over NVMe-oF/TCP, the disaggregated-target comparison.
- `../iops_core_bench.sh` / `../iops_core_hostbound.sh` — the small-IO
  IOPS/core + cycles/IO study (where SPDK wins and premap does not).

## Open problem: beat SPDK below 64K

premap does **not** win small random I/O — SPDK takes 4–16K. If you want to close
that, the gap is **not** DMA setup (premap already removes it) and **not** the
submission syscall (already amortized at depth). It is the **per-command kernel
stack**: even `io_uring_cmd` passthrough still allocates a `blk_mq` request + tag
and runs the `io_kiocb` lifecycle, where SPDK writes a 64-byte command straight
into the drive's SQ from a lockless per-core loop. Leads worth trying, all on the
same harness (add an arm to `run_crossover.sh`, sweep 512B–16K, weight QD1–16):

- **`IORING_SETUP_SQPOLL`** shared across rings (one poll thread, `ATTACH_WQ`) —
  the smoke tool already takes `--sqpoll-cpu`.
- **`io_uring_cmd` + poll queues + `IOPOLL`** tuned to its limit.
- **Cutting the per-command request/tag cost** on the passthrough path — the real
  structural difference from SPDK. This is the interesting, unsolved lane.

## Not in scope here

`ublk` (kublk in `../ublk_bench.sh`) is **orthogonal** to premap-vs-SPDK: its
bottleneck is the kernel↔userspace control-plane round-trip, which premap does
not address. Kept for reference, not part of this reproduction.

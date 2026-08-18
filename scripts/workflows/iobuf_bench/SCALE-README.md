# Multi-drive scaling: kernel io_uring_cmd vs SPDK

`scale_sweep.sh` measures storage throughput **per CPU core** as you add NVMe
drives, for three paths: stock `io_uring_cmd` (fio, hugepage fixed buffers),
premap (`blk_iobuf_pool` map-once, via the smoke tool), and SPDK
`spdk_nvme_perf` over VFIO. It answers whether the kernel's efficiency edge over
SPDK holds as drive count grows — it does, and widens, because SPDK needs one
polling core per drive while the kernel stays interrupt-driven and near-flat.

`kernpath_sweep.sh` isolates the **kernel buffer path** by running the *same*
tool (the io_uring_cmd smoke loop) in both arms, changing only the buffer mode
(`--hugepage --fixed` vs `--premap`), so the CPU delta is the kernel per-command
mapping work alone — not a fio-vs-smoke tool difference.

## Requirements

- Boot the premap kernel: pool + clamp lift, e.g. `nvme.lift_dma_opt_clamp=1
  nvme_core.multipath=0 nvme_core.iobuf_pool_folios=80 nvme_core.iobuf_pool_order=9`
  (order-9 = 2 MiB pool folios; the branch is
  `blk-iobuf-pool-v5-premap-iova-pgsize-clamp-param-test`).
- `fio`, a premap-capable smoke tool (`--premap`), a built SPDK
  (`build/bin/spdk_nvme_perf`), reserved huge pages.
- Free NVMe namespaces (the scripts auto-detect Samsung drives with no holder;
  adjust the model filter for other hardware).

## Run

```
CSV=$HOME/scale.csv REPS=3 T=12 QD=64 \
  SMOKE=$HOME/smoke SPDK_PERF=$HOME/spdk/build/bin/spdk_nvme_perf \
  bash scale_sweep.sh
CSV=$HOME/kernpath.csv REPS=3 QD=64 SMOKE=$HOME/smoke bash kernpath_sweep.sh
python3 plot_scale.py scale.csv .    # two figures
```

Both emit `arm,drives,rep,gbps,busy_cores,gbps_per_core`. The SPDK arm binds
only the passed BDFs to vfio-pci and rebinds them to `nvme` afterwards; always
pass free namespaces. See the report
`knlp-key-results/premap-spdk-multidrive-20260818` for the measured result on
4× Samsung PM9A3 behind an AMD EPYC 9554P.

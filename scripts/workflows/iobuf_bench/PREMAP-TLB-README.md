# premap IOMMU-leaf / TLB campaign

What to test: whether premap's contiguous buffers get large (2 MiB) IOMMU
mappings, how much host CPU premap saves over huge pages, and whether the large
mappings reduce device-side (IOTLB) translation misses and/or storage
throughput. Needs a **translating IOMMU** (AMD-Vi or Intel VT-d) and a **free**
2 MiB-MDTS NVMe namespace (a Samsung PM9A3 works; do not use a read-only OS
mirror member).

Nothing here draws conclusions -- it produces CSV/JSON you interpret.

## 0. Kernel and boot

Build and boot `blk-iobuf-pool-v5-premap-iova-pgsize-clamp-param-test` with
`CONFIG_BLK_IOBUF_POOL=y` and `CONFIG_DMA_IOVA_PGSIZE_SELFTEST=m`:

```sh
make defconfig-iobuf-premap-tlb-baremetal DECLARE_HOSTS=<host>
make -j$(nproc) && make linux
```

Two boot arms, differing only in the last cmdline token:

```
huge-on  : nvme_core.multipath=N nvme_core.iobuf_pool_order=9 \
           nvme_core.iobuf_pool_folios=256 nvme.lift_dma_opt_clamp=1
huge-off : ... same ... amd_iommu=pgtbl_v1,nohugepages
```

Verify (huge-on): `cat /proc/cmdline`; `cat /sys/module/nvme/parameters/lift_dma_opt_clamp`
is `Y`; `cat /sys/block/nvme2n1/queue/max_hw_sectors_kb` >= 2048;
`dmesg | grep iobuf_pool:` shows `order 9`; `ls /sys/bus/event_source/devices/amd_iommu_*`.
huge-off additionally shows `dmesg | grep 'Restricting V1 page-sizes to 4KiB'`.

Prereqs: `sudo apt-get install -y fio nvme-cli liburing-dev linux-tools-generic
jq python3`; build the smoke tool from the ebpf-syscall tree
(`make nvme_uring_cmd_smoke` -- needs the `--strict-premap` build).

## 1. CPU: huge page vs premap vs strict premap (produces the CSV)

Tightened, 10 reps + a discarded warmup. Run it on BOTH boots:

```sh
./premap_tlb_smoke.sh /dev/ng2n1 /path/to/nvme_uring_cmd_smoke premap_tlb.csv
```

Rows are `boot,arm,cyc_per_cmd,reps`. On the huge-off boot the `strict-premap`
arm is expected to fail (no 2 MiB IOMMU leaves) and is recorded as such. Knobs:
`REPS`, `COUNT`, `QD`, `LEN`, `LBA` env vars.

Expected shape (pilot): premap ~35-40% fewer cycles/command than huge pages;
strict premap within noise of premap; huge page cycles rise on huge-off while
premap stays flat (map-once).

## 2. Leaf geometry, IOTLB PMU, and sustained throughput (full harness)

The complete matrix -- installed-leaf histograms (`iommu:iommu_map_leaf`), the
strict-API negative tests, the requester-filtered AMD IOMMU PMU group
(`amd_iommu_2`, `mem_iommu_tlb_pte_*`), and the sustained `iobuf-fixed-test
--bench` legs -- is driven by `premap-run-arm.sh` from the campaign archive
(`knlp-key-results/premap-tlb-leaf-20260813/raw-results.tar.gz`,
`results/campaign-meta/`). It resolves the free PM9A3 by serial, gates on the
exact cmdline, and validates every step with jq.

To use it here, adjust two things for this branch:
- it gates on `CONFIG_NVME_LIFT_DMA_OPT_CLAMP=y`; this branch uses the **module
  parameter** instead, so gate on
  `grep -q 1 /sys/module/nvme/parameters/lift_dma_opt_clamp` (or `=Y`) and boot
  `nvme.lift_dma_opt_clamp=1`.
- for acceptance-grade numbers raise `PERF_REPS` to 10, add bench warmup, and
  collect the PMU only over the measured window (the smoke tool's ready/start
  barrier: `--ready-fd`/`--start-fd`).

Build the bench first: `cd tools/testing/selftests/blk-iobuf && make`
(if it fails on `linux/blkdev.h`, run `make headers_install` in the kernel tree
and rebuild).

## Rigor checklist (why the first pilot was a NO-GO)

- >= 5 warmups, >= 10 measured repetitions per arm.
- Alternate boot order across reboots (huge-on, huge-off, huge-on, ...) to
  decorrelate boot/thermal drift.
- PMU and CPU counters over the measured window only, not wrapping setup.
- Direct leaf + command tracing of the real blk-iobuf premap registrations.
- Report medians and dispersion; normalize IOTLB events per GiB and per command.

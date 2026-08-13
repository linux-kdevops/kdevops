# dma_opt clamp-lift: host-CPU benchmarks

Run two benchmarks and plot the result. This measures the **host CPU cost** of
NVMe command size and buffer/mapping strategy on the clamp-lift kernel. It does
**not** draw conclusions here — it produces `sweep.csv`, `ace.csv`, and three
PNGs; interpret them yourself.

## 0. Kernel

Build and boot a kernel with `CONFIG_NVME_LIFT_DMA_OPT_CLAMP=y` so
`max_sectors_kb` can exceed 128 KiB:

```sh
# emulated large-MDTS NVMe, any host, no special hardware:
make defconfig-iobuf-clamp-lift-qemu && make -j$(nproc) && make bringup && make linux
# or on a real host you have SSH to:
make defconfig-iobuf-clamp-lift-baremetal DECLARE_HOSTS=<host> && make -j$(nproc) && make linux
```

Verify the lift is live (should exceed 128) and note the IOMMU is translating:

```sh
cat /sys/block/nvme0n1/queue/max_hw_sectors_kb      # > 128 means the lift is active
dmesg | grep 'Default domain type'                  # want: Translated
sudo nvme id-ctrl /dev/nvme0 | grep mdts            # the drive's max command (log2 over 4 KiB)
```

Install prerequisites once: `sudo apt-get install -y fio nvme-cli liburing-dev
python3-matplotlib linux-tools-common linux-tools-generic`.

## 1. CPU vs command size (produces `sweep.csv`)

Reserve huge pages (needed for the >1 MiB points), then sweep each drive you
want. Reads only, so a read-only drive (e.g. an OS-mirror member) is fine.

```sh
echo 6144 | sudo tee /proc/sys/vm/nr_hugepages
./cpu_sweep.sh /dev/nvme2n1 PM9A3  sweep.csv        # appends rows for this drive
./cpu_sweep.sh /dev/nvme0n1 Micron sweep.csv        # add a second drive if present
```

Each row is `drive,size_kb,cmds_per_gib,mcyc_per_gib,buffer` (`mcyc_per_gib` =
million CPU cycles per GiB, the perf-counter CPU cost; `buffer` = pages/huge).

## 2. page vs huge page vs premap (produces `ace.csv`)

This uses the `nvme_uring_cmd_smoke` tool from the **ebpf-syscall** tree:

```sh
git clone https://github.com/SamsungDS/ebpf-syscall && (cd ebpf-syscall && make nvme_uring_cmd_smoke)
```

`--premap` needs the pool provisioned and multipath off. Boot the kernel with:

```
nvme_core.multipath=N nvme_core.iobuf_pool_folios=32 nvme_core.iobuf_pool_order=10
```

(`iobuf-clamp-lift-baremetal` can carry these on its cmdline; or set them in
grub and reboot). Confirm the pool came up: `dmesg | grep iobuf_pool:`. Then:

```sh
echo 200 | sudo tee /proc/sys/vm/nr_hugepages
./premap_bench.sh /dev/ng2n1 2097152 ./ebpf-syscall/nvme_uring_cmd_smoke ace.csv
```

Rows are `arm,cyc_per_cmd,note`. A drive whose `/dev/ng` is a multipath **head**
refuses premap — use the per-controller path or boot `nvme_core.multipath=N`.
The page-granular arm is expected to fail at large sizes (segment limit); the
script records that as an empty `cyc_per_cmd` with a note.

## 3. Plot (produces the three PNGs)

```sh
python3 plot_clamp_cpu.py sweep.csv ace.csv ./out
# out/fig1_cpu_vs_cmdsize.png  out/fig2_premap_vs_huge.png  out/fig3_mdts_projection.png
```

`fig3` fits the contiguous (huge-buffer) points and projects to large MDTS, so it
needs at least the 2 MiB (and ideally 4 MiB) points in `sweep.csv`.

## Knobs (env vars)

`RATE` (fixed data rate, default `4000m`), `T` (seconds per run, `15`), `QD`
(`32`), `REP` (runs to take the median of, `3`) for `cpu_sweep.sh`; `LEN`, `QD`,
`CNT`, `REP`, `LBA` for `premap_bench.sh`. CPU is reported in CPU cycles, not
wall-clock %, because `perf` counters are precise where a busy-time % on a
many-core idle box is dominated by noise.

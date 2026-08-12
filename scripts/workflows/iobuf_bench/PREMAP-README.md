# Premap large-command test — for a host with a large-MDTS NVMe drive

You have a box with a **large-MDTS NVMe drive**. This proves the one thing a
128 KiB-clamped host cannot: that the `blk-iobuf-pool-v5-premap-iova` kernel
issues a **single NVMe command up to the drive's real MDTS** (past the 128 KiB
`dma_opt` clamp) by allocating **zero per-I/O IOVA**. You run three make commands
plus one bench script, then send back one tarball.

Run kdevops **on the box itself** (simplest — the box is both control node and
target). Needs root and internet.

## 1. Build and boot the premap kernel

```bash
git clone https://github.com/linux-kdevops/kdevops && cd kdevops
make defconfig-iobuf-premap-baremetal DECLARE_HOSTS=localhost
make -j$(nproc)
make linux          # clones + builds + installs the premap kernel on this box
```

`make linux` leaves the kernel source in `~/linux` (the bench finds it there).

## 2. One-time: pool + IOMMU on the kernel cmdline, then reboot

The premap path needs the pool provisioned and a **translating** IOMMU. Add this
to the new kernel's cmdline (edit `/etc/default/grub`, append to
`GRUB_CMDLINE_LINUX`, then `update-grub` — or `grubby --update-kernel`), and make
sure you boot the just-installed premap kernel:

```
iommu.passthrough=0 nvme_core.iobuf_pool=1 nvme_core.iobuf_pool_order=10 nvme_core.iobuf_pool_folios=32
```

- On Intel add `intel_iommu=on`; on AMD add `amd_iommu=on` **only if** the IOMMU
  is not already up (check after boot: `ls /sys/kernel/iommu_groups | wc -l` > 0,
  and `cat /sys/block/nvmeXnY/queue/max_hw_sectors_kb` should read `128` — that
  128 is the clamp we are beating, and its presence confirms a translating IOMMU).

Confirm the pool is provisioned. **This branch has no per-queue `iobuf_pool_*`
sysfs** (the old RFC-v2 interface was dropped) — the pool is set via read-only
module params and reported in dmesg:

```
dmesg | grep 'iobuf_pool:'                              # "N folios of order M ... on nvmeXnY"
cat /sys/module/nvme_core/parameters/iobuf_pool_order   # 10
cat /sys/module/nvme_core/parameters/iobuf_pool_folios  # 32
```

The device named in that dmesg line is the one with the pool — run the bench
against its `/dev/ngXnY`.

Reboot into the premap kernel (`uname -r` should show the `blk-iobuf-pool` build).

## 3. Run the bench and send back the tarball

Pick the drive under test — its char device `/dev/ngXnY` and matching block node
`/dev/nvmeXnY` (**use a spare/scratch namespace**; the test does a bounded
round-trip but reads/writes it):

```bash
cd kdevops/scripts/workflows/iobuf_bench
sudo ./run_premap.sh /dev/ng0n1 /dev/nvme0n1
# -> premap-results-<host>-<ts>.tar.gz
```

**Multipath caveat (important).** If your NVMe uses native multipath, `/dev/ng0n1`
is the multipath **head**, and premap is *deliberately refused* on the head (commit
`912328a`: the head resolves a floating path, so a retained DMA mapping could
dangle). The tell: the `iobuf_pool:` dmesg line names a **path** device like
`nvme0c0n1`, not `nvme0n1`. Point the bench at the **fixed per-controller path**
instead — `sudo ./run_premap.sh /dev/ng0c0n1 /dev/nvme0c0n1` — or boot with
`nvme_core.multipath=N` so `/dev/ng0n1` becomes the fixed path. The script prints a
`VERDICT: PREMAP DID NOT ENGAGE … multipath head` if it detects this.

Send back that **one tarball**. It contains:

- `env.txt` — kernel, device MDTS, the `max_hw_sectors_kb` clamp,
  `max_hw_premapped_sectors`, pool state, IOMMU groups, cmdline;
- `premap_sizes.csv` — PASS/FAIL per command size (128 KiB … 8 MiB);
- `summary.txt` — the headline: **largest single premapped command vs the clamp**;
- per-size logs.

The bench fails loudly with the exact fix if a prerequisite (pool / IOMMU /
`/dev/ng`) is missing, so it is safe to just run it.

## What we are looking for

`summary.txt` should show the largest premapped command reaching
`min(device MDTS, 8 MiB)` — e.g. **8 MiB (64× the 128 KiB clamp)** on a large-MDTS
drive — while the ordinary path stays pinned at `max_hw_sectors_kb = 128 KiB`.
That is the large-MDTS proof — on a real *or* QEMU-emulated `mdts >= 7` device;
our own 128 KiB-clamped drives cannot produce it.

*(A sustained throughput/CPU comparison at large command sizes is a separate,
heavier arm — not in this script. This one establishes the command-size ceiling
against the device's real MDTS, whether that device is physical or QEMU-emulated.)*

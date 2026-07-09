# kvio × blk_iobuf_pool — test setup and results

This documents the `run_kvio.sh` arm of the `iobuf_bench` workflow: whether the
kvio KV-cache-offload storage workload engages the per-queue `blk_iobuf_pool`,
and a matched A/B once it can.

**How kvio works, its dependencies, and how to run it:** see the kvio
documentation page (dark-theme, styled after the blk_iobuf RFC page):

- <https://htmlpreview.github.io/?https://github.com/SamsungDS/ebpf-syscall/blob/ebpf-fixes/docs/kvio.html>

kvio itself (the LMCache `raw_block` engine + the real-model-geometry generator
+ the op-38 opt-in described below) lives on the LMCache `kvio` branch:

- <https://github.com/mcgrof/LMCache/tree/kvio>
- generator: `examples/kv_cache_offload_io/run_kv_offload_io.py`
- pool opt-in: `examples/kv_cache_offload_io/iobuf_pool_bench.py`

## Test setup

| | |
|---|---|
| Host | libvirt guest `debian13` on `prune` (never monster) |
| Kernel | `7.2.0-rc1+` (blk-iobuf-pool tree, nvme commit `e9676b3`) |
| Pool knob | `nvme_core.iobuf_pool` = `0/1/2` (off/auto/force), runtime-writable |
| Global sizing | `blk_iobuf.iobuf_pool_{max_order=5,min_folios=16,prefer_io_opt}` |
| Devices | 4× virtio-NVMe: `nvme0n1` 512 b LBS; `nvme1..3n1` **16 KiB LBS** |
| Pool state | 16 KiB-LBS namespaces: `pool_enabled=1 order=2 reasons=0x1 (IO_MIN)`; the 512 b namespace gets no pool |
| Workload | LMCache `raw_block`, io_uring_cmd NVMe passthrough on `/dev/ng1n1`, Llama-3.1-8B geometry, 256-token chunks (32 MiB KV blocks), 16 KiB block-align |
| kvio env | venv with torch (CPU) + LMCache `kvio` branch + the rust `raw_block` ext; run with `LMCACHE_TRACK_USAGE=false` |

kvio is self-contained in the guest (venv + LMCache source + prebuilt ext); it
does **not** require kdevops inside the guest.

## What was done, and what we found

1. **kvio never engages the pool.** Running the real io_uring_cmd passthrough
   workload against the pool-live 16 KiB-LBS drive leaves `iobuf_pool_allocs`
   at **0** — under `nvme_core.iobuf_pool` = off, auto, **and** force alike.

2. **`force` is not unconditional.** On the 512 b / `io_opt=0` namespace,
   `nvme_core.iobuf_pool=2` + `blk_iobuf.iobuf_pool_prefer_io_opt=1` still
   created **no** pool (`pool_enabled=0`, `reasons=0x0`): `blk_iobuf_choose_order()`
   returns 0 with no geometry reason, and `force` only warns on a *failed*
   creation — it does not bypass the zero-order decision. Pool creation on a
   regular drive needs a reason to fire (IO_MIN on LBS, or IO_OPT with
   `prefer_io_opt` and `optimal_io_size >= 4096`).

3. **Root cause (source + live ftrace).** The LMCache `raw_block` ext submits
   `IORING_OP_URING_CMD` (NVMe passthrough) with an inline, page-aligned *user*
   buffer, which the kernel maps zero-copy. A live trace of a run: 1028× URING
   submits, one `io_uring_register` = opcode 4 (EVENTFD); **never** opcode 38
   (`IORING_REGISTER_BUFFERS_ALLOC_FOR_FILE`), the only io_uring path that pulls
   kernel-allocated folios from `blk_iobuf_pool`. Hence `allocs=0`.

4. **Opt-in + matched A/B.** Added `iobuf_pool_bench()` to the ext: on a *block*
   device (op 38 requires `S_ISBLK`, not the `/dev/ng` char device), register a
   fixed buffer and loop `ReadFixed`/`WriteFixed` against it, either from
   pool-backed op-38 folios (arm B) or from an ordinary user buffer registered
   via op 0 (arm A) — identical otherwise, so the pool is the only variable. The
   op-38 folios are kernel-owned (no userspace mapping), which is fine because
   kvio is content-free (storage geometry is independent of tensor values).

## Results (16 KiB-LBS NVMe, pool order 2, 128 KiB buffer, 128× ReadFixed)

| arm | buffer source | `iobuf_pool_allocs` delta | throughput |
|---|---|---|---|
| **A** pool-OFF | user buffer (op 0) | **+0** | ~23k ops/s |
| **B** pool-ON | op-38 pool folios | **+8** (128 KiB ÷ 16 KiB) | ~27k ops/s |

- **Reproducible:** A never touches the pool (`+0`); B pulls exactly 8 folios
  (`+8`). That engagement signal is stable.
- **Noisy:** B is faster in every run, but the magnitude swings (~1.2–2× across
  runs) — expected on an *emulated* QEMU NVMe with caching and a serial QD-1
  loop. Do not cite a fixed speedup from this setup; a trustworthy number needs
  a real bare-metal LBS NVMe (the plausible mechanism is large folios → fewer
  bio segments).

## Real bare-metal 4 KiB NVMe (`force_order`, the operator knob)

The QEMU result above needed a 16 KiB-LBS device to get a pool at all (IO_MIN
fired). The more interesting case is a **plain 4 KiB-IU datacenter NVMe** that
advertises *nothing* optimal — the drives everyone actually has — where we still
want the io_uring command to pull deterministic large folios. On such a drive
`blk_iobuf_choose_order()` legitimately returns 0: `io_min = 4096` (not
`> PAGE_SIZE`), `io_opt = 0` (the device advertises **no** optimal I/O size —
`0` means *unspecified*, not 4096; nvme only sets `io_opt` when `id->nows` is
non-zero), and the segment-geometry reason lands at order 0 too. Neither `auto`
nor `force` creates a pool, because `force` only warns on a *failed* creation —
it does not override a legitimate order-0 decision.

The fix is an explicit operator knob — the same shape Linux already uses for
`max_sectors_kb`, `read_ahead_kb`, `nr_requests`: **`blk_iobuf.iobuf_pool_force_order`**
(`-1` = auto/geometry, `0` = disabled, `>0` = force that order regardless of
geometry). It sets `reasons = 0x8 (FORCE)` so the origin is auditable, and is
clamped to `iobuf_pool_max_order`. This does **not** fake `io_min`/`io_opt`
(those are visible to the FS and stacking drivers and get rounded/cleared by
`blk-settings.c`) — it only sizes the pool.

Validated on a **Latitude `m4-metal-small`** bare-metal box (real 960 GB Micron
`MTFDKCC960TGP`, reformatted to a 4 KiB LBA, unmounted spare namespace), booting
the `blk-iobuf-pool-v2` kernel with `nvme_core.iobuf_pool=1
blk_iobuf.iobuf_pool_force_order=3`. On a drive with `io_min=4096 io_opt=0` the
pool comes up `pool_enabled=1 order=3 folio_size=32768 reasons=0x8 (FORCE)` —
32 KiB folios on a drive that asked for none. The A/B here uses `iobuf_ab.c` (a
self-contained liburing program — no rust/Python/LMCache stack needed on the
target):

```
gcc -O2 -o iobuf_ab iobuf_ab.c -luring
./iobuf_ab /dev/nvme1n1 <buffer_size> <nr_ops> <0=user-buf | 1=pool>
```

| arm | buffer source | `iobuf_pool_allocs` delta | throughput (128 KiB × 256, QD1) |
|---|---|---|---|
| **A** pool-OFF | user buffer (op 0) | **+0** | 22,259 ops/s |
| **B** pool-ON | op-38 pool folios | **+4** (128 KiB ÷ 32 KiB) | 21,922 ops/s |

The engagement is **exactly deterministic** — `allocs` delta = `buffer_size ÷
folio_size` on every size:

| buffer | expected folios | `allocs` delta |
|---|---|---|
| 32 KiB | 1 | 1 |
| 64 KiB | 2 | 2 |
| 128 KiB | 4 | 4 |
| 256 KiB | 8 | 8 |
| 512 KiB | 16 | 16 |

Throughput is **flat** between the arms (~22k ops/s either way) — as expected: at
QD1 with 128 KiB reads on a datacenter NVMe the path is device-bound, and the
buffer's *origin* doesn't change bandwidth. The value `force_order` delivers is
not a QD1 speedup but **deterministic kernel-side large-folio provisioning** on a
drive that advertises nothing: every registered buffer is backed by contiguous
order-3 folios from a pre-sized pool, so the passthrough/DIO path builds fewer,
larger bio segments instead of depending on whatever the page allocator hands
back. That determinism — "more large IOs available, predictably" — is the goal,
independent of device geometry.

## Bottom line

For the workload LMCache actually issues today (aligned io_uring_cmd
passthrough), `blk_iobuf_pool` is a no-op regardless of the module knob — the
data never bounces and never registers pool buffers. The pool's beneficiaries
are the op-38 registered-buffer path (the opt-in here), the iomap DIO bounce
(`run_iomap.sh`), and misaligned/vectored maps — not this one. On a plain 4 KiB
drive the pool only exists at all once the operator asks for it via
`iobuf_pool_force_order`; once it does, the op-38 path pulls large folios from it
deterministically (proven on real Micron bare metal above).

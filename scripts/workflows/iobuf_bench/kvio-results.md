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

## Bottom line

For the workload LMCache actually issues today (aligned io_uring_cmd
passthrough), `blk_iobuf_pool` is a no-op regardless of the module knob — the
data never bounces and never registers pool buffers. The pool's beneficiaries
are the op-38 registered-buffer path (the opt-in here), the iomap DIO bounce
(`run_iomap.sh`), and misaligned/vectored maps — not this one.

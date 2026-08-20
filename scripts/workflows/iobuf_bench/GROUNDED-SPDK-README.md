# Grounded SPDK-vs-Linux comparisons

Two comparisons that reflect how SPDK is actually used, not the
`spdk_nvme_perf -o 2M` microbench:

## 1. NVMe-oF/TCP target: SPDK nvmf_tgt vs kernel nvmet (two boxes)

`two_box.sh` drives the clean version from a host with SSH to both a **target**
box (exports the drives) and an **initiator** box (runs fio over the wire). The
target box runs *only* the target, so its whole-system CPU is the pure target
cost. Sweeps SPDK reactor count {2,4,8} vs kernel nvmet. Helpers:
`nvmet_setup.sh` / `nvmet_teardown.sh` (kernel target, `LISTEN_IP=<ip>`),
`spdk_nvmf_setup.sh` (`REACTOR_MASK=0x3 LISTEN_IP=<ip>`). Edit the two SSH
wrappers + IPs/BDFs at the top of `two_box.sh`. `plot_two_box.py` makes the
figure. NOTE: do NOT run target+initiator on one host over loopback — SPDK
reactors are pinned while nvmet floats all cores (non-overlapping IOPS) and the
loopback initiator drowns the target CPU signal. Two boxes is mandatory.

## 2. Local crossover: SPDK vs the kernel's own poll path

`frontier_local.sh` compares `spdk_nvme_perf` (VFIO poller) against the kernel's
own `io_uring`+IOPOLL (`--hipri`) path across 4K→2M at 1/2/4 pinned cores.
Needs `nvme.poll_queues>=cores` on the cmdline (one reboot, stock kernel).
`plot_frontier.py` renders GB/s-per-core vs block size — SPDK saturates the
drives with one core at every size; the kernel poll path converges to it only at
2M. Result and full writeup: `knlp-key-results/spdk-vs-linux-grounded-20260819`.

## 3. The premap arm (kernel's large-object win, on the crossover axis)

`premap_frontier.sh` adds the `io_uring_cmd --premap` (map-once) arm to the
local crossover, driven by the smoke tool at QD ≤ pool folios. Run it on the
premap kernel (pool + clamp lift), then merge its CSV with `frontier_local.sh`'s
and render with `plot_crossover3.py`. Result: premap crosses above SPDK around
40–64K block size and runs ~6× past it at 512K (interrupt-driven vs SPDK's
mandatory busy-poll when the drive is bandwidth-bound). SPDK still wins 4–16K.

#!/usr/bin/env python3
"""3-arm local crossover: SPDK vs kernel poll (io_uring IOPOLL) vs kernel premap
(io_uring_cmd map-once). GB/s per core at 1 pinned core vs block size. Reads one
or more CSVs with columns arm,bs,cores,iops,bw_mbps,p99_us,busy_cores."""
import csv, sys
from collections import defaultdict
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

outdir = sys.argv[1]
csvs = sys.argv[2:]
rows = defaultdict(dict)  # arm -> bs -> gbps_per_core (at 1 core)
for path in csvs:
    for r in csv.DictReader(open(path)):
        if r["cores"] != "1": continue
        bc = float(r["busy_cores"])
        if bc <= 0: continue
        rows[r["arm"]][r["bs"]] = (float(r["bw_mbps"])/1024) / bc
BSORD = ["4k","16k","128k","512k"]; BSX = {"4k":4,"16k":16,"128k":128,"512k":512}
STYLE = {
    "spdk_nvme_perf": ("SPDK spdk_nvme_perf (VFIO poller)",       "#d62728", "^"),
    "kernel_iopoll":  ("kernel io_uring + IOPOLL (block, poll)",  "#1f77b4", "o"),
    "kernel_premap":  ("kernel io_uring_cmd + premap (map-once)", "#2ca02c", "s"),
}
fig, ax = plt.subplots(figsize=(9, 5.6))
for arm, (lab, c, m) in STYLE.items():
    xs = [BSX[b] for b in BSORD if b in rows.get(arm, {})]
    ys = [rows[arm][b] for b in BSORD if b in rows.get(arm, {})]
    if not xs: continue
    ax.plot(xs, ys, marker=m, color=c, lw=2.2, ms=10, label=lab)
    for b in BSORD:
        if b in rows.get(arm, {}):
            ax.annotate(f"{rows[arm][b]:.0f}", (BSX[b], rows[arm][b]),
                        textcoords="offset points", xytext=(5,7), fontsize=8, color=c)
ax.set_xscale("log", base=2); ax.set_yscale("log")
ax.set_xticks([BSX[b] for b in BSORD]); ax.set_xticklabels(BSORD)
ax.set_xlabel("block size (random read)")
ax.set_ylabel("GB/s per CPU core (1 core, log scale)")
ax.set_title("Local crossover, all three paths on one premap kernel\n"
             "SPDK wins small IO; premap crosses far above everyone at large objects")
ax.grid(True, which="both", alpha=0.3); ax.legend(loc="upper left", fontsize=9)
fig.tight_layout()
fig.savefig(f"{outdir}/fig_crossover_3arm.png", dpi=130)
print("wrote fig_crossover_3arm.png")
for arm in rows:
    print(arm, {b: round(rows[arm][b],1) for b in BSORD if b in rows[arm]})

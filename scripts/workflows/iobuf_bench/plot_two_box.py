#!/usr/bin/env python3
"""Two-box NVMe-oF target comparison: target-box CPU cores vs delivered load,
SPDK nvmf (reactor sweep) vs kernel nvmet. Lower cores at the same load = more
efficient target. One panel per block size."""
import csv, sys
from collections import defaultdict
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

csv_path = sys.argv[1] if len(sys.argv) > 1 else "two_box.csv"
outdir = sys.argv[2] if len(sys.argv) > 2 else "."
rows = defaultdict(list)  # (bs) -> list of (arm,iops,bw,p99,cores)
for r in csv.DictReader(open(csv_path)):
    rows[r["bs"]].append((r["arm"], float(r["iops"]), float(r["bw_mbps"]),
                          float(r["p99_us"]), float(r["tgt_cores"])))

STYLE = {
    "nvmet":   ("kernel nvmet",     "#d62728", "o"),
    "spdk_r2": ("SPDK nvmf 2 react","#1f77b4", "s"),
    "spdk_r4": ("SPDK nvmf 4 react","#2ca02c", "^"),
    "spdk_r8": ("SPDK nvmf 8 react","#9467bd", "D"),
}
bses = list(rows.keys())
fig, axes = plt.subplots(1, len(bses), figsize=(6.5*len(bses), 5.2), squeeze=False)
for ax, bs in zip(axes[0], bses):
    use_bw = bs in ("128k", "2m")
    per_arm = defaultdict(list)
    for arm, iops, bw, p99, cores in rows[bs]:
        x = bw/1024 if use_bw else iops/1000  # GB/s or kIOPS
        per_arm[arm].append((x, cores, p99))
    for arm, (lab, col, mk) in STYLE.items():
        pts = sorted(per_arm.get(arm, []))
        if not pts: continue
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        ax.plot(xs, ys, marker=mk, color=col, lw=1.8, ms=9, label=lab)
    ax.set_xlabel(("delivered GB/s" if use_bw else "delivered kIOPS"))
    ax.set_ylabel("target-box CPU cores")
    ax.set_title(f"{bs} random read")
    ax.grid(True, alpha=0.3); ax.legend(fontsize=8)
fig.suptitle("NVMe-oF/TCP target efficiency (two boxes): CPU to serve the load\n"
             "target-box CPU measured in isolation — lower is better", fontsize=12)
fig.tight_layout()
fig.savefig(f"{outdir}/fig_two_box_target.png", dpi=130)
print("wrote fig_two_box_target.png")
for bs in rows:
    print(f"--- {bs} ---")
    for arm, iops, bw, p99, cores in sorted(rows[bs], key=lambda r:(r[0],r[1])):
        print(f"  {arm:9} iops={iops:>8.0f} bw={bw:>6.0f}MB/s p99={p99:>6.0f}us tgt_cores={cores:.2f}")

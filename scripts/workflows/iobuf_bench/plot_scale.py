#!/usr/bin/env python3
"""Plot GB/s-per-core and CPU-cost scaling vs NVMe drive count from scale.csv."""
import csv, sys, statistics as st
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

csv_path = sys.argv[1] if len(sys.argv) > 1 else "scale.csv"
outdir = sys.argv[2] if len(sys.argv) > 2 else "."

rows = defaultdict(lambda: defaultdict(list))  # arm -> drives -> list of dict
with open(csv_path) as f:
    for r in csv.DictReader(f):
        try:
            n = int(r["drives"])
            rows[r["arm"]][n].append({
                "gbps": float(r["gbps"]),
                "cores": float(r["busy_cores"]),
                "gpc": float(r["gbps_per_core"]),
            })
        except (ValueError, KeyError):
            continue  # skip BIND_FAIL rows

LABEL = {
    "stock_iouring_cmd": ("stock io_uring_cmd\n(hugepage fixed bufs)", "#1f77b4", "o"),
    "premap_map_once":   ("premap (map-once)",                          "#2ca02c", "s"),
    "spdk_nvme_perf":    ("SPDK nvme_perf\n(VFIO poller)",              "#d62728", "^"),
}
def agg(lst, key):
    vals = [d[key] for d in lst]
    return (st.mean(vals), (st.stdev(vals) if len(vals) > 1 else 0.0))

# ---- Figure 1: GB/s per core vs drive count (log y) ----
fig, ax = plt.subplots(figsize=(8, 5.2))
for arm, (lab, col, mk) in LABEL.items():
    if arm not in rows: continue
    xs = sorted(rows[arm])
    ys = [agg(rows[arm][n], "gpc")[0] for n in xs]
    es = [agg(rows[arm][n], "gpc")[1] for n in xs]
    ax.errorbar(xs, ys, yerr=es, marker=mk, color=col, lw=2, ms=9, capsize=4, label=lab)
    for x, y in zip(xs, ys):
        ax.annotate(f"{y:.0f}", (x, y), textcoords="offset points", xytext=(6, 6),
                    fontsize=9, color=col, fontweight="bold")
ax.set_yscale("log")
ax.set_xticks(sorted({n for a in rows for n in rows[a]}))
ax.set_xlabel("NVMe drives (concurrent)")
ax.set_ylabel("GB/s per CPU core  (log scale, higher = more efficient)")
ax.set_title("Storage efficiency vs drive count: kernel io_uring_cmd vs SPDK\n"
             "2 MiB reads, QD64, whole-system CPU accounting")
ax.grid(True, which="both", alpha=0.3)
ax.legend(loc="center right", fontsize=9)
fig.tight_layout()
fig.savefig(f"{outdir}/fig_scale_gbps_per_core.png", dpi=130)
print("wrote fig_scale_gbps_per_core.png")

# ---- Figure 2: CPU cores consumed vs drive count (the honest cost) ----
fig, ax = plt.subplots(figsize=(8, 5.2))
for arm, (lab, col, mk) in LABEL.items():
    if arm not in rows: continue
    xs = sorted(rows[arm])
    ys = [agg(rows[arm][n], "cores")[0] for n in xs]
    es = [agg(rows[arm][n], "cores")[1] for n in xs]
    ax.errorbar(xs, ys, yerr=es, marker=mk, color=col, lw=2, ms=9, capsize=4, label=lab)
    for x, y in zip(xs, ys):
        ax.annotate(f"{y:.2f}", (x, y), textcoords="offset points", xytext=(6, 6),
                    fontsize=9, color=col, fontweight="bold")
ax.set_xticks(sorted({n for a in rows for n in rows[a]}))
ax.set_xlabel("NVMe drives (concurrent)")
ax.set_ylabel("CPU cores consumed to saturate the drives")
ax.set_title("CPU cost to saturate storage vs drive count\n"
             "kernel scales with load; SPDK pays a poller core per drive")
ax.grid(True, alpha=0.3)
ax.legend(loc="upper left", fontsize=9)
fig.tight_layout()
fig.savefig(f"{outdir}/fig_scale_cpu_cost.png", dpi=130)
print("wrote fig_scale_cpu_cost.png")

# ---- text summary ----
print("\narm,drives,gbps_mean,cores_mean,gbps_per_core_mean")
for arm in rows:
    for n in sorted(rows[arm]):
        g = agg(rows[arm][n], "gbps")[0]
        c = agg(rows[arm][n], "cores")[0]
        p = agg(rows[arm][n], "gpc")[0]
        print(f"{arm},{n},{g:.2f},{c:.3f},{p:.0f}")

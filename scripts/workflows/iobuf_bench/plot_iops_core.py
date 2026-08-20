#!/usr/bin/env python3
"""Analyze results.jsonl from iops_core_bench: median across reps, 8 plots, the
operating-point table, and premap win/tie/loss ranges vs stock and SPDK."""
import json, sys, statistics as st
from collections import defaultdict
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

path = sys.argv[1]; outdir = sys.argv[2] if len(sys.argv) > 2 else "."
runs = defaultdict(list)   # (impl,size,qd) -> [row,...]
for line in open(path):
    try: r = json.loads(line)
    except Exception: continue
    if r.get("error"): continue
    runs[(r["impl"], r["size"], r["qd"])].append(r)

def med(impl, size, qd, key):
    rows = runs.get((impl, size, qd), [])
    vals = [x[key] for x in rows if key in x and x[key] is not None]
    return st.median(vals) if vals else None

IMPLS = ["stock", "premap", "spdk"]
COL = {"stock": "#1f77b4", "premap": "#2ca02c", "spdk": "#d62728",
       "stock_irq": "#1f77b4", "premap_irq": "#2ca02c"}
LAB = {"stock": "stock io_uring_cmd (fixed, poll)", "premap": "premap (map-once, poll)",
       "spdk": "SPDK nvme_perf",
       "stock_irq": "stock (fixed, interrupt)", "premap_irq": "premap (map-once, interrupt)"}
sizes = sorted({k[1] for k in runs}); qds = sorted({k[2] for k in runs})
def kib(s): return f"{s//1024}K" if s>=1024 else f"{s}B"

# ---- plots 3,4,5,6: vs I/O size, one line per impl (at a representative QD each) ----
def line_vs_size(key, ylabel, fname, qd_pick, logy=False, title="", impls=None):
    fig, ax = plt.subplots(figsize=(8,5))
    for impl in (impls or IMPLS):
        xs=[s for s in sizes if med(impl,s,qd_pick,key) is not None]
        ys=[med(impl,s,qd_pick,key) for s in xs]
        if xs: ax.plot(xs, ys, marker="o", color=COL[impl], lw=2, label=LAB[impl])
    ax.set_xscale("log", base=2); ax.set_xticks(sizes); ax.set_xticklabels([kib(s) for s in sizes])
    if logy: ax.set_yscale("log")
    ax.set_xlabel("I/O size"); ax.set_ylabel(ylabel)
    ax.set_title(title or f"{ylabel} vs I/O size (QD{qd_pick})")
    ax.grid(True, which="both", alpha=0.3); ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(f"{outdir}/{fname}", dpi=130); print("wrote", fname)

qd_lo = 32 if 32 in qds else qds[-1]
# cycles/IO + instr/IO: interrupt arms (real per-IO work, no poll-spin masking)
line_vs_size("cycles_per_io","cycles / I/O","fig4_cycles_per_io.png", qd_lo,
             title=f"cycles/I/O vs I/O size (interrupt mode, QD{qd_lo}) — the CPU-work metric",
             impls=["stock_irq","premap_irq"])
line_vs_size("instr_per_io","instructions / I/O","fig5_instr_per_io.png", qd_lo,
             title=f"instructions/I/O vs I/O size (interrupt, QD{qd_lo})",
             impls=["stock_irq","premap_irq"])
# IOPS/core + p99: polled arms + SPDK
line_vs_size("iops_per_core","IOPS per core","fig3_iops_per_core.png", qd_lo, logy=True)
line_vs_size("p99_us","p99 latency (us)","fig6_p99.png", qd_lo, logy=True)

# ---- plot 1: IOPS vs size for every QD (premap only, faceted as lines) ----
fig, ax = plt.subplots(figsize=(8,5))
for qd in qds:
    xs=[s for s in sizes if med("premap",s,qd,"iops") is not None]
    ys=[med("premap",s,qd,"iops") for s in xs]
    if xs: ax.plot(xs, ys, marker=".", lw=1.5, label=f"QD{qd}")
ax.set_xscale("log",base=2); ax.set_yscale("log"); ax.set_xticks(sizes); ax.set_xticklabels([kib(s) for s in sizes])
ax.set_xlabel("I/O size"); ax.set_ylabel("IOPS (premap)"); ax.set_title("premap IOPS vs I/O size, per QD")
ax.grid(True,which="both",alpha=0.3); ax.legend(fontsize=8,ncol=2)
fig.tight_layout(); fig.savefig(f"{outdir}/fig1_iops_vs_size.png",dpi=130); print("wrote fig1")

# ---- plot 2: IOPS vs QD for every size (premap) ----
fig, ax = plt.subplots(figsize=(8,5))
for s in sizes:
    xs=[q for q in qds if med("premap",s,q,"iops") is not None]
    ys=[med("premap",s,q,"iops") for q in xs]
    if xs: ax.plot(xs, ys, marker=".", lw=1.5, label=kib(s))
ax.set_xscale("log",base=2); ax.set_yscale("log"); ax.set_xticks(qds); ax.set_xticklabels(qds)
ax.set_xlabel("queue depth"); ax.set_ylabel("IOPS (premap)"); ax.set_title("premap IOPS vs QD, per I/O size")
ax.grid(True,which="both",alpha=0.3); ax.legend(fontsize=8,ncol=2)
fig.tight_layout(); fig.savefig(f"{outdir}/fig2_iops_vs_qd.png",dpi=130); print("wrote fig2")

# ---- plots 7,8: ratio with 1.0x parity, vs size, per QD ----
def ratio_plot(num,den,fname,title):
    fig, ax = plt.subplots(figsize=(8,5))
    for qd in qds:
        xs=[]; ys=[]
        for s in sizes:
            a=med(num,s,qd,"iops"); b=med(den,s,qd,"iops")
            if a and b: xs.append(s); ys.append(a/b)
        if xs: ax.plot(xs, ys, marker="o", lw=1.6, label=f"QD{qd}")
    ax.axhline(1.0, color="k", ls="--", lw=1.2)
    ax.set_xscale("log",base=2); ax.set_xticks(sizes); ax.set_xticklabels([kib(s) for s in sizes])
    ax.set_xlabel("I/O size"); ax.set_ylabel(f"{num} IOPS / {den} IOPS"); ax.set_title(title)
    ax.grid(True,which="both",alpha=0.3); ax.legend(fontsize=8,ncol=2)
    fig.tight_layout(); fig.savefig(f"{outdir}/{fname}",dpi=130); print("wrote",fname)
ratio_plot("premap","stock","fig7_premap_over_stock.png","premap speedup over stock (1.0x = parity)")
ratio_plot("premap","spdk","fig8_premap_over_spdk.png","premap vs SPDK (>1 = premap wins, 1.0x = parity)")

# ---- operating-point table + win/tie/loss ----
tbl="size,qd,stock_iops,premap_iops,spdk_iops,premap/stock,premap/spdk,stock_cyc,premap_cyc,spdk_cyc,p99_stock,p99_premap,p99_spdk\n"
wins=[]; ties=[]; losses=[]
for s in sizes:
    for qd in qds:
        si=med("stock",s,qd,"iops"); pi=med("premap",s,qd,"iops"); ki=med("spdk",s,qd,"iops")
        sc=med("stock",s,qd,"cycles_per_io"); pc=med("premap",s,qd,"cycles_per_io"); kc=med("spdk",s,qd,"cycles_per_io")
        ps=med("stock",s,qd,"p99_us"); pp=med("premap",s,qd,"p99_us"); pk=med("spdk",s,qd,"p99_us")
        rps=(pi/si if si and pi else None); rpk=(pi/ki if ki and pi else None)
        tbl+=f"{kib(s)},{qd},{si or ''},{pi or ''},{ki or ''},{round(rps,3) if rps else ''},{round(rpk,3) if rpk else ''},{sc or ''},{pc or ''},{kc or ''},{ps or ''},{pp or ''},{pk or ''}\n"
        if rpk is not None:
            tol = 1.03
            if rpk >= tol: wins.append((kib(s),qd,round(rpk,3),pp,pk))
            elif rpk >= 1/tol: ties.append((kib(s),qd,round(rpk,3),pp,pk))
            else: losses.append((kib(s),qd,round(rpk,3),pp,pk))
open(f"{outdir}/operating_points.csv","w").write(tbl)
print("\n=== premap vs SPDK: WINS (>3%) ==="); [print(f"  {w[0]} QD{w[1]}: {w[2]}x IOPS  p99 {w[3]} vs {w[4]}us") for w in wins] or print("  none")
print("=== TIES (within 3%) ==="); [print(f"  {t[0]} QD{t[1]}: {t[2]}x") for t in ties] or print("  none")
print("=== LOSSES ==="); [print(f"  {l[0]} QD{l[1]}: {l[2]}x") for l in losses[:12]]
print(f"\nwrote operating_points.csv ({len(wins)} wins, {len(ties)} ties, {len(losses)} losses)")

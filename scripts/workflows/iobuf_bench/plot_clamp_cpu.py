#!/usr/bin/env python3
"""Plot the dma_opt clamp-lift CPU-cost results.

Reads two CSVs produced by the benchmarks and writes three PNGs:

  sweep.csv : drive,size_kb,cmds_per_gib,mcyc_per_gib,buffer
  ace.csv   : arm,cyc_per_cmd,note

  fig1_cpu_vs_cmdsize.png   host CPU per GiB vs command size (both drives)
  fig2_premap_vs_huge.png   per-command CPU: page vs huge page vs premap
  fig3_mdts_projection.png  projected CPU vs MDTS (diminishing returns)

Usage: plot_clamp_cpu.py [sweep.csv] [ace.csv] [output_dir]
CPU is reported as measured (million CPU cycles per GiB) and, on a second
axis, as milliseconds of one CPU core per GiB assuming a 3.0 GHz core.
"""
import csv, sys, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

GHZ = 3.0                      # EPYC 9124 base clock (approx) for cyc->time
# 1 Mcyc = 1e6 cycles; at GHZ*1e9 cyc/s that is (1e6/(GHZ*1e9))*1e3 ms = 1/GHZ ms.
def mcyc_to_ms(m): return m / GHZ              # Mcyc/GiB -> ms-of-one-core/GiB
def kcyc_to_us(k): return k / GHZ              # thousand-cyc/cmd -> µs/cmd

# colourblind-safe
C = {"PM9A3": "#4E79A7", "Micron": "#E15759", "huge": "#F28E2B",
     "premap": "#59A14F", "page": "#B0A9A0", "fit": "#4E79A7", "floor": "#9C755F"}
plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.25,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "figure.dpi": 150})

def kb_label(kb):
    return f"{kb} KiB" if kb < 1024 else f"{kb//1024} MiB"

def load_sweep(p):
    d = {}
    for r in csv.DictReader(open(p)):
        d.setdefault(r["drive"], []).append(
            (int(r["size_kb"]), float(r["mcyc_per_gib"]), r["buffer"]))
    for k in d: d[k].sort()
    return d

def fig1(sweep, out):
    fig, ax = plt.subplots(figsize=(8, 5))
    for drive, pts in sweep.items():
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        ax.plot(xs, ys, "-o", color=C.get(drive, "#555"), lw=2.2, ms=7, label=drive)
        for x, y, buf in pts:
            if buf == "huge":
                ax.scatter([x], [y], s=140, facecolors="none",
                           edgecolors=C.get(drive), lw=2, zorder=5)
    ax.set_xscale("log", base=2)
    ax.set_xticks([128, 256, 512, 1024, 2048, 4096])
    ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: kb_label(int(v))))
    ax.set_xlabel("NVMe command size (bytes per command)")
    ax.set_ylabel("Host CPU per GiB moved  (million CPU cycles)")
    ax.set_title("Host CPU cost falls as commands get larger\n"
                 "(same 4 GB/s read rate; circled points use a contiguous huge-page buffer)")
    ax.set_ylim(0, None)
    ax2 = ax.twinx(); ax2.set_ylim(*[mcyc_to_ms(v) for v in ax.get_ylim()])
    ax2.set_ylabel(f"≈ ms of one CPU core per GiB  (at {GHZ:.0f} GHz)")
    ax2.grid(False)
    ax.annotate("128 KiB clamp\n(the ceiling this work lifts)",
                xy=(128, sweep[list(sweep)[0]][0][1]), xytext=(150, 560),
                fontsize=9, color="#333")
    ax.annotate("page-granular → contiguous\n(huge page): CPU collapses",
                xy=(1500, 120), xytext=(520, 300), fontsize=9, color="#333",
                arrowprops=dict(arrowstyle="->", color="#777"))
    ax.legend(title="drive", frameon=False)
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig1_cpu_vs_cmdsize.png"))
    plt.close(fig)

def fig2(ace, out):
    fig, ax = plt.subplots(figsize=(7, 5))
    order = ["page-granular", "huge page", "premap"]
    vals = {a["arm"]: a for a in ace}
    xs, ys, cols, labels = [], [], [], []
    for i, name in enumerate(order):
        a = vals.get(name, {})
        v = a.get("cyc_per_cmd", "")
        y = float(v)/1000.0 if v else 0.0
        xs.append(i); ys.append(y)
        cols.append(C["page"] if "page-gran" in name else
                    C["huge"] if "huge" in name else C["premap"])
        labels.append(name)
    bars = ax.bar(xs, ys, color=cols, width=0.6)
    for i, name in enumerate(order):
        v = vals.get(name, {}).get("cyc_per_cmd", "")
        if not v:
            ax.text(i, 3, "cannot issue\n(errors)", ha="center", va="bottom",
                    fontsize=10, color="#B00", fontweight="bold")
            ax.bar([i], [max(ys)], color="none", edgecolor=C["page"], hatch="//",
                   lw=1.2, width=0.6)
        else:
            ax.text(i, ys[i]+0.6, f"{ys[i]:.1f}k cyc\n≈{kcyc_to_us(ys[i]):.1f} µs",
                    ha="center", va="bottom", fontsize=9)
    # -23% annotation between huge and premap
    if vals.get("huge page", {}).get("cyc_per_cmd") and vals.get("premap", {}).get("cyc_per_cmd"):
        h = float(vals["huge page"]["cyc_per_cmd"])/1000
        p = float(vals["premap"]["cyc_per_cmd"])/1000
        ax.annotate(f"−{(1-p/h)*100:.0f}%  (map-once)", xy=(2, p), xytext=(1.35, h+ (max(ys)*0.02)),
                    fontsize=11, color=C["premap"], fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color=C["premap"]))
    ax.set_xticks(xs); ax.set_xticklabels(
        ["page-granular\nuser buffer", "huge-page\nuser buffer", "premap\npool buffer"])
    ax.set_ylabel("CPU per command  (thousand CPU cycles)")
    ax.set_title("Per-command CPU at a 2 MiB command (NVMe passthrough)\n"
                 "all contiguous arms move the same 6.7 GB/s")
    ax.set_ylim(0, max(ys)*1.25)
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig2_premap_vs_huge.png"))
    plt.close(fig)

def fig3(sweep, out):
    # fit CPU/GiB = A*(cmds/GiB) + B on the CONTIGUOUS (huge) points of the
    # widest-MDTS drive, then project to large MDTS.
    pts = [(1073741824/(kb*1024), y) for d in sweep for kb, y, b in sweep[d] if b == "huge"]
    pts.sort()
    # least squares on (cmds_per_gib, mcyc_per_gib)
    n = len(pts); sx = sum(p[0] for p in pts); sy = sum(p[1] for p in pts)
    sxx = sum(p[0]**2 for p in pts); sxy = sum(p[0]*p[1] for p in pts)
    A = (n*sxy - sx*sy)/(n*sxx - sx*sx) if n*sxx-sx*sx else 0
    B = (sy - A*sx)/n
    mdts_mib = [2, 4, 8, 16, 32, 64, 128]
    xs = mdts_mib
    ys = [A*(1024/m) + B for m in mdts_mib]   # cmds/GiB = 1024 MiB / m
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(xs, ys, "-o", color=C["fit"], lw=2.2, ms=6,
            label=f"projected  (fit: {A:.3f}·cmds/GiB + {B:.0f})")
    # mark measured points
    meas = [(int(kb/1024), y) for d in sweep for kb, y, b in sweep[d]
            if b == "huge" and kb >= 2048]
    mx = [m[0] for m in meas]; my = [m[1] for m in meas]
    ax.scatter(mx, my, s=120, color=C["premap"], zorder=6, label="measured")
    ax.axhline(B, ls="--", color=C["floor"], lw=1.4)
    ax.text(80, B+3, f"floor ≈ {B:.0f} Mcyc/GiB (≈{mcyc_to_ms(B):.0f} ms/GiB)",
            color=C["floor"], fontsize=9)
    ax.set_xscale("log", base=2); ax.set_xticks(mdts_mib)
    ax.get_xaxis().set_major_formatter(FuncFormatter(lambda v, _: f"{int(v)} MiB"))
    ax.set_xlabel("Maximum command size (drive MDTS), contiguous buffer")
    ax.set_ylabel("Host CPU per GiB  (million CPU cycles)")
    ax.set_title("Beyond ~4 MiB the CPU win saturates at a floor\n"
                 "(projection from the measured 2 & 4 MiB contiguous points)")
    ax.set_ylim(0, max(ys)*1.15)
    ax2 = ax.twinx(); ax2.set_ylim(*[mcyc_to_ms(v) for v in ax.get_ylim()]); ax2.grid(False)
    ax2.set_ylabel(f"≈ ms of one CPU core per GiB  (at {GHZ:.0f} GHz)")
    ax.legend(frameon=False, loc="upper right")
    fig.tight_layout(); fig.savefig(os.path.join(out, "fig3_mdts_projection.png"))
    plt.close(fig)

if __name__ == "__main__":
    sweep_csv = sys.argv[1] if len(sys.argv) > 1 else "sweep.csv"
    ace_csv = sys.argv[2] if len(sys.argv) > 2 else "ace.csv"
    out = sys.argv[3] if len(sys.argv) > 3 else "."
    sweep = load_sweep(sweep_csv)
    ace = list(csv.DictReader(open(ace_csv)))
    fig1(sweep, out); fig2(ace, out); fig3(sweep, out)
    print("wrote fig1_cpu_vs_cmdsize.png, fig2_premap_vs_huge.png, fig3_mdts_projection.png to", out)

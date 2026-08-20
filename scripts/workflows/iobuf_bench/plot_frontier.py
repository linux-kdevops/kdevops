import csv
from collections import defaultdict
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
rows=defaultdict(dict)  # arm -> bs -> (gbps_per_core at 1 core)
BSORD=["4k","16k","128k","2m"]; BSX={"4k":4,"16k":16,"128k":128,"2m":2048}
for r in csv.DictReader(open("frontier.csv")):
    if r["cores"]!="1": continue
    gpc=(float(r["bw_mbps"])/1024)/float(r["busy_cores"])
    rows[r["arm"]][r["bs"]]=gpc
fig,ax=plt.subplots(figsize=(8.5,5.4))
STYLE={"spdk_nvme_perf":("SPDK spdk_nvme_perf (VFIO poller)","#d62728","^"),
       "kernel_iopoll":("kernel io_uring + IOPOLL (--hipri)","#1f77b4","o")}
for arm,(lab,c,m) in STYLE.items():
    xs=[BSX[b] for b in BSORD if b in rows[arm]]
    ys=[rows[arm][b] for b in BSORD if b in rows[arm]]
    ax.plot(xs,ys,marker=m,color=c,lw=2,ms=10,label=lab)
    for b in BSORD:
        if b in rows[arm]: ax.annotate(f"{rows[arm][b]:.1f}",(BSX[b],rows[arm][b]),textcoords="offset points",xytext=(5,7),fontsize=8,color=c)
# ratio annotations
for b in BSORD:
    if b in rows["spdk_nvme_perf"] and b in rows["kernel_iopoll"]:
        ratio=rows["spdk_nvme_perf"][b]/rows["kernel_iopoll"][b]
        ax.annotate(f"{ratio:.1f}x",(BSX[b],rows["kernel_iopoll"][b]),textcoords="offset points",xytext=(-8,-16),fontsize=9,color="#555",fontweight="bold")
ax.set_xscale("log",base=2); ax.set_xticks([BSX[b] for b in BSORD]); ax.set_xticklabels(BSORD)
ax.set_xlabel("block size (random read)"); ax.set_ylabel("GB/s per CPU core (1-core, pinned)")
ax.set_title("Local crossover: SPDK vs the kernel's own poll path\n"
             "SPDK dominates small IO; the gap collapses toward 2 MiB (grey = SPDK/kernel ratio)")
ax.grid(True,which="both",alpha=0.3); ax.legend(loc="upper left",fontsize=9)
fig.tight_layout(); fig.savefig("/home/mcgrof/reports/spdk-vs-linux-grounded-20260819/fig_local_crossover.png",dpi=130)
print("wrote fig_local_crossover.png")
for arm in rows:
    print(arm,{b:round(rows[arm][b],1) for b in BSORD if b in rows[arm]})

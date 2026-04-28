# fstests reports on the qsu (QEMU_SYSTEM_UNITS) backend

This document covers the report side of the fstests workflow on the
`QEMU_SYSTEM_UNITS` (qsu) bringup: where results land on disk, how
to read the HTML report, how to filter to a single host or a
specific kernel, and how to drive an A/B comparison between two
kernels with overlay charts and at-a-glance pass/fail diff.

The libvirt path's results layout (`results/last-run/<vm>/...`) is
unchanged. The new layout described here applies only when
`CONFIG_KDEVOPS_ENABLE_QEMU_SYSTEM_UNITS=y`.

# Results layout

After a `make fstests-baseline` run, the workflow tree looks like:

```
workflows/fstests/results/
├── qsu-xfs-crc/
│   ├── last-run -> 7.0.0-gABCDE              # symlink to the most recent run
│   ├── last-kernel.txt                        # text pointer (mirrors the symlink)
│   ├── 7.0.0-gABCDE/                          # one directory per kernel run
│   │   ├── monitoring/
│   │   │   ├── sysstat/{sa-current, sa-current.json}
│   │   │   ├── cpu_governor/{start,end}.json
│   │   │   └── blockdev/{start,end}.json
│   │   ├── xfs_crc/                           # the xfstests section
│   │   │   ├── result.xml                     # xunit test output
│   │   │   ├── check.{time,full,log}
│   │   │   └── generic/{042.out.bad, 042.full, 042.dmesg, ...}
│   │   ├── xunit_results.txt                  # gen_results_summary output
│   │   ├── bad_results.txt
│   │   ├── check.time.distribution
│   │   └── new_expunge_files.txt
│   ├── 7.0.0-gABCDE.tar.xz                    # long-term archive
│   ├── 7.0.0-gFGHIJ/                          # next kernel's run
│   └── 7.0.0-gFGHIJ.tar.xz
├── qsu-xfs-reflink/
│   ├── last-run -> 7.0.0-gABCDE
│   └── ...
└── fstests-report*.html                       # rendered reports
```

Each guest gets its own per-VM directory. Inside, every kernel run
has its own subdirectory (the kernel name), so two distinct kernel
builds never collide on disk and the previous run's data is
preserved when you deploy a new kernel.

The `last-run` symlink at the per-VM root resolves to the most
recently deployed kernel — tooling that just wants "the latest
data for this VM" reads `<vm>/last-run/...` and the kernel name is
transparent.

The `last-kernel.txt` text file mirrors the symlink so consumers
that don't follow symlinks can still discover the current kernel
name with `cat`.

# Unique kernel naming via `CONFIG_LOCALVERSION_AUTO=y`

`config-qsu` sets `CONFIG_LOCALVERSION_AUTO=y`, which causes
`scripts/setlocalversion` to append `-NN-gABCDE` (commits past the
latest tag plus the short HEAD SHA) and `-dirty` when the source
tree has uncommitted changes. With this, every kernel build of a
distinct source revision gets a distinct `uname -r` value, and that
value flows from the build through `vm.env`, the data-results
virtiofs share path, and finally the per-(VM, kernel) result
directory.

Two builds of the same source revision produce the same kernel
name, which means re-running fstests against them overwrites the
previous data. That is intentional for A/B testing — the second
build only matters when you change the source. If you want to
preserve runs of the exact same kernel build, copy the directory
aside before re-running.

# Generating reports

The `make fstests-report` target accepts two filters as Make
variables. Reports are written into
`workflows/fstests/results/` with filenames that encode the
filters, so multiple variants sit side-by-side without
overwriting.

## Default — every guest, each guest's most recent run

```
make fstests-report
# → workflows/fstests/results/fstests-report.html
```

Every VM's `last-run` symlink is followed; the report covers all
hosts at their most recent kernel.

## One guest only

```
make fstests-report HOST=qsu-xfs-crc
# → workflows/fstests/results/fstests-report-qsu-xfs-crc.html
```

`HOST=` is a comma-separated list (`HOST=qsu-xfs-crc,qsu-xfs-reflink`)
or a single VM name. The stat cards, chart, monitoring section and
per-section detail all narrow to the listed hosts; aggregate totals
are recomputed for the filtered set.

## A specific archived kernel

```
make fstests-report KERNEL=7.0.0-gABCDE
# → workflows/fstests/results/fstests-report-7.0.0-gABCDE.html
```

Reads `<vm>/<KERNEL>/...` directly instead of following each VM's
last-run symlink — useful for regenerating a report against an
older kernel without changing what `last-run` points at. VMs that
don't have the named kernel directory are silently skipped.

## One guest, one specific kernel

```
make fstests-report HOST=qsu-xfs-crc KERNEL=7.0.0-gABCDE
# → workflows/fstests/results/fstests-report-7.0.0-gABCDE-qsu-xfs-crc.html
```

`HOST=` and `KERNEL=` compose. The output filename suffix carries
both filters so several per-(host, kernel) reports can sit
side-by-side in `results/` without clobbering each other.

## A/B — two kernels compared (every guest)

```
make fstests-report KERNEL=7.0.0-gABCDE,7.0.0-gFGHIJ
# → workflows/fstests/results/fstests-report-7.0.0-gABCDE-vs-7.0.0-gFGHIJ.html
```

`KERNEL=` accepts two comma-separated values. The report switches
to A/B mode: regression and fix counts in the stat cards, a
per-test diff table at the top, A/B status columns in the
per-section detail, and overlay charts in the System monitoring
section (per-metric colour, solid/circle for kernel A, dashed/square
for kernel B).

## A/B for one guest

```
make fstests-report HOST=qsu-xfs-crc KERNEL=7.0.0-gABCDE,7.0.0-gFGHIJ
# → workflows/fstests/results/fstests-report-7.0.0-gABCDE-vs-7.0.0-gFGHIJ-qsu-xfs-crc.html
```

The host filter narrows the A/B comparison to a single VM —
useful when only one profile actually has both kernels' runs
archived, or when reading a focused per-VM diff.

## Discover what's archived

```
ls workflows/fstests/results/qsu-xfs-crc/
```

Each kernel-named subdirectory under a VM root is a complete
archived run. The `last-run` symlink points at whichever one was
most recently deployed.

# Reading the A/B report

The A/B report has three top-level sections, designed to surface
the most attention-worthy outcomes first:

## A/B summary

Stat cards at the top show the per-kernel test count plus four diff
counters:

  - **Regressions (A→B)**: tests that passed on A and fail on B.
    Highlighted in the failure colour. Read this first.
  - **Fixes (A→B)**: tests that failed on A and pass on B. The
    "expected to be a fix" or "flaky test" signal.
  - **New skips on B**: tests that ran on A but are skipped on B
    — usually a `CONFIG_*` change in the build.
  - **Coverage diff**: tests present in only one of the two runs.

Below the cards, a diff table lists every test where the two
kernels disagree, sorted regressions-first. Same-outcome tests are
counted in the "unchanged" tally but not listed; the table only
shows what changed.

## System monitoring (A/B overlay)

Per-host CPU usage, Memory, Run queue + load average, and Disk I/O
charts plot both kernels' time series on a shared axis. Per-metric
colour stays consistent across both kernels (CPU `user` is one
colour on both lines, `system` another, etc.) so the eye reads the
line by what it represents. Per-kernel line style differentiates
the runs:

  - solid + circle markers — kernel A (the first `KERNEL=` value)
  - dashed + square markers — kernel B

The legend collapses to one entry per metric plus two entries
explaining the line-style convention so the chart stays readable
when each metric has both kernels' lines on top of each other.

Test execution timeline strips render *separately* per kernel
(one strip per kernel under the metric overlays) rather than
overlaid: stacking two strips' worth of named test labels in one
ribbon would be unreadable.

CPU governor and storage-device sysfs sub-sections render once per
kernel sequentially with the kernel name in the heading rather
than overlaid: their natural shape is key/value, and a comparison
reads better as side-by-side tables than as a chart attempt.

## Per-section detail

Each `<vm> / <section>` block has:

  - **Tests** table — one row per test, two status columns (A and
    B) plus per-kernel duration. Regression cells (FAIL on B
    where A passed) and fix cells (FAIL on A where B passed) are
    highlighted in the failure colour so the eye is drawn to the
    divergent rows.
  - **Failure detail** subsection — for every test that failed on
    at least one kernel (including the "fix" case where A failed
    and B passed), an open `<details>` block with the per-kernel
    `.out.bad` (diff), `.full` (test execution log) and `.dmesg`
    (kernel messages) artefacts. Only the kernel that actually
    failed shows its diagnostics; a regression shows just B's, a
    persistent failure shows both A and B side-by-side, a fix
    shows just A's (so flaky-test diagnosis lands here too).

# A worked example: A/B against a no-op kernel commit

Goal: verify the A/B pipeline by building two kernels from
identical source — kernel B is just an empty commit on top of
kernel A. Differences in test outcomes are then real flaky-test
signal, not source-code regressions.

```bash
# Run kernel A first (current source)
make fstests-baseline TESTS="$(echo generic/{001..050})"

# Capture the kernel name
cat workflows/fstests/results/qsu-xfs-crc/last-kernel.txt
# → 7.0.0-g892c894b4ba4

# Advance the source revision: empty commit changes only the SHA
git -C data/linux commit --allow-empty -m "kdevops: A/B test marker"

# Rebuild + redeploy under the new SHA
make linux-install
make linux-deploy

# Confirm the guests booted the new kernel
ssh qsu-xfs-crc 'uname -r'
# → 7.0.0-gNEWSHA

# Run the same test set under kernel B
make fstests-baseline TESTS="$(echo generic/{001..050})"

# Both runs are now archived side-by-side per VM:
ls workflows/fstests/results/qsu-xfs-crc/
# 7.0.0-g892c894b4ba4/  7.0.0-g892c894b4ba4.tar.xz
# 7.0.0-gNEWSHA/        7.0.0-gNEWSHA.tar.xz
# last-kernel.txt       last-run -> 7.0.0-gNEWSHA

# Render the A/B report
make fstests-report KERNEL=7.0.0-g892c894b4ba4,7.0.0-gNEWSHA
# → fstests-report-7.0.0-g892c894b4ba4-vs-7.0.0-gNEWSHA.html
```

Identical-source kernels should show 0 regressions, 0 new skips,
and 0 coverage diff. Any differences in the report indicate flaky
tests — the same workload on the same code produced different
outcomes between the two runs. The A/B summary diff table names
which tests flaked.

For a real source-revision A/B, replace the `git commit
--allow-empty` step with `git checkout <other-ref>` (or your patch
series). The rest of the flow is identical: rebuild, redeploy,
re-run, render with both kernels.

# Cleaning up: `make fstests-results-clean`

The new layout makes per-kernel cleanup natural — old kernel runs
are not held open by virtiofsd, only the live one is. The clean
target reflects that:

```bash
# Default: remove every <kernel>/ subdir under each <vm>/ that is
# NOT the live last-run target. Archives at the top of <vm>/ stay.
make fstests-results-clean

# Target a single archived run for removal (rejected if it matches
# the live last-run target).
make fstests-results-clean KERNEL=7.0.0-gOLDONE

# Wipe everything including the live kernel's contents and the
# archives. Caller is expected to have stopped the VM, otherwise
# virtiofsd will have stale fds.
make fstests-results-clean ALL=y
```

# See also

  - `docs/fstests.md` — the broader fstests workflow, test-selection
    knobs (`TESTS=`, `START_AFTER=`, `SKIP_TESTS=`, `RUN_FAILURES=`,
    `INITIAL_BASELINE=`, `COUNT=`, `SKIP_RUN=`), libvirt-side A/B
    via baseline+dev nodes.
  - `docs/kdevops-qemu-system-units.md` — the qsu bringup backend,
    SSH transports, cleanup, troubleshooting.
  - `docs/viewing-fstests-results.md` — reading the long-term tar.xz
    archives directly without un-tarring.

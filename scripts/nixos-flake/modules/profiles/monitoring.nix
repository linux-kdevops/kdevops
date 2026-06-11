# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Test-run-bracketed system monitoring on the guest.
#
# Provides systemd-managed monitor daemons that an external
# orchestrator starts before a workload runs and stops after.
# Every monitor runs under a systemd template
# (monitor-<name>@<run-id>.service); the orchestrator instantiates
# each unit with the workload's run-id at start time, and systemd
# substitutes the run-id wherever the unit references %i. Output
# lands under nixos-flake.monitoring.outputDir, which is by default
# /var/lib/monitoring/runs/%i and which consumers typically back
# with a virtiofs share or a block-device mount so the data ends
# up on the host alongside the run's other artifacts.
#
# Each unit pins ReadWritePaths to the monitoring output directory
# so the kernel hard-confines writes to the current run-id's
# monitoring tree — defense in depth for the systemd-managed
# writers we author.
#
# Daemons:
#
#   monitor-sysstat: long-lived sadc(1) recorder. Captures CPU
#     (global + per-CPU + virtualization), memory, hugepages, swap,
#     paging, IO (global + per-device), interrupts, network (DEV +
#     IP/TCP/UDP/ICMP + IPv6), NFS, sockets, run queue + load,
#     softnet, kernel tables, TTY, USB, filesystem util, power
#     (CPU freq, temp, fans, voltage), pressure-stall (PSI). On
#     stop, ExecStopPost converts the binary recording to JSON via
#     sadf -j.
#
#   monitor-cpu-governor: oneshot snapshot of every CPU's
#     /sys/devices/system/cpu/cpuN/cpufreq/scaling_governor at
#     start and end of the workload window. Useful to verify test
#     conditions and detect governor changes mid-run.
#
#   monitor-blkalgn: long-lived blkalgn-libbpf recorder. blkalgn
#     traces block I/O issue events via eBPF and reports per-request
#     granularity and alignment distribution against a configurable
#     indirection unit (IU) size set, plus a per-IU write
#     amplification factor. The service exec's
#     blkalgn-libbpf --json <out>/blkalgn/blkalgn.json, which
#     rewrites the JSON file on every main-loop iteration so the
#     most recent dump survives even an ungraceful stop. Requires
#     the closure to ship blkalgn-libbpf; the libbpf-tools
#     derivation in pkgs/ builds the upstream BCC tag, which does
#     not yet carry blkalgn — consumers that need it override the
#     derivation src to a bcc fork that does.
#
#   monitor-biolatency: long-lived biolatency-libbpf recorder.
#     Prints log2 histograms of block I/O latency (issue to
#     completion, optionally including OS queue time) at a
#     configurable interval. biolatency does not write JSON
#     itself, so the unit captures stdout to
#     <out>/biolatency/biolatency.txt via systemd's
#     StandardOutput=append: directive. Bucketing defaults to
#     milliseconds; the per-disk and per-flag breakdowns are
#     off by default to keep the captured text compact.
#
# This module declares the daemons but does not enable them by
# default — they are started and stopped by the orchestrator that
# brackets the workload, instantiated as
# monitor-<name>@<run-id>.service so the run-id is substituted
# everywhere %i appears in the unit. The module assumes the
# configured outputDir is writable at unit start time; consumers
# typically provision it via a virtiofs share, a block-device
# mount, or a tmpfiles rule.

{
  config,
  lib,
  pkgs,
  ...
}:
let
  cfg = config.nixos-flake.monitoring;

  governorSnapshot = pkgs.writeShellScript "monitor-cpu-governor-snapshot" ''
    set -eu
    out_dir="$1"
    phase="$2"  # start or end
    mkdir -p "$out_dir"

    # Emit a JSON object: {timestamp, governors:{cpuN:gov}}
    {
      printf '{\n'
      printf '  "timestamp": "%s",\n' "$(${pkgs.coreutils}/bin/date -Iseconds)"
      printf '  "governors": {\n'
      first=1
      for cpu_path in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        [ -e "$cpu_path" ] || continue
        # Strip the /cpufreq/scaling_governor suffix, then take the basename.
        cpu_dir=''${cpu_path%/cpufreq/scaling_governor}
        cpu_name=''${cpu_dir##*/}
        gov=$(${pkgs.coreutils}/bin/cat "$cpu_path")
        if [ "$first" -eq 1 ]; then first=0; else printf ',\n'; fi
        printf '    "%s": "%s"' "$cpu_name" "$gov"
      done
      printf '\n  }\n}\n'
    } > "$out_dir/$phase.json"
  '';

  sysstatJsonExport = pkgs.writeShellScript "monitor-sysstat-json-export" ''
    set -eu
    out_dir="$1"
    if [ -f "$out_dir/sa-current" ]; then
      # sadf -j defaults to CPU only; pass -A through to sar so the
      # JSON output includes every activity sadc recorded (memory,
      # disk IO, network, scheduler runqueue, paging, sockets, NFS,
      # power/freq, PSI, etc.).
      ${pkgs.sysstat}/bin/sadf -j "$out_dir/sa-current" -- -A \
        > "$out_dir/sa-current.json" || true
    fi
  '';

  # Per-instance run-id-scoped output dir. systemd substitutes %i
  # (the instance arg, e.g. r0001 for monitor-blkalgn@r0001.service)
  # at unit-load time; the literal "%i" inside the configured
  # outputDir flows through the nix build unchanged and only gets
  # resolved when systemd instantiates the unit.
  monitorOutDir = cfg.outputDir;

  # Factory for libbpf-tools-backed monitor services. The
  # libbpf-tools binaries in pkgs/ install with a -libbpf suffix
  # (so they don't collide with BCC's Python wrappers), are
  # long-lived, and respond to SIGTERM by cleaning up and exiting;
  # that envelope fits every tool in the collection, so the only
  # per-tool inputs are the binary's basename and its argv. The
  # factory returns an attrset suitable for a systemd template
  # unit (declared as "monitor-<name>@") so the run-id is the
  # instance argument every consumer passes in.
  #
  # captureStdout tells the unit to redirect the binary's stdout to
  # ${monitorOutDir}/${name}/${name}.txt via systemd's
  # StandardOutput=append:. Tools that write structured output to a
  # path themselves (blkalgn -j) leave this off and pass the path in
  # args; tools that print histograms to stdout (biolatency,
  # biopattern, biostacks, ...) flip it on so systemd captures the
  # text without a shell wrapper.
  mkLibbpfMonitor =
    {
      name,
      description,
      args,
      captureStdout ? false,
    }:
    {
      inherit description;
      documentation = [ "https://github.com/iovisor/bcc/tree/master/libbpf-tools" ];

      serviceConfig = {
        Type = "simple";
        ExecStartPre = "${pkgs.coreutils}/bin/mkdir -p ${monitorOutDir}/${name}";
        ExecStart = lib.concatStringsSep " " ([ "${pkgs.libbpf-tools}/bin/${name}-libbpf" ] ++ args);
        KillSignal = "SIGTERM";
        TimeoutStopSec = "30s";
        Restart = "no";
        # systemd specifiers (%i etc.) are expanded in path-bearing
        # directives like ReadWritePaths, so the kernel-enforced write
        # boundary tracks the per-instance output dir automatically.
        ReadWritePaths = "${monitorOutDir}";
      }
      // lib.optionalAttrs captureStdout {
        StandardOutput = "append:${monitorOutDir}/${name}/${name}.txt";
        StandardError = "journal";
      };
    };

  blkalgnArgs = lib.concatLists [
    (lib.optionals (cfg.blkalgn.disk != "") [
      "--disk"
      cfg.blkalgn.disk
    ])
    (lib.optionals (cfg.blkalgn.ops != "") [
      "--ops"
      cfg.blkalgn.ops
    ])
    [
      "--json"
      "${monitorOutDir}/blkalgn/blkalgn.json"
    ]
  ];

  # biolatency prints log2 histograms of block-I/O latency to stdout
  # every <interval> seconds. Args order matches biolatency's argp
  # parser: option flags first, then the trailing positional
  # interval. Omitting `count` lets the daemon print histograms
  # forever until SIGTERM, which is what test-run-bracketed monitor
  # mode wants - the orchestrator stops the unit when the workload
  # ends and the last histogram lands in the captured stdout.
  #
  # biolatency's argp registers the long name "disk" twice — once
  # for -D (per-disk grouping, no arg) and once for -d (filter to
  # one disk, takes a DISK arg). The `--disk` long form is
  # therefore ambiguous; short forms are the only unambiguous
  # spelling here. This is the documented exception to the
  # long-form-flag preference: when the tool's CLI does not have
  # an unambiguous long form, the short flag is the correct
  # choice.
  biolatencyArgs = lib.concatLists [
    (lib.optional cfg.biolatency.milliseconds "--milliseconds")
    (lib.optional cfg.biolatency.queued "--queued")
    (lib.optional cfg.biolatency.perDisk "-D")
    (lib.optional cfg.biolatency.perFlag "-F")
    (lib.optionals (cfg.biolatency.disk != "") [
      "-d"
      cfg.biolatency.disk
    ])
    [
      "--timestamp"
      (toString cfg.biolatency.interval)
    ]
  ];
in
{
  options.nixos-flake.monitoring = {
    enable = lib.mkEnableOption "test-run-bracketed system monitoring";

    outputDir = lib.mkOption {
      type = lib.types.str;
      default = "/var/lib/monitoring/runs/%i";
      example = "/mnt/results/%i/monitoring";
      description = ''
        Per-instance directory under which monitor daemons write
        their output. The literal %i is resolved by systemd to the
        unit's instance argument (typically the run-id), so each
        instantiation gets its own subtree. Consumers usually back
        this path with a virtiofs share or a block-device mount so
        the captured data lives outside the guest's ephemeral
        root.
      '';
    };

    sysstat = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = cfg.enable;
        description = ''
          Enable the monitor-sysstat@<run-id>.service template
          unit. The orchestrator instantiates one unit per run-id.
        '';
      };
      interval = lib.mkOption {
        type = lib.types.ints.positive;
        default = 5;
        description = "sadc sample interval in seconds.";
      };
      maxSamples = lib.mkOption {
        type = lib.types.ints.positive;
        default = 999999;
        description = ''
          Upper bound on samples sadc records before exiting on its
          own. Large enough that the recorder runs for the full
          workload duration; the orchestrator stops the service
          when the workload ends.
        '';
      };
    };

    cpuGovernor = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = cfg.enable;
        description = ''
          Enable the monitor-cpu-governor@<run-id>.service
          template unit. The orchestrator instantiates one unit
          per run-id.
        '';
      };
    };

    blkalgn = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = ''
          Enable the monitor-blkalgn@<run-id>.service template
          unit. Off by default even when monitoring.enable is on,
          because blkalgn requires the closure to ship
          blkalgn-libbpf — and the upstream BCC tag the
          libbpf-tools derivation builds against does not yet
          carry it. Consumers that need blkalgn override
          libbpf-tools.src to a bcc fork that does.
        '';
      };
      disk = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = ''
          Disk to trace (blkalgn --disk). Empty traces every
          block device the kernel exposes.
        '';
      };
      ops = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = ''
          Block operation type to trace (blkalgn --ops). Empty
          traces every op type. Spelling is case-sensitive and
          must match blkalgn's internal ops[] table verbatim.

          Data ops:           Read, Write, Flush, Discard,
                              SecureErase, WriteSame,
                              WriteZeroes.

          Zoned-device ops:   ZoneReset, ZoneResetAll, ZoneOpen,
                              ZoneClose, ZoneFinish.

          Driver/transport:   SCSIIn, SCSIOut, DrvIn, DrvOut.

          For write-amplification analysis the meaningful filter
          is "Write".
        '';
      };
    };

    biolatency = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = ''
          Enable the monitor-biolatency@<run-id>.service template
          unit. biolatency-libbpf prints log2 histograms of block
          I/O latency to stdout at the configured interval; the
          unit captures stdout to
          <outputDir>/biolatency/biolatency.txt via systemd's
          StandardOutput=append:. Off by default even when
          monitoring.enable is on so it stays opt-in like
          blkalgn. The guest kernel must enable eBPF tracepoint
          support (CONFIG_BPF_EVENTS, CONFIG_DEBUG_INFO_BTF) for
          the binary to attach.
        '';
      };
      milliseconds = lib.mkOption {
        type = lib.types.bool;
        default = true;
        description = ''
          Print histograms in milliseconds instead of microseconds
          (biolatency --milliseconds). Default true because typical
          fstests block I/O sits in the 10us-100ms range and the
          millisecond bucketing keeps the bucket count manageable
          for time-series visualisation.
        '';
      };
      queued = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = ''
          Include OS queued time in the I/O latency total
          (biolatency --queued). Default false: the standard
          measurement covers issue-to-completion only, which is
          what the storage-tier hardware sees.
        '';
      };
      perDisk = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = ''
          Emit a histogram per disk device (biolatency -D).
          Useful when several block devices participate in the
          workload and per-device tail latency comparison
          matters; off by default to keep the captured stdout
          compact when there is only one device under test.
        '';
      };
      perFlag = lib.mkOption {
        type = lib.types.bool;
        default = false;
        description = ''
          Emit a histogram per set of I/O flags (biolatency -F).
          Splits read / write / sync / discard / etc. into
          separate histograms.
        '';
      };
      disk = lib.mkOption {
        type = lib.types.str;
        default = "";
        description = ''
          Restrict tracing to a single disk by name (biolatency
          -d DISK). Empty traces every block device. Note this
          is the lowercase short -d form, distinct from the
          uppercase -D --disk-grouping flag exposed via perDisk.
        '';
      };
      interval = lib.mkOption {
        type = lib.types.ints.positive;
        default = 30;
        description = ''
          Histogram print interval in seconds. biolatency's
          positional [interval] argument; the trailing [count]
          is intentionally omitted so the daemon runs until
          SIGTERM rather than terminating after a fixed number
          of intervals. Default 30 s gives enough samples for a
          typical fstests run without flooding stdout.
        '';
      };
    };
  };

  config = lib.mkIf cfg.enable {
    environment.systemPackages = with pkgs; [
      sysstat
      # fastfetch is the host_info monitor's collector — invoked
      # directly from the ansible host_info/{run,collect}.yml tasks
      # with --format json and a fixed module list. The binary is
      # ~1.7MB, depends only on libc + libyyjson; cheap addition
      # for the host_info coverage even when the monitor is off.
      fastfetch
    ];

    systemd.services."monitor-sysstat@" = lib.mkIf cfg.sysstat.enable {
      description = "sysstat sadc recorder for run %i";
      documentation = [
        "man:sadc(8)"
        "man:sadf(1)"
      ];

      serviceConfig = {
        Type = "simple";
        # Each start wipes the previous binary recording so sa-current
        # is always per-run-id. Per-run-id means a fresh sa-current
        # by construction (each instance has a different %i and a
        # different output dir), but the rm guard keeps the unit
        # idempotent across same-instance restarts.
        ExecStartPre = [
          "${pkgs.coreutils}/bin/mkdir -p ${monitorOutDir}/sysstat"
          "${pkgs.coreutils}/bin/rm -f ${monitorOutDir}/sysstat/sa-current ${monitorOutDir}/sysstat/sa-current.json"
        ];
        ExecStart = "${pkgs.sysstat}/lib/sa/sadc -S ALL ${toString cfg.sysstat.interval} ${toString cfg.sysstat.maxSamples} ${monitorOutDir}/sysstat/sa-current";
        ExecStopPost = "${sysstatJsonExport} ${monitorOutDir}/sysstat";

        KillSignal = "SIGTERM";
        TimeoutStopSec = "30s";
        Restart = "no";
        ReadWritePaths = "${monitorOutDir}";
      };
    };

    systemd.services."monitor-cpu-governor@" = lib.mkIf cfg.cpuGovernor.enable {
      description = "CPU governor snapshot for run %i";

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        ExecStart = "${governorSnapshot} ${monitorOutDir}/cpu_governor start";
        ExecStop = "${governorSnapshot} ${monitorOutDir}/cpu_governor end";
        ReadWritePaths = "${monitorOutDir}";
      };
    };

    systemd.services."monitor-blkalgn@" = lib.mkIf cfg.blkalgn.enable (mkLibbpfMonitor {
      name = "blkalgn";
      description = "blkalgn libbpf-tools recorder for run %i";
      args = blkalgnArgs;
    });

    systemd.services."monitor-biolatency@" = lib.mkIf cfg.biolatency.enable (mkLibbpfMonitor {
      name = "biolatency";
      description = "biolatency libbpf-tools recorder for run %i";
      args = biolatencyArgs;
      captureStdout = true;
    });
  };
}

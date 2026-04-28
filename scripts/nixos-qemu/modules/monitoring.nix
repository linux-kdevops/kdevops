# SPDX-License-Identifier: copyleft-next-0.3.1
#
# Workflow-bracketed system monitoring on the guest.
#
# Provides systemd-managed monitor daemons that an external
# orchestrator starts before a workload runs and stops after, with
# each monitor writing into a per-name subdirectory under
# nixos-qemu.monitoring.outputDir (default /data/monitor).
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
# This module declares the daemons but does not enable them by
# default — they are started and stopped by the orchestrator that
# brackets the workload. Output backing (typically a virtiofs
# share) is composed by the consumer; this module assumes
# outputDir is writable.

{ config, lib, pkgs, ... }:
let
  cfg = config.nixos-qemu.monitoring;

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
in {
  options.nixos-qemu.monitoring = {
    enable = lib.mkEnableOption "workflow-bracketed system monitoring";

    outputDir = lib.mkOption {
      type = lib.types.str;
      default = "/data/monitor";
      description = ''
        Base directory where each monitor writes its data, with one
        subdirectory per monitor (e.g. <outputDir>/sysstat/,
        <outputDir>/cpu_governor/). The consumer composes the
        backing for this path; a virtiofs share at the same path is
        the typical setup.
      '';
    };

    sysstat = {
      enable = lib.mkOption {
        type = lib.types.bool;
        default = cfg.enable;
        description = "Enable the monitor-sysstat.service unit.";
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
        description = "Enable the monitor-cpu-governor.service unit.";
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

    systemd.services.monitor-sysstat = lib.mkIf cfg.sysstat.enable {
      description = "sysstat sadc recorder for workflow-bracketed monitoring";
      documentation = [ "man:sadc(8)" "man:sadf(1)" ];

      serviceConfig = {
        Type = "simple";
        # Each start wipes the previous binary recording so sa-current
        # is always per-run. Without this sadc appends to the existing
        # file and downstream sadf -j ends up emitting a series that
        # spans every run since boot, breaking the test-timeline
        # alignment that assumes sample 0 is recent.
        ExecStartPre = [
          "${pkgs.coreutils}/bin/mkdir -p ${cfg.outputDir}/sysstat"
          "${pkgs.coreutils}/bin/rm -f ${cfg.outputDir}/sysstat/sa-current ${cfg.outputDir}/sysstat/sa-current.json"
        ];
        ExecStart = "${pkgs.sysstat}/lib/sa/sadc -S ALL ${toString cfg.sysstat.interval} ${toString cfg.sysstat.maxSamples} ${cfg.outputDir}/sysstat/sa-current";
        ExecStopPost = "${sysstatJsonExport} ${cfg.outputDir}/sysstat";

        KillSignal = "SIGTERM";
        TimeoutStopSec = "30s";
        Restart = "no";
      };
    };

    systemd.services.monitor-cpu-governor = lib.mkIf cfg.cpuGovernor.enable {
      description = "CPU governor snapshot at workflow start and end";

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        ExecStart = "${governorSnapshot} ${cfg.outputDir}/cpu_governor start";
        ExecStop = "${governorSnapshot} ${cfg.outputDir}/cpu_governor end";
      };
    };
  };
}

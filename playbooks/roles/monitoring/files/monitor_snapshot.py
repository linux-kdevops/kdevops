# SPDX-License-Identifier: copyleft-next-0.3.1
"""monitor_snapshot.py — snapshot kernel-exposed virtual filesystems as JSON.

Single-tool, multi-profile snapshot collector. Each profile reads a
fixed subset of /proc and /sys and emits a JSON document keyed by
the surfaces it covers. The same script powers every snapshot-style
monitor under playbooks/roles/monitoring/tasks/monitors/<NAME>/, so
adding a new profile means adding a function below and a Kconfig
knob in kconfigs/monitors/Kconfig — no new collector script.

Profiles:

    blockdev      /sys/class/block/<dev>/ + queue/ + device/
                  /sys/class/nvme/<ctrl>/
                  (block-layer + NVMe identity)
    boot_params   /proc/cmdline, /proc/version, /proc/sys/kernel/{tainted,
                  randomize_va_space}
    cpu_features  /sys/devices/system/cpu/{vulnerabilities/, smt/, online,
                  present, possible, offline, cpu0/microcode/}
    clocksource   /sys/devices/system/clocksource/clocksource0/
    vm_tuning     /sys/kernel/mm/transparent_hugepage/, /proc/sys/vm/<knob>
    lsm           /sys/kernel/security/{lsm,lockdown}, /sys/firmware/efi
    dmi           /sys/devices/virtual/dmi/id/

Every read is best-effort: a missing file or directory yields a
``null`` (or empty dict) in the output rather than an error, so the
same JSON schema works on emulated guests where some files don't
exist (e.g. microcode on QEMU, /sys/kernel/security/* without
CONFIG_SECURITYFS).

Usage:
    monitor_snapshot.py --profile <name> [output-path]

Output goes to stdout when the path is "-" or omitted.

Run-by-Ansible: each monitor's tasks/monitors/<NAME>/{run,collect}.yml
calls this script via ``ansible.builtin.script`` with ``executable:
python3``, mirroring the pattern fragmentation_tracker.py uses, and
writes to /data/monitor/<NAME>/{start,end}.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional


def _read_scalar(path) -> Optional[str]:
    """Read a sysfs/procfs file as a single rstripped string, or None."""
    try:
        return Path(path).read_text(errors="replace").rstrip()
    except (OSError, PermissionError):
        return None


def _walk_dir_scalars(d) -> dict[str, str]:
    """Read every regular file in ``d`` as a scalar attribute.

    Symlinks are skipped to keep walks bounded — sysfs uses symlinks
    extensively to express relationships and following them would
    pull in unrelated branches.
    """
    out: dict[str, str] = {}
    p = Path(d)
    if not p.is_dir():
        return out
    for entry in sorted(p.iterdir()):
        if entry.is_symlink() or not entry.is_file():
            continue
        v = _read_scalar(entry)
        if v is not None:
            out[entry.name] = v
    return out


def _walk_class_devices(
    base, *, skip_prefixes: tuple = (), recurse_subdirs: tuple = (),
) -> dict[str, dict]:
    """Walk a /sys/class/<x>/ directory, capturing each device's scalars.

    Each entry under ``base`` is a class symlink pointing at the real
    device path; we resolve once and read the regular files under it.
    ``recurse_subdirs`` names subdirectories whose scalar files become
    nested dicts in the per-device record (e.g. ``queue/`` and
    ``device/`` for /sys/class/block).
    """
    base = Path(base)
    out: dict[str, dict] = {}
    if not base.is_dir():
        return out
    for entry in sorted(base.iterdir()):
        name = entry.name
        if skip_prefixes and name.startswith(skip_prefixes):
            continue
        dev = entry.resolve()
        record: dict[str, object] = dict(_walk_dir_scalars(dev))
        for sub in recurse_subdirs:
            sub_data = _walk_dir_scalars(dev / sub)
            if sub_data:
                record[sub] = sub_data
        if record:
            out[name] = record
    return out


# ---- Profiles ------------------------------------------------------------


def profile_blockdev() -> dict:
    """Storage device sysfs surfaces (sysfs-block + sysfs-class-nvme).

    Top-level keys are the kernel ABI document names; each maps to
    a per-device dict. The shape is preserved from the original
    blockdev_snapshot.py so the report renderer doesn't need to
    change.
    """
    return {
        "sysfs-block": _walk_class_devices(
            "/sys/class/block",
            skip_prefixes=("loop", "ram", "dm-", "zram", "nbd"),
            recurse_subdirs=("queue", "device"),
        ),
        "sysfs-class-nvme": _walk_class_devices(
            "/sys/class/nvme",
        ),
    }


def profile_boot_params() -> dict:
    """Kernel boot-time invariants — set at boot, should not drift."""
    return {
        "cmdline": _read_scalar("/proc/cmdline"),
        "version": _read_scalar("/proc/version"),
        "tainted": _read_scalar("/proc/sys/kernel/tainted"),
        "randomize_va_space": _read_scalar(
            "/proc/sys/kernel/randomize_va_space"
        ),
    }


def profile_cpu_features() -> dict:
    """CPU mitigations + topology + microcode."""
    return {
        "vulnerabilities": _walk_dir_scalars(
            "/sys/devices/system/cpu/vulnerabilities"
        ),
        "smt":      _walk_dir_scalars("/sys/devices/system/cpu/smt"),
        "online":   _read_scalar("/sys/devices/system/cpu/online"),
        "present":  _read_scalar("/sys/devices/system/cpu/present"),
        "possible": _read_scalar("/sys/devices/system/cpu/possible"),
        "offline":  _read_scalar("/sys/devices/system/cpu/offline"),
        "microcode": _walk_dir_scalars(
            "/sys/devices/system/cpu/cpu0/microcode"
        ),
    }


def profile_clocksource() -> dict:
    """Active and available clocksources."""
    return _walk_dir_scalars(
        "/sys/devices/system/clocksource/clocksource0"
    )


def profile_vm_tuning() -> dict:
    """Virtual-memory tuning state (THP + /proc/sys/vm/* sysctls)."""
    return {
        "transparent_hugepage": _walk_dir_scalars(
            "/sys/kernel/mm/transparent_hugepage"
        ),
        "vm": {
            k: _read_scalar(f"/proc/sys/vm/{k}")
            for k in (
                "swappiness",
                "dirty_ratio",
                "dirty_background_ratio",
                "overcommit_memory",
                "overcommit_ratio",
            )
        },
    }


def profile_lsm() -> dict:
    """Linux Security Module status + EFI presence flag.

    Requires CONFIG_SECURITYFS=y and CONFIG_SECURITY_LOCKDOWN_LSM=y
    in the guest kernel for the first two fields to be present.
    """
    return {
        "lsm":         _read_scalar("/sys/kernel/security/lsm"),
        "lockdown":    _read_scalar("/sys/kernel/security/lockdown"),
        "efi_present": Path("/sys/firmware/efi").is_dir(),
    }


def profile_dmi() -> dict:
    """DMI/firmware identity tree under /sys/devices/virtual/dmi/id/."""
    return _walk_dir_scalars("/sys/devices/virtual/dmi/id")


PROFILES = {
    "blockdev":     profile_blockdev,
    "boot_params":  profile_boot_params,
    "cpu_features": profile_cpu_features,
    "clocksource":  profile_clocksource,
    "vm_tuning":    profile_vm_tuning,
    "lsm":          profile_lsm,
    "dmi":          profile_dmi,
}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n", 1)[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--profile", required=True,
        choices=sorted(PROFILES),
        help="Which surface set to capture.",
    )
    ap.add_argument(
        "output", nargs="?", default="-",
        help="Output path (default stdout).",
    )
    args = ap.parse_args()

    data = PROFILES[args.profile]()
    payload = json.dumps(data, indent=2, sort_keys=True) + "\n"

    if args.output == "-":
        sys.stdout.write(payload)
    else:
        os.makedirs(
            os.path.dirname(os.path.abspath(args.output)) or ".",
            exist_ok=True,
        )
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())

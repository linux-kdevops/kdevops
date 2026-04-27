# SPDX-License-Identifier: copyleft-next-0.3.1
"""Snapshot storage-related sysfs surfaces and emit JSON.

Invoked twice per workflow by the ``monitors/blockdev/{run,collect}.yml``
ansible tasks, which copy this script onto the guest via
``ansible.builtin.script`` and execute it once at the start of the
workload window (writing ``start.json``) and once at the end
(``end.json``). No daemon and no systemd unit — a plain one-shot
collector matches the reality of "snapshot the kernel's view of
storage twice per run".

Output is keyed by the kernel ABI document that governs each surface
so the reader can immediately tell which interface defines a setting
and where to read its contract:

    {
      "sysfs-block": {
        "<dev>": {
            "<file>": "<value>", ...,
            "queue":  {<file>: <value>, ...},
            "device": {<file>: <value>, ...},
        }, ...
      },
      "sysfs-class-nvme": {
        "<ctrl>": { "<file>": "<value>", ... }, ...
      }
    }

Adding a new surface (e.g. sysfs-bus-scsi, sysfs-class-zram) only
requires extending the ``SURFACES`` list — the walker is generic.
Within a surface, attributes are auto-discovered: every readable
file under the chosen base path becomes a key, so kernel-added
attributes appear in future runs without a script change.

Usage:
    blockdev_snapshot.py <output-path>

The output directory is created on demand.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

# A surface = one ABI document + the sysfs base it covers + how deep
# we descend into it. ``recurse_subdirs`` lists subdirectories whose
# scalar files we capture as nested dicts; we never auto-recurse into
# arbitrary symlinks (sysfs has many) because that would wander into
# /sys/devices/... and duplicate data already covered by another
# surface.
SURFACES: list[dict] = [
    {
        # Documentation/ABI/stable/sysfs-block
        "name": "sysfs-block",
        "base": Path("/sys/class/block"),
        "skip_prefixes": ("loop", "ram", "dm-", "zram", "nbd"),
        "recurse_subdirs": ("queue", "device"),
        "device_iter": lambda base: sorted(base.iterdir()),
    },
    {
        # Documentation/ABI/stable/sysfs-class-nvme
        # /sys/class/nvme/<ctrl>/ — controller-level attrs only.
        # Per-namespace files are reachable via /sys/class/block,
        # so we don't double-capture them here.
        "name": "sysfs-class-nvme",
        "base": Path("/sys/class/nvme"),
        "skip_prefixes": (),
        "recurse_subdirs": (),
        "device_iter": lambda base: sorted(base.iterdir()),
    },
]


def _read_scalar(path: Path) -> Optional[str]:
    """Read a sysfs file as a single stripped string, or None."""
    try:
        return path.read_text(errors="replace").strip()
    except (OSError, PermissionError):
        return None


def _walk_scalar_dir(d: Path) -> dict[str, str]:
    """Read every regular file in ``d`` as a sysfs scalar attribute.

    Symlinks are skipped to keep walks bounded — sysfs uses symlinks
    extensively to express relationships and following them would
    pull in unrelated branches of the tree.
    """
    out: dict[str, str] = {}
    if not d.is_dir():
        return out
    for f in sorted(d.iterdir()):
        if f.is_symlink() or not f.is_file():
            continue
        v = _read_scalar(f)
        if v is not None:
            out[f.name] = v
    return out


def _collect_surface(surface: dict) -> dict[str, dict]:
    base: Path = surface["base"]
    if not base.is_dir():
        return {}
    out: dict[str, dict] = {}
    for entry in surface["device_iter"](base):
        name = entry.name
        if name.startswith(surface["skip_prefixes"]):
            continue
        # Resolve once so we walk the real device path; the class
        # directory is composed of symlinks back to /sys/devices/...
        dev = entry.resolve()
        record: dict[str, object] = dict(_walk_scalar_dir(dev))
        for sub in surface["recurse_subdirs"]:
            sub_data = _walk_scalar_dir(dev / sub)
            if sub_data:
                record[sub] = sub_data
        if record:
            out[name] = record
    return out


def collect() -> dict[str, dict]:
    return {s["name"]: _collect_surface(s) for s in SURFACES}


def main() -> int:
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} <output-path>", file=sys.stderr)
        return 2
    out_path = sys.argv[1]
    payload = json.dumps(collect(), indent=2, sort_keys=True) + "\n"
    if out_path == "-":
        sys.stdout.write(payload)
    else:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".",
                    exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())

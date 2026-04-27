# SPDX-License-Identifier: copyleft-next-0.3.1
"""Convention-based loaders for results trees.

Reads JSON files; iterates per-host directories; nothing more.
Workflow-specific schema parsing belongs in the workflow's adapter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, Optional


def read_json(path: Path) -> Optional[dict]:
    """Load a JSON file; return None if absent or unparseable."""
    if not path.exists():
        return None
    try:
        with path.open() as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def write_json(path: Path, data: dict) -> None:
    """Write data as pretty JSON, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def iter_hosts(results_dir: Path) -> Iterator[Path]:
    """Yield per-host subdirectories of a results tree.

    Convention: a host directory is any direct child of ``results_dir``
    that is itself a directory and is not a kernel-named archive
    directory (heuristic: kernel names start with a digit). Adapters
    that want strict matching should pass an explicit list of hosts.
    """
    if not results_dir.is_dir():
        return
    for child in sorted(results_dir.iterdir()):
        if not child.is_dir():
            continue
        # Skip kernel-named dirs like 7.0.0/ at the same level.
        if child.name and child.name[0].isdigit():
            continue
        yield child


def load_pattern(results_dir: Path, pattern: str) -> dict[str, dict]:
    """Load every JSON file matching ``pattern`` under ``results_dir``.

    Returns a dict keyed by file stem (without extension). Useful for
    workflows that emit per-host summary or timing files alongside each
    other in the same directory.
    """
    out: dict[str, dict] = {}
    if not results_dir.is_dir():
        return out
    for path in sorted(results_dir.glob(pattern)):
        data = read_json(path)
        if data is None:
            continue
        out[path.stem] = data
    return out

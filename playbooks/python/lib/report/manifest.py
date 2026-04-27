# SPDX-License-Identifier: copyleft-next-0.3.1
"""Run manifest read/write.

A manifest is a small JSON file at the top of a results tree that
identifies the run for downstream tooling (comparison, archival,
catalog UIs). Schema:

    {
        "workflow": "fstests",
        "kernel":   "7.0.0-fastpath",
        "run_id":   "2026-04-27T10-30-00-utc",
        "hosts":    ["qsu-xfs-crc", "qsu-xfs-reflink"],
        "sections": ["xfs_crc", "xfs_reflink"],
        "started":  "2026-04-27T10:30:00+00:00",
        "finished": "2026-04-27T11:25:43+00:00"
    }

All fields are optional; consumers should be tolerant of partial
manifests (e.g. legacy archives that only have a kernel name in the
filename).
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import data


MANIFEST_NAME = "manifest.json"


@dataclasses.dataclass
class Manifest:
    workflow: Optional[str] = None
    kernel: Optional[str] = None
    run_id: Optional[str] = None
    hosts: list[str] = dataclasses.field(default_factory=list)
    sections: list[str] = dataclasses.field(default_factory=list)
    started: Optional[str] = None
    finished: Optional[str] = None

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> "Manifest":
        d = d or {}
        return cls(
            workflow=d.get("workflow"),
            kernel=d.get("kernel"),
            run_id=d.get("run_id"),
            hosts=list(d.get("hosts") or []),
            sections=list(d.get("sections") or []),
            started=d.get("started"),
            finished=d.get("finished"),
        )

    @classmethod
    def from_path(cls, path: Path) -> "Manifest":
        """Load from the manifest file or its containing directory."""
        if path.is_dir():
            path = path / MANIFEST_NAME
        return cls.from_dict(data.read_json(path))

    def to_dict(self) -> dict:
        return {k: v for k, v in dataclasses.asdict(self).items() if v}

    def write(self, dest: Path) -> Path:
        """Write the manifest to ``dest`` (file or directory)."""
        if dest.is_dir():
            dest = dest / MANIFEST_NAME
        data.write_json(dest, self.to_dict())
        return dest


def utc_run_id(now: Optional[datetime] = None) -> str:
    """Filename-safe UTC timestamp suitable as a run_id."""
    now = now or datetime.now(timezone.utc)
    return now.strftime("%Y-%m-%dT%H-%M-%S-utc")

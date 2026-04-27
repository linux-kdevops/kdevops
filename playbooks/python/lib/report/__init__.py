# SPDX-License-Identifier: copyleft-next-0.3.1
"""Workflow-agnostic reporting library for kdevops.

Modules:
    html         Self-contained HTML report template + section helpers.
    charts       matplotlib helpers that return base64-encoded PNGs.
    data         Convention-based JSON loaders for results trees.
    monitoring   Render plots from the kdevops monitoring framework
                 (sysstat sa-current.json, cpu_governor snapshots, etc.).
    manifest     Read/write the per-run manifest JSON that ties a
                 results tree to its workflow, kernel, and host inventory.
    compare      Multi-run delta tables and overlay charts.

Adapters live per-workflow under workflows/<workflow>/scripts/, set up
sys.path to find this package, and call into the helpers exposed here.
"""

from . import charts, compare, data, html, manifest, monitoring

__all__ = ["charts", "compare", "data", "html", "manifest", "monitoring"]

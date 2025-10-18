#!/usr/bin/env python3
"""
Expand workflow to section list for matrix execution.

For expandable workflows (like 'blktests'), returns list of sections.
For single-section workflows (like 'blktests_nvme'), returns list with one element.
"""
import json
import sys
from pathlib import Path


def expand_workflow(workflow_name: str) -> list:
    """Expand workflow to list of sections for matrix execution."""
    script_dir = Path(__file__).parent
    mapping_file = (
        script_dir.parent / ".github" / "workflows" / "workflow-sections.json"
    )

    with open(mapping_file) as f:
        mapping = json.load(f)

    # Check if this is an expandable workflow
    expandable = mapping.get("expandable_workflows", {})
    if workflow_name in expandable:
        return expandable[workflow_name]["sections"]

    # Check if this is a known single-section workflow
    single_section = mapping.get("single_section_workflows", [])
    if workflow_name in single_section:
        return [workflow_name]

    # Unknown workflow - treat as single section
    return [workflow_name]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: expand_workflow_sections.py <workflow_name>", file=sys.stderr)
        sys.exit(1)

    workflow = sys.argv[1]
    sections = expand_workflow(workflow)
    print(json.dumps(sections))

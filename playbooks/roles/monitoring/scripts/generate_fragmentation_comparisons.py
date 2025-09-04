#!/usr/bin/env python3
"""
Generate fragmentation comparison plots for different filesystem configurations.
This replaces the complex shell script in the Ansible task.
"""

import os
import sys
import argparse
from pathlib import Path
import glob
import subprocess
import json


def find_first_matching_file(pattern, directory):
    """Find the first file matching a pattern in a directory."""
    matches = glob.glob(os.path.join(directory, pattern))
    return matches[0] if matches else None


def generate_comparison(
    visualizer_script,
    file1_pattern,
    file2_pattern,
    label1,
    label2,
    output_file,
    directory,
):
    """Generate a comparison plot between two fragmentation data files."""

    file1 = find_first_matching_file(file1_pattern, directory)
    file2 = find_first_matching_file(file2_pattern, directory)

    if file1 and file2 and os.path.isfile(file1) and os.path.isfile(file2):
        print(f"Generating comparison: {label1} vs {label2}")
        print(f"  Using files: {os.path.basename(file1)} and {os.path.basename(file2)}")

        cmd = [
            "python3",
            visualizer_script,
            file1,
            "--compare",
            file2,
            "--labels",
            label1,
            label2,
            "-o",
            os.path.join(directory, output_file),
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode == 0:
                print(f"  Created: {output_file}")
                return True
            else:
                print(f"  Error generating {output_file}: {result.stderr}")
                return False
        except Exception as e:
            print(f"  Exception generating {output_file}: {e}")
            return False
    else:
        print(f"Skipping {label1} vs {label2} - one or both files not found")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate fragmentation comparison plots"
    )
    parser.add_argument(
        "directory", help="Directory containing fragmentation data files"
    )
    parser.add_argument(
        "--visualizer", default=None, help="Path to fragmentation_visualizer.py script"
    )

    args = parser.parse_args()

    # Find the visualizer script
    if args.visualizer:
        visualizer_script = args.visualizer
    else:
        # Try to find it relative to this script
        script_dir = Path(__file__).parent
        # Look in the monitoring role files directory
        visualizer_script = script_dir.parent / "files" / "fragmentation_visualizer.py"
        if not visualizer_script.exists():
            # Try the playbook directory
            visualizer_script = (
                script_dir.parent.parent.parent
                / "roles"
                / "monitoring"
                / "files"
                / "fragmentation_visualizer.py"
            )

    if not os.path.exists(visualizer_script):
        print(f"Error: fragmentation_visualizer.py not found at {visualizer_script}")
        return 1

    # Change to the target directory
    os.chdir(args.directory)

    print("Starting fragmentation comparison generation...")

    # List available JSON files
    json_files = glob.glob("*_fragmentation_data.json")
    if json_files:
        print("Available JSON files:")
        for f in sorted(json_files):
            print(f"  - {f}")
    else:
        print("No fragmentation data files found")
        return 0

    print("")

    # Define comparison pairs
    comparisons = [
        # XFS block size comparisons
        (
            "*xfs-4k*_fragmentation_data.json",
            "*xfs-16k*_fragmentation_data.json",
            "XFS 4k",
            "XFS 16k",
            "comparison_xfs_4k_vs_16k.png",
        ),
        (
            "*xfs-4k*_fragmentation_data.json",
            "*xfs-32k*_fragmentation_data.json",
            "XFS 4k",
            "XFS 32k",
            "comparison_xfs_4k_vs_32k.png",
        ),
        (
            "*xfs-16k*_fragmentation_data.json",
            "*xfs-32k*_fragmentation_data.json",
            "XFS 16k",
            "XFS 32k",
            "comparison_xfs_16k_vs_32k.png",
        ),
        # Filesystem comparisons
        (
            "*ext4*_fragmentation_data.json",
            "*btrfs*_fragmentation_data.json",
            "EXT4",
            "Btrfs",
            "comparison_ext4_vs_btrfs.png",
        ),
        (
            "*ext4*_fragmentation_data.json",
            "*xfs-4k*_fragmentation_data.json",
            "EXT4",
            "XFS 4k",
            "comparison_ext4_vs_xfs4k.png",
        ),
        (
            "*btrfs*_fragmentation_data.json",
            "*xfs-4k*_fragmentation_data.json",
            "Btrfs",
            "XFS 4k",
            "comparison_btrfs_vs_xfs4k.png",
        ),
    ]

    # Generate comparisons
    successful = 0
    for pattern1, pattern2, label1, label2, output in comparisons:
        if generate_comparison(
            str(visualizer_script),
            pattern1,
            pattern2,
            label1,
            label2,
            output,
            args.directory,
        ):
            successful += 1

    # Count generated comparisons
    print("")
    comparison_files = glob.glob("comparison_*.png")
    print(f"Summary: Generated {len(comparison_files)} comparison plots")

    if comparison_files:
        print("Comparison files created:")
        for f in sorted(comparison_files):
            print(f"  - {f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

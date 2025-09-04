#!/usr/bin/env python3
"""
Build Linux kernel multiple times and collect statistics.

This script builds the Linux kernel multiple times to measure build
performance and collect statistics. It runs as a regular user and
does not require root privileges.
"""

import os
import sys
import time
import json
import argparse
import subprocess
import statistics
from pathlib import Path
from datetime import datetime


class LinuxBuilder:
    def __init__(self, args):
        self.args = args
        self.results = []
        self.build_dir = Path(args.build_dir)
        self.source_dir = Path(args.source_dir)
        self.results_dir = Path(args.results_dir)

        # Create results directory
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Determine number of jobs
        if args.jobs == 0:
            self.jobs = os.cpu_count() + 1
        else:
            self.jobs = args.jobs

    def run_command(self, cmd, cwd=None, capture=True):
        """Run a command and optionally capture output."""
        if capture:
            result = subprocess.run(
                cmd, cwd=cwd, shell=True, capture_output=True, text=True
            )
            return result
        else:
            result = subprocess.run(cmd, cwd=cwd, shell=True)
            return result

    def get_latest_tag(self):
        """Get the latest stable kernel tag from the git repository."""
        cmd = "git tag --list 'v6.*' | grep -v -- '-rc' | sort -V | tail -1"
        result = self.run_command(cmd, cwd=self.source_dir)
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            print(f"Failed to get latest tag: {result.stderr}")
            return None

    def is_git_writable(self):
        """Check if the git repository is writable."""
        git_dir = self.source_dir / ".git"
        if not git_dir.exists():
            return False

        # Try to access the git index file
        index_file = git_dir / "index"
        try:
            # Try to touch the index file to check writability
            test_result = self.run_command(
                "test -w .git/index || test -w .git", cwd=self.source_dir
            )
            return test_result.returncode == 0
        except:
            return False

    def checkout_tag(self, tag):
        """Checkout a specific git tag or branch."""
        print(f"Checking out {tag}...")
        cmd = f"git checkout {tag}"
        result = self.run_command(cmd, cwd=self.source_dir)
        if result.returncode != 0:
            print(f"Failed to checkout {tag}: {result.stderr}")
            return False
        return True

    def configure_kernel(self):
        """Configure the kernel with defconfig."""
        print("Configuring kernel...")

        # Ensure build directory exists
        self.build_dir.mkdir(parents=True, exist_ok=True)

        # For out-of-tree builds, specify source directory
        if self.build_dir != self.source_dir:
            # Use absolute paths to avoid any confusion
            cmd = f"make -C {self.source_dir.absolute()} O={self.build_dir.absolute()} defconfig"
            # Run from the build directory
            result = self.run_command(cmd, cwd=self.build_dir)
        else:
            cmd = "make defconfig"
            result = self.run_command(cmd, cwd=self.source_dir)

        if result.returncode != 0:
            print(f"Failed to configure kernel: {result.stderr}")
            return False
        return True

    def clean_build(self):
        """Clean the build directory."""
        if self.args.clean_between:
            print("Cleaning build directory...")
            # For out-of-tree builds, just remove everything in build dir
            # but keep the directory itself
            if self.build_dir != self.source_dir:
                cmd = "rm -rf *"
                self.run_command(cmd, cwd=self.build_dir, capture=False)
            else:
                # For in-tree builds, use git clean
                cmd = "git clean -f -x -d"
                self.run_command(cmd, cwd=self.source_dir, capture=False)

    def build_kernel(self, iteration):
        """Build the kernel and measure time."""
        print(f"Starting build {iteration} of {self.args.count}...")

        # Clean if requested
        self.clean_build()

        # Record start time
        start_time = time.time()
        start_datetime = datetime.now()

        # Build command - for out-of-tree builds, specify source dir
        if self.build_dir != self.source_dir:
            cmd = f"make -C {self.source_dir} O={self.build_dir} -j{self.jobs} {self.args.target}"
        else:
            cmd = f"make -j{self.jobs} {self.args.target}"

        if self.args.collect_stats:
            cmd = f"/usr/bin/time -v {cmd}"

        # Log file for this build - store in results dir, not build dir
        log_file = self.results_dir / f"build_{iteration}.log"

        # Run the build
        with open(log_file, "w") as f:
            result = subprocess.run(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)

        # Record end time
        end_time = time.time()
        end_datetime = datetime.now()
        duration = end_time - start_time

        # Store result
        build_result = {
            "iteration": iteration,
            "start_time": start_datetime.isoformat(),
            "end_time": end_datetime.isoformat(),
            "duration": duration,
            "exit_code": result.returncode,
            "success": result.returncode == 0,
        }

        self.results.append(build_result)

        if result.returncode != 0:
            print(f"  Build {iteration} failed with exit code {result.returncode}")
        else:
            print(f"  Build {iteration} completed in {duration:.2f} seconds")

        return result.returncode == 0

    def save_results(self):
        """Save results to JSON and generate summary."""
        # Save raw results
        results_file = self.results_dir / f"build_times_{os.uname().nodename}.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)

        # Generate summary
        successful_builds = [r for r in self.results if r["success"]]
        if successful_builds:
            durations = [r["duration"] for r in successful_builds]

            summary = {
                "hostname": os.uname().nodename,
                "total_builds": self.args.count,
                "successful_builds": len(successful_builds),
                "failed_builds": len(self.results) - len(successful_builds),
                "build_target": self.args.target,
                "make_jobs": self.jobs,
                "clean_between": self.args.clean_between,
                "statistics": {
                    "average": statistics.mean(durations),
                    "median": statistics.median(durations),
                    "min": min(durations),
                    "max": max(durations),
                    "total_time": sum(durations),
                    "total_hours": sum(durations) / 3600,
                },
            }

            if len(durations) > 1:
                summary["statistics"]["stddev"] = statistics.stdev(durations)

            # Save summary
            summary_file = self.results_dir / f"summary_{os.uname().nodename}.json"
            with open(summary_file, "w") as f:
                json.dump(summary, f, indent=2)

            # Print summary
            print("\nBuild Statistics Summary")
            print("========================")
            print(f"Total builds: {summary['total_builds']}")
            print(f"Successful builds: {summary['successful_builds']}")
            print(f"Failed builds: {summary['failed_builds']}")
            print(f"Build target: {summary['build_target']}")
            print(f"Make jobs: {summary['make_jobs']}")
            print()
            print(f"Average build time: {summary['statistics']['average']:.2f} seconds")
            print(f"Median build time: {summary['statistics']['median']:.2f} seconds")
            print(f"Minimum build time: {summary['statistics']['min']:.2f} seconds")
            print(f"Maximum build time: {summary['statistics']['max']:.2f} seconds")
            print(
                f"Total time: {summary['statistics']['total_time']:.2f} seconds "
                f"({summary['statistics']['total_hours']:.2f} hours)"
            )
            if "stddev" in summary["statistics"]:
                print(
                    f"Standard deviation: {summary['statistics']['stddev']:.2f} seconds"
                )

    def run(self):
        """Run the build workflow."""
        # Determine which tag to build
        if self.args.use_latest:
            tag = self.get_latest_tag()
            if not tag:
                print("Failed to determine latest tag")
                return 1
            print(f"Using latest stable tag: {tag}")
        else:
            tag = self.args.tag
            print(f"Using custom tag: {tag}")

        # Checkout the tag (skip if git repo is read-only)
        if self.is_git_writable():
            if not self.checkout_tag(tag):
                return 1
        else:
            print(
                f"Skipping git checkout - repository is read-only (9P mount detected)"
            )

        # Configure kernel if needed
        config_file = self.build_dir / ".config"
        if not config_file.exists():
            # Check if there's a config in the source directory we can copy (for read-only mounts)
            source_config = self.source_dir / ".config"
            if not self.is_git_writable() and source_config.exists():
                print("Copying configuration from read-only source directory...")
                import shutil

                shutil.copy2(source_config, config_file)
            else:
                if not self.configure_kernel():
                    return 1

        # Run builds
        for i in range(1, self.args.count + 1):
            self.build_kernel(i)

            # Brief pause between builds
            if i < self.args.count:
                time.sleep(1)

        # Save results
        self.save_results()

        print(f"\nCompleted {self.args.count} builds")
        print(f"Results saved to {self.results_dir}")

        return 0


def main():
    parser = argparse.ArgumentParser(description="Build Linux kernel multiple times")
    parser.add_argument("--source-dir", required=True, help="Linux source directory")
    parser.add_argument("--build-dir", required=True, help="Build output directory")
    parser.add_argument("--results-dir", required=True, help="Results directory")
    parser.add_argument("--count", type=int, default=100, help="Number of builds")
    parser.add_argument(
        "--jobs", type=int, default=0, help="Number of make jobs (0=auto)"
    )
    parser.add_argument("--target", default="all", help="Make target to build")
    parser.add_argument(
        "--clean-between", action="store_true", help="Clean between builds"
    )
    parser.add_argument(
        "--collect-stats", action="store_true", help="Collect detailed stats"
    )
    parser.add_argument(
        "--use-latest", action="store_true", help="Use latest stable tag"
    )
    parser.add_argument("--tag", default="master", help="Git tag/branch to build")

    args = parser.parse_args()

    builder = LinuxBuilder(args)
    return builder.run()


if __name__ == "__main__":
    sys.exit(main())

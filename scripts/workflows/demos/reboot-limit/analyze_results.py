#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Analyze and visualize reboot-limit workflow results.

This script parses systemd-analyze output and generates graphs showing:
- Boot time trends across reboots
- Individual component times (kernel, initrd, userspace)
- Statistical analysis of boot performance
"""

import os
import sys
import re
import argparse
import statistics
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from typing import Dict, List, Tuple, Optional


class RebootLimitAnalyzer:
    """Analyzes reboot-limit workflow results."""

    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.hosts_data: Dict[str, Dict] = {}
        self.comparison_mode = False
        self.regular_data: Dict[str, Dict] = {}
        self.kexec_data: Dict[str, Dict] = {}

    def parse_systemd_analyze_line(self, line: str) -> Optional[Dict[str, float]]:
        """
        Parse a systemd-analyze output line.

        Example line:
        Startup finished in 2.345s (kernel) + 1.234s (initrd) + 5.678s (userspace) = 9.257s

        Returns dict with times in seconds or None if parse fails.
        """
        # Pattern for systemd-analyze output
        pattern = r"Startup finished in ([\d.]+)s \(kernel\) \+ ([\d.]+)s \(initrd\) \+ ([\d.]+)s \(userspace\) = ([\d.]+)s"

        # Alternative pattern without initrd (for systems without initrd)
        pattern_no_initrd = r"Startup finished in ([\d.]+)s \(kernel\) \+ ([\d.]+)s \(userspace\) = ([\d.]+)s"

        match = re.search(pattern, line)
        if match:
            return {
                "kernel": float(match.group(1)),
                "initrd": float(match.group(2)),
                "userspace": float(match.group(3)),
                "total": float(match.group(4)),
            }

        match = re.search(pattern_no_initrd, line)
        if match:
            return {
                "kernel": float(match.group(1)),
                "initrd": 0.0,
                "userspace": float(match.group(2)),
                "total": float(match.group(3)),
            }

        return None

    def load_host_data(self, host_dir: Path) -> Dict:
        """Load and parse data for a single host."""
        data = {"boot_count": 0, "boot_times": []}

        # Read boot count
        count_file = host_dir / "reboot-count.txt"
        if count_file.exists():
            with open(count_file, "r") as f:
                content = f.read().strip()
                if content:
                    data["boot_count"] = int(content)

        # Read systemd-analyze results
        analyze_file = host_dir / "systemctl-analyze.txt"
        if analyze_file.exists():
            with open(analyze_file, "r") as f:
                for line in f:
                    parsed = self.parse_systemd_analyze_line(line.strip())
                    if parsed:
                        data["boot_times"].append(parsed)

        return data

    def load_all_data(self):
        """Load data for all hosts in the results directory."""
        # Check if we're in comparison mode (regular/ and kexec/ subdirs exist)
        regular_dir = self.results_dir / "regular"
        kexec_dir = self.results_dir / "kexec"

        if regular_dir.exists() and kexec_dir.exists():
            self.comparison_mode = True
            print("Detected comparison mode: analyzing both regular and kexec reboots")

            # Load regular reboot data
            for item in regular_dir.iterdir():
                if item.is_dir():
                    self.regular_data[item.name] = self.load_host_data(item)

            # Load kexec reboot data
            for item in kexec_dir.iterdir():
                if item.is_dir():
                    self.kexec_data[item.name] = self.load_host_data(item)
        else:
            # Standard single mode
            for item in self.results_dir.iterdir():
                if item.is_dir():
                    self.hosts_data[item.name] = self.load_host_data(item)

    def calculate_statistics(self, times: List[float]) -> Dict[str, float]:
        """Calculate statistical measures for a list of times."""
        if not times:
            return {}

        return {
            "min": min(times),
            "max": max(times),
            "mean": statistics.mean(times),
            "median": statistics.median(times),
            "stdev": statistics.stdev(times) if len(times) > 1 else 0,
        }

    def plot_boot_times(self, output_file: str = "reboot_limit_analysis.png"):
        """Generate plots for boot time analysis."""
        if self.comparison_mode:
            self.plot_comparison_analysis(output_file)
        else:
            self.plot_single_mode_analysis(output_file)

    def plot_single_mode_analysis(self, output_file: str):
        """Generate plots for single mode analysis."""
        if not self.hosts_data:
            print("No data to plot")
            return

        # Ensure the output directory exists
        output_path = Path(output_file)
        if output_path.parent != Path("."):
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create figure with subplots
        num_hosts = len(self.hosts_data)
        fig, axes = plt.subplots(num_hosts, 2, figsize=(14, 6 * num_hosts))

        if num_hosts == 1:
            axes = axes.reshape(1, -1)

        for idx, (host, data) in enumerate(self.hosts_data.items()):
            boot_times = data["boot_times"]
            if not boot_times:
                continue

            # Extract time series
            boot_numbers = list(range(1, len(boot_times) + 1))
            kernel_times = [bt["kernel"] for bt in boot_times]
            initrd_times = [bt["initrd"] for bt in boot_times]
            userspace_times = [bt["userspace"] for bt in boot_times]
            total_times = [bt["total"] for bt in boot_times]

            # Plot 1: Stacked area chart of boot components
            ax1 = axes[idx, 0]
            ax1.fill_between(boot_numbers, 0, kernel_times, alpha=0.7, label="Kernel")
            ax1.fill_between(
                boot_numbers,
                kernel_times,
                [k + i for k, i in zip(kernel_times, initrd_times)],
                alpha=0.7,
                label="Initrd",
            )
            ax1.fill_between(
                boot_numbers,
                [k + i for k, i in zip(kernel_times, initrd_times)],
                total_times,
                alpha=0.7,
                label="Userspace",
            )

            ax1.set_xlabel("Boot Number")
            ax1.set_ylabel("Time (seconds)")
            ax1.set_title(f"{host}: Boot Component Times")
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            ax1.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

            # Plot 2: Total boot time with statistics
            ax2 = axes[idx, 1]
            ax2.plot(
                boot_numbers, total_times, "b-", linewidth=2, label="Total Boot Time"
            )

            # Add statistical lines
            stats = self.calculate_statistics(total_times)
            if stats:
                ax2.axhline(
                    y=stats["mean"],
                    color="r",
                    linestyle="--",
                    label=f"Mean: {stats['mean']:.2f}s",
                )
                ax2.axhline(
                    y=stats["median"],
                    color="g",
                    linestyle="--",
                    label=f"Median: {stats['median']:.2f}s",
                )

                # Add standard deviation band
                if stats["stdev"] > 0:
                    ax2.fill_between(
                        boot_numbers,
                        stats["mean"] - stats["stdev"],
                        stats["mean"] + stats["stdev"],
                        alpha=0.2,
                        color="gray",
                        label=f"±1 StdDev: {stats['stdev']:.2f}s",
                    )

            ax2.set_xlabel("Boot Number")
            ax2.set_ylabel("Time (seconds)")
            ax2.set_title(f"{host}: Total Boot Time Analysis")
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

            # Add text box with statistics
            stats_text = f"Boots: {data['boot_count']}\n"
            if stats:
                stats_text += f"Min: {stats['min']:.2f}s\n"
                stats_text += f"Max: {stats['max']:.2f}s\n"
                stats_text += f"Range: {stats['max'] - stats['min']:.2f}s"

            ax2.text(
                0.02,
                0.98,
                stats_text,
                transform=ax2.transAxes,
                verticalalignment="top",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
            )

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"Saved plot to {output_file}")

    def plot_comparison_analysis(self, output_file: str):
        """Generate streamlined comparison plot combining all hosts' regular vs kexec data."""
        if not self.regular_data and not self.kexec_data:
            print("No comparison data to plot")
            return

        # Ensure the output directory exists
        output_path = Path(output_file)
        if output_path.parent != Path("."):
            output_path.parent.mkdir(parents=True, exist_ok=True)

        # Combine data from all hosts
        all_regular_times = []
        all_kexec_times = []
        host_labels = []

        # Collect all data points from all hosts
        all_hosts = sorted(set(self.regular_data.keys()) | set(self.kexec_data.keys()))

        for host in all_hosts:
            regular_data = self.regular_data.get(host, {"boot_times": []})
            kexec_data = self.kexec_data.get(host, {"boot_times": []})

            regular_times = regular_data.get("boot_times", [])
            kexec_times = kexec_data.get("boot_times", [])

            # Add host data to combined arrays
            if regular_times:
                regular_totals = [bt["total"] for bt in regular_times]
                all_regular_times.extend(regular_totals)
                host_labels.extend([f"{host}-regular"] * len(regular_totals))

            if kexec_times:
                kexec_totals = [bt["total"] for bt in kexec_times]
                all_kexec_times.extend(kexec_totals)

        # Create single comprehensive comparison plot
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))

        # Plot combined data
        if all_regular_times:
            regular_boot_numbers = list(range(1, len(all_regular_times) + 1))
            ax.plot(
                regular_boot_numbers,
                all_regular_times,
                "b-",
                linewidth=2,
                label="Regular Reboot",
                alpha=0.8,
                marker="o",
                markersize=4,
            )

        if all_kexec_times:
            kexec_boot_numbers = list(range(1, len(all_kexec_times) + 1))
            ax.plot(
                kexec_boot_numbers,
                all_kexec_times,
                "g-",
                linewidth=2,
                label="Kexec Reboot",
                alpha=0.8,
                marker="s",
                markersize=4,
            )

        # Calculate and display combined statistics
        if all_regular_times and all_kexec_times:
            regular_stats = self.calculate_statistics(all_regular_times)
            kexec_stats = self.calculate_statistics(all_kexec_times)

            if regular_stats and kexec_stats:
                # Add mean lines
                ax.axhline(
                    y=regular_stats["mean"],
                    color="blue",
                    linestyle="--",
                    alpha=0.7,
                    linewidth=2,
                    label=f"Regular Mean: {regular_stats['mean']:.2f}s",
                )
                ax.axhline(
                    y=kexec_stats["mean"],
                    color="green",
                    linestyle="--",
                    alpha=0.7,
                    linewidth=2,
                    label=f"Kexec Mean: {kexec_stats['mean']:.2f}s",
                )

                # Add shaded confidence regions
                ax.fill_between(
                    range(1, max(len(all_regular_times), len(all_kexec_times)) + 1),
                    regular_stats["mean"] - regular_stats["stdev"],
                    regular_stats["mean"] + regular_stats["stdev"],
                    alpha=0.2,
                    color="blue",
                    label=f"Regular ±1σ: {regular_stats['stdev']:.2f}s",
                )

                ax.fill_between(
                    range(1, max(len(all_regular_times), len(all_kexec_times)) + 1),
                    kexec_stats["mean"] - kexec_stats["stdev"],
                    kexec_stats["mean"] + kexec_stats["stdev"],
                    alpha=0.2,
                    color="green",
                    label=f"Kexec ±1σ: {kexec_stats['stdev']:.2f}s",
                )

                # Calculate performance improvement
                speedup = (
                    regular_stats["mean"] / kexec_stats["mean"]
                    if kexec_stats["mean"] > 0
                    else 0
                )
                time_saved = regular_stats["mean"] - kexec_stats["mean"]
                percent_improvement = (
                    (regular_stats["mean"] - kexec_stats["mean"])
                    / regular_stats["mean"]
                ) * 100

                # Create comprehensive statistics text
                stats_text = f"PERFORMANCE COMPARISON\n"
                stats_text += f"{'='*25}\n"
                stats_text += f"Regular Boot:\n"
                stats_text += f"  Mean: {regular_stats['mean']:.2f}s\n"
                stats_text += f"  Range: {regular_stats['min']:.2f}s - {regular_stats['max']:.2f}s\n"
                stats_text += f"  Samples: {len(all_regular_times)}\n\n"
                stats_text += f"Kexec Boot:\n"
                stats_text += f"  Mean: {kexec_stats['mean']:.2f}s\n"
                stats_text += (
                    f"  Range: {kexec_stats['min']:.2f}s - {kexec_stats['max']:.2f}s\n"
                )
                stats_text += f"  Samples: {len(all_kexec_times)}\n\n"
                stats_text += f"IMPROVEMENT:\n"
                stats_text += f"  Speedup: {speedup:.2f}x faster\n"
                stats_text += f"  Time Saved: {time_saved:.2f}s per boot\n"
                stats_text += f"  Improvement: {percent_improvement:.1f}%\n\n"
                stats_text += f"Combined Hosts: {', '.join(all_hosts)}"

                # Position statistics box
                ax.text(
                    0.02,
                    0.98,
                    stats_text,
                    transform=ax.transAxes,
                    verticalalignment="top",
                    fontsize=10,
                    bbox=dict(
                        boxstyle="round,pad=0.5", facecolor="lightblue", alpha=0.8
                    ),
                )

        # Customize plot appearance
        ax.set_xlabel("Boot Sequence", fontsize=12, fontweight="bold")
        ax.set_ylabel("Boot Time (seconds)", fontsize=12, fontweight="bold")
        ax.set_title(
            "Regular vs Kexec Boot Performance Comparison\n(Combined Data from All Hosts)",
            fontsize=14,
            fontweight="bold",
        )
        ax.legend(loc="upper right", fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

        # Improve visual styling
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_linewidth(0.5)
        ax.spines["bottom"].set_linewidth(0.5)

        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches="tight", facecolor="white")
        print(f"Saved comparison plot to {output_file}")

    def print_summary(self):
        """Print a summary of the analysis to stdout."""
        if self.comparison_mode:
            self.print_comparison_summary()
        else:
            self.print_single_mode_summary()

    def print_single_mode_summary(self):
        """Print summary for single mode analysis."""
        for host, data in self.hosts_data.items():
            print(f"\n{'=' * 60}")
            print(f"Host: {host}")
            print(f"Total boots: {data['boot_count']}")

            if data["boot_times"]:
                total_times = [bt["total"] for bt in data["boot_times"]]
                stats = self.calculate_statistics(total_times)

                print(f"\nBoot time statistics:")
                print(f"  Samples analyzed: {len(total_times)}")
                if stats:
                    print(f"  Minimum: {stats['min']:.2f}s")
                    print(f"  Maximum: {stats['max']:.2f}s")
                    print(f"  Mean: {stats['mean']:.2f}s")
                    print(f"  Median: {stats['median']:.2f}s")
                    print(f"  StdDev: {stats['stdev']:.2f}s")
                    print(f"  Range: {stats['max'] - stats['min']:.2f}s")

                # Component breakdown
                kernel_times = [bt["kernel"] for bt in data["boot_times"]]
                initrd_times = [bt["initrd"] for bt in data["boot_times"]]
                userspace_times = [bt["userspace"] for bt in data["boot_times"]]

                print(f"\nComponent averages:")
                print(f"  Kernel: {statistics.mean(kernel_times):.2f}s")
                if any(t > 0 for t in initrd_times):
                    print(f"  Initrd: {statistics.mean(initrd_times):.2f}s")
                print(f"  Userspace: {statistics.mean(userspace_times):.2f}s")
            else:
                print("  No boot time data available")

    def print_comparison_summary(self):
        """Print summary for comparison mode analysis."""
        all_hosts = set(self.regular_data.keys()) | set(self.kexec_data.keys())

        for host in sorted(all_hosts):
            print(f"\n{'=' * 80}")
            print(f"Host: {host} - COMPARISON ANALYSIS")
            print(f"{'=' * 80}")

            regular_data = self.regular_data.get(
                host, {"boot_times": [], "boot_count": 0}
            )
            kexec_data = self.kexec_data.get(host, {"boot_times": [], "boot_count": 0})

            print(f"\nREGULAR REBOOT RESULTS:")
            print(f"  Total boots: {regular_data['boot_count']}")

            if regular_data["boot_times"]:
                regular_total_times = [bt["total"] for bt in regular_data["boot_times"]]
                regular_stats = self.calculate_statistics(regular_total_times)

                print(f"  Samples analyzed: {len(regular_total_times)}")
                if regular_stats:
                    print(f"  Mean: {regular_stats['mean']:.2f}s")
                    print(f"  StdDev: {regular_stats['stdev']:.2f}s")
                    print(
                        f"  Range: {regular_stats['max'] - regular_stats['min']:.2f}s"
                    )
            else:
                print("  No boot time data available")
                regular_stats = None

            print(f"\nKEXEC REBOOT RESULTS:")
            print(f"  Total boots: {kexec_data['boot_count']}")

            if kexec_data["boot_times"]:
                kexec_total_times = [bt["total"] for bt in kexec_data["boot_times"]]
                kexec_stats = self.calculate_statistics(kexec_total_times)

                print(f"  Samples analyzed: {len(kexec_total_times)}")
                if kexec_stats:
                    print(f"  Mean: {kexec_stats['mean']:.2f}s")
                    print(f"  StdDev: {kexec_stats['stdev']:.2f}s")
                    print(f"  Range: {kexec_stats['max'] - kexec_stats['min']:.2f}s")
            else:
                print("  No boot time data available")
                kexec_stats = None

            # Comparison analysis
            if regular_stats and kexec_stats:
                print(f"\nCOMPARISON ANALYSIS:")
                speedup = (
                    regular_stats["mean"] / kexec_stats["mean"]
                    if kexec_stats["mean"] > 0
                    else 0
                )
                time_saved = regular_stats["mean"] - kexec_stats["mean"]

                print(f"  Kexec Speedup: {speedup:.2f}x faster")
                print(f"  Time Saved per Boot: {time_saved:.2f}s")
                print(f"  Regular Mean: {regular_stats['mean']:.2f}s")
                print(f"  Kexec Mean: {kexec_stats['mean']:.2f}s")

                if speedup > 1.1:
                    print(f"  ✓ Kexec provides significant speedup!")
                elif speedup > 1.0:
                    print(f"  → Kexec provides minor speedup")
                else:
                    print(f"  ⚠ Regular reboot is faster")
            else:
                print(f"\nCOMPARISON ANALYSIS:")
                print(f"  Cannot compare - missing data for one or both reboot types")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze reboot-limit workflow results"
    )
    parser.add_argument(
        "results_dir",
        nargs="?",
        default="workflows/demos/reboot-limit/results",
        help="Path to results directory (default: workflows/demos/reboot-limit/results)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="workflows/demos/reboot-limit/results/graphs/reboot_limit_analysis.png",
        help="Output filename for plot (default: workflows/demos/reboot-limit/results/graphs/reboot_limit_analysis.png)",
    )
    parser.add_argument(
        "--no-plot", action="store_true", help="Skip plotting, only show summary"
    )

    args = parser.parse_args()

    # Check if results directory exists
    if not os.path.exists(args.results_dir):
        print(f"Error: Results directory '{args.results_dir}' not found")
        sys.exit(1)

    # Create analyzer and load data
    analyzer = RebootLimitAnalyzer(args.results_dir)
    analyzer.load_all_data()

    # Check if we have data (either single mode or comparison mode)
    has_data = False
    if analyzer.comparison_mode:
        if analyzer.regular_data or analyzer.kexec_data:
            has_data = True
    else:
        if analyzer.hosts_data:
            has_data = True

    if not has_data:
        print(f"No host data found in '{args.results_dir}'")
        if analyzer.comparison_mode:
            print(
                "Make sure you've run 'make reboot-limit-tests' with comparison mode enabled"
            )
        else:
            print(
                "Make sure you've run 'make reboot-limit-baseline' or 'make reboot-limit-tests' first"
            )
        print("This is normal if you haven't run any tests yet.")
        sys.exit(0)  # Exit cleanly when no data exists

    # Print summary
    analyzer.print_summary()

    # Generate plots
    if not args.no_plot:
        try:
            analyzer.plot_boot_times(args.output)
        except ImportError:
            print("\nWarning: matplotlib not installed. Install with:")
            print("  pip install matplotlib")
            print("Skipping plot generation.")


if __name__ == "__main__":
    main()

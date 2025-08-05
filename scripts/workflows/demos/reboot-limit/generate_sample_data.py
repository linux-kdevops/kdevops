#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
Generate sample reboot-limit data for testing the visualization.
This is only for testing purposes.
"""

import os
import random
from pathlib import Path


def generate_sample_data(results_dir: str, num_hosts: int = 2, num_boots: int = 50):
    """Generate sample systemd-analyze data for testing."""
    results_path = Path(results_dir)

    for i in range(num_hosts):
        if i == 0:
            host_name = "demo-reboot-limit"
        else:
            host_name = f"demo-reboot-limit-dev"

        host_dir = results_path / host_name
        host_dir.mkdir(parents=True, exist_ok=True)

        # Generate boot count
        count_file = host_dir / "reboot-count.txt"
        with open(count_file, "w") as f:
            f.write(str(num_boots))

        # Generate systemd-analyze data
        analyze_file = host_dir / "systemctl-analyze.txt"
        with open(analyze_file, "w") as f:
            for boot in range(num_boots):
                # Generate realistic boot times with some variation
                kernel_base = 2.5 + (
                    0.1 if i == 0 else 0.15
                )  # Dev might be slightly slower
                initrd_base = 1.2 + (0.05 if i == 0 else 0.08)
                userspace_base = 5.5 + (0.2 if i == 0 else 0.3)

                # Add some random variation and occasional spikes
                if boot % 10 == 0:  # Occasional slow boot
                    spike = random.uniform(0.5, 2.0)
                else:
                    spike = 0

                kernel_time = kernel_base + random.uniform(-0.3, 0.3) + spike * 0.3
                initrd_time = initrd_base + random.uniform(-0.2, 0.2) + spike * 0.2
                userspace_time = (
                    userspace_base + random.uniform(-0.5, 0.5) + spike * 0.5
                )

                total_time = kernel_time + initrd_time + userspace_time

                line = f"Startup finished in {kernel_time:.3f}s (kernel) + {initrd_time:.3f}s (initrd) + {userspace_time:.3f}s (userspace) = {total_time:.3f}s\n"
                f.write(line)

        print(f"Generated sample data for {host_name}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        results_dir = sys.argv[1]
    else:
        results_dir = "workflows/demos/reboot-limit/results"

    print(f"Generating sample data in {results_dir}")
    generate_sample_data(results_dir)
    print("Sample data generation complete")

#!/usr/bin/env python3
"""
AI Benchmark Results Analysis and Visualization

This script analyzes benchmark results and generates comprehensive graphs
showing performance characteristics of the AI workload testing.
"""

import json
import glob
import os
import sys
import argparse
import subprocess
import platform
from typing import List, Dict, Any
import logging
from datetime import datetime

# Optional imports with graceful fallback
GRAPHING_AVAILABLE = True
try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    import numpy as np
except ImportError as e:
    GRAPHING_AVAILABLE = False
    print(f"Warning: Graphing libraries not available: {e}")
    print("Install with: pip install pandas matplotlib seaborn numpy")


class ResultsAnalyzer:
    def __init__(self, results_dir: str, output_dir: str, config: Dict[str, Any]):
        self.results_dir = results_dir
        self.output_dir = output_dir
        self.config = config
        self.results_data = []

        # Setup logging
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger(__name__)

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Collect system information for DUT details
        self.system_info = self._collect_system_info()

    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information for DUT details in HTML report"""
        info = {}

        try:
            # Basic system information
            info["hostname"] = platform.node()
            info["platform"] = platform.platform()
            info["architecture"] = platform.architecture()[0]
            info["processor"] = platform.processor()

            # Memory information
            try:
                with open("/proc/meminfo", "r") as f:
                    meminfo = f.read()
                    for line in meminfo.split("\n"):
                        if "MemTotal:" in line:
                            info["total_memory"] = line.split()[1] + " kB"
                            break
            except:
                info["total_memory"] = "Unknown"

            # CPU information
            try:
                with open("/proc/cpuinfo", "r") as f:
                    cpuinfo = f.read()
                    cpu_count = cpuinfo.count("processor")
                    info["cpu_count"] = cpu_count

                    # Extract CPU model
                    for line in cpuinfo.split("\n"):
                        if "model name" in line:
                            info["cpu_model"] = line.split(":", 1)[1].strip()
                            break
            except:
                info["cpu_count"] = "Unknown"
                info["cpu_model"] = "Unknown"

            # Storage information
            info["storage_devices"] = self._get_storage_info()

            # Virtualization detection
            info["is_vm"] = self._detect_virtualization()

            # Filesystem information for AI data directory
            info["filesystem_info"] = self._get_filesystem_info()

        except Exception as e:
            self.logger.warning(f"Error collecting system information: {e}")

        return info

    def _get_storage_info(self) -> List[Dict[str, str]]:
        """Get storage device information including NVMe details"""
        devices = []

        try:
            # Get block devices
            result = subprocess.run(
                ["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,FSTYPE"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                lsblk_data = json.loads(result.stdout)
                for device in lsblk_data.get("blockdevices", []):
                    if device.get("type") == "disk":
                        dev_info = {
                            "name": device.get("name", ""),
                            "size": device.get("size", ""),
                            "type": "disk",
                        }

                        # Check if it's NVMe and get additional details
                        if device.get("name", "").startswith("nvme"):
                            nvme_info = self._get_nvme_info(device.get("name", ""))
                            dev_info.update(nvme_info)

                        devices.append(dev_info)
        except Exception as e:
            self.logger.warning(f"Error getting storage info: {e}")

        return devices

    def _get_nvme_info(self, device_name: str) -> Dict[str, str]:
        """Get detailed NVMe device information"""
        nvme_info = {}

        try:
            # Get NVMe identify info
            result = subprocess.run(
                ["nvme", "id-ctrl", f"/dev/{device_name}"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                output = result.stdout
                for line in output.split("\n"):
                    if "mn :" in line:
                        nvme_info["model"] = line.split(":", 1)[1].strip()
                    elif "fr :" in line:
                        nvme_info["firmware"] = line.split(":", 1)[1].strip()
                    elif "sn :" in line:
                        nvme_info["serial"] = line.split(":", 1)[1].strip()
        except Exception as e:
            self.logger.debug(f"Could not get NVMe info for {device_name}: {e}")

        return nvme_info

    def _detect_virtualization(self) -> str:
        """Detect if running in a virtual environment"""
        try:
            # Check systemd-detect-virt
            result = subprocess.run(
                ["systemd-detect-virt"], capture_output=True, text=True
            )
            if result.returncode == 0:
                virt_type = result.stdout.strip()
                return virt_type if virt_type != "none" else "Physical"
        except:
            pass

        try:
            # Check dmesg for virtualization hints
            result = subprocess.run(["dmesg"], capture_output=True, text=True)
            if result.returncode == 0:
                dmesg_output = result.stdout.lower()
                if "kvm" in dmesg_output:
                    return "KVM"
                elif "vmware" in dmesg_output:
                    return "VMware"
                elif "virtualbox" in dmesg_output:
                    return "VirtualBox"
                elif "xen" in dmesg_output:
                    return "Xen"
        except:
            pass

        return "Unknown"

    def _get_filesystem_info(self) -> Dict[str, str]:
        """Get filesystem information for the AI benchmark directory"""
        fs_info = {}

        try:
            # Get filesystem info for the results directory
            result = subprocess.run(
                ["df", "-T", self.results_dir], capture_output=True, text=True
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) > 1:
                    fields = lines[1].split()
                    if len(fields) >= 2:
                        fs_info["filesystem_type"] = fields[1]
                        fs_info["mount_point"] = (
                            fields[6] if len(fields) > 6 else "Unknown"
                        )

            # Get mount options
            try:
                with open("/proc/mounts", "r") as f:
                    for line in f:
                        parts = line.split()
                        if (
                            len(parts) >= 4
                            and fs_info.get("mount_point", "") in parts[1]
                        ):
                            fs_info["mount_options"] = parts[3]
                            break
            except:
                pass
        except Exception as e:
            self.logger.warning(f"Error getting filesystem info: {e}")

        return fs_info

    def _extract_filesystem_config(
        self, result: Dict[str, Any]
    ) -> tuple[str, str, str]:
        """Extract filesystem type and block size from result data.
        Returns (fs_type, block_size, config_key)"""
        filename = result.get("_file", "")

        # Primary: Extract filesystem type from filename (more reliable than JSON)
        fs_type = "unknown"
        block_size = "default"

        if "xfs" in filename:
            fs_type = "xfs"
            # Check larger sizes first to avoid substring matches
            if "64k" in filename and "64k-" in filename:
                block_size = "64k"
            elif "32k" in filename and "32k-" in filename:
                block_size = "32k"
            elif "16k" in filename and "16k-" in filename:
                block_size = "16k"
            elif "4k" in filename and "4k-" in filename:
                block_size = "4k"
        elif "ext4" in filename:
            fs_type = "ext4"
            if "16k" in filename:
                block_size = "16k"
            elif "4k" in filename:
                block_size = "4k"
        elif "btrfs" in filename:
            fs_type = "btrfs"
            block_size = "default"
        else:
            # Fallback to JSON data if filename parsing fails
            fs_type = result.get("filesystem", "unknown")
            self.logger.warning(
                f"Could not determine filesystem from filename {filename}, using JSON data: {fs_type}"
            )

        config_key = f"{fs_type}-{block_size}" if block_size != "default" else fs_type
        return fs_type, block_size, config_key

    def _extract_node_info(self, result: Dict[str, Any]) -> tuple[str, bool]:
        """Extract node hostname and determine if it's a dev node.
        Returns (hostname, is_dev_node)"""
        # Get hostname from system_info (preferred) or fall back to filename
        system_info = result.get("system_info", {})
        hostname = system_info.get("hostname", "")

        # If no hostname in system_info, try extracting from filename
        if not hostname:
            filename = result.get("_file", "")
            # Remove results_ prefix and .json suffix
            hostname = filename.replace("results_", "").replace(".json", "")
            # Remove iteration number if present (_1, _2, etc.)
            if "_" in hostname and hostname.split("_")[-1].isdigit():
                hostname = "_".join(hostname.split("_")[:-1])

        # Determine if this is a dev node
        is_dev = hostname.endswith("-dev")

        return hostname, is_dev

    def load_results(self) -> bool:
        """Load all result files from the results directory"""
        try:
            pattern = os.path.join(self.results_dir, "results_*.json")
            result_files = glob.glob(pattern)

            if not result_files:
                self.logger.warning(f"No result files found in {self.results_dir}")
                return False

            self.logger.info(f"Found {len(result_files)} result files")

            for file_path in result_files:
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                        data["_file"] = os.path.basename(file_path)
                        self.results_data.append(data)
                except Exception as e:
                    self.logger.error(f"Error loading {file_path}: {e}")

            self.logger.info(
                f"Successfully loaded {len(self.results_data)} result sets"
            )
            return len(self.results_data) > 0

        except Exception as e:
            self.logger.error(f"Error loading results: {e}")
            return False

    def generate_summary_report(self) -> str:
        """Generate a text summary report"""
        try:
            report = []
            report.append("=" * 80)
            report.append("AI BENCHMARK RESULTS SUMMARY")
            report.append("=" * 80)
            report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append(f"Total result sets: {len(self.results_data)}")
            report.append("")

            if not self.results_data:
                report.append("No results to analyze.")
                return "\n".join(report)

            # Configuration summary
            first_result = self.results_data[0]
            config = first_result.get("config", {})

            report.append("CONFIGURATION:")
            report.append(
                f"  Vector dataset size: {config.get('vector_dataset_size', 'N/A'):,}"
            )
            report.append(
                f"  Vector dimensions: {config.get('vector_dimensions', 'N/A')}"
            )
            report.append(f"  Index type: {config.get('index_type', 'N/A')}")
            report.append(f"  Benchmark iterations: {len(self.results_data)}")
            report.append("")

            # Insert performance summary
            insert_times = []
            insert_rates = []
            for result in self.results_data:
                insert_perf = result.get("insert_performance", {})
                if insert_perf:
                    insert_times.append(insert_perf.get("total_time_seconds", 0))
                    insert_rates.append(insert_perf.get("vectors_per_second", 0))

            if insert_times:
                report.append("INSERT PERFORMANCE:")
                report.append(
                    f"  Average insert time: {np.mean(insert_times):.2f} seconds"
                )
                report.append(
                    f"  Average insert rate: {np.mean(insert_rates):.2f} vectors/sec"
                )
                report.append(
                    f"  Insert rate range: {np.min(insert_rates):.2f} - {np.max(insert_rates):.2f} vectors/sec"
                )
                report.append("")

            # Index performance summary
            index_times = []
            for result in self.results_data:
                index_perf = result.get("index_performance", {})
                if index_perf:
                    index_times.append(index_perf.get("creation_time_seconds", 0))

            if index_times:
                report.append("INDEX PERFORMANCE:")
                report.append(
                    f"  Average index creation time: {np.mean(index_times):.2f} seconds"
                )
                report.append(
                    f"  Index time range: {np.min(index_times):.2f} - {np.max(index_times):.2f} seconds"
                )
                report.append("")

            # Query performance summary
            report.append("QUERY PERFORMANCE:")
            for result in self.results_data:
                query_perf = result.get("query_performance", {})
                if query_perf:
                    for topk, topk_data in query_perf.items():
                        report.append(f"  {topk.upper()}:")
                        for batch, batch_data in topk_data.items():
                            qps = batch_data.get("queries_per_second", 0)
                            avg_time = batch_data.get("average_time_seconds", 0)
                            report.append(
                                f"    {batch}: {qps:.2f} QPS, {avg_time*1000:.2f}ms avg"
                            )
                    break  # Only show first result for summary

            return "\n".join(report)

        except Exception as e:
            self.logger.error(f"Error generating summary report: {e}")
            return f"Error generating summary: {e}"

    def generate_html_report(self) -> str:
        """Generate comprehensive HTML report with DUT details and test configuration"""
        try:
            html = []

            # HTML header
            html.append("<!DOCTYPE html>")
            html.append("<html lang='en'>")
            html.append("<head>")
            html.append("    <meta charset='UTF-8'>")
            html.append(
                "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>"
            )
            html.append("    <title>AI Benchmark Results Report</title>")
            html.append("    <style>")
            html.append(
                "        body { font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }"
            )
            html.append(
                "        .header { background-color: #f4f4f4; padding: 20px; border-radius: 5px; margin-bottom: 20px; }"
            )
            html.append("        .section { margin-bottom: 30px; }")
            html.append(
                "        .section h2 { color: #333; border-bottom: 2px solid #007acc; padding-bottom: 5px; }"
            )
            html.append("        .section h3 { color: #555; }")
            html.append(
                "        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }"
            )
            html.append(
                "        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }"
            )
            html.append("        th { background-color: #f2f2f2; font-weight: bold; }")
            html.append(
                "        .metric-table td:first-child { font-weight: bold; width: 30%; }"
            )
            html.append(
                "        .config-table td:first-child { font-weight: bold; width: 40%; }"
            )
            html.append("        .performance-good { color: #27ae60; }")
            html.append("        .performance-warning { color: #f39c12; }")
            html.append("        .performance-poor { color: #e74c3c; }")
            html.append(
                "        .highlight { background-color: #fff3cd; padding: 10px; border-radius: 3px; }"
            )
            html.append("        .baseline-row { background-color: #e8f5e9; }")
            html.append("        .dev-row { background-color: #e3f2fd; }")
            html.append("    </style>")
            html.append("</head>")
            html.append("<body>")

            # Report header
            html.append("    <div class='header'>")
            html.append("        <h1>AI Benchmark Results Report</h1>")
            html.append(
                f"        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>"
            )
            html.append(
                f"        <p><strong>Test Results:</strong> {len(self.results_data)} benchmark iterations</p>"
            )

            # Test type identification
            html.append("        <div class='highlight'>")
            html.append("            <h3>🤖 AI Workflow Test Type</h3>")
            html.append(
                "            <p><strong>Vector Database Performance Testing</strong> using <strong>Milvus Vector Database</strong></p>"
            )
            html.append(
                "            <p>This test evaluates AI workload performance including vector insertion, indexing, and similarity search operations.</p>"
            )
            html.append("        </div>")
            html.append("    </div>")

            # Device Under Test (DUT) Section
            html.append("    <div class='section'>")
            html.append("        <h2>📋 Device Under Test (DUT) Details</h2>")
            html.append("        <table class='config-table'>")
            html.append(
                "            <tr><td>Hostname</td><td>"
                + str(self.system_info.get("hostname", "Unknown"))
                + "</td></tr>"
            )
            html.append(
                "            <tr><td>System Type</td><td>"
                + str(self.system_info.get("is_vm", "Unknown"))
                + "</td></tr>"
            )
            html.append(
                "            <tr><td>Platform</td><td>"
                + str(self.system_info.get("platform", "Unknown"))
                + "</td></tr>"
            )
            html.append(
                "            <tr><td>Architecture</td><td>"
                + str(self.system_info.get("architecture", "Unknown"))
                + "</td></tr>"
            )
            html.append(
                "            <tr><td>CPU Model</td><td>"
                + str(self.system_info.get("cpu_model", "Unknown"))
                + "</td></tr>"
            )
            html.append(
                "            <tr><td>CPU Count</td><td>"
                + str(self.system_info.get("cpu_count", "Unknown"))
                + " cores</td></tr>"
            )
            html.append(
                "            <tr><td>Total Memory</td><td>"
                + str(self.system_info.get("total_memory", "Unknown"))
                + "</td></tr>"
            )
            html.append("        </table>")

            # Storage devices section
            html.append("        <h3>💾 Storage Configuration</h3>")
            storage_devices = self.system_info.get("storage_devices", [])
            if storage_devices:
                html.append("        <table>")
                html.append(
                    "            <tr><th>Device</th><th>Size</th><th>Type</th><th>Model</th><th>Firmware</th></tr>"
                )
                for device in storage_devices:
                    model = device.get("model", "N/A")
                    firmware = device.get("firmware", "N/A")
                    html.append(f"            <tr>")
                    html.append(
                        f"                <td>{device.get('name', 'Unknown')}</td>"
                    )
                    html.append(
                        f"                <td>{device.get('size', 'Unknown')}</td>"
                    )
                    html.append(
                        f"                <td>{device.get('type', 'Unknown')}</td>"
                    )
                    html.append(f"                <td>{model}</td>")
                    html.append(f"                <td>{firmware}</td>")
                    html.append(f"            </tr>")
                html.append("        </table>")
            else:
                html.append("        <p>No storage device information available.</p>")

            # Node Configuration section - Extract from actual benchmark results
            html.append("        <h3>🗂️ Node Configuration</h3>")

            # Collect node and filesystem information from benchmark results
            node_configs = {}
            for result in self.results_data:
                # Extract node information
                hostname, is_dev = self._extract_node_info(result)
                fs_type, block_size, config_key = self._extract_filesystem_config(
                    result
                )

                system_info = result.get("system_info", {})
                data_path = system_info.get("data_path", "/data/milvus")
                mount_point = system_info.get("mount_point", "/data")
                kernel_version = system_info.get("kernel_version", "unknown")

                if hostname not in node_configs:
                    node_configs[hostname] = {
                        "hostname": hostname,
                        "node_type": "Development" if is_dev else "Baseline",
                        "filesystem": fs_type,
                        "block_size": block_size,
                        "data_path": data_path,
                        "mount_point": mount_point,
                        "kernel": kernel_version,
                        "test_count": 0,
                    }
                node_configs[hostname]["test_count"] += 1

            if node_configs:
                html.append("        <table class='config-table'>")
                html.append(
                    "            <tr><th>Node</th><th>Type</th><th>Filesystem</th><th>Block Size</th><th>Data Path</th><th>Mount Point</th><th>Kernel</th><th>Tests</th></tr>"
                )
                # Sort nodes with baseline first, then dev
                sorted_nodes = sorted(
                    node_configs.items(),
                    key=lambda x: (x[1]["node_type"] != "Baseline", x[0]),
                )
                for hostname, config_info in sorted_nodes:
                    row_class = (
                        "dev-row"
                        if config_info["node_type"] == "Development"
                        else "baseline-row"
                    )
                    html.append(f"            <tr class='{row_class}'>")
                    html.append(f"                <td><strong>{hostname}</strong></td>")
                    html.append(f"                <td>{config_info['node_type']}</td>")
                    html.append(f"                <td>{config_info['filesystem']}</td>")
                    html.append(f"                <td>{config_info['block_size']}</td>")
                    html.append(f"                <td>{config_info['data_path']}</td>")
                    html.append(
                        f"                <td>{config_info['mount_point']}</td>"
                    )
                    html.append(f"                <td>{config_info['kernel']}</td>")
                    html.append(f"                <td>{config_info['test_count']}</td>")
                    html.append(f"            </tr>")
                html.append("        </table>")
            else:
                html.append(
                    "        <p>No node configuration data found in results.</p>"
                )
            html.append("    </div>")

            # Test Configuration Section
            if self.results_data:
                first_result = self.results_data[0]
                config = first_result.get("config", {})

                html.append("    <div class='section'>")
                html.append("        <h2>⚙️ AI Test Configuration</h2>")
                html.append("        <table class='config-table'>")
                html.append(
                    f"            <tr><td>Vector Dataset Size</td><td>{config.get('vector_dataset_size', 'N/A'):,} vectors</td></tr>"
                )
                html.append(
                    f"            <tr><td>Vector Dimensions</td><td>{config.get('vector_dimensions', 'N/A')}</td></tr>"
                )
                html.append(
                    f"            <tr><td>Index Type</td><td>{config.get('index_type', 'N/A')}</td></tr>"
                )
                html.append(
                    f"            <tr><td>Benchmark Iterations</td><td>{len(self.results_data)}</td></tr>"
                )

                # Add index-specific parameters
                if config.get("index_type") == "HNSW":
                    html.append(
                        f"            <tr><td>HNSW M Parameter</td><td>{config.get('hnsw_m', 'N/A')}</td></tr>"
                    )
                    html.append(
                        f"            <tr><td>HNSW ef Construction</td><td>{config.get('hnsw_ef_construction', 'N/A')}</td></tr>"
                    )
                    html.append(
                        f"            <tr><td>HNSW ef Search</td><td>{config.get('hnsw_ef', 'N/A')}</td></tr>"
                    )
                elif config.get("index_type") == "IVF_FLAT":
                    html.append(
                        f"            <tr><td>IVF nlist</td><td>{config.get('ivf_nlist', 'N/A')}</td></tr>"
                    )
                    html.append(
                        f"            <tr><td>IVF nprobe</td><td>{config.get('ivf_nprobe', 'N/A')}</td></tr>"
                    )

                html.append("        </table>")
                html.append("    </div>")

            # Performance Results Section - Per Node
            html.append("    <div class='section'>")
            html.append("        <h2>📊 Performance Results by Node</h2>")

            if self.results_data:
                # Group results by node
                node_performance = {}

                for result in self.results_data:
                    # Use node hostname as the grouping key
                    hostname, is_dev = self._extract_node_info(result)
                    fs_type, block_size, config_key = self._extract_filesystem_config(
                        result
                    )

                    if hostname not in node_performance:
                        node_performance[hostname] = {
                            "hostname": hostname,
                            "node_type": "Development" if is_dev else "Baseline",
                            "insert_rates": [],
                            "insert_times": [],
                            "index_times": [],
                            "query_performance": {},
                            "filesystem": fs_type,
                            "block_size": block_size,
                        }

                    # Add insert performance
                    insert_perf = result.get("insert_performance", {})
                    if insert_perf:
                        rate = insert_perf.get("vectors_per_second", 0)
                        time = insert_perf.get("total_time_seconds", 0)
                        if rate > 0:
                            node_performance[hostname]["insert_rates"].append(rate)
                        if time > 0:
                            node_performance[hostname]["insert_times"].append(time)

                    # Add index performance
                    index_perf = result.get("index_performance", {})
                    if index_perf:
                        time = index_perf.get("creation_time_seconds", 0)
                        if time > 0:
                            node_performance[hostname]["index_times"].append(time)

                    # Collect query performance (use first result for each node)
                    query_perf = result.get("query_performance", {})
                    if (
                        query_perf
                        and not node_performance[hostname]["query_performance"]
                    ):
                        node_performance[hostname]["query_performance"] = query_perf

                # Display results for each node, sorted with baseline first
                sorted_nodes = sorted(
                    node_performance.items(),
                    key=lambda x: (x[1]["node_type"] != "Baseline", x[0]),
                )
                for hostname, perf_data in sorted_nodes:
                    node_type_badge = (
                        "🔵" if perf_data["node_type"] == "Development" else "🟢"
                    )
                    html.append(
                        f"        <h3>{node_type_badge} {hostname} ({perf_data['node_type']})</h3>"
                    )
                    html.append(
                        f"        <p>Filesystem: {perf_data['filesystem']}, Block Size: {perf_data['block_size']}</p>"
                    )

                    # Insert performance
                    insert_rates = perf_data["insert_rates"]
                    if insert_rates:
                        html.append("        <h4>📈 Vector Insert Performance</h4>")
                        html.append("        <table class='metric-table'>")
                        html.append(
                            f"            <tr><td>Average Insert Rate</td><td>{np.mean(insert_rates):.2f} vectors/sec</td></tr>"
                        )
                        html.append(
                            f"            <tr><td>Insert Rate Range</td><td>{np.min(insert_rates):.2f} - {np.max(insert_rates):.2f} vectors/sec</td></tr>"
                        )
                        html.append(
                            f"            <tr><td>Test Iterations</td><td>{len(insert_rates)}</td></tr>"
                        )
                        html.append("        </table>")

                    # Index performance
                    index_times = perf_data["index_times"]
                    if index_times:
                        html.append("        <h4>🔗 Index Creation Performance</h4>")
                        html.append("        <table class='metric-table'>")
                        html.append(
                            f"            <tr><td>Average Index Creation Time</td><td>{np.mean(index_times):.3f} seconds</td></tr>"
                        )
                        html.append(
                            f"            <tr><td>Index Time Range</td><td>{np.min(index_times):.3f} - {np.max(index_times):.3f} seconds</td></tr>"
                        )
                        html.append("        </table>")

                    # Query performance
                    query_perf = perf_data["query_performance"]
                    if query_perf:
                        html.append("        <h4>🔍 Query Performance</h4>")
                        html.append("        <table>")
                        html.append(
                            "            <tr><th>Query Type</th><th>Batch Size</th><th>QPS</th><th>Avg Latency (ms)</th></tr>"
                        )

                        for topk, topk_data in query_perf.items():
                            for batch, batch_data in topk_data.items():
                                qps = batch_data.get("queries_per_second", 0)
                                avg_time = (
                                    batch_data.get("average_time_seconds", 0) * 1000
                                )

                                # Color coding for performance
                                qps_class = ""
                                if qps > 1000:
                                    qps_class = "performance-good"
                                elif qps > 100:
                                    qps_class = "performance-warning"
                                else:
                                    qps_class = "performance-poor"

                                html.append(f"            <tr>")
                                html.append(
                                    f"                <td>{topk.replace('topk_', 'Top-')}</td>"
                                )
                                html.append(
                                    f"                <td>{batch.replace('batch_', 'Batch ')}</td>"
                                )
                                html.append(
                                    f"                <td class='{qps_class}'>{qps:.2f}</td>"
                                )
                                html.append(f"                <td>{avg_time:.2f}</td>")
                                html.append(f"            </tr>")
                        html.append("        </table>")

                    html.append("        <br>")  # Add spacing between configurations

            html.append("    </div>")

            # Footer
            # Performance Graphs Section
            html.append("    <div class='section'>")
            html.append("        <h2>📈 Performance Visualizations</h2>")
            html.append(
                "        <p>The following graphs provide visual analysis of the benchmark results across all tested filesystem configurations:</p>"
            )
            html.append("        <ul>")
            html.append(
                "            <li><strong>Insert Performance:</strong> Shows vector insertion rates and times for each filesystem configuration</li>"
            )
            html.append(
                "            <li><strong>Query Performance:</strong> Displays query performance heatmaps for different Top-K and batch sizes</li>"
            )
            html.append(
                "            <li><strong>Index Performance:</strong> Compares index creation times across filesystems</li>"
            )
            html.append(
                "            <li><strong>Performance Matrix:</strong> Comprehensive comparison matrix of all metrics</li>"
            )
            html.append(
                "            <li><strong>Filesystem Comparison:</strong> Side-by-side comparison of filesystem performance</li>"
            )
            html.append("        </ul>")
            html.append(
                "        <p><em>Note: Graphs are generated as separate PNG files in the same directory as this report.</em></p>"
            )
            html.append("        <div style='margin-top: 20px;'>")
            html.append(
                "            <img src='insert_performance.png' alt='Insert Performance' style='max-width: 100%; height: auto; margin-bottom: 20px;'>"
            )
            html.append(
                "            <img src='query_performance.png' alt='Query Performance' style='max-width: 100%; height: auto; margin-bottom: 20px;'>"
            )
            html.append(
                "            <img src='index_performance.png' alt='Index Performance' style='max-width: 100%; height: auto; margin-bottom: 20px;'>"
            )
            html.append(
                "            <img src='performance_matrix.png' alt='Performance Matrix' style='max-width: 100%; height: auto; margin-bottom: 20px;'>"
            )
            html.append(
                "            <img src='filesystem_comparison.png' alt='Filesystem Comparison' style='max-width: 100%; height: auto; margin-bottom: 20px;'>"
            )
            html.append("        </div>")
            html.append("    </div>")

            html.append("    <div class='section'>")
            html.append("        <h2>📝 Notes</h2>")
            html.append("        <ul>")
            html.append(
                "            <li>This report was generated automatically by the AI benchmark analysis tool</li>"
            )
            html.append(
                "            <li>Performance metrics are averaged across all benchmark iterations</li>"
            )
            html.append(
                "            <li>QPS (Queries Per Second) values are color-coded: <span class='performance-good'>Green (>1000)</span>, <span class='performance-warning'>Orange (100-1000)</span>, <span class='performance-poor'>Red (<100)</span></li>"
            )
            html.append(
                "            <li>Storage device information may require root privileges to display NVMe details</li>"
            )
            html.append("        </ul>")
            html.append("    </div>")

            html.append("</body>")
            html.append("</html>")

            return "\n".join(html)

        except Exception as e:
            import traceback

            tb = traceback.format_exc()
            self.logger.error(f"Error generating HTML report: {e}\n{tb}")
            return f"<html><body><h1>Error generating HTML report: {e}</h1><pre>{tb}</pre></body></html>"

    def generate_graphs(self) -> bool:
        """Generate performance visualization graphs"""
        if not GRAPHING_AVAILABLE:
            self.logger.warning(
                "Graphing libraries not available, skipping graph generation"
            )
            return False

        try:
            # Set matplotlib style
            if self.config.get("graph_theme", "default") != "default":
                plt.style.use(self.config["graph_theme"])

            # Graph 1: Insert Performance
            self._plot_insert_performance()

            # Graph 2: Query Performance by Top-K
            self._plot_query_performance()

            # Graph 3: Index Creation Time
            self._plot_index_performance()

            # Graph 4: Performance Comparison Matrix
            self._plot_performance_matrix()

            # Graph 5: Multi-filesystem Comparison (if applicable)
            self._plot_filesystem_comparison()

            self.logger.info("Graphs generated successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error generating graphs: {e}")
            return False

    def _plot_insert_performance(self):
        """Plot insert performance metrics with node differentiation"""
        # Group data by node
        node_performance = {}

        for result in self.results_data:
            hostname, is_dev = self._extract_node_info(result)

            if hostname not in node_performance:
                node_performance[hostname] = {
                    "insert_rates": [],
                    "insert_times": [],
                    "iterations": [],
                    "is_dev": is_dev,
                }

            insert_perf = result.get("insert_performance", {})
            if insert_perf:
                node_performance[hostname]["insert_rates"].append(
                    insert_perf.get("vectors_per_second", 0)
                )
                node_performance[hostname]["insert_times"].append(
                    insert_perf.get("total_time_seconds", 0)
                )
                node_performance[hostname]["iterations"].append(
                    len(node_performance[hostname]["insert_rates"])
                )

        # Check if we have multiple nodes
        if len(node_performance) > 1:
            # Multi-node mode: separate lines for each node
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

            # Sort nodes with baseline first, then dev
            sorted_nodes = sorted(
                node_performance.items(), key=lambda x: (x[1]["is_dev"], x[0])
            )

            # Create color palettes for baseline and dev nodes
            baseline_colors = [
                "#2E7D32",
                "#43A047",
                "#66BB6A",
                "#81C784",
                "#A5D6A7",
                "#C8E6C9",
            ]  # Greens
            dev_colors = [
                "#0D47A1",
                "#1565C0",
                "#1976D2",
                "#1E88E5",
                "#2196F3",
                "#42A5F5",
                "#64B5F6",
            ]  # Blues

            # Additional colors if needed
            extra_colors = [
                "#E65100",
                "#F57C00",
                "#FF9800",
                "#FFB300",
                "#FFC107",
                "#FFCA28",
            ]  # Oranges

            # Line styles to cycle through
            line_styles = ["-", "--", "-.", ":"]
            markers = ["o", "s", "^", "v", "D", "p", "*", "h"]

            baseline_idx = 0
            dev_idx = 0

            # Use different colors and styles for each node
            for idx, (hostname, perf_data) in enumerate(sorted_nodes):
                if not perf_data["insert_rates"]:
                    continue

                # Choose color and style based on node type and index
                if perf_data["is_dev"]:
                    # Development nodes - blues
                    color = dev_colors[dev_idx % len(dev_colors)]
                    linestyle = line_styles[
                        (dev_idx // len(dev_colors)) % len(line_styles)
                    ]
                    marker = markers[4 + (dev_idx % 4)]  # Use markers 4-7 for dev
                    label = f"{hostname} (Dev)"
                    dev_idx += 1
                else:
                    # Baseline nodes - greens
                    color = baseline_colors[baseline_idx % len(baseline_colors)]
                    linestyle = line_styles[
                        (baseline_idx // len(baseline_colors)) % len(line_styles)
                    ]
                    marker = markers[
                        baseline_idx % 4
                    ]  # Use first 4 markers for baseline
                    label = f"{hostname} (Baseline)"
                    baseline_idx += 1

                iterations = list(range(1, len(perf_data["insert_rates"]) + 1))

                # Plot insert rate with alpha for better visibility
                ax1.plot(
                    iterations,
                    perf_data["insert_rates"],
                    color=color,
                    linestyle=linestyle,
                    marker=marker,
                    linewidth=1.5,
                    markersize=5,
                    label=label,
                    alpha=0.8,
                )

                # Plot insert time
                ax2.plot(
                    iterations,
                    perf_data["insert_times"],
                    color=color,
                    linestyle=linestyle,
                    marker=marker,
                    linewidth=1.5,
                    markersize=5,
                    label=label,
                    alpha=0.8,
                )

            ax1.set_xlabel("Iteration")
            ax1.set_ylabel("Vectors/Second")
            ax1.set_title("Milvus Insert Rate by Node")
            ax1.grid(True, alpha=0.3)
            # Position legend outside plot area for better visibility with many nodes
            ax1.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=7, ncol=1)

            ax2.set_xlabel("Iteration")
            ax2.set_ylabel("Total Time (seconds)")
            ax2.set_title("Milvus Insert Time by Node")
            ax2.grid(True, alpha=0.3)
            # Position legend outside plot area for better visibility with many nodes
            ax2.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=7, ncol=1)

            plt.suptitle(
                "Insert Performance Analysis: Baseline vs Development",
                fontsize=14,
                y=1.02,
            )
        else:
            # Single node mode: original behavior
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

            # Extract insert data from single node
            hostname = list(node_performance.keys())[0] if node_performance else None
            if hostname:
                perf_data = node_performance[hostname]
                iterations = list(range(1, len(perf_data["insert_rates"]) + 1))

                # Plot insert rate
                ax1.plot(
                    iterations,
                    perf_data["insert_rates"],
                    "b-o",
                    linewidth=2,
                    markersize=6,
                )
                ax1.set_xlabel("Iteration")
                ax1.set_ylabel("Vectors/Second")
                ax1.set_title(f"Vector Insert Rate Performance - {hostname}")
                ax1.grid(True, alpha=0.3)

                # Plot insert time
                ax2.plot(
                    iterations,
                    perf_data["insert_times"],
                    "r-o",
                    linewidth=2,
                    markersize=6,
                )
                ax2.set_xlabel("Iteration")
                ax2.set_ylabel("Total Time (seconds)")
                ax2.set_title(f"Vector Insert Time Performance - {hostname}")
                ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        output_file = os.path.join(
            self.output_dir,
            f"insert_performance.{self.config.get('graph_format', 'png')}",
        )
        plt.savefig(
            output_file, dpi=self.config.get("graph_dpi", 300), bbox_inches="tight"
        )
        plt.close()

    def _plot_query_performance(self):
        """Plot query performance metrics comparing baseline vs dev nodes"""
        if not self.results_data:
            return

        # Group data by filesystem configuration
        fs_groups = {}
        for result in self.results_data:
            hostname, is_dev = self._extract_node_info(result)
            fs_type, block_size, config_key = self._extract_filesystem_config(result)

            if config_key not in fs_groups:
                fs_groups[config_key] = {"baseline": [], "dev": []}

            query_perf = result.get("query_performance", {})
            if query_perf:
                node_type = "dev" if is_dev else "baseline"
                for topk, topk_data in query_perf.items():
                    for batch, batch_data in topk_data.items():
                        fs_groups[config_key][node_type].append(
                            {
                                "hostname": hostname,
                                "topk": topk.replace("topk_", ""),
                                "batch": batch.replace("batch_", ""),
                                "qps": batch_data.get("queries_per_second", 0),
                                "avg_time": batch_data.get("average_time_seconds", 0)
                                * 1000,
                            }
                        )

        if not fs_groups:
            return

        # Create subplots for each filesystem config
        n_configs = len(fs_groups)
        fig_height = max(8, 4 * n_configs)
        fig, axes = plt.subplots(n_configs, 2, figsize=(16, fig_height))

        if n_configs == 1:
            axes = axes.reshape(1, -1)

        for idx, (config_key, data) in enumerate(sorted(fs_groups.items())):
            # Create DataFrames for baseline and dev
            baseline_df = (
                pd.DataFrame(data["baseline"]) if data["baseline"] else pd.DataFrame()
            )
            dev_df = pd.DataFrame(data["dev"]) if data["dev"] else pd.DataFrame()

            # Baseline QPS heatmap
            ax_base = axes[idx][0]
            if not baseline_df.empty:
                baseline_pivot = baseline_df.pivot_table(
                    values="qps", index="topk", columns="batch", aggfunc="mean"
                )
                sns.heatmap(
                    baseline_pivot,
                    annot=True,
                    fmt=".1f",
                    ax=ax_base,
                    cmap="Greens",
                    cbar_kws={"label": "QPS"},
                )
                ax_base.set_title(f"{config_key.upper()} - Baseline QPS")
                ax_base.set_xlabel("Batch Size")
                ax_base.set_ylabel("Top-K")
            else:
                ax_base.text(
                    0.5,
                    0.5,
                    f"No baseline data for {config_key}",
                    ha="center",
                    va="center",
                    transform=ax_base.transAxes,
                )
                ax_base.set_title(f"{config_key.upper()} - Baseline QPS")

            # Dev QPS heatmap
            ax_dev = axes[idx][1]
            if not dev_df.empty:
                dev_pivot = dev_df.pivot_table(
                    values="qps", index="topk", columns="batch", aggfunc="mean"
                )
                sns.heatmap(
                    dev_pivot,
                    annot=True,
                    fmt=".1f",
                    ax=ax_dev,
                    cmap="Blues",
                    cbar_kws={"label": "QPS"},
                )
                ax_dev.set_title(f"{config_key.upper()} - Development QPS")
                ax_dev.set_xlabel("Batch Size")
                ax_dev.set_ylabel("Top-K")
            else:
                ax_dev.text(
                    0.5,
                    0.5,
                    f"No dev data for {config_key}",
                    ha="center",
                    va="center",
                    transform=ax_dev.transAxes,
                )
                ax_dev.set_title(f"{config_key.upper()} - Development QPS")

        plt.suptitle("Query Performance: Baseline vs Development", fontsize=16, y=1.02)
        plt.tight_layout()
        output_file = os.path.join(
            self.output_dir,
            f"query_performance.{self.config.get('graph_format', 'png')}",
        )
        plt.savefig(
            output_file, dpi=self.config.get("graph_dpi", 300), bbox_inches="tight"
        )
        plt.close()

    def _plot_index_performance(self):
        """Plot index creation performance comparing baseline vs dev"""
        # Group by filesystem configuration
        fs_groups = {}

        for result in self.results_data:
            hostname, is_dev = self._extract_node_info(result)
            fs_type, block_size, config_key = self._extract_filesystem_config(result)

            if config_key not in fs_groups:
                fs_groups[config_key] = {"baseline": [], "dev": []}

            index_perf = result.get("index_performance", {})
            if index_perf:
                time = index_perf.get("creation_time_seconds", 0)
                if time > 0:
                    node_type = "dev" if is_dev else "baseline"
                    fs_groups[config_key][node_type].append(time)

        if not fs_groups:
            return

        # Create comparison bar chart
        fig, ax = plt.subplots(figsize=(14, 8))

        configs = sorted(fs_groups.keys())
        x = np.arange(len(configs))
        width = 0.35

        # Calculate averages for each config
        baseline_avgs = []
        dev_avgs = []
        baseline_stds = []
        dev_stds = []

        for config in configs:
            baseline_times = fs_groups[config]["baseline"]
            dev_times = fs_groups[config]["dev"]

            baseline_avgs.append(np.mean(baseline_times) if baseline_times else 0)
            dev_avgs.append(np.mean(dev_times) if dev_times else 0)
            baseline_stds.append(np.std(baseline_times) if baseline_times else 0)
            dev_stds.append(np.std(dev_times) if dev_times else 0)

        # Create bars
        bars1 = ax.bar(
            x - width / 2,
            baseline_avgs,
            width,
            yerr=baseline_stds,
            label="Baseline",
            color="#4CAF50",
            capsize=5,
        )
        bars2 = ax.bar(
            x + width / 2,
            dev_avgs,
            width,
            yerr=dev_stds,
            label="Development",
            color="#2196F3",
            capsize=5,
        )

        # Add value labels on bars
        for bar, val in zip(bars1, baseline_avgs):
            if val > 0:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{val:.3f}s",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        for bar, val in zip(bars2, dev_avgs):
            if val > 0:
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.0,
                    height,
                    f"{val:.3f}s",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        ax.set_xlabel("Filesystem Configuration", fontsize=12)
        ax.set_ylabel("Index Creation Time (seconds)", fontsize=12)
        ax.set_title("Index Creation Performance: Baseline vs Development", fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels([c.upper() for c in configs], rotation=45, ha="right")
        ax.legend(loc="upper right")
        ax.grid(True, alpha=0.3, axis="y")

        output_file = os.path.join(
            self.output_dir,
            f"index_performance.{self.config.get('graph_format', 'png')}",
        )
        plt.savefig(
            output_file, dpi=self.config.get("graph_dpi", 300), bbox_inches="tight"
        )
        plt.close()

    def _plot_performance_matrix(self):
        """Plot performance comparison matrix for each filesystem config"""
        if len(self.results_data) < 2:
            return

        # Group by filesystem configuration
        fs_metrics = {}

        for result in self.results_data:
            hostname, is_dev = self._extract_node_info(result)
            fs_type, block_size, config_key = self._extract_filesystem_config(result)

            if config_key not in fs_metrics:
                fs_metrics[config_key] = {"baseline": [], "dev": []}

            # Collect metrics
            insert_perf = result.get("insert_performance", {})
            index_perf = result.get("index_performance", {})
            query_perf = result.get("query_performance", {})

            metric = {
                "hostname": hostname,
                "insert_rate": insert_perf.get("vectors_per_second", 0),
                "index_time": index_perf.get("creation_time_seconds", 0),
            }

            # Get representative query performance (topk_10, batch_1)
            if "topk_10" in query_perf and "batch_1" in query_perf["topk_10"]:
                metric["query_qps"] = query_perf["topk_10"]["batch_1"].get(
                    "queries_per_second", 0
                )
            else:
                metric["query_qps"] = 0

            node_type = "dev" if is_dev else "baseline"
            fs_metrics[config_key][node_type].append(metric)

        if not fs_metrics:
            return

        # Create subplots for each filesystem
        n_configs = len(fs_metrics)
        n_cols = min(3, n_configs)
        n_rows = (n_configs + n_cols - 1) // n_cols

        fig, axes = plt.subplots(n_rows, n_cols, figsize=(n_cols * 6, n_rows * 5))
        if n_rows == 1 and n_cols == 1:
            axes = [[axes]]
        elif n_rows == 1:
            axes = [axes]
        elif n_cols == 1:
            axes = [[ax] for ax in axes]

        for idx, (config_key, data) in enumerate(sorted(fs_metrics.items())):
            row = idx // n_cols
            col = idx % n_cols
            ax = axes[row][col]

            # Calculate averages
            baseline_metrics = data["baseline"]
            dev_metrics = data["dev"]

            if baseline_metrics and dev_metrics:
                categories = ["Insert Rate\n(vec/s)", "Index Time\n(s)", "Query QPS"]

                baseline_avg = [
                    np.mean([m["insert_rate"] for m in baseline_metrics]),
                    np.mean([m["index_time"] for m in baseline_metrics]),
                    np.mean([m["query_qps"] for m in baseline_metrics]),
                ]

                dev_avg = [
                    np.mean([m["insert_rate"] for m in dev_metrics]),
                    np.mean([m["index_time"] for m in dev_metrics]),
                    np.mean([m["query_qps"] for m in dev_metrics]),
                ]

                x = np.arange(len(categories))
                width = 0.35

                bars1 = ax.bar(
                    x - width / 2,
                    baseline_avg,
                    width,
                    label="Baseline",
                    color="#4CAF50",
                )
                bars2 = ax.bar(
                    x + width / 2, dev_avg, width, label="Development", color="#2196F3"
                )

                # Add value labels
                for bar, val in zip(bars1, baseline_avg):
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f"{val:.0f}" if val > 100 else f"{val:.2f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )

                for bar, val in zip(bars2, dev_avg):
                    height = bar.get_height()
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height,
                        f"{val:.0f}" if val > 100 else f"{val:.2f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                    )

                ax.set_xlabel("Metrics")
                ax.set_ylabel("Value")
                ax.set_title(f"{config_key.upper()}")
                ax.set_xticks(x)
                ax.set_xticklabels(categories)
                ax.legend(loc="upper right", fontsize=8)
                ax.grid(True, alpha=0.3, axis="y")
            else:
                ax.text(
                    0.5,
                    0.5,
                    f"Insufficient data\nfor {config_key}",
                    ha="center",
                    va="center",
                    transform=ax.transAxes,
                )
                ax.set_title(f"{config_key.upper()}")

        # Hide unused subplots
        for idx in range(n_configs, n_rows * n_cols):
            row = idx // n_cols
            col = idx % n_cols
            axes[row][col].set_visible(False)

        plt.suptitle(
            "Performance Comparison Matrix: Baseline vs Development",
            fontsize=14,
            y=1.02,
        )

        output_file = os.path.join(
            self.output_dir,
            f"performance_matrix.{self.config.get('graph_format', 'png')}",
        )
        plt.savefig(
            output_file, dpi=self.config.get("graph_dpi", 300), bbox_inches="tight"
        )
        plt.close()

    def _plot_filesystem_comparison(self):
        """Plot node performance comparison chart"""
        if len(self.results_data) < 2:
            return

        # Group results by node
        node_performance = {}

        for result in self.results_data:
            hostname, is_dev = self._extract_node_info(result)

            if hostname not in node_performance:
                node_performance[hostname] = {
                    "insert_rates": [],
                    "index_times": [],
                    "query_qps": [],
                    "is_dev": is_dev,
                }

            # Collect metrics
            insert_perf = result.get("insert_performance", {})
            if insert_perf:
                node_performance[hostname]["insert_rates"].append(
                    insert_perf.get("vectors_per_second", 0)
                )

            index_perf = result.get("index_performance", {})
            if index_perf:
                node_performance[hostname]["index_times"].append(
                    index_perf.get("creation_time_seconds", 0)
                )

            # Get top-10 batch-1 query performance as representative
            query_perf = result.get("query_performance", {})
            if "topk_10" in query_perf and "batch_1" in query_perf["topk_10"]:
                qps = query_perf["topk_10"]["batch_1"].get("queries_per_second", 0)
                node_performance[hostname]["query_qps"].append(qps)

        # Only create comparison if we have multiple nodes
        if len(node_performance) > 1:
            # Calculate averages
            node_metrics = {}
            for hostname, perf_data in node_performance.items():
                node_metrics[hostname] = {
                    "avg_insert_rate": (
                        np.mean(perf_data["insert_rates"])
                        if perf_data["insert_rates"]
                        else 0
                    ),
                    "avg_index_time": (
                        np.mean(perf_data["index_times"])
                        if perf_data["index_times"]
                        else 0
                    ),
                    "avg_query_qps": (
                        np.mean(perf_data["query_qps"]) if perf_data["query_qps"] else 0
                    ),
                    "is_dev": perf_data["is_dev"],
                }

            # Create comparison bar chart with more space
            fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(24, 8))

            # Sort nodes with baseline first
            sorted_nodes = sorted(
                node_metrics.items(), key=lambda x: (x[1]["is_dev"], x[0])
            )
            node_names = [hostname for hostname, _ in sorted_nodes]

            # Use different colors for baseline vs dev
            colors = [
                "#4CAF50" if not node_metrics[hostname]["is_dev"] else "#2196F3"
                for hostname in node_names
            ]

            # Add labels for clarity
            labels = [
                f"{hostname}\n({'Dev' if node_metrics[hostname]['is_dev'] else 'Baseline'})"
                for hostname in node_names
            ]

            # Insert rate comparison
            insert_rates = [
                node_metrics[hostname]["avg_insert_rate"] for hostname in node_names
            ]
            bars1 = ax1.bar(labels, insert_rates, color=colors)
            ax1.set_title("Average Milvus Insert Rate by Node")
            ax1.set_ylabel("Vectors/Second")
            # Rotate labels for better readability
            ax1.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)

            # Index time comparison (lower is better)
            index_times = [
                node_metrics[hostname]["avg_index_time"] for hostname in node_names
            ]
            bars2 = ax2.bar(labels, index_times, color=colors)
            ax2.set_title("Average Milvus Index Time by Node")
            ax2.set_ylabel("Seconds (Lower is Better)")
            ax2.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)

            # Query QPS comparison
            query_qps = [
                node_metrics[hostname]["avg_query_qps"] for hostname in node_names
            ]
            bars3 = ax3.bar(labels, query_qps, color=colors)
            ax3.set_title("Average Milvus Query QPS by Node")
            ax3.set_ylabel("Queries/Second")
            ax3.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)

            # Add value labels on bars
            for bars, values in [
                (bars1, insert_rates),
                (bars2, index_times),
                (bars3, query_qps),
            ]:
                for bar, value in zip(bars, values):
                    height = bar.get_height()
                    ax = bar.axes
                    ax.text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height + height * 0.01,
                        f"{value:.1f}",
                        ha="center",
                        va="bottom",
                        fontsize=10,
                    )

            plt.suptitle(
                "Milvus Performance Comparison: Baseline vs Development Nodes",
                fontsize=16,
                y=1.02,
            )
            plt.tight_layout()

            output_file = os.path.join(
                self.output_dir,
                f"filesystem_comparison.{self.config.get('graph_format', 'png')}",
            )
            plt.savefig(
                output_file, dpi=self.config.get("graph_dpi", 300), bbox_inches="tight"
            )
            plt.close()

    def analyze(self) -> bool:
        """Run complete analysis"""
        self.logger.info("Starting results analysis...")

        if not self.load_results():
            return False

        # Generate summary report
        summary = self.generate_summary_report()
        summary_file = os.path.join(self.output_dir, "benchmark_summary.txt")
        with open(summary_file, "w") as f:
            f.write(summary)
        self.logger.info(f"Summary report saved to {summary_file}")

        # Generate HTML report
        html_report = self.generate_html_report()
        html_file = os.path.join(self.output_dir, "benchmark_report.html")
        with open(html_file, "w") as f:
            f.write(html_report)
        self.logger.info(f"HTML report saved to {html_file}")

        # Generate graphs if enabled
        if self.config.get("enable_graphing", True):
            self.generate_graphs()

        # Create consolidated JSON report
        consolidated_file = os.path.join(self.output_dir, "consolidated_results.json")
        with open(consolidated_file, "w") as f:
            json.dump(
                {
                    "summary": summary.split("\n"),
                    "raw_results": self.results_data,
                    "analysis_timestamp": datetime.now().isoformat(),
                    "system_info": self.system_info,
                },
                f,
                indent=2,
            )

        self.logger.info("Analysis completed successfully")
        return True


def main():
    parser = argparse.ArgumentParser(description="Analyze AI benchmark results")
    parser.add_argument(
        "--results-dir", required=True, help="Directory containing result files"
    )
    parser.add_argument(
        "--output-dir", required=True, help="Directory for analysis output"
    )
    parser.add_argument("--config", help="Analysis configuration file (JSON)")

    args = parser.parse_args()

    # Load configuration
    config = {
        "enable_graphing": True,
        "graph_format": "png",
        "graph_dpi": 300,
        "graph_theme": "default",
    }

    if args.config:
        try:
            with open(args.config, "r") as f:
                config.update(json.load(f))
        except Exception as e:
            print(f"Error loading config file: {e}")

    # Run analysis
    analyzer = ResultsAnalyzer(args.results_dir, args.output_dir, config)
    success = analyzer.analyze()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

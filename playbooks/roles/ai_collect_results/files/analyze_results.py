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

            # Filesystem section
            html.append("        <h3>🗂️ Filesystem Configuration</h3>")
            fs_info = self.system_info.get("filesystem_info", {})
            html.append("        <table class='config-table'>")
            html.append(
                "            <tr><td>Filesystem Type</td><td>"
                + str(fs_info.get("filesystem_type", "Unknown"))
                + "</td></tr>"
            )
            html.append(
                "            <tr><td>Mount Point</td><td>"
                + str(fs_info.get("mount_point", "Unknown"))
                + "</td></tr>"
            )
            html.append(
                "            <tr><td>Mount Options</td><td>"
                + str(fs_info.get("mount_options", "Unknown"))
                + "</td></tr>"
            )
            html.append("        </table>")
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

            # Performance Results Section
            html.append("    <div class='section'>")
            html.append("        <h2>📊 Performance Results Summary</h2>")

            if self.results_data:
                # Insert performance
                insert_times = [
                    r.get("insert_performance", {}).get("total_time_seconds", 0)
                    for r in self.results_data
                ]
                insert_rates = [
                    r.get("insert_performance", {}).get("vectors_per_second", 0)
                    for r in self.results_data
                ]

                if insert_times and any(t > 0 for t in insert_times):
                    html.append("        <h3>📈 Vector Insert Performance</h3>")
                    html.append("        <table class='metric-table'>")
                    html.append(
                        f"            <tr><td>Average Insert Time</td><td>{np.mean(insert_times):.2f} seconds</td></tr>"
                    )
                    html.append(
                        f"            <tr><td>Average Insert Rate</td><td>{np.mean(insert_rates):.2f} vectors/sec</td></tr>"
                    )
                    html.append(
                        f"            <tr><td>Insert Rate Range</td><td>{np.min(insert_rates):.2f} - {np.max(insert_rates):.2f} vectors/sec</td></tr>"
                    )
                    html.append("        </table>")

                # Index performance
                index_times = [
                    r.get("index_performance", {}).get("creation_time_seconds", 0)
                    for r in self.results_data
                ]
                if index_times and any(t > 0 for t in index_times):
                    html.append("        <h3>🔗 Index Creation Performance</h3>")
                    html.append("        <table class='metric-table'>")
                    html.append(
                        f"            <tr><td>Average Index Creation Time</td><td>{np.mean(index_times):.2f} seconds</td></tr>"
                    )
                    html.append(
                        f"            <tr><td>Index Time Range</td><td>{np.min(index_times):.2f} - {np.max(index_times):.2f} seconds</td></tr>"
                    )
                    html.append("        </table>")

                # Query performance
                html.append("        <h3>🔍 Query Performance</h3>")
                first_query_perf = self.results_data[0].get("query_performance", {})
                if first_query_perf:
                    html.append("        <table>")
                    html.append(
                        "            <tr><th>Query Type</th><th>Batch Size</th><th>QPS</th><th>Avg Latency (ms)</th></tr>"
                    )

                    for topk, topk_data in first_query_perf.items():
                        for batch, batch_data in topk_data.items():
                            qps = batch_data.get("queries_per_second", 0)
                            avg_time = batch_data.get("average_time_seconds", 0) * 1000

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

                html.append("    </div>")

            # Footer
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
            self.logger.error(f"Error generating HTML report: {e}")
            return (
                f"<html><body><h1>Error generating HTML report: {e}</h1></body></html>"
            )

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

            self.logger.info("Graphs generated successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error generating graphs: {e}")
            return False

    def _plot_insert_performance(self):
        """Plot insert performance metrics"""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # Extract insert data
        iterations = []
        insert_rates = []
        insert_times = []

        for i, result in enumerate(self.results_data):
            insert_perf = result.get("insert_performance", {})
            if insert_perf:
                iterations.append(i + 1)
                insert_rates.append(insert_perf.get("vectors_per_second", 0))
                insert_times.append(insert_perf.get("total_time_seconds", 0))

        # Plot insert rate
        ax1.plot(iterations, insert_rates, "b-o", linewidth=2, markersize=6)
        ax1.set_xlabel("Iteration")
        ax1.set_ylabel("Vectors/Second")
        ax1.set_title("Vector Insert Rate Performance")
        ax1.grid(True, alpha=0.3)

        # Plot insert time
        ax2.plot(iterations, insert_times, "r-o", linewidth=2, markersize=6)
        ax2.set_xlabel("Iteration")
        ax2.set_ylabel("Total Time (seconds)")
        ax2.set_title("Vector Insert Time Performance")
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
        """Plot query performance metrics"""
        if not self.results_data:
            return

        # Collect query performance data
        query_data = []
        for result in self.results_data:
            query_perf = result.get("query_performance", {})
            for topk, topk_data in query_perf.items():
                for batch, batch_data in topk_data.items():
                    query_data.append(
                        {
                            "topk": topk.replace("topk_", ""),
                            "batch": batch.replace("batch_", ""),
                            "qps": batch_data.get("queries_per_second", 0),
                            "avg_time": batch_data.get("average_time_seconds", 0)
                            * 1000,  # Convert to ms
                        }
                    )

        if not query_data:
            return

        df = pd.DataFrame(query_data)

        # Create subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # QPS heatmap
        qps_pivot = df.pivot_table(
            values="qps", index="topk", columns="batch", aggfunc="mean"
        )
        sns.heatmap(qps_pivot, annot=True, fmt=".1f", ax=ax1, cmap="YlOrRd")
        ax1.set_title("Queries Per Second (QPS)")
        ax1.set_xlabel("Batch Size")
        ax1.set_ylabel("Top-K")

        # Latency heatmap
        latency_pivot = df.pivot_table(
            values="avg_time", index="topk", columns="batch", aggfunc="mean"
        )
        sns.heatmap(latency_pivot, annot=True, fmt=".1f", ax=ax2, cmap="YlOrRd")
        ax2.set_title("Average Query Latency (ms)")
        ax2.set_xlabel("Batch Size")
        ax2.set_ylabel("Top-K")

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
        """Plot index creation performance"""
        iterations = []
        index_times = []

        for i, result in enumerate(self.results_data):
            index_perf = result.get("index_performance", {})
            if index_perf:
                iterations.append(i + 1)
                index_times.append(index_perf.get("creation_time_seconds", 0))

        if not index_times:
            return

        plt.figure(figsize=(10, 6))
        plt.bar(iterations, index_times, alpha=0.7, color="green")
        plt.xlabel("Iteration")
        plt.ylabel("Index Creation Time (seconds)")
        plt.title("Index Creation Performance")
        plt.grid(True, alpha=0.3)

        # Add average line
        avg_time = np.mean(index_times)
        plt.axhline(
            y=avg_time, color="red", linestyle="--", label=f"Average: {avg_time:.2f}s"
        )
        plt.legend()

        output_file = os.path.join(
            self.output_dir,
            f"index_performance.{self.config.get('graph_format', 'png')}",
        )
        plt.savefig(
            output_file, dpi=self.config.get("graph_dpi", 300), bbox_inches="tight"
        )
        plt.close()

    def _plot_performance_matrix(self):
        """Plot comprehensive performance comparison matrix"""
        if len(self.results_data) < 2:
            return

        # Extract key metrics for comparison
        metrics = []
        for i, result in enumerate(self.results_data):
            insert_perf = result.get("insert_performance", {})
            index_perf = result.get("index_performance", {})

            metric = {
                "iteration": i + 1,
                "insert_rate": insert_perf.get("vectors_per_second", 0),
                "index_time": index_perf.get("creation_time_seconds", 0),
            }

            # Add query metrics
            query_perf = result.get("query_performance", {})
            if "topk_10" in query_perf and "batch_1" in query_perf["topk_10"]:
                metric["query_qps"] = query_perf["topk_10"]["batch_1"].get(
                    "queries_per_second", 0
                )

            metrics.append(metric)

        df = pd.DataFrame(metrics)

        # Normalize metrics for comparison
        numeric_cols = ["insert_rate", "index_time", "query_qps"]
        for col in numeric_cols:
            if col in df.columns:
                df[f"{col}_norm"] = (df[col] - df[col].min()) / (
                    df[col].max() - df[col].min() + 1e-6
                )

        # Create radar chart
        fig, ax = plt.subplots(figsize=(10, 8), subplot_kw=dict(projection="polar"))

        angles = np.linspace(0, 2 * np.pi, len(numeric_cols), endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle

        for i, row in df.iterrows():
            values = [row.get(f"{col}_norm", 0) for col in numeric_cols]
            values += values[:1]  # Complete the circle

            ax.plot(
                angles, values, "o-", linewidth=2, label=f'Iteration {row["iteration"]}'
            )
            ax.fill(angles, values, alpha=0.25)

        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(["Insert Rate", "Index Time (inv)", "Query QPS"])
        ax.set_ylim(0, 1)
        ax.set_title("Performance Comparison Matrix (Normalized)", y=1.08)
        ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0))

        output_file = os.path.join(
            self.output_dir,
            f"performance_matrix.{self.config.get('graph_format', 'png')}",
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

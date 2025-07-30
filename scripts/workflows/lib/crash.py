#!/usr/bin/env python3
# SPDX-License-Identifier: copyleft-next-0.3.1

"""
This module implements a kernel crash watchdog to detect kernel crashes in hosts
and collect crash information using journalctl.
"""

import os
import sys
import subprocess
import re
import logging
import argparse
import yaml
from datetime import datetime, timedelta
from pathlib import Path
import glob
import pwd
import getpass
import hashlib
import qrcode
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("crash_watchdog")

EXTRA_VARS_FILE = "extra_vars.yaml"
REMOTE_JOURNAL_DIR = "/var/log/journal/remote"


class KernelCrashWatchdog:
    CRASH_PATTERNS = [
        r"Kernel panic",
        r"BUG:",
        r"BUG at",
        r"Oops:",
        r"general protection fault",
        r"Unable to handle kernel",
        r"divide error",
        r"kernel BUG at",
        r"UBSAN:",
        r"kernel stack overflow",
        r"Kernel offset leak",
        r"segfault at",
        r"kernel thread",
        r"detected stall on CPU",
        r"soft lockup",
        r"watchdog: BUG: soft lockup",
        r"hung_task: blocked tasks",
        r"NMI backtrace",
        r"Stack:",
        r"nfs: server .* not responding",
        r"INFO: task .* blocked for more than \\d+ seconds",
    ]

    WARNINGS = [
        r"WARNING:",
    ]

    BENIGN_WARNINGS = [
        r"Spectre V2 : WARNING: Unprivileged eBPF is enabled",
        r"WARNING: CPU: \d+ PID: \d+ at (net|drivers|security|arch)/.*spectre",
        r"WARNING: You are running an unsupported configuration",
        r"WARNING: Support for unprivileged eBPF will be removed soon",
    ]

    FILESYSTEM_CORRUPTION_PATTERNS = [
        # General
        r"Filesystem corruption detected",
        r"Corrupted directory entry",
        r"bad inode",
        r"I/O error",
        r"failed to read block",
        r"journal commit I/O error",
        # XFS
        r"XFS: Internal error",
        r"XFS \(.+\): Corruption detected",
        r"XFS \(.+\): Metadata corruption",
        r"XFS \(.+\): bad magic number",
        r"XFS \(.+\): Unrecoverable I/O failure",
        r"XFS \(.+\): Attempted to access beyond EOF",
        r"XFS \(.+\): Log inconsistent",
        r"XFS \(.+\): Inode .+ has inconsistent extent state",
        r"XFS \(.+\): AGF has mismatched freelist count",
        r"XFS \(.+\): Log recovery failed",
        r"XFS: Assertion failed:",
        # Btrfs
        r"BTRFS error",
        r"BTRFS critical",
        r"BTRFS: corruption",
        r"BTRFS: device label .+ lost",
        r"BTRFS: unable to find logical",
        r"BTRFS: failed to read",
        r"BTRFS: parent transid verify failed",
        r"BTRFS: inode corruption",
        r"BTRFS: checksum verify failed",
        r"BTRFS: block group .+ bad",
        r"BTRFS: Transaction aborted",
        r"BTRFS: tree block corruption detected",
    ]

    # List of xfstests that use _require_scratch_nocheck (intentional corruption)
    INTENTIONAL_CORRUPTION_TESTS = [
        "btrfs/011",
        "btrfs/012",
        "btrfs/027",
        "btrfs/060",
        "btrfs/061",
        "btrfs/062",
        "btrfs/063",
        "btrfs/064",
        "btrfs/065",
        "btrfs/066",
        "btrfs/067",
        "btrfs/068",
        "btrfs/069",
        "btrfs/070",
        "btrfs/071",
        "btrfs/072",
        "btrfs/073",
        "btrfs/074",
        "btrfs/080",
        "btrfs/136",
        "btrfs/196",
        "btrfs/207",
        "btrfs/254",
        "btrfs/290",
        "btrfs/321",
        "ext4/002",
        "ext4/025",
        "ext4/033",
        "ext4/037",
        "ext4/040",
        "ext4/041",
        "ext4/054",
        "ext4/055",
        "generic/050",
        "generic/311",
        "generic/321",
        "generic/322",
        "generic/338",
        "generic/347",
        "generic/405",
        "generic/455",
        "generic/461",
        "generic/464",
        "generic/466",
        "generic/482",
        "generic/484",
        "generic/487",
        "generic/500",
        "generic/520",
        "generic/556",
        "generic/563",
        "generic/570",
        "generic/590",
        "generic/623",
        "generic/740",
        "generic/749",
        "generic/757",
        "overlay/005",
        "overlay/010",
        "overlay/014",
        "overlay/019",
        "overlay/031",
        "overlay/035",
        "overlay/036",
        "overlay/037",
        "overlay/038",
        "overlay/041",
        "overlay/043",
        "overlay/044",
        "overlay/045",
        "overlay/046",
        "overlay/049",
        "overlay/051",
        "overlay/053",
        "overlay/055",
        "overlay/056",
        "overlay/057",
        "overlay/059",
        "overlay/060",
        "overlay/065",
        "overlay/067",
        "overlay/069",
        "overlay/070",
        "overlay/071",
        "overlay/077",
        "overlay/079",
        "overlay/080",
        "overlay/083",
        "overlay/084",
        "overlay/085",
        "overlay/086",
        "overlay/087",
        "xfs/001",
        "xfs/002",
        "xfs/005",
        "xfs/045",
        "xfs/049",
        "xfs/058",
        "xfs/070",
        "xfs/076",
        "xfs/081",
        "xfs/115",
        "xfs/132",
        "xfs/133",
        "xfs/134",
        "xfs/154",
        "xfs/155",
        "xfs/157",
        "xfs/162",
        "xfs/179",
        "xfs/202",
        "xfs/205",
        "xfs/270",
        "xfs/306",
        "xfs/310",
        "xfs/424",
        "xfs/438",
        "xfs/439",
        "xfs/448",
        "xfs/449",
        "xfs/490",
        "xfs/493",
        "xfs/495",
        "xfs/500",
        "xfs/503",
        "xfs/504",
        "xfs/506",
        "xfs/516",
        "xfs/520",
        "xfs/521",
        "xfs/522",
        "xfs/523",
        "xfs/524",
        "xfs/525",
        "xfs/526",
        "xfs/528",
        "xfs/530",
        "xfs/533",
        "xfs/546",
        "xfs/569",
        "xfs/601",
        "xfs/602",
        "xfs/603",
        "xfs/608",
        "xfs/798",
    ]

    def __init__(
        self,
        host_name=None,
        output_dir="crashes",
        full_log=False,
        decode_crash=True,
        reset_host=True,
        save_warnings=False,
        context_prefix=0,
        context_postfix=35,
        ssh_timeout=180,
    ):
        self.host_name = host_name
        self.output_dir = os.path.join(output_dir, host_name)
        self.save_warnings = save_warnings
        self.full_log = full_log
        self.decode_crash = decode_crash
        self.should_reset_host = reset_host
        self.topdir_path = None
        self.libvirt_provider = False
        self.libvirt_uri_system = False
        self.config = {}
        self.devconfig_enable_systemd_journal_remote = False
        self.kdevops_enable_guestfs = False
        self.ssh_timeout = ssh_timeout

        self.known_crashes = []
        self.last_known_console_line = None
        self.last_issue_count = 0
        self.latest_file_with_issue = None
        self.context_prefix = context_prefix
        self.context_postfix = context_postfix

        self.is_an_fstests = False
        self.current_test_id = None
        self.unexpected_corrupting_tests = set()
        self.test_logs = {}
        self.intentional_corruption_tests_seen = set()

        try:
            with open(EXTRA_VARS_FILE, "r") as f:
                self.config = yaml.safe_load(f)
                self.devconfig_enable_systemd_journal_remote = self.config.get(
                    "devconfig_enable_systemd_journal_remote", False
                )
                self.kdevops_enable_guestfs = self.config.get(
                    "kdevops_enable_guestfs", False
                )
                self.topdir_path = self.config.get("topdir_path")
                self.libvirt_provider = self.config.get("libvirt_provider", False)
                self.libvirt_uri_system = self.config.get("libvirt_uri_system", False)
        except Exception as e:
            logger.warning(f"Failed to read {EXTRA_VARS_FILE}: {e}")

        # Leave this last
        self.load_known_crashes()

    def normalize_kernel_snippet(self, log_content):
        # Allow both string or list inputs
        if isinstance(log_content, list):
            log_content = "\n".join(log_content)
        # Strip timestamps + hostnames from all lines
        clean_lines = []
        for line in log_content.splitlines():
            # Remove leading timestamps and hostnames (e.g., 'Oct 01 23:30:21 host kernel: ...')
            clean = re.sub(
                r"^[A-Z][a-z]{2}\s+\d+\s+\d{2}:\d{2}:\d{2}\s+[\w\-.]+", "", line
            )
            clean_lines.append(clean.strip())
        return clean_lines

    def get_qr_ascii(self, content, invert=True):
        """Return the ASCII QR code as a string."""
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(content)
        qr.make(fit=True)

        # Redirect stdout to capture print_ascii()
        buffer = io.StringIO()
        original_stdout = sys.stdout
        try:
            sys.stdout = buffer
            qr.print_ascii(invert=invert)
        finally:
            sys.stdout = original_stdout

        return buffer.getvalue()

    def load_known_crashes(self):
        """Load previously detected log hashes from the output directory."""
        if not os.path.exists(self.output_dir):
            return

        file_patterns = [
            "journal-*.crash",
            "journal-*.corruption",
            "journal-*.crash_and_corruption",
            "journal-*.warning",
        ]

        all_files = []
        for pattern in file_patterns:
            all_files.extend(glob.glob(os.path.join(self.output_dir, pattern)))

        max_issue = 0
        issue_pattern = re.compile(
            r"journal-(\d+)\.(?:crash|warning|corruption|crash_and_corruption)$"
        )

        for file_path in all_files:
            # Decoded files are just that, a variant of an existing file,
            # a decoded version of the crash file so just skip them.
            if ".decoded" in file_path:
                continue
            try:
                with open(file_path, "r") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    if not lines:
                        continue
                    match = issue_pattern.search(os.path.basename(file_path))
                    if match:
                        issue_number = int(match.group(1))
                        if issue_number > max_issue:
                            max_issue = issue_number
                            self.latest_file_with_issue = file_path
                            for line in reversed(lines[-5:]):
                                if line.startswith("console line number:"):
                                    try:
                                        self.last_known_console_line = int(
                                            line.split(":", 1)[1].strip()
                                        )
                                        logger.debug(
                                            f"Set last_known_console_line={self.last_known_console_line} from {file_path}"
                                        )
                                        break
                                    except ValueError:
                                        logger.warning(
                                            f"Malformed console line number in {file_path}: {line}"
                                        )

                    lines = self.normalize_kernel_snippet(lines)
                    normalized_text = "\n".join(lines)
                    context_patterns = (
                        self.CRASH_PATTERNS
                        + self.FILESYSTEM_CORRUPTION_PATTERNS
                        + self.WARNINGS
                    )
                    ignore_patterns = self.BENIGN_WARNINGS
                    kernel_snippet, key_log_line = self.extract_kernel_snippet(
                        normalized_text, context_patterns, ignore_patterns
                    )

                    if not key_log_line:
                        logger.warning(f"Error getting key log line for {file_path}")
                        continue
                    # Use the first relevant line for any context
                    log_hash = hashlib.md5(key_log_line.encode()).hexdigest()
                    self.known_crashes.append(log_hash)

                self.last_issue_count = max_issue

            except Exception as e:
                logger.warning(f"Failed to process known log file {file_path}: {e}")

    def is_known_crash(self, key_log_line=None):
        """Check if the crash log content matches a previously detected crash."""
        if not key_log_line:
            return True

        content_hash = hashlib.md5(key_log_line.encode()).hexdigest()

        return content_hash in self.known_crashes

    def get_host_ip(self):
        try:
            result = subprocess.run(
                ["ssh", "-G", self.host_name],
                capture_output=True,
                text=True,
                check=True,
            )
            for line in result.stdout.splitlines():
                if line.startswith("hostname "):
                    return line.split()[1]
        except subprocess.SubprocessError as e:
            logger.warning(f"Failed to resolve IP for {self.host_name}: {e}")
        return None

    def try_remote_journal(self):
        ip = self.get_host_ip()
        if not ip:
            return None

        journal_file = os.path.join(REMOTE_JOURNAL_DIR, f"remote-{ip}.journal")
        if not os.path.exists(journal_file):
            logger.info(
                f"Remote journal not found for {self.host_name} at {journal_file}"
            )
            return None

        try:
            result = subprocess.run(
                ["journalctl", "-k", f"--file={journal_file}"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return result.stdout
        except subprocess.SubprocessError as e:
            logger.warning(f"Failed to read remote journal for {self.host_name}: {e}")

        return None

    def convert_console_log(self):
        ip = self.get_host_ip()
        if not ip:
            return None

        console_dir = Path(f"guestfs/{self.host_name}")
        if not console_dir.exists():
            return None

        log_files = sorted(console_dir.glob("console.log*"), key=os.path.getmtime)
        if not log_files:
            return None

        all_lines = []

        for log_file in log_files:
            try:
                # Try reading file, fallback to sudo chown if permission denied
                try:
                    with open(log_file, "rb") as f:
                        raw = f.readlines()
                except PermissionError:
                    if getattr(self, "libvirt_uri_system", False):
                        logger.info(f"Fixing permissions for {log_file}")
                        subprocess.run(
                            [
                                "sudo",
                                "chown",
                                f"{getpass.getuser()}:{getpass.getuser()}",
                                str(log_file),
                            ],
                            check=True,
                        )
                        with open(log_file, "rb") as f:
                            raw = f.readlines()
                    else:
                        raise

                all_lines.extend(raw)
            except Exception as e:
                logger.warning(f"Failed to read {log_file}: {e}")

        # Decode all lines safely
        decoded_lines = [
            l.decode("utf-8", errors="replace").rstrip() for l in all_lines
        ]

        # Find last Linux version line
        linux_indices = [
            i for i, line in enumerate(decoded_lines) if "Linux version" in line
        ]
        if not linux_indices:
            logger.warning(
                f"No 'Linux version' line found in console logs for {self.host_name}"
            )
            return None

        start_index = linux_indices[-1]

        try:
            btime_output = subprocess.run(
                ["awk", "/^btime/ {print $2}", "/proc/stat"],
                capture_output=True,
                text=True,
                check=True,
            )
            btime = int(btime_output.stdout.strip())
            boot_time = datetime.fromtimestamp(btime)
        except Exception as e:
            logger.warning(f"Failed to get boot time: {e}")
            return None

        # Convert logs from last boot only
        converted_lines = []
        for line in decoded_lines[start_index:]:
            match = re.match(r"\[\s*(\d+\.\d+)\] (.*)", line)
            if match:
                seconds = float(match.group(1))
                wall_time = boot_time + timedelta(seconds=seconds)
                timestamp = wall_time.strftime("%b %d %H:%M:%S")
                converted_lines.append(f"{timestamp} {self.host_name} {match.group(2)}")
            else:
                converted_lines.append(line)

        return "\n".join(converted_lines)

    def check_host_reachable(self):
        try:
            result = subprocess.run(
                ["ssh", self.host_name, "true"], capture_output=True, timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, subprocess.SubprocessError):
            return False

    def collect_journal(self):
        try:
            result = subprocess.run(
                ["ssh", self.host_name, "sudo journalctl -k -b"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return result.stdout
            else:
                logger.error(f"Failed to collect journal: {result.stderr}")
                return None
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            logger.error(f"Error collecting journal: {e}")
            return None

    def detect_crash(self, log_content):
        if not log_content:
            return False
        for pattern in self.CRASH_PATTERNS:
            if re.search(pattern, log_content):
                return True
        return False

    def detect_filesystem_corruption(self, log_content):
        if not log_content:
            return False
        for pattern in self.FILESYSTEM_CORRUPTION_PATTERNS:
            if re.search(pattern, log_content):
                return True
        return False

    def infer_fstests_state(self, log_content):
        current_test = None
        in_fstests = False
        lines = log_content.split("\n")

        for line in lines:
            if "run fstests fstestsstart/000" in line:
                in_fstests = True
                continue
            elif "run fstests fstestsdone/000" in line:
                in_fstests = False
                current_test = None
                continue
            elif in_fstests and "run fstests" in line:
                match = re.search(r"run fstests (\S+/\d+) ", line)
                if match:
                    current_test = match.group(1)
                    self.test_logs.setdefault(current_test, [])
                    continue

            if in_fstests and current_test:
                self.test_logs[current_test].append(line)

        for test, logs in self.test_logs.items():
            if test in self.INTENTIONAL_CORRUPTION_TESTS:
                self.intentional_corruption_tests_seen.add(test)
            else:
                for pattern in self.FILESYSTEM_CORRUPTION_PATTERNS:
                    for line in logs:
                        if re.search(pattern, line):
                            self.unexpected_corrupting_tests.add(test)
                            break

        self.is_an_fstests = bool(self.test_logs)
        if self.test_logs:
            self.current_test_id = list(self.test_logs.keys())[-1]

    def get_fstests_log(self, test_id):
        if test_id in self.test_logs:
            return "\n".join(self.test_logs[test_id])
        logger.warning(f"Test ID {test_id} not found in log records")
        return None

    def extract_kernel_snippet(
        self, log_content, context_patterns, ignore_patterns=None
    ):
        if not log_content:
            return None, None

        if self.full_log:
            return log_content, None

        benign_regexes = None
        if ignore_patterns:
            benign_regexes = [re.compile(p) for p in ignore_patterns]

        lines = self.normalize_kernel_snippet(log_content)
        issue_line_idx = -1
        issue_pattern = None

        for pattern in context_patterns:
            for i, line in enumerate(lines):
                if re.search(pattern, line):
                    if ignore_patterns and benign_regexes:
                        if any(p.search(line) for p in benign_regexes):
                            continue
                    issue_line_idx = i
                    issue_pattern = pattern
                    break
            if issue_line_idx != -1:
                break

        if issue_line_idx == -1:
            return None, None

        start_idx = max(0, issue_line_idx - self.context_prefix)
        end_idx = min(len(lines), issue_line_idx + self.context_postfix)
        crash_context = "\n".join(lines[start_idx:end_idx])
        key_log_line = lines[issue_line_idx].strip()

        return f"{crash_context}\n\nconsole line number: {end_idx}", key_log_line

    def decode_log_output(self, log_file):
        if not self.decode_crash:
            return

        if not self.topdir_path:
            return

        decode_script = os.path.join(
            self.topdir_path, "linux/scripts/decode_stacktrace.sh"
        )
        vmlinux_path = os.path.join(self.topdir_path, "linux/vmlinux")

        if not (os.path.exists(decode_script) and os.path.exists(vmlinux_path)):
            logger.info("Skipping crash decode: required files not found")
            return

        try:
            logger.info("Decoding crash log with decode_stacktrace.sh...")
            base, ext = os.path.splitext(log_file)
            decoded_file = f"{base}.decoded{ext}"
            with open(log_file, "r") as log_input, open(
                decoded_file, "w"
            ) as log_output:
                subprocess.run(
                    [decode_script, vmlinux_path],
                    stdin=log_input,
                    stdout=log_output,
                    stderr=subprocess.STDOUT,
                    check=True,
                )
            logger.info(f"Decoded kernel log saved to: {decoded_file}")
        except subprocess.SubprocessError as e:
            logger.warning(f"Failed to decode kernel log output: {e}")

    def save_log(self, kernel_snippet, context, key_line=None):
        if not kernel_snippet or not key_line:
            return None

        log_hash = hashlib.md5(key_line.encode()).hexdigest()
        if log_hash in self.known_crashes:
            logger.info(f"Skipping known {context} for {self.host_name}: {key_line}")
            return None

        log_file = self.next_issue_filename(context)
        os.makedirs(self.output_dir, exist_ok=True)

        qr = self.get_qr_ascii(key_line)
        with open(log_file, "w") as f:
            f.write(kernel_snippet)
            f.write(f"\n\nQR Code:\n{qr}")

        self.known_crashes.append(log_hash)
        logger.info(f"{context} log saved to: {log_file} for: {key_line}")
        return log_file

    def reset_host_now(self):
        if not self.should_reset_host:
            logger.info("Host reset disabled by user")
            return False

        if self.libvirt_provider:
            virsh_cmd = ["virsh", "reset", self.host_name]
            if self.libvirt_uri_system:
                virsh_cmd.insert(0, "sudo")

            try:
                result = subprocess.run(virsh_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Successfully reset host {self.host_name}")
                    return True
                else:
                    logger.error(f"Failed to reset host: {result.stderr}")
                    return False
            except subprocess.SubprocessError as e:
                logger.error(f"Error resetting host: {e}")
                return False
        else:
            logger.warning("Reset for non-libvirt providers is not yet implemented")
            return False

    def wait_for_ssh(self):
        logger.info(f"Waiting for {self.host_name} to become reachable via SSH...")
        try:
            subprocess.run(
                [
                    "ansible",
                    "'baseline:dev'",
                    "-m",
                    "wait_for_connection",
                    "-l",
                    self.host_name,
                ],
                check=True,
                timeout=self.ssh_timeout,
            )
            logger.info(f"{self.host_name} is now reachable.")
        except subprocess.TimeoutExpired:
            logger.error(
                f"Timeout: SSH connection to {self.host_name} did not succeed within {self.ssh_timeout} seconds. This kernel is probably seriously broken."
            )
            sys.exit(1)
        except subprocess.CalledProcessError as e:
            logger.warning(f"Failed to wait for SSH on {self.host_name}: {e}")
            sys.exit(1)

    def next_issue_filename(self, context):
        self.last_issue_count += 1
        return os.path.join(
            self.output_dir, f"journal-{self.last_issue_count:04d}.{context}"
        )

    def check_and_reset_host(self, method="auto", get_fstests_log=None):
        crash_file = None
        warnings_file = None
        journal_logs = None

        # 1. Try console log first if guestfs is enabled
        if method == "console" or (method == "auto" and self.kdevops_enable_guestfs):
            logger.debug(f"Trying console.log fallback for {self.host_name}")
            journal_logs = self.convert_console_log()

        # 2. Try remote journal if that didn't work and it's enabled.
        # If you are using a cloud provider try to get systemd remote journal
        # devconfig_enable_systemd_journal_remote working so you can leverage
        # this. Experience seems to be that it may not capture all crashes.
        if not journal_logs and (
            method == "remote"
            or (method == "auto" and self.devconfig_enable_systemd_journal_remote)
        ):
            journal_logs = self.try_remote_journal()
            if journal_logs:
                logger.debug(f"Using remote journal logs for {self.host_name}")

        # 3. Fallback to SSH-based journal access if nothing worked yet
        if (
            not journal_logs
            and (method == "ssh" or method == "auto")
            and self.check_host_reachable()
        ):
            logger.debug(f"Trying SSH-based journalctl access for {self.host_name}")
            journal_logs = self.collect_journal()

        if not journal_logs:
            logger.warning(f"Unable to collect logs for {self.host_name}, resetting")
            self.reset_host_now()
            self.wait_for_ssh()
            return None, None

        journal_logs = self.normalize_kernel_snippet(journal_logs)

        if self.last_known_console_line is not None:
            journal_logs = journal_logs[self.last_known_console_line :]
            logger.debug(
                f"Trimmed journal logs starting at console line {self.last_known_console_line} "
                f"({len(journal_logs)} lines remain)"
            )

        journal_logs = "\n".join(journal_logs)

        self.infer_fstests_state(journal_logs)

        warnings = []
        if self.save_warnings:
            warning_context_patterns = self.WARNINGS
            warning_ignore_patterns = self.BENIGN_WARNINGS
            warning_snippet, key_log_line = self.extract_kernel_snippet(
                journal_logs, warning_context_patterns, warning_ignore_patterns
            )
            if warning_snippet and key_log_line:
                warning_hash = hashlib.md5(key_log_line.encode()).hexdigest()

                if warning_hash in self.known_crashes:
                    logger.debug(f"Skipping known warning for {self.host_name}")
                else:
                    os.makedirs(self.output_dir, exist_ok=True)
                    warning_file = self.next_issue_filename("warning")
                    qr = self.get_qr_ascii(key_log_line)
                    with open(warning_file, "w") as out:
                        out.write(warning_snippet)
                        out.write(f"\n\nQR Code:\n{qr}")
                    self.known_crashes.append(warning_hash)
                    logger.info(
                        f"Saved new kernel warning to: {warning_file}: {key_log_line}"
                    )

        if get_fstests_log:
            log_output = self.get_fstests_log(get_fstests_log)
            if log_output:
                print(log_output)
            return None, None

        crash_detected = self.detect_crash(journal_logs)
        fs_corruption_detected = self.detect_filesystem_corruption(journal_logs)

        if warnings and not crash_detected and not fs_corruption_detected:
            logger.debug(f"Only warnings found for {self.host_name}, skipping reset")
            return None, warnings_file

        if (
            fs_corruption_detected
            and self.is_an_fstests
            and not self.unexpected_corrupting_tests
        ):
            fs_corruption_detected = False

        if crash_detected and fs_corruption_detected:
            issue_context = "crash_and_corruption"
            context_patterns = self.CRASH_PATTERNS + self.FILESYSTEM_CORRUPTION_PATTERNS
        elif crash_detected:
            issue_context = "crash"
            context_patterns = self.CRASH_PATTERNS
        elif fs_corruption_detected:
            issue_context = "corruption"
            context_patterns = self.FILESYSTEM_CORRUPTION_PATTERNS
        else:
            return None, None

        kernel_snippet, key_log_line = self.extract_kernel_snippet(
            journal_logs, context_patterns
        )
        if not kernel_snippet or not key_log_line:
            logger.warning(
                f"Unable to extract valid kernel snippet for {self.host_name}"
            )
            return None, None

        # Check if this is a known crash before proceeding
        if self.is_known_crash(key_log_line):
            logger.debug(f"Detected known crash for {self.host_name}, skipping")
            return None, None

        # This can be a crash or an unexpected filesystem corruption
        log_file = self.save_log(kernel_snippet, issue_context, key_log_line)
        if log_file:  # Only decode and reset if we actually saved a new crash
            self.decode_log_output(log_file)
            self.reset_host_now()
            self.wait_for_ssh()

        return log_file, warnings_file

# SPDX-License-Identifier: copyleft-next-0.3.1

import subprocess, os, sys
from datetime import datetime


class SystemdError(Exception):
    pass


class ExecutionError(SystemdError):
    def __init__(self, errcode):
        self.error_code = errcode


class TimeoutExpired(SystemdError):
    def __init__(self, errcode):
        self.error_code = errcode
        return "timeout"


def get_host_ip(host):
    try:
        result = subprocess.run(
            ["ssh", "-G", host], capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            if line.startswith("hostname "):
                return line.split()[1]
    except subprocess.SubprocessError as e:
        logger.warning(f"Failed to resolve IP for {host}: {e}")
    return None


def get_current_time(host):
    format = "%Y-%m-%d %H:%M:%S"
    today = datetime.today()
    today_str = today.strftime(format)
    return today_str


def get_extra_journals(remote_path, host):
    ip = get_host_ip(host)
    extra_journals_path = "remote-" + ip + "@"
    extra_journals = []
    for file in os.listdir(remote_path):
        if extra_journals_path in file:
            extra_journals.append("--file")
            extra_journals.append(remote_path + file)
    return extra_journals


def get_uname(remote_path, host, configured_kernel):
    ip = get_host_ip(host)
    extra_journals = get_extra_journals(remote_path, host)
    fpath = remote_path + "remote-" + ip + ".journal"
    grep = "Linux version"
    grep_str = '"Linux version"'
    cmd = ["journalctl", "--no-pager", "-n 1", "-k", "-g", grep, "--file", fpath]
    cmd = cmd + extra_journals
    cmd_verbose = [
        "journalctl",
        "--no-pager",
        "-n 1",
        "-k",
        "-g",
        grep_str,
        "--file",
        fpath,
    ]
    cmd_verbose = cmd_verbose + extra_journals
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        universal_newlines=True,
    )
    data = None
    try:
        data = process.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        return "Timeout"
    else:
        process.wait()
        if process.returncode != 0:
            if configured_kernel is None:
                sys.stderr.write("\nProcess returned non-zero")
                sys.stderr.write("\nCommand used:\n%s\n\n" % " ".join(cmd_verbose))
            return configured_kernel
        last_line = data[0].strip()
        if grep not in last_line:
            sys.stderr.write("\nThe string %s was not found in the journal." % grep_str)
            sys.stderr.write("\nCommand used:\n%s\n\n" % " ".join(cmd_verbose))
            return None
        if len(last_line.split(grep)) <= 1:
            sys.stderr.write(
                "\nThe string %s could not be used to split the line." % grep_str
            )
            sys.stderr.write("\nCommand used:\n%s\n\n" % " ".join(cmd_verbose))
            return None
        kernel_line = last_line.split(grep)[1].strip()
        if len(last_line.split()) <= 1:
            sys.stderr.write(
                "\nThe string %s was used but could not find kernel version." % grep_str
            )
            sys.stderr.write("\nCommand used:\n%s\n\n" % " ".join(cmd_verbose))
            return None
        kernel = kernel_line.split()[0].strip()

        return kernel


# Returns something like "xfs/040 at 2023-12-17 23:52:14"
def get_test(remote_path, host, suite):
    ip = get_host_ip(host)
    if suite not in ["fstests", "blktests"]:
        return None
    # Example: /var/log/journal/remote/remote-line-xfs-reflink.journal
    fpath = remote_path + "remote-" + ip + ".journal"
    extra_journals = get_extra_journals(remote_path, host)
    run_string = "run " + suite
    cmd = ["journalctl", "--no-pager", "-n 1", "-k", "-g", run_string, "--file", fpath]
    cmd = cmd + extra_journals
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True,
        universal_newlines=True,
    )
    data = None
    try:
        data = process.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        return "Timeout"
    else:
        process.wait()
        if process.returncode != 0:
            return None
        last_line = data[0].strip()
        if "at " not in last_line:
            return None
        if len(last_line.split("at ")) <= 1:
            return None
        test_line = last_line.split(run_string)[1].strip()

        return test_line


def get_last_fstest(remote_path, host):
    return get_test(remote_path, host, "fstests")


def get_last_blktest(remote_path, host):
    return get_test(remote_path, host, "blktests")

#!/usr/bin/python3
# SPDX-License-Identifier: copyleft-next-0.3.1

# fstests test watchdog for kdevops
#
# Example usage:
#
# ./fstests_watchdog.py kdevops/hosts all

from datetime import datetime
from lib import kssh
from lib import fstests
from lib import systemd_remote
from lib.crash import KernelCrashWatchdog
import sys, os, grp
import configparser
import argparse
from itertools import chain


def print_fstest_host_status(host, verbose, use_remote, use_ssh, basedir, config):
    if "CONFIG_DEVCONFIG_ENABLE_SYSTEMD_JOURNAL_REMOTE" in config and not use_ssh:
        configured_kernel = None
        if "CONFIG_WORKFLOW_LINUX_DISTRO" in config:
            configured_kernel = "Distro-kernel"
        elif "CONFIG_BOOTLINUX_TREE_REF" in config:
            configured_kernel = config["CONFIG_BOOTLINUX_TREE_REF"].strip('"')
        remote_path = "/var/log/journal/remote/"
        kernel = systemd_remote.get_uname(remote_path, host, configured_kernel)
        if kernel == configured_kernel:
            kernel += " (custom)"
        if kernel is None:
            sys.stderr.write("No kernel could be identified for host: %s\n" % host)
            sys.exit(1)
    else:
        kernel = kssh.get_uname(host).rstrip()

    section = fstests.get_section(host, config)
    (last_test, last_test_time, current_time_str, delta_seconds, stall_suspect) = (
        fstests.get_fstest_host(
            use_remote, use_ssh, host, basedir, kernel, section, config
        )
    )

    checktime = fstests.get_checktime(host, basedir, kernel, section, last_test)
    percent_done = (delta_seconds * 100 / checktime) if checktime > 0 else 0

    stall_str = "OK"
    if stall_suspect:
        if kernel == "Timeout" or last_test is None:
            stall_str = "Timeout"
        else:
            stall_str = "Hung-Stalled"

    crash_state = "OK"
    watchdog = KernelCrashWatchdog(
        host_name=host, decode_crash=True, reset_host=True, save_warnings=True
    )
    crash_file, warning_file = watchdog.check_and_reset_host()
    if crash_file:
        crash_state = "CRASH"
    elif warning_file:
        crash_state = "WARNING"

    if not verbose:
        soak_duration_seconds = int(
            config.get("CONFIG_FSTESTS_SOAK_DURATION", "0").strip('"')
        )
        uses_soak = fstests.fstests_test_uses_soak_duration(last_test or "")
        is_soaking = uses_soak and soak_duration_seconds != 0
        soaking_str = "(soak)" if is_soaking else ""
        percent_done_str = "%.0f%% %s" % (percent_done, soaking_str)
        if delta_seconds is None:
            delta_seconds = 0
        if checktime is None:
            checktime = 0
        sys.stdout.write(
            f"{host:>25}  {last_test or 'None':>15}  {percent_done_str:>15}  "
            f"{delta_seconds:>12}  {checktime:>17}  {stall_str:>13}  "
            f"{kernel:<38}  {crash_state:<10}\n"
        )
        return

    sys.stdout.write("Host               : %s\n" % (host))
    sys.stdout.write("Last    test       : %s\n" % (last_test))
    sys.stdout.write("Last    test   time: %s\n" % (last_test_time))
    sys.stdout.write("Current system time: %s\n" % (current_time_str))
    sys.stdout.write("Delta: %d total second\n" % (delta_seconds))
    sys.stdout.write("\t%d minutes\n" % (delta_seconds / 60))
    sys.stdout.write("\t%d seconds\n" % (delta_seconds % 60))
    sys.stdout.write(
        "Timeout-status: %s\n" % ("POSSIBLE-STALL" if stall_suspect else "OK")
    )
    sys.stdout.write("Crash-status  : %s\n" % crash_state)


def _main():
    parser = argparse.ArgumentParser(description="fstest-watchdog")
    parser.add_argument(
        "hostfile",
        metavar="<ansible hostfile>",
        type=str,
        default="hosts",
        help="Ansible hostfile to use",
    )
    parser.add_argument(
        "hostsection",
        metavar="<ansible hostsection>",
        type=str,
        default="baseline",
        help="The name of the section to read hosts from",
    )
    parser.add_argument(
        "--verbose",
        const=True,
        default=False,
        action="store_const",
        help="Be verbose on output.",
    )
    parser.add_argument(
        "--use-systemd-remote",
        const=True,
        default=True,
        action="store_const",
        help="Use systemd-remote uploaded journals if available",
    )
    parser.add_argument(
        "--use-ssh",
        const=True,
        default=False,
        action="store_const",
        help="Force to only use ssh for journals.",
    )
    args = parser.parse_args()

    if not os.path.isfile(args.hostfile):
        sys.stdout.write("%s does not exist\n" % (args.hostfile))
        sys.exit(1)

    dotconfig = os.path.dirname(os.path.abspath(args.hostfile)) + "/.config"
    config = fstests.get_config(dotconfig)
    if not config:
        sys.stdout.write("%s does not exist\n" % (dotconfig))
        sys.exit(1)
    basedir = os.path.dirname(dotconfig)

    remote_group = "systemd-journal-remote"
    if "CONFIG_DEVCONFIG_ENABLE_SYSTEMD_JOURNAL_REMOTE" in config and not args.use_ssh:
        group = grp.getgrnam(remote_group)
        if group is not None:
            remote_gid = group[2]
            if remote_gid not in os.getgrouplist(os.getlogin(), os.getgid()):
                sys.stderr.write(
                    "Your username is not part of the group %s\n" % remote_group
                )
                sys.stderr.write("Fix this and try again")
                sys.exit(1)
        else:
            sys.stderr.write(
                "The group %s was not found, add Kconfig support for the systemd-remote-journal group used"
                % remote_group
            )
            sys.exit(1)

    hosts = fstests.get_hosts(args.hostfile, args.hostsection)
    sys.stdout.write(
        f"{'Hostname':>25}  {'Test-name':>15}  {'Completion %':>15}  "
        f"{'runtime(s)':>12}  {'last-runtime(s)':>17}  {'Stall-status':>13}  "
        f"{'Kernel':<38}  {'Crash-status':<10}\n"
    )
    for h in hosts:
        print_fstest_host_status(
            h, args.verbose, args.use_systemd_remote, args.use_ssh, basedir, config
        )

    soak_duration_seconds = int(
        config.get("CONFIG_FSTESTS_SOAK_DURATION", "0").strip('"')
    )
    journal_method = "ssh"
    if "CONFIG_DEVCONFIG_ENABLE_SYSTEMD_JOURNAL_REMOTE" in config and not args.use_ssh:
        journal_method = "systemd-journal-remote"

    sys.stdout.write("\n%25s%20s\n" % ("Journal-method", "Soak-duration(s)"))
    sys.stdout.write("%25s%20d\n" % (journal_method, soak_duration_seconds))


if __name__ == "__main__":
    ret = _main()

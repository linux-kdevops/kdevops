#!/usr/bin/env python3
"""
Lucid Ansible Callback Plugin

A modern stdout callback plugin providing:
- Clean, minimal output with progressive verbosity levels
- Task-level output control via output_verbosity variable
- Comprehensive logging (always max verbosity)
- Dynamic terminal display (Yocto/BitBake style) for interactive use
- Static output for CI/CD and non-interactive terminals
"""

from __future__ import annotations

import atexit
import json
import os
import shutil
import sys
import time
import threading
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from collections import deque

from ansible.plugins.callback import CallbackBase
from ansible import constants as C
from ansible import context

DOCUMENTATION = """
    name: lucid
    type: stdout
    short_description: Clean, minimal Ansible output with dynamic display
    description:
        - Provides clean, minimal output by default
        - Progressive verbosity levels (-v, -vv, -vvv)
        - Task-level output control via output_verbosity variable
        - Comprehensive logging independent of display verbosity
        - Dynamic live display for interactive terminals
        - Static output for CI/CD environments
    author:
        - Daniel Gomez (@dagmcr) <da.gomez@samsung.com>
    extends_documentation_fragment:
        - default_callback
        - result_format_callback
    requirements:
        - Ansible 2.10+
        - Python 3.8+
    options:
        output_mode:
            description: Output display mode (auto, static, dynamic)
            default: auto
            type: str
            ini:
                - section: callback_lucid
                  key: output_mode
            env:
                - name: ANSIBLE_LUCID_OUTPUT_MODE
            choices: ['auto', 'static', 'dynamic']
"""


class CallbackModule(CallbackBase):
    """
    Lucid callback plugin for clean, minimal Ansible output
    with dynamic terminal display and comprehensive logging.
    """

    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "stdout"
    CALLBACK_NAME = "lucid"

    # Spinner animation frames
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    # Status symbols and colors (used consistently across static, dynamic, and logging)
    STATUS_SYMBOLS = {
        "ok": "✓",
        "changed": "*",
        "failed": "✗",
        "skipped": "⊘",
        "unreachable": "!",
    }

    STATUS_COLORS = {
        "ok": C.COLOR_OK,
        "changed": C.COLOR_CHANGED,
        "failed": C.COLOR_ERROR,
        "skipped": C.COLOR_SKIP,
        "unreachable": C.COLOR_UNREACHABLE,
    }

    # Default terminal width when detection fails
    DEFAULT_TERMINAL_WIDTH = 80

    def __init__(self):
        super(CallbackModule, self).__init__()

        # State tracking
        self.running_tasks: Dict[Tuple[str, str], Dict[str, Any]] = (
            {}
        )  # (host, task_uuid) -> task_info
        self.completed_tasks = deque(maxlen=3)  # Keep last 3 completed
        self.current_task_name: str = ""
        self.current_task_hosts: List[str] = []
        self.play_hosts: List[str] = []  # All hosts in current play
        self.pending_play_header: Optional[str] = None  # Deferred play banner
        self.current_play_name: str = ""  # Current play name for dynamic display

        # Dynamic display state
        self.display_lines = 0
        self.last_update = 0.0
        self.spinner_index = 0
        self.dynamic_mode = False
        self.update_thread: Optional[threading.Thread] = None
        self.update_thread_stop: Optional[threading.Event] = None
        self.task_lock = threading.Lock()
        self.output_lock = threading.Lock()

        # Failed loop items for display on task failure
        self.failed_items: List[dict] = []

        # Will be set in set_options()
        self.output_mode = "auto"
        self.log_file_path: Optional[str] = None
        self.log_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_write_failed = False

    def set_options(self, task_keys=None, var_options=None, direct=None):
        """Set plugin options from ansible.cfg"""
        super(CallbackModule, self).set_options(
            task_keys=task_keys, var_options=var_options, direct=direct
        )

        # Load configuration
        self.output_mode = self.get_option("output_mode")

        # Cache standard stdout-callback options from the default_callback
        # fragment so we pay the lookup cost once, not per-result.
        self.display_ok_hosts = self.get_option("display_ok_hosts")
        self.display_skipped_hosts = self.get_option("display_skipped_hosts")
        self.display_failed_stderr = self.get_option("display_failed_stderr")
        self.check_mode_markers = self.get_option("check_mode_markers")
        self.show_custom_stats = self.get_option("show_custom_stats")
        self.show_task_path_on_failure = self.get_option("show_task_path_on_failure")

        # Determine display mode based on configuration
        is_interactive = self._detect_interactive()
        if self.output_mode == "static":
            self.dynamic_mode = False
        elif self.output_mode == "dynamic":
            self.dynamic_mode = True
        else:  # 'auto' or any other value
            self.dynamic_mode = is_interactive

        # Initialize logging
        self._init_log_file()

        # Start update thread for dynamic mode
        if self.dynamic_mode:
            self._start_update_thread()

    def _detect_interactive(self) -> bool:
        """Detect if running in interactive terminal"""
        return (
            sys.stdout.isatty()
            and sys.stderr.isatty()
            and os.getenv("TERM") != "dumb"
            and os.getenv("CI") is None
            and os.getenv("JENKINS_HOME") is None
            and os.getenv("GITHUB_ACTIONS") is None
            and os.getenv("GITLAB_CI") is None
        )

    def _init_log_file(self):
        """Defer log file creation until playbook name is known"""
        # Log file path will be set in _create_log_file when playbook starts
        pass

    def _create_log_file(self, playbook_name: str):
        """Create log file with playbook name and timestamp using auto-detection"""
        if self.log_file_path:
            # Already initialized
            return

        # Remove extension from playbook name
        playbook_base = os.path.splitext(playbook_name)[0]

        # Try default locations in order (project dir first, then user home, then system)
        attempts = [
            f".ansible/logs/{playbook_base}-{self.log_timestamp}.log",
            os.path.expanduser(
                f"~/.ansible/logs/{playbook_base}-{self.log_timestamp}.log"
            ),
            f"/var/log/ansible/{playbook_base}-{self.log_timestamp}.log",
        ]

        for path in attempts:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                # Test write access
                with open(path, "a"):
                    pass
                self.log_file_path = path
                break
            except (PermissionError, OSError):
                continue

        if self.log_file_path:
            try:
                with open(self.log_file_path, "w") as f:
                    f.write(
                        f"=== Ansible Playbook Log Started: {datetime.now().isoformat()} ===\n"
                    )
                    f.write(f"=== Playbook: {playbook_name} ===\n\n")
            except (PermissionError, OSError) as e:
                self._display.warning(
                    f"Could not initialize log file {self.log_file_path}: {e}"
                )
                self.log_file_path = None

    def _write_to_log(self, message: str):
        """Write to log file with timestamp (always max verbosity)"""
        if self.log_file_path:
            timestamp = datetime.now().isoformat()
            try:
                with open(self.log_file_path, "a") as f:
                    f.write(f"[{timestamp}] {message}\n")
            except (PermissionError, OSError) as e:
                # Warn once on first failure, then disable logging
                if not self.log_write_failed:
                    self._display.warning(f"Log write failed, disabling logging: {e}")
                    self.log_write_failed = True
                    self.log_file_path = None

    def _start_update_thread(self):
        """Start background thread for live display updates"""
        self.update_thread_stop = threading.Event()
        self.update_thread = threading.Thread(target=self._update_loop)
        self.update_thread.start()
        atexit.register(self._cleanup)

    def _cleanup(self):
        """Clean up display thread and reset terminal state"""
        if self.update_thread_stop:
            self.update_thread_stop.set()
        if self.update_thread:
            self.update_thread.join(timeout=2.0)
        # Reset terminal state
        if self.dynamic_mode and self.display_lines > 0:
            self._clear_display()
        with self.output_lock:
            sys.stdout.write("\033[?25h")  # Ensure cursor visible
            sys.stdout.flush()

    def _update_loop(self):
        """Update display every 0.5 seconds in dynamic mode"""
        while not self.update_thread_stop.is_set():
            if self.running_tasks:
                self._redraw_display()
            time.sleep(0.5)

    def _should_display_output(self, result, status: str) -> bool:
        """
        Determine if task output should be shown based on verbosity.

        Rules:
        - Changed tasks: ALWAYS show
        - Failed tasks: ALWAYS show
        - OK tasks: Show if current_verbosity >= task's output_verbosity
          and display_ok_hosts is enabled
        - Skipped tasks: Only at -v or higher and display_skipped_hosts enabled
        """
        # Changed and failed always show
        if status == "changed" or status == "failed" or status == "unreachable":
            return True

        # Skipped only at -v, and only when the user wants to see skipped hosts
        if status == "skipped":
            return self._display.verbosity >= 1 and self.display_skipped_hosts

        # Suppress OK output entirely when the user has disabled ok-host display
        if status == "ok" and not self.display_ok_hosts:
            return False

        # Get task verbosity setting (default is 1)
        task_verbosity = self._get_task_verbosity(result)

        # Compare with current verbosity
        current_verbosity = self._display.verbosity

        return current_verbosity >= task_verbosity

    def _get_task_verbosity(self, result) -> int:
        """Get the output_verbosity setting for a task (default is 1)"""
        task_verbosity = 1
        if hasattr(result, "_task_fields"):
            task_vars = result._task_fields.get("vars", {})
            task_verbosity = task_vars.get("output_verbosity", 1)
        elif hasattr(result, "_task"):
            task_vars = getattr(result._task, "vars", {})
            task_verbosity = task_vars.get("output_verbosity", 1)
        return task_verbosity

    def _get_task_command(self, result) -> Optional[str]:
        """
        Extract the resolved command from modules that execute shell commands.
        Returns None for modules that don't expose their commands.
        Only returns fully resolved commands — never raw Jinja2 templates.

        Supported modules:
        - ansible.builtin.shell/command: returns cmd (string or list)
        - ansible.builtin.pip: returns cmd (string)
        - community.general.make: returns command (string)
        - community.general.flatpak: returns command (string)
        - community.general.flatpak_remote: returns command (string)
        - community.general.terraform: returns command (string)
        """
        res = result._result
        action = result._task.action

        # Modules that return 'cmd' key in the result (already resolved)
        if action in (
            "ansible.builtin.shell",
            "ansible.builtin.command",
            "ansible.builtin.pip",
            "shell",
            "command",
            "pip",
        ):
            if "cmd" in res:
                cmd = res["cmd"]
                if isinstance(cmd, list):
                    return " ".join(cmd)
                return cmd
            return None

        # Modules that return 'command' key in the result
        if action in (
            "community.general.make",
            "community.general.flatpak",
            "community.general.flatpak_remote",
            "community.general.terraform",
            "make",
            "flatpak",
            "flatpak_remote",
            "terraform",
        ):
            if "command" in res:
                return res["command"]
            return None

        return None

    def _has_significant_output(self, result) -> bool:
        """Check if result has stdout, stderr, or msg content worth showing"""
        res = result._result
        return bool(
            (res.get("stdout") and res["stdout"].strip())
            or (res.get("stderr") and res["stderr"].strip())
            or (res.get("msg") and not res.get("stdout"))
        )

    def _get_terminal_width(self) -> int:
        """Get current terminal width, with fallback to default"""
        try:
            size = shutil.get_terminal_size(fallback=(self.DEFAULT_TERMINAL_WIDTH, 24))
            return size.columns
        except Exception:
            return self.DEFAULT_TERMINAL_WIDTH

    def _truncate_line(self, line: str, max_width: Optional[int] = None) -> str:
        """Truncate line to fit terminal width, adding ellipsis if needed"""
        if max_width is None:
            max_width = self._get_terminal_width()

        if len(line) <= max_width:
            return line

        # Reserve 3 characters for ellipsis
        if max_width <= 3:
            return "..." if max_width >= 3 else line[:max_width]

        return line[: max_width - 3] + "..."

    def _format_duration(self, seconds: float, width: int = 0) -> str:
        """Format duration as human readable, optionally right-aligned to width"""
        if seconds < 60:
            duration = f"{seconds:.1f}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            duration = f"{mins}m {secs}s"
        elif seconds < 86400:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            duration = f"{hours}h {mins}m"
        else:
            days = int(seconds // 86400)
            hours = int((seconds % 86400) // 3600)
            duration = f"{days}d {hours}h"

        if width > 0:
            return duration.rjust(width)
        return duration

    def _display_message(self, message: str, color=None, stderr: bool = False):
        """Display message with optional color, optionally to stderr"""
        with self.output_lock:
            if color:
                self._display.display(message, color=color, stderr=stderr)
            else:
                self._display.display(message, stderr=stderr)

    # ========================================================================
    # Ansible v2 Callback Methods
    # ========================================================================

    def v2_playbook_on_start(self, playbook):
        """Playbook started"""
        playbook_name = os.path.basename(playbook._file_name)

        # Create log file now that we have playbook name
        self._create_log_file(playbook_name)

        msg = f"PLAYBOOK: {playbook_name}"
        self._display_message(msg, C.COLOR_HIGHLIGHT)
        self._write_to_log(msg)

        # Show log file path early so user can tail -f
        if self.log_file_path:
            with self.output_lock:
                self._display.display(f"Log: {self.log_file_path}")

        # Emit the standard DRY RUN banner at the start of check-mode runs
        # when the user has opted into check_mode_markers.
        if self.check_mode_markers and context.CLIARGS.get("check"):
            self._display_message("DRY RUN", C.COLOR_HIGHLIGHT)

    def v2_playbook_on_play_start(self, play):
        """Play started"""
        name = play.get_name().strip()

        # Get actual host list from play (resolved from inventory)
        # play.hosts is just the pattern, we need to get actual hosts
        self.play_hosts = []
        try:
            # Get hosts from the play's host list (resolved by PlayIterator)
            host_list = (
                play.get_variable_manager()
                .get_vars(play=play)
                .get("ansible_play_hosts_all", [])
            )
            if host_list:
                self.play_hosts = list(host_list)
        except (AttributeError, TypeError):
            # Fallback: hosts will be populated as tasks start
            pass

        hosts = play.hosts
        if isinstance(hosts, list):
            hosts_str = ", ".join(hosts[:3])
            if len(hosts) > 3:
                hosts_str += f" (+{len(hosts) - 3} more)"
        else:
            hosts_str = str(hosts)

        # Suffix check-mode plays with [CHECK MODE] when the option is on.
        check_suffix = (
            " [CHECK MODE]"
            if (self.check_mode_markers and getattr(play, "check_mode", False))
            else ""
        )

        msg = f"\nPLAY: {name} [{hosts_str}]{check_suffix}"
        with self.task_lock:
            self.current_play_name = f"PLAY: {name} [{hosts_str}]{check_suffix}"
            self.pending_play_header = msg
        self._write_to_log(msg)

    def _flush_play_header(self):
        """Print deferred play header on first task of the play"""
        with self.task_lock:
            header = self.pending_play_header
            self.pending_play_header = None
        if header and not self.dynamic_mode:
            self._display_message(header, C.COLOR_HIGHLIGHT)

    def v2_playbook_on_task_start(self, task, is_conditional):
        """Task started"""
        task_name = task.get_name().strip()

        # Suppress empty arg spec validation tasks injected by Ansible for
        # every role regardless of tag filtering (ansible/ansible#82505).
        # Still flush the play header in case real tasks follow.
        is_empty_argspec = task_name == "Validating arguments against arg spec None"
        if is_empty_argspec:
            self._write_to_log(f"TASK: {task_name}")
            return

        self._flush_play_header()

        # Suffix check-mode tasks with [CHECK MODE] when enabled.
        check_suffix = (
            " [CHECK MODE]"
            if (self.check_mode_markers and getattr(task, "check_mode", False))
            else ""
        )
        display_name = f"{task_name}{check_suffix}"

        with self.task_lock:
            self.current_task_name = display_name
            self.failed_items = []
            # Initialize with play hosts so display is stable from the start
            self.current_task_hosts = list(self.play_hosts) if self.play_hosts else []

        # In static mode, print immediately (compact - no leading newline)
        if not self.dynamic_mode:
            msg = f"TASK: {display_name}"
            self._display_message(msg, C.COLOR_HIGHLIGHT)

        self._write_to_log(f"TASK: {display_name}")

    def v2_playbook_on_include(self, included_file):
        """Include/import tasks file has been loaded.

        Fires when include_tasks or import_tasks actually pulls in a
        file. CallbackBase leaves this as a no-op, so lucid used to
        stay silent on includes even though they frequently change
        the branch of tasks about to run. We log unconditionally and
        mirror the log line to the terminal at -v or higher, using
        the same skip/included color as the reference default
        callback so visually the line reads as flow control rather
        than a task result.
        """
        filename = included_file._filename
        hosts = ",".join(h.name for h in included_file._hosts)
        msg = f"INCLUDED: {filename} for {hosts}"
        if self._display.verbosity >= 1:
            with self.output_lock:
                self._display.display(msg, color=C.COLOR_SKIP)
        self._write_to_log(msg)

    def v2_playbook_on_notify(self, handler, host):
        """A task triggered a notify on a host.

        Well-written playbooks fan out many notifications, most of
        which never translate to a handler run if nothing changed.
        We log each notification unconditionally (the log is the
        audit trail) but only surface them on screen at -v or
        higher, matching the reference default callback's quiet
        default so lucid doesn't drown the user in pending-handler
        chatter.
        """
        handler_name = handler.get_name()
        host_name = host.get_name() if hasattr(host, "get_name") else str(host)
        msg = f"NOTIFY: {handler_name} on {host_name}"
        if self._display.verbosity >= 1:
            with self.output_lock:
                self._display.display(msg, color=C.COLOR_VERBOSE)
        self._write_to_log(msg)

    def v2_playbook_on_no_hosts_matched(self):
        """A play's hosts pattern matched zero inventory hosts.

        This is almost always a user error (typo in the pattern,
        wrong inventory loaded, stale group name), so we always
        display it regardless of verbosity. Coloring matches the
        reference default callback's skip palette so the line reads
        as a skipped play rather than a failure.
        """
        msg = "skipping: no hosts matched"
        with self.output_lock:
            self._display.display(msg, color=C.COLOR_SKIP)
        self._write_to_log(msg)

    def v2_playbook_on_no_hosts_remaining(self):
        """All hosts have been removed from the active set.

        Fires when any_errors_fatal or max_fail_percentage escalates
        a failure out of scope and there is nothing left to run
        against. Always displayed in error color because the
        playbook is about to end prematurely and the user needs to
        see why.
        """
        msg = "NO MORE HOSTS LEFT"
        with self.output_lock:
            self._display.display(msg, color=C.COLOR_ERROR)
        self._write_to_log(msg)

    def v2_playbook_on_handler_task_start(self, task):
        """A notified handler task is beginning to run.

        Handlers are load-bearing: they encode the state-change side
        effects of an otherwise-successful play. Inherited as a
        no-op from CallbackBase, lucid had no way to distinguish a
        silent handler run from no handler run at all. We emit the
        task name with a HANDLER: prefix so log consumers can grep
        for state transitions, and feed the dynamic display with the
        same current_task_name pipeline regular tasks use.
        """
        task_name = task.get_name().strip()
        with self.task_lock:
            self.current_task_name = task_name
            self.failed_items = []
            self.current_task_hosts = list(self.play_hosts) if self.play_hosts else []

        if not self.dynamic_mode:
            msg = f"HANDLER: {task_name}"
            self._display_message(msg, C.COLOR_HIGHLIGHT)
        self._write_to_log(f"HANDLER: {task_name}")

    def v2_runner_on_start(self, host, task):
        """Task started on a host (for dynamic tracking)"""
        key = (host.name, task._uuid)

        # Check for task delegation
        delegate_to = getattr(task, "delegate_to", None)

        with self.task_lock:
            self.running_tasks[key] = {
                "start_time": time.time(),
                "host": host.name,
                "delegate_to": delegate_to,
                "task_name": task.get_name().strip(),
            }
            if host.name not in self.current_task_hosts:
                self.current_task_hosts.append(host.name)

        if self.dynamic_mode:
            self._redraw_display()

    def v2_runner_on_ok(self, result):
        """Task succeeded"""
        changed = result._result.get("changed", False)
        status = "changed" if changed else "ok"
        self._handle_result(result, status)

    def v2_runner_on_failed(self, result, ignore_errors=False):
        """Task failed"""
        self._handle_result(result, "failed", ignore_errors=ignore_errors)

    def v2_runner_on_skipped(self, result):
        """Task skipped"""
        self._handle_result(result, "skipped")

    def v2_runner_on_unreachable(self, result):
        """Host unreachable"""
        self._handle_result(result, "unreachable")

    def v2_runner_on_async_poll(self, result):
        """Async task polled and has not yet finished.

        Async tasks fire this hook repeatedly between dispatch and
        completion. It is noisy by design, so we only emit on screen
        at -vv or higher and always route through the log with a
        consistent ASYNC POLL: prefix so post-hoc debugging can
        reconstruct the polling cadence.
        """
        host = result._host.name
        ajid = result._result.get("ansible_job_id", "")
        msg = f"ASYNC POLL: [{host}] job {ajid}"
        if self._display.verbosity >= 2:
            with self.output_lock:
                self._display.display(msg, color=C.COLOR_VERBOSE)
        self._write_to_log(msg)

    def v2_runner_on_async_ok(self, result):
        """Async task finished successfully.

        Routing through _handle_result treats async completion the
        same as a sync ok: the running-task map clears, the dynamic
        display updates, and failed_items / logging behave
        identically. Without this, lucid would show async tasks as
        perpetually running because the normal on_ok never fires
        for them.
        """
        changed = result._result.get("changed", False)
        status = "changed" if changed else "ok"
        self._handle_result(result, status)

    def v2_runner_on_async_failed(self, result):
        """Async task finished with a failure.

        Same routing as on_async_ok, but lands in the failed branch
        of _handle_result so the dynamic display freezes and output
        is surfaced the way a sync failure would be.
        """
        self._handle_result(result, "failed")

    def v2_runner_item_on_ok(self, result):
        """Loop item succeeded — log per-item command and output"""
        self._log_item_result(result)

    def v2_runner_item_on_failed(self, result):
        """Loop item failed — log per-item command and output"""
        self._log_item_result(result)
        # Read label-related fields from the raw result: the _ansible_item_label
        # and ansible_loop_var keys are Ansible bookkeeping that identify the
        # item and are not user-content subject to no_log redaction. The
        # rendered stdout/stderr/msg, however, come from the cleaned copy so
        # the per-item failure buffer never carries unredacted payload.
        res = result._result
        item = res.get("_ansible_item_label")
        if item is None:
            loop_var = res.get("ansible_loop_var", "item")
            item = res.get(loop_var, "")
        if isinstance(item, dict):
            item = item.get("name", item.get("group", str(item)))
        cleaned = self._cleaned_result(result)
        self.failed_items.append({
            "item": item,
            "stderr": cleaned.get("stderr", ""),
            "stdout": cleaned.get("stdout", ""),
            "msg": cleaned.get("msg", ""),
            "cmd": self._get_task_command(result),
        })

    def v2_runner_item_on_skipped(self, result):
        """Loop item skipped"""
        pass

    def _log_item_result(self, result):
        """Log per-item command and output for loop tasks"""
        res = result._result
        item = res.get("_ansible_item_label")
        if item is None:
            loop_var = res.get("ansible_loop_var", "item")
            item = res.get(loop_var, "")
        if isinstance(item, dict):
            item = item.get("name", item.get("group", str(item)))

        command = self._get_task_command(result)
        if command:
            self._write_to_log(f"  [{item}] $ {command}")

        if res.get("stdout"):
            self._write_to_log(f"  [{item}] stdout: {res['stdout']}")
        if res.get("stderr"):
            self._write_to_log(f"  [{item}] stderr: {res['stderr']}")
        if res.get("msg") and not res.get("stdout"):
            msg = res["msg"]
            if isinstance(msg, (list, dict)):
                msg = json.dumps(msg, indent=2)
            self._write_to_log(f"  [{item}] msg: {msg}")

    def v2_on_file_diff(self, result):
        """Render task diff output when --diff is enabled.

        Ansible populates result._result['diff'] with before/after
        structures when the user runs with --diff. The default callback
        renders these via _get_diff, but lucid previously did not
        implement this hook at all, so --diff was silently dropped. We
        wire it in using CallbackBase._get_diff so the formatting honors
        the same result_format / pretty_results / result_indentation
        options the rest of the result rendering does. On-screen display
        is gated behind verbosity >= 1 so lucid stays silent at the
        default verbosity; the log always captures the diff regardless
        so post-hoc debugging has the full picture.
        """
        diff_data = result._result.get("diff")
        if not diff_data:
            return

        # Handle loop tasks: diffs can be nested under results[*].diff.
        if isinstance(diff_data, list) and diff_data and all(
            isinstance(d, dict) for d in diff_data
        ):
            diffs_to_render = diff_data
        elif isinstance(diff_data, dict):
            diffs_to_render = [diff_data]
        else:
            diffs_to_render = diff_data

        diff_text = self._get_diff(diffs_to_render)
        if not diff_text:
            return

        if self._display.verbosity >= 1:
            with self.output_lock:
                self._display.display(diff_text)
        self._write_to_log(f"DIFF:\n{diff_text}")

    def v2_runner_retry(self, result):
        """Task is being retried after failure"""
        host = result._host.name
        task_uuid = result._task._uuid
        key = (host, task_uuid)

        retries = result._result.get("retries", 0)
        attempts = result._result.get("attempts", 0)

        # Update retry info in running_tasks
        with self.task_lock:
            if key in self.running_tasks:
                self.running_tasks[key]["retry_attempt"] = attempts
                self.running_tasks[key]["retry_total"] = retries

        # Log the retry attempt
        self._write_to_log(f"  ✗ [{host}] retry {attempts}/{retries} - retrying...")

        # In static mode, show retry immediately
        if not self.dynamic_mode:
            msg = f"  ✗ [{host}] retry {attempts}/{retries}"
            self._display_message(msg, C.COLOR_WARN)

    def v2_playbook_on_stats(self, stats):
        """Final summary"""
        # Stop update thread
        if self.update_thread_stop:
            self.update_thread_stop.set()
        if self.update_thread:
            self.update_thread.join(timeout=1.0)

        # Clear dynamic display if active
        if self.dynamic_mode and self.display_lines > 0:
            self._clear_display()

        # Print recap
        self._display_recap(stats)

        # Log file footer
        self._write_to_log(
            f"\n=== Playbook Completed: {datetime.now().isoformat()} ==="
        )

    # ========================================================================
    # Result Handling
    # ========================================================================

    def _handle_result(self, result, status: str, ignore_errors: bool = False):
        """Unified result handler for all task outcomes"""
        host = result._host.name
        task_uuid = result._task._uuid
        key = (host, task_uuid)

        # Calculate duration with defensive access
        with self.task_lock:
            task_info = self.running_tasks.pop(key, None)
        start_time = (
            task_info.get("start_time", time.time()) if task_info else time.time()
        )
        duration = time.time() - start_time

        # Get delegation info from result (more reliable than task attribute)
        delegated_vars = result._result.get("_ansible_delegated_vars", {})
        delegate_to = delegated_vars.get("ansible_delegated_host")

        # Store result data for dynamic mode display
        result_data = {
            "result": result,
            "status": status,
            "duration": duration,
            "host": host,
            "delegate_to": delegate_to,
            "task_name": result._task.get_name().strip(),
        }

        # Add to completed tasks (last 3 for dynamic mode)
        with self.task_lock:
            self.completed_tasks.append(result_data)

        # Log everything (max verbosity)
        self._log_result(result, status, duration)

        # Display based on mode
        if self.dynamic_mode:
            # Dynamic mode will update on next refresh
            # Freeze display and show output for failed/unreachable tasks (not ignored)
            if status in ("failed", "unreachable") and not ignore_errors:
                self._freeze_and_show_output(result_data)
        else:
            # Show per-item failures before the aggregate result
            if self.failed_items and status == "failed":
                self._display_failed_items()
            # Static mode - display immediately
            self._display_result_static(result, status, duration)

    def _display_result_static(self, result, status: str, duration: float):
        """Display result in static mode"""
        host = result._host.name

        # Early exit for tasks that shouldn't be shown at current verbosity
        # At verbosity 0: only show changed, failed, unreachable
        if self._display.verbosity < 1 and status in ("ok", "skipped"):
            return

        # Respect the standard default_callback options: users who set
        # display_ok_hosts=False or display_skipped_hosts=False want those
        # classes of results hidden even when verbosity would otherwise
        # reveal them.
        if status == "ok" and not self.display_ok_hosts:
            return
        if status == "skipped" and not self.display_skipped_hosts:
            return

        # Determine if we should show output (for tasks that pass visibility check)
        show_output = self._should_display_output(result, status)

        # Format status line using class constants
        symbol = self.STATUS_SYMBOLS.get(status, "?")
        color = self.STATUS_COLORS.get(status, C.COLOR_OK)

        # Get delegation info for display (like Ansible default: [host -> delegate])
        delegated_vars = result._result.get("_ansible_delegated_vars", {})
        delegate_to = delegated_vars.get("ansible_delegated_host")
        if delegate_to:
            host_display = f"{host} -> {delegate_to}"
        else:
            host_display = host

        # Format time (always shown for all statuses)
        time_str = f" ({self._format_duration(duration)})"

        # Route failed / unreachable task output to stderr when the user has
        # set display_failed_stderr. This matches the ansible default callback.
        use_stderr = self.display_failed_stderr and status in (
            "failed",
            "unreachable",
        )

        # Status line with unicode spacing (using regular spaces, not braille)
        status_line = f"  {symbol} [{host_display}]{time_str}"
        self._display_message(status_line, color, stderr=use_stderr)

        # Show command for supported modules when running with -v or higher
        if self._display.verbosity >= 1:
            command = self._get_task_command(result)
            if command:
                # Truncate very long commands
                if len(command) > 200:
                    command = command[:197] + "..."
                with self.output_lock:
                    self._display.display(
                        f"    $ {command}",
                        color=C.COLOR_VERBOSE,
                        stderr=use_stderr,
                    )

        # Resolve the failing task's source path when we are meant to show
        # it: either the user opted in via show_task_path_on_failure, or they
        # asked for -vv+ verbosity which always exposes the path in the
        # reference default callback.
        task_path = ""
        if status in ("failed", "unreachable") and (
            self.show_task_path_on_failure or self._display.verbosity >= 2
        ):
            try:
                task_path = result._task.get_path() or ""
            except AttributeError:
                task_path = ""

        # Show output if conditions met
        if show_output:
            self._display_output(result, stderr=use_stderr, task_path=task_path)
        elif task_path:
            # Still surface the failing task's source location even when the
            # body is suppressed (e.g. no stdout/stderr/msg to display).
            self._display_message(
                f"task path: {task_path}", color=C.COLOR_VERBOSE, stderr=use_stderr
            )

    def _cleaned_result(self, result):
        """Return a cleaned copy of result._result suitable for display.

        CallbackBase._clean_results mutates in place, so we copy first to
        preserve the original for other observers. The returned dict has
        debug-module specific redaction applied; the _ansible_* bookkeeping
        keys are only stripped when we subsequently pass through
        _dump_results (which calls strip_internal_keys on its own deep copy).
        For the ad-hoc stdout/stderr/msg reads the lucid compact format does
        at verbosity 0–1, reading cleaned[...] is safe because no_log results
        arrive at callbacks with their payload already replaced by a
        'censored' placeholder at the executor level.
        """
        cleaned = result._result.copy()
        self._clean_results(cleaned, result._task.action)
        return cleaned

    def _display_output(self, result, stderr: bool = False, task_path: str = ""):
        """Display stdout/stderr/msg from task result"""
        output = []
        cleaned = self._cleaned_result(result)

        # stdout
        if "stdout" in cleaned and cleaned["stdout"]:
            output.append(f"\nSTDOUT:\n{cleaned['stdout']}")

        # stderr
        if "stderr" in cleaned and cleaned["stderr"]:
            output.append(f"\nSTDERR:\n{cleaned['stderr']}")

        # msg (only if no stdout content)
        if "msg" in cleaned and cleaned["msg"] and not cleaned.get("stdout"):
            msg_text = cleaned["msg"]
            # Handle lists/dicts in msg
            if isinstance(msg_text, (list, dict)):
                msg_text = json.dumps(msg_text, indent=2)
            output.append(f"\nMSG:\n{msg_text}")

        # exception (Python traceback from module failures)
        if "exception" in cleaned and cleaned["exception"]:
            output.append(f"\nEXCEPTION:\n{cleaned['exception']}")

        # At -vvv or higher the user explicitly asked for the full structured
        # result. Delegate serialization to _dump_results so the user's
        # result_format, pretty_results, result_yaml_line_width, and
        # result_indentation options (declared via the result_format_callback
        # doc fragment) actually take effect. _dump_results strips _ansible_*
        # keys internally, so secrets and bookkeeping are not leaked even at
        # the highest verbosity.
        if self._display.verbosity >= 3:
            dump = self._dump_results(cleaned, keep_invocation=False)
            output.append(f"\n{dump}")

        # Task source path for failures, mirroring the default callback's
        # show_task_path_on_failure behavior.
        if task_path:
            output.append(f"\ntask path: {task_path}")

        if output:
            with self.output_lock:
                self._display.display("".join(output), stderr=stderr)

    def _log_result(self, result, status: str, duration: float):
        """Write result to log file (always max verbosity)"""
        host = result._host.name
        res = result._result

        # Produce a cleaned copy of the result for the log body. We copy first
        # because CallbackBase._clean_results mutates in place, and we must
        # not touch the original result dict (other callbacks and downstream
        # code may still observe it). _clean_results handles debug-module
        # specific redaction; for the full dump below we rely on
        # _dump_results, which strips every _ansible_* bookkeeping key and
        # honors no_log redaction through strip_internal_keys.
        cleaned = res.copy()
        self._clean_results(cleaned, result._task.action)

        # Get delegation info for logging (read from raw res — this is the
        # public _ansible_delegated_vars contract surface, not sensitive user
        # content).
        delegated_vars = res.get("_ansible_delegated_vars", {})
        delegate_to = delegated_vars.get("ansible_delegated_host")
        if delegate_to:
            host_display = f"{host} -> {delegate_to}"
        else:
            host_display = host

        # Status line using class constants
        symbol = self.STATUS_SYMBOLS.get(status, "?")
        time_str = self._format_duration(duration)
        log_line = f"  {symbol} [{host_display}] ({time_str})"
        self._write_to_log(log_line)

        # Log command for supported modules (skip for skipped/unreachable — no resolved command)
        if status not in ("skipped", "unreachable"):
            command = self._get_task_command(result)
            if command:
                self._write_to_log(f"\n$ {command}")

        # Always log full output. Read from the cleaned dict so tasks marked
        # no_log have their stdout/stderr/msg already censored by the task
        # runner (ansible replaces the result body with a censored placeholder
        # before dispatching to callbacks) and so debug-module results are
        # trimmed to the keys _clean_results allows.
        if "stdout" in cleaned and cleaned["stdout"]:
            self._write_to_log(f"\nSTDOUT:\n{cleaned['stdout']}\n")

        if "stderr" in cleaned and cleaned["stderr"]:
            self._write_to_log(f"\nSTDERR:\n{cleaned['stderr']}\n")

        if "msg" in cleaned and cleaned["msg"]:
            msg_text = cleaned["msg"]
            if isinstance(msg_text, (list, dict)):
                msg_text = json.dumps(msg_text, indent=2)
            self._write_to_log(f"\nMSG:\n{msg_text}\n")

        if status == "failed" and "exception" in cleaned:
            self._write_to_log(f"\nEXCEPTION:\n{cleaned['exception']}\n")

        # Always record the failing task's source path in the log, regardless
        # of the show_task_path_on_failure option or verbosity, so the log
        # stays self-sufficient for post-hoc debugging of failures.
        if status in ("failed", "unreachable"):
            try:
                task_path = result._task.get_path()
            except AttributeError:
                task_path = None
            if task_path:
                self._write_to_log(f"task path: {task_path}")

        # Append a full structured dump so the log carries the complete result
        # for post-hoc debugging. _dump_results runs strip_internal_keys on a
        # deep copy, which drops every _ansible_* bookkeeping key and yields a
        # redaction-safe serialization even when higher verbosity is not in
        # effect. indent=4 keeps the dump readable regardless of the user's
        # result_format / pretty_results choices for on-screen output; the log
        # is a stable audit trail, not user-facing display.
        full_dump = self._dump_results(cleaned, indent=4, keep_invocation=False)
        self._write_to_log(f"FULL RESULT:\n{full_dump}")

    def _display_recap(self, stats):
        """Display final statistics"""
        self._display_message("\nPLAY RECAP", C.COLOR_HIGHLIGHT)

        hosts = sorted(stats.processed.keys())
        for host in hosts:
            summary = stats.summarize(host)

            # More compact format
            msg = (
                f"{host:25s} : "
                f"ok={summary['ok']:<3d} "
                f"changed={summary['changed']:<3d} "
                f"unreachable={summary['unreachable']:<3d} "
                f"failed={summary['failures']:<3d} "
                f"skipped={summary['skipped']:<3d}"
            )

            # Color based on status
            if summary["failures"] > 0 or summary["unreachable"] > 0:
                color = C.COLOR_ERROR
            elif summary["changed"] > 0:
                color = C.COLOR_CHANGED
            else:
                color = C.COLOR_OK

            self._display_message(msg, color)

        # Render custom set_stats aggregation when the user has opted in.
        custom = getattr(stats, "custom", None)
        if self.show_custom_stats and custom:
            self._display_message("\nCUSTOM STATS:", C.COLOR_HIGHLIGHT)
            for key in sorted(k for k in custom.keys() if k != "_run"):
                value = json.dumps(custom[key], indent=1).replace("\n", "")
                self._display_message(f"\t{key}: {value}")
            if "_run" in custom:
                run_value = json.dumps(custom["_run"], indent=1).replace("\n", "")
                self._display_message(f"\tRUN: {run_value}")

        # Mirror the default callback's closing DRY RUN banner when markers
        # are enabled and the playbook was invoked with --check.
        if self.check_mode_markers and context.CLIARGS.get("check"):
            self._display_message("\nDRY RUN", C.COLOR_HIGHLIGHT)

    # ========================================================================
    # Dynamic Mode Display
    # ========================================================================

    def _redraw_display(self):
        """Redraw entire display in dynamic mode"""
        # Snapshot all shared state under task_lock for a consistent frame
        with self.task_lock:
            now = time.time()
            if now - self.last_update < 0.1:
                return
            self.last_update = now

            self.spinner_index = (self.spinner_index + 1) % len(self.SPINNER_FRAMES)
            spinner_idx = self.spinner_index

            task_name = self.current_task_name
            task_hosts = list(self.current_task_hosts)
            completed = list(self.completed_tasks)
            play_name = self.current_play_name
            running_hosts = {
                host: dict(info) for (host, _), info in self.running_tasks.items()
            }

        # Clear previous display
        self._clear_display()

        # Get terminal width once for all lines
        term_width = self._get_terminal_width()

        # Build new display
        lines = []

        # Play header
        if play_name:
            lines.append(self._truncate_line(play_name, term_width))

        # Task header - truncate to terminal width
        if task_name:
            task_line = f"TASK: {task_name}"
            lines.append(self._truncate_line(task_line, term_width))
            lines.append("")

        # Host status - show ALL hosts in task, running ones get spinner
        if task_hosts:
            running_count = len(running_hosts)
            total_hosts = len(task_hosts)
            lines.append(f"Hosts: {running_count}/{total_hosts} running")

            spinner = self.SPINNER_FRAMES[spinner_idx]

            # Show all hosts in stable order, running ones with spinner
            # Format: [spinner] <time> <hostname> - time is fixed width (8 chars)
            # This keeps spinner and time columns stable, hostname varies at end
            time_width = 8  # Enough for "1m 30s", "10h 5m", or "99d 23h"

            for host in task_hosts:
                if host in running_hosts:
                    # Running - show spinner, time, then hostname
                    task_info = running_hosts[host]
                    elapsed = time.time() - task_info["start_time"]
                    duration_str = self._format_duration(elapsed, width=time_width)

                    # Get delegation info
                    delegate_to = task_info.get("delegate_to")
                    if delegate_to:
                        host_display = f"{host} -> {delegate_to}"
                    else:
                        host_display = host

                    # Build retry suffix if applicable
                    retry_suffix = ""
                    if "retry_attempt" in task_info:
                        attempt = task_info["retry_attempt"]
                        total = task_info["retry_total"]
                        retry_suffix = f" (retry {attempt}/{total})"

                    # Format: spinner, fixed-width time, hostname at end
                    host_line = (
                        f"  [{spinner}] {duration_str}  {host_display}{retry_suffix}"
                    )
                else:
                    # Not running - show empty brackets and blank time column
                    blank_time = " " * time_width
                    host_line = f"  [ ] {blank_time}  {host}"

                lines.append(self._truncate_line(host_line, term_width))

            lines.append("")

        # Recently completed (after running tasks)
        if completed:
            lines.append("Recent:")
            for task_data in completed:
                status = task_data["status"]
                host = task_data["host"]
                duration = task_data["duration"]
                task_name = task_data.get("task_name", "Unknown task")
                delegate_to = task_data.get("delegate_to")

                # Format host with delegation if present
                if delegate_to:
                    host_display = f"{host} -> {delegate_to}"
                else:
                    host_display = host

                # Use class constants for consistent symbols
                symbol = self.STATUS_SYMBOLS.get(status, "?")

                time_str = self._format_duration(duration)
                recent_line = f"  {symbol} {task_name} [{host_display}] ({time_str})"
                lines.append(self._truncate_line(recent_line, term_width))
            lines.append("")

        # Display all lines atomically
        if lines:
            output = "\n".join(lines)
            with self.output_lock:
                sys.stdout.write(output)
                sys.stdout.flush()
            # Count actual lines printed (number of newlines + 1 for the last line)
            self.display_lines = output.count("\n") + 1
        else:
            self.display_lines = 0

    def _clear_display(self):
        """Clear dynamic display using ANSI escape codes"""
        if self.display_lines > 0:
            # Build full escape sequence then write atomically under lock
            buf = "\r\033[2K"
            for _ in range(self.display_lines - 1):
                buf += "\033[1A\033[2K"
            with self.output_lock:
                sys.stdout.write(buf)
                sys.stdout.flush()
            self.display_lines = 0

    def _display_failed_items(self):
        """Display collected per-item failures and clear the list"""
        use_stderr = self.display_failed_stderr
        with self.output_lock:
            for fi in self.failed_items:
                label = fi["item"]
                if fi["cmd"]:
                    self._display.display(
                        f"  [{label}] $ {fi['cmd']}",
                        color=C.COLOR_VERBOSE,
                        stderr=use_stderr,
                    )
                if fi["stderr"]:
                    self._display.display(
                        f"  [{label}] stderr: {fi['stderr']}",
                        color=C.COLOR_ERROR,
                        stderr=use_stderr,
                    )
                if fi["stdout"]:
                    self._display.display(
                        f"  [{label}] stdout: {fi['stdout']}",
                        stderr=use_stderr,
                    )
                if fi["msg"] and not fi["stdout"]:
                    self._display.display(
                        f"  [{label}] msg: {fi['msg']}",
                        color=C.COLOR_ERROR,
                        stderr=use_stderr,
                    )
        with self.task_lock:
            self.failed_items = []

    def _freeze_and_show_output(self, result_data):
        """
        Freeze display and show task output in dynamic mode for failures.
        Disables dynamic mode for the rest of the playbook.
        """
        # Clear dynamic display
        if self.display_lines > 0:
            self._clear_display()

        # Show result in static format
        result = result_data["result"]
        status = result_data["status"]
        duration = result_data["duration"]

        # Print task name
        msg = f"TASK: {self.current_task_name}"
        self._display_message(msg, C.COLOR_HIGHLIGHT)

        # Show per-item failures before the aggregate result
        if self.failed_items:
            self._display_failed_items()

        # Show result with output
        self._display_result_static(result, status, duration)

        # Disable dynamic mode for rest of playbook after failure
        self.dynamic_mode = False
        if self.update_thread_stop:
            self.update_thread_stop.set()

"""Unit tests for the lucid Ansible callback plugin.

Run with:

    cd kdevops
    python3 -m unittest discover -s tests -v

The tests mock out the Ansible Display object and construct lightweight
stand-ins for CallbackTaskResult / TaskResult / Host / Task rather than
wiring up a full PlayIterator. This keeps the suite fast and lets each
test target a single helper or state transition in isolation.

If the environment cannot write to ~/.ansible/tmp (some sandboxes),
set ANSIBLE_LOCAL_TEMP and ANSIBLE_REMOTE_TEMP to a writable path before
running the suite.
"""

from __future__ import annotations

import copy
import os
import sys
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

import yaml

# Make the plugin importable without installing it.
HERE = os.path.dirname(os.path.abspath(__file__))
CALLBACK_DIR = os.path.abspath(os.path.join(HERE, "..", "..", "callback_plugins"))
if CALLBACK_DIR not in sys.path:
    sys.path.insert(0, CALLBACK_DIR)

try:
    import lucid  # noqa: E402
    ANSIBLE_IMPORT_ERROR = None
except Exception as exc:  # pragma: no cover - exercised only on broken envs
    lucid = None
    ANSIBLE_IMPORT_ERROR = exc


ANSIBLE_REQUIRED = unittest.skipIf(
    lucid is None,
    f"lucid callback plugin could not be imported: {ANSIBLE_IMPORT_ERROR!r}",
)


def _make_callback():
    """Build a CallbackModule with a mocked Display and pre-seeded options.

    Tests that exercise runner hooks need a cached option set in place of
    a real set_options() call (which would touch the config manager). We
    populate the attributes that set_options() would normally fill so
    downstream hooks behave deterministically.
    """
    cb = lucid.CallbackModule()
    cb._display = MagicMock()
    cb._display.verbosity = 0
    cb._display.columns = 80
    cb.dynamic_mode = False
    cb.display_ok_hosts = True
    cb.display_skipped_hosts = True
    cb.display_failed_stderr = False
    cb.check_mode_markers = False
    cb.show_custom_stats = False
    cb.show_task_path_on_failure = False
    return cb


@ANSIBLE_REQUIRED
class TestCallbackMetadata(unittest.TestCase):
    """Plugin identity constants must stay stable for Ansible to load it."""

    def test_callback_version(self):
        self.assertEqual(lucid.CallbackModule.CALLBACK_VERSION, 2.0)

    def test_callback_type(self):
        self.assertEqual(lucid.CallbackModule.CALLBACK_TYPE, "stdout")

    def test_callback_name(self):
        self.assertEqual(lucid.CallbackModule.CALLBACK_NAME, "lucid")


@ANSIBLE_REQUIRED
class TestDocumentation(unittest.TestCase):
    """DOCUMENTATION must be valid YAML and carry the expected fragments."""

    def test_documentation_parses(self):
        doc = yaml.safe_load(lucid.DOCUMENTATION)
        self.assertIsInstance(doc, dict)

    def test_documentation_required_keys(self):
        doc = yaml.safe_load(lucid.DOCUMENTATION)
        for key in (
            "name",
            "type",
            "author",
            "short_description",
            "description",
            "options",
            "extends_documentation_fragment",
        ):
            self.assertIn(key, doc, f"missing key: {key}")

    def test_documentation_extends_fragments(self):
        doc = yaml.safe_load(lucid.DOCUMENTATION)
        fragments = doc["extends_documentation_fragment"]
        self.assertIn("default_callback", fragments)
        self.assertIn("result_format_callback", fragments)


@ANSIBLE_REQUIRED
class TestDetectInteractive(unittest.TestCase):
    """_detect_interactive must flip to False in every common CI context."""

    def _run(self, env, tty):
        cb = _make_callback()
        with patch.dict(os.environ, env, clear=True):
            with patch("sys.stdout.isatty", return_value=tty):
                with patch("sys.stderr.isatty", return_value=tty):
                    return cb._detect_interactive()

    def test_clean_tty_is_interactive(self):
        self.assertTrue(self._run({}, tty=True))

    def test_not_a_tty(self):
        self.assertFalse(self._run({}, tty=False))

    def test_ci_env(self):
        self.assertFalse(self._run({"CI": "1"}, tty=True))

    def test_jenkins_env(self):
        self.assertFalse(self._run({"JENKINS_HOME": "/x"}, tty=True))

    def test_github_actions_env(self):
        self.assertFalse(self._run({"GITHUB_ACTIONS": "true"}, tty=True))

    def test_gitlab_ci_env(self):
        self.assertFalse(self._run({"GITLAB_CI": "true"}, tty=True))

    def test_term_dumb(self):
        self.assertFalse(self._run({"TERM": "dumb"}, tty=True))


@ANSIBLE_REQUIRED
class TestFormatDuration(unittest.TestCase):
    """_format_duration bucket boundaries.

    The helper uses strict < comparisons (e.g. < 60, < 3600, < 86400), so
    the values tested here hit each bucket exactly.
    """

    def setUp(self):
        self.cb = _make_callback()

    def test_sub_minute_uses_seconds(self):
        self.assertEqual(self.cb._format_duration(30), "30.0s")

    def test_one_minute_flat(self):
        self.assertEqual(self.cb._format_duration(60), "1m 0s")

    def test_sub_hour_upper_bound(self):
        self.assertEqual(self.cb._format_duration(3599), "59m 59s")

    def test_one_hour_flat(self):
        self.assertEqual(self.cb._format_duration(3600), "1h 0m")

    def test_sub_day_upper_bound(self):
        self.assertEqual(self.cb._format_duration(86399), "23h 59m")

    def test_one_day_flat(self):
        self.assertEqual(self.cb._format_duration(86400), "1d 0h")

    def test_width_right_aligns(self):
        result = self.cb._format_duration(30, width=8)
        self.assertEqual(result, "   30.0s")
        self.assertEqual(len(result), 8)


@ANSIBLE_REQUIRED
class TestTruncateLine(unittest.TestCase):
    """_truncate_line must preserve short input and trim long input with '...'."""

    def setUp(self):
        self.cb = _make_callback()

    def test_empty_string(self):
        self.assertEqual(self.cb._truncate_line("", 80), "")

    def test_shorter_than_width(self):
        self.assertEqual(self.cb._truncate_line("hello", 80), "hello")

    def test_equal_to_width(self):
        line = "a" * 10
        self.assertEqual(self.cb._truncate_line(line, 10), line)

    def test_longer_than_width_gets_ellipsis(self):
        line = "a" * 20
        result = self.cb._truncate_line(line, 10)
        self.assertEqual(result, "aaaaaaa...")
        self.assertEqual(len(result), 10)

    def test_tiny_width_returns_bare_ellipsis(self):
        # When max_width is exactly 3, the helper returns "..." for any
        # overflow rather than producing a degenerate output.
        self.assertEqual(self.cb._truncate_line("abcdef", 3), "...")


@ANSIBLE_REQUIRED
class TestGetTaskCommand(unittest.TestCase):
    """_get_task_command dispatches on the module action."""

    def setUp(self):
        self.cb = _make_callback()

    def _result(self, action, res):
        r = MagicMock()
        r._task.action = action
        r._result = res
        return r

    def test_shell_with_string_cmd(self):
        r = self._result("ansible.builtin.shell", {"cmd": "echo hi"})
        self.assertEqual(self.cb._get_task_command(r), "echo hi")

    def test_shell_with_list_cmd(self):
        r = self._result("ansible.builtin.shell", {"cmd": ["echo", "hi"]})
        self.assertEqual(self.cb._get_task_command(r), "echo hi")

    def test_command_module(self):
        r = self._result("ansible.builtin.command", {"cmd": "ls -la"})
        self.assertEqual(self.cb._get_task_command(r), "ls -la")

    def test_unsupported_module_returns_none(self):
        r = self._result("ansible.builtin.ping", {})
        self.assertIsNone(self.cb._get_task_command(r))

    def test_community_make_uses_command_key(self):
        r = self._result("community.general.make", {"command": "make -j4"})
        self.assertEqual(self.cb._get_task_command(r), "make -j4")

    def test_shell_missing_cmd_returns_none(self):
        # Previously there was a fallback to task.args["cmd"] that returned
        # the raw Jinja template; the fallback was removed, so a missing
        # cmd key in the result must resolve to None.
        r = self._result("ansible.builtin.shell", {})
        self.assertIsNone(self.cb._get_task_command(r))


@ANSIBLE_REQUIRED
class TestHandleResult(unittest.TestCase):
    """_handle_result drives the running/completed state machine."""

    def test_ok_result_promotes_task_to_completed(self):
        cb = _make_callback()

        result = MagicMock()
        result._host.name = "localhost"
        result._task.action = "ansible.builtin.command"
        result._task._uuid = "uuid-1"
        result._task.get_name.return_value = "test task"
        result._task.get_path.return_value = None
        result._result = {
            "cmd": "echo hi",
            "stdout": "hi",
            "stderr": "",
            "changed": True,
        }

        # Simulate v2_runner_on_start having seen this task.
        cb.running_tasks[("localhost", "uuid-1")] = {
            "start_time": time.time(),
            "host": "localhost",
            "delegate_to": None,
            "task_name": "test task",
        }

        cb.v2_runner_on_ok(result)

        self.assertEqual(len(cb.completed_tasks), 1)
        entry = cb.completed_tasks[0]
        self.assertEqual(entry["host"], "localhost")
        self.assertEqual(entry["status"], "changed")
        self.assertNotIn(("localhost", "uuid-1"), cb.running_tasks)


@ANSIBLE_REQUIRED
class TestItemOnFailed(unittest.TestCase):
    """v2_runner_item_on_failed must push a structured entry into failed_items."""

    def test_failed_item_records_label_and_streams(self):
        cb = _make_callback()

        result = MagicMock()
        result._task.action = "ansible.builtin.command"
        result._result = {
            "_ansible_item_label": "item-1",
            "stderr": "oops",
            "stdout": "",
            "msg": "failed",
        }

        cb.v2_runner_item_on_failed(result)

        self.assertEqual(len(cb.failed_items), 1)
        entry = cb.failed_items[0]
        self.assertEqual(entry["item"], "item-1")
        self.assertEqual(entry["stderr"], "oops")
        self.assertEqual(entry["msg"], "failed")


@ANSIBLE_REQUIRED
class TestCleanedResult(unittest.TestCase):
    """_cleaned_result must return a sanitized copy without mutating the original."""

    def test_debug_module_strips_bookkeeping(self):
        cb = _make_callback()

        result = MagicMock()
        result._task.action = "ansible.builtin.debug"
        original = {
            "changed": True,
            "invocation": "foo --bar",
            "msg": "hello",
        }
        result._result = copy.deepcopy(original)

        cleaned = cb._cleaned_result(result)

        # _clean_results strips changed / invocation for debug tasks but
        # leaves the user-facing msg in place.
        self.assertNotIn("changed", cleaned)
        self.assertNotIn("invocation", cleaned)
        self.assertEqual(cleaned.get("msg"), "hello")
        # The original result dict is never mutated by the helper.
        self.assertEqual(result._result, original)


@ANSIBLE_REQUIRED
class TestArgspecFilter(unittest.TestCase):
    """Empty argspec validation tasks must be suppressed from the task header."""

    def test_argspec_task_does_not_overwrite_current_task(self):
        cb = _make_callback()
        cb.current_task_name = "real task"

        argspec_task = MagicMock()
        argspec_task.get_name.return_value = (
            "Validating arguments against arg spec None"
        )

        cb.v2_playbook_on_task_start(argspec_task, is_conditional=False)

        self.assertEqual(cb.current_task_name, "real task")


@ANSIBLE_REQUIRED
class TestThreadCleanup(unittest.TestCase):
    """_cleanup must stop the update thread and leave the terminal usable."""

    def test_update_thread_stops_on_cleanup(self):
        cb = _make_callback()
        cb.dynamic_mode = True
        cb.display_lines = 0

        # Mimic _start_update_thread without triggering atexit registration,
        # which would leak a real thread across the test suite.
        cb.update_thread_stop = threading.Event()
        cb.update_thread = threading.Thread(target=cb._update_loop)
        cb.update_thread.start()

        # Let the update loop enter its first iteration.
        time.sleep(0.05)
        self.assertTrue(cb.update_thread.is_alive())

        cb._cleanup()

        self.assertTrue(cb.update_thread_stop.is_set())
        # _cleanup joins with a 2s timeout; confirm the thread has exited.
        self.assertFalse(cb.update_thread.is_alive())


if __name__ == "__main__":
    unittest.main()

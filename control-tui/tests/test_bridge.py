from pathlib import Path
import unittest
from unittest.mock import patch

from xiaozhi_control_tui.bridge import BridgeManager


class FakeProcess:
    def __init__(self, poll_values=None):
        self._poll_values = list(poll_values or [None, None])
        self.terminated = False
        self.killed = False
        self.wait_called = False

    def poll(self):
        if self._poll_values:
            return self._poll_values.pop(0)
        return None

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        self.wait_called = True
        return 0

    def kill(self):
        self.killed = True


class BridgeManagerTests(unittest.TestCase):
    def make_manager(self):
        return BridgeManager(
            Path(r"C:\bridge-root"),
            Path(r"C:\bridge-root\scripts\run-bridge-server-clean.ps1"),
            Path(r"C:\python.exe"),
        )

    @patch.object(BridgeManager, "stop", return_value=None)
    @patch.object(BridgeManager, "ensure_runtime", return_value=Path(r"C:\python.exe"))
    @patch("xiaozhi_control_tui.bridge.time.sleep", return_value=None)
    @patch("xiaozhi_control_tui.bridge.get_bridge_processes")
    @patch("xiaozhi_control_tui.bridge.subprocess.Popen")
    def test_start_returns_when_port_detected_even_if_wrapper_process_lingers(self, popen_mock, bridge_processes_mock, _sleep_mock, _runtime_mock, stop_mock):
        popen_mock.return_value = FakeProcess()
        bridge_processes_mock.side_effect = [[], [{"pid": 1234}], [{"pid": 1234}], [{"pid": 1234}], [{"pid": 1234}]]
        manager = self.make_manager()

        result = manager.start()

        stop_mock.assert_called_once()
        self.assertEqual(result.exit_code, 0)
        self.assertIn("Bridge server running on port 8000", result.output)
        self.assertTrue(popen_mock.return_value.terminated)

    @patch.object(BridgeManager, "stop", return_value=None)
    @patch.object(BridgeManager, "ensure_runtime", return_value=Path(r"C:\python.exe"))
    @patch("xiaozhi_control_tui.bridge.time.sleep", return_value=None)
    @patch("xiaozhi_control_tui.bridge.get_bridge_processes", return_value=[])
    @patch("xiaozhi_control_tui.bridge.subprocess.Popen")
    @patch.object(BridgeManager, "_tail_error_log", return_value=["--- bridge stderr ---", "boom"])
    def test_start_returns_failure_when_wrapper_exits_early(self, tail_mock, popen_mock, _bridge_processes_mock, _sleep_mock, _runtime_mock, _stop_mock):
        popen_mock.return_value = FakeProcess(poll_values=[17])
        manager = self.make_manager()

        result = manager.start()

        self.assertEqual(result.exit_code, 17)
        self.assertIn("Bridge start script exited early with code 17", result.output)
        self.assertIn("boom", result.output)

    @patch.object(BridgeManager, "stop", return_value=None)
    @patch.object(BridgeManager, "ensure_runtime", return_value=Path(r"C:\python.exe"))
    @patch("xiaozhi_control_tui.bridge.time.sleep", return_value=None)
    @patch("xiaozhi_control_tui.bridge.get_bridge_processes")
    @patch("xiaozhi_control_tui.bridge.subprocess.Popen")
    @patch.object(BridgeManager, "_tail_error_log", return_value=["--- bridge stderr ---", "bridge vanished"])
    def test_start_fails_when_bridge_drops_during_post_start_verification(
        self,
        tail_mock,
        popen_mock,
        bridge_processes_mock,
        _sleep_mock,
        _runtime_mock,
        _stop_mock,
    ):
        popen_mock.return_value = FakeProcess()
        bridge_processes_mock.side_effect = [[], [{"pid": 1234}], [], []]
        manager = self.make_manager()

        result = manager.start()

        self.assertEqual(result.exit_code, 1)
        self.assertIn("Bridge listener disappeared during post-start verification", result.output)
        self.assertIn("bridge vanished", result.output)

    @patch("xiaozhi_control_tui.bridge.run_subprocess", return_value=(0, ["ok"]))
    @patch("xiaozhi_control_tui.bridge.resolve_bridge_python")
    def test_ensure_runtime_bootstraps_missing_bridge_venv(self, resolve_python_mock, run_subprocess_mock):
        venv_python = Path(r"C:\bridge-root\.venv\Scripts\python.exe")
        resolve_python_mock.side_effect = [None, venv_python]
        manager = self.make_manager()

        lines: list[str] = []
        python_path = manager.ensure_runtime(on_line=lines.append)

        self.assertEqual(python_path, venv_python)
        self.assertTrue(any("Bootstrapping .venv" in line for line in lines))
        self.assertEqual(run_subprocess_mock.call_count, 3)

    @patch("xiaozhi_control_tui.bridge.run_subprocess", return_value=(0, ["ok"]))
    @patch("xiaozhi_control_tui.bridge.resolve_bridge_python")
    def test_ensure_runtime_returns_existing_python_without_bootstrap(self, resolve_python_mock, run_subprocess_mock):
        existing = Path(r"C:\bridge-root\.venv\Scripts\python.exe")
        resolve_python_mock.return_value = existing
        manager = self.make_manager()

        python_path = manager.ensure_runtime()

        self.assertEqual(python_path, existing)
        run_subprocess_mock.assert_not_called()

    @patch("xiaozhi_control_tui.bridge.get_bridge_processes", return_value=[])
    @patch("xiaozhi_control_tui.bridge.run_subprocess", return_value=(0, ["Bridge server stopped"]))
    def test_stop_excludes_its_own_powershell_process(self, run_subprocess_mock, _bridge_processes_mock):
        manager = self.make_manager()

        manager.stop()

        command = run_subprocess_mock.call_args.args[0]
        self.assertIn('$_.ProcessId -ne $PID', " ".join(command))

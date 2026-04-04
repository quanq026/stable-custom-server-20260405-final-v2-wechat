from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

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

    @patch.object(BridgeManager, "resolved_python", return_value=Path(r"C:\python.exe"))
    @patch("xiaozhi_control_tui.bridge.time.sleep", return_value=None)
    @patch("xiaozhi_control_tui.bridge.get_bridge_processes")
    @patch("xiaozhi_control_tui.bridge.subprocess.Popen")
    def test_start_returns_when_port_detected_even_if_wrapper_process_lingers(self, popen_mock, bridge_processes_mock, _sleep_mock, _python_mock):
        popen_mock.return_value = FakeProcess()
        bridge_processes_mock.side_effect = [[], [{"pid": 1234}]]
        manager = self.make_manager()

        result = manager.start()

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Bridge server running on port 8000", result.output)
        self.assertTrue(popen_mock.return_value.terminated)

    @patch.object(BridgeManager, "resolved_python", return_value=Path(r"C:\python.exe"))
    @patch("xiaozhi_control_tui.bridge.time.sleep", return_value=None)
    @patch("xiaozhi_control_tui.bridge.get_bridge_processes", return_value=[])
    @patch("xiaozhi_control_tui.bridge.subprocess.Popen")
    def test_start_returns_failure_when_wrapper_exits_early(self, popen_mock, _bridge_processes_mock, _sleep_mock, _python_mock):
        popen_mock.return_value = FakeProcess(poll_values=[17])
        manager = self.make_manager()

        result = manager.start()

        self.assertEqual(result.exit_code, 17)
        self.assertIn("Bridge start script exited early with code 17", result.output)

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from xiaozhi_control_tui.controller import ControlController
from xiaozhi_control_tui.models import CommandResult


class FakeBridgeManager:
    def __init__(self):
        self.python = Path(r"C:\bridge-python.exe")

    def resolved_python(self):
        return self.python

    def start(self, on_line=None):
        if on_line:
            on_line("start")
        return CommandResult(0, ["start"])

    def stop(self, on_line=None):
        if on_line:
            on_line("stop")
        return CommandResult(0, ["stop"])

    def restart(self, on_line=None):
        if on_line:
            on_line("restart")
        return CommandResult(0, ["restart"])


class MissingBridgePythonManager(FakeBridgeManager):
    def resolved_python(self):
        raise FileNotFoundError("Bridge Python runtime not found")


class FailingBridgeManager(FakeBridgeManager):
    def start(self, on_line=None):
        if on_line:
            on_line("bridge-fail")
        return CommandResult(1, ["bridge-fail"])


class FakeDiscoveryManager:
    def __init__(self):
        self.python = Path(r"C:\tui-python.exe")
        self.calls: list[str] = []

    def start(self, on_line=None):
        self.calls.append("start")
        if on_line:
            on_line("discovery-start")
        return CommandResult(0, ["discovery-start"])

    def stop(self, on_line=None):
        self.calls.append("stop")
        if on_line:
            on_line("discovery-stop")
        return CommandResult(0, ["discovery-stop"])

    def restart(self, on_line=None):
        self.calls.append("restart")
        if on_line:
            on_line("discovery-restart")
        return CommandResult(0, ["discovery-restart"])


class FakeFirmwareManager:
    def build(self, on_line=None):
        if on_line:
            on_line("build")
        return CommandResult(0, ["build"])

    def flash(self, port, on_line=None):
        if on_line:
            on_line(f"flash:{port}")
        return CommandResult(0, [f"flash:{port}"])

    def fresh_flash(self, port, on_line=None):
        if on_line:
            on_line(f"fresh-flash:{port}")
        return CommandResult(0, [f"fresh-flash:{port}"])


class FailingFirmwareManager(FakeFirmwareManager):
    def build(self, on_line=None):
        raise RuntimeError("build failed")


class FakeLmStudioClient:
    def list_models(self):
        return ["qwen2.5-14b-instruct-1m", "qwen3-1.7b"]

    def is_reachable(self):
        return True


class ControllerTests(unittest.TestCase):
    def make_controller(self, temp_dir: str, firmware_manager=None):
        artifacts = Path(temp_dir) / "artifacts"
        artifacts.mkdir(parents=True, exist_ok=True)
        for name in (
            "xiaozhi.bin",
            "generated_assets.bin",
            "bootloader.bin",
            "partition-table.bin",
            "ota_data_initial.bin",
        ):
            (artifacts / name).write_text("x", encoding="utf-8")
        bridge_log = Path(temp_dir) / "bridge.log"
        bridge_log.write_text("", encoding="utf-8")
        discovery_manager = FakeDiscoveryManager()
        controller = ControlController(
            env_path=Path(temp_dir) / ".env.local",
            firmware_artifacts_root=artifacts,
            bridge_log_path=bridge_log,
            bridge_manager=FakeBridgeManager(),
            discovery_manager=discovery_manager,
            firmware_manager=firmware_manager or FakeFirmwareManager(),
            lmstudio_client=FakeLmStudioClient(),
        )
        controller._test_discovery_manager = discovery_manager
        return controller

    def test_refresh_status_updates_last_status(self):
        with TemporaryDirectory() as tmp:
            controller = self.make_controller(tmp)
            status = controller.refresh_status()
        self.assertTrue(status.lm_studio_reachable)
        self.assertEqual(controller.last_status.configured_model, "qwen3-1.7b")
        self.assertEqual(status.connection_mode, "Manual IP (v1)")

    def test_save_model_selection_persists(self):
        with TemporaryDirectory() as tmp:
            controller = self.make_controller(tmp)
            saved = controller.save_model_selection("qwen2.5-14b-instruct-1m")
            reread = controller.managed_env()
        self.assertEqual(saved["XIAOZHI_BRIDGE_MODEL_NAME"], "qwen2.5-14b-instruct-1m")
        self.assertEqual(reread["XIAOZHI_BRIDGE_MODEL_NAME"], "qwen2.5-14b-instruct-1m")

    def test_save_runtime_settings_persists_system_prompt(self):
        with TemporaryDirectory() as tmp:
            controller = self.make_controller(tmp)
            prompt = "Reply in Vietnamese.\nKeep it short."
            saved = controller.save_runtime_settings({"XIAOZHI_BRIDGE_SYSTEM_PROMPT": prompt})
            reread = controller.managed_env()
        self.assertEqual(saved["XIAOZHI_BRIDGE_SYSTEM_PROMPT"], prompt)
        self.assertEqual(reread["XIAOZHI_BRIDGE_SYSTEM_PROMPT"], prompt)

    def test_flash_requires_explicit_com_confirmation(self):
        with TemporaryDirectory() as tmp:
            controller = self.make_controller(tmp)
            with self.assertRaises(ValueError):
                controller.flash_firmware("")

    def test_fresh_flash_requires_explicit_com_confirmation(self):
        with TemporaryDirectory() as tmp:
            controller = self.make_controller(tmp)
            with self.assertRaises(ValueError):
                controller.fresh_flash_firmware("")

    def test_action_failures_surface_in_logs_and_status(self):
        with TemporaryDirectory() as tmp:
            controller = self.make_controller(tmp, firmware_manager=FailingFirmwareManager())
            with self.assertRaises(RuntimeError):
                controller.build_firmware()
        self.assertIn("Build Firmware failed", controller.banner)
        self.assertTrue(any("Build Firmware failed" in line for line in controller.log_messages))

    @patch("xiaozhi_control_tui.controller.detect_lan_ip_candidates")
    def test_status_lines_include_manual_ip_guidance(self, detect_lan_ip_candidates_mock):
        detect_lan_ip_candidates_mock.return_value = ["192.168.1.15", "10.0.0.12"]
        with TemporaryDirectory() as tmp:
            controller = self.make_controller(tmp)
            controller.refresh_status()
            lines = controller.status_lines()
        self.assertTrue(any("Connection mode: Manual IP (v1)" in line for line in lines))
        self.assertTrue(any("Laptop IP: 192.168.1.15" in line for line in lines))

    def test_start_bridge_does_not_start_discovery_service(self):
        with TemporaryDirectory() as tmp:
            controller = self.make_controller(tmp)
            controller.start_bridge()
        self.assertEqual(controller._test_discovery_manager.calls, [])

    def test_start_bridge_returns_bridge_failure_without_discovery_actions(self):
        with TemporaryDirectory() as tmp:
            controller = self.make_controller(tmp)
            controller.bridge_manager = FailingBridgeManager()
            result = controller.start_bridge()
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(controller._test_discovery_manager.calls, [])

    def test_refresh_status_does_not_crash_when_bridge_python_is_missing(self):
        with TemporaryDirectory() as tmp:
            controller = self.make_controller(tmp)
            controller.bridge_manager = MissingBridgePythonManager()
            status = controller.refresh_status()
            lines = controller.status_lines()
        self.assertEqual(status.bridge_python_path, "MISSING")
        self.assertTrue(any("create bridge-server\\.venv before starting bridge" in line for line in lines))

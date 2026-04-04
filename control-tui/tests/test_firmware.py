from pathlib import Path
import unittest

from xiaozhi_control_tui.firmware import FirmwareManager


class FirmwareManagerTests(unittest.TestCase):
    def test_build_command_targets_existing_script(self):
        manager = FirmwareManager(Path(r"C:\firmware"), Path(r"C:\firmware\scripts\flash_bridge_touch_server.ps1"))
        command = manager.build_command()
        self.assertIn("flash_bridge_touch_server.ps1", command[-1])

    def test_flash_command_requires_port(self):
        manager = FirmwareManager(Path(r"C:\firmware"), Path(r"C:\firmware\scripts\flash_bridge_touch_server.ps1"))
        with self.assertRaises(ValueError):
            manager.flash_command("")

import unittest

from xiaozhi_control_tui.runtime import parse_bridge_processes


class RuntimeTests(unittest.TestCase):
    def test_parse_bridge_processes_handles_single_dict_payload(self):
        payload = {"Port": 8000, "PID": 123, "Executable": "python.exe", "CommandLine": "python -m xiaozhi_bridge.server"}
        items = parse_bridge_processes(payload)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].pid, 123)
        self.assertEqual(items[0].port, 8000)

    def test_parse_bridge_processes_handles_list_payload(self):
        payload = [
            {"Port": 8000, "PID": 123, "Executable": "python.exe", "CommandLine": "python a"},
            {"Port": 8000, "PID": 124, "Executable": "python.exe", "CommandLine": "python b"},
        ]
        items = parse_bridge_processes(payload)
        self.assertEqual([item.pid for item in items], [123, 124])

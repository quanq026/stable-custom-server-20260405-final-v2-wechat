import unittest

from xiaozhi_control_tui.runtime import (
    LanIpCandidate,
    choose_preferred_lan_ip,
    filter_processes_by_marker,
    parse_bridge_processes,
    parse_lan_ip_candidates,
)


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

    def test_filter_processes_by_marker_keeps_only_expected_module(self):
        payload = [
            {"Port": 8000, "PID": 123, "Executable": "python.exe", "CommandLine": "python -m xiaozhi_bridge.server"},
            {"Port": 8000, "PID": 124, "Executable": "python.exe", "CommandLine": "python -m http.server 8000"},
        ]

        items = filter_processes_by_marker(parse_bridge_processes(payload), "xiaozhi_bridge.server")

        self.assertEqual([item.pid for item in items], [123])

    def test_parse_lan_ip_candidates_keeps_only_private_ipv4_addresses(self):
        payload = [
            {
                "InterfaceAlias": "Wi-Fi",
                "HasDefaultGateway": True,
                "IPv4Addresses": ["192.168.1.15", "169.254.10.20", "8.8.8.8"],
            },
            {
                "InterfaceAlias": "Ethernet",
                "HasDefaultGateway": False,
                "IPv4Addresses": ["10.0.0.12", "127.0.0.1"],
            },
        ]

        items = parse_lan_ip_candidates(payload)

        self.assertEqual(
            items,
            [
                LanIpCandidate(interface_alias="Wi-Fi", address="192.168.1.15", has_default_gateway=True),
                LanIpCandidate(interface_alias="Ethernet", address="10.0.0.12", has_default_gateway=False),
            ],
        )

    def test_choose_preferred_lan_ip_prefers_default_gateway_candidate(self):
        candidates = [
            LanIpCandidate(interface_alias="Ethernet", address="10.0.0.12", has_default_gateway=False),
            LanIpCandidate(interface_alias="Wi-Fi", address="192.168.1.15", has_default_gateway=True),
        ]

        preferred = choose_preferred_lan_ip(candidates)

        self.assertEqual(preferred, "192.168.1.15")

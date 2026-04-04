from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from xiaozhi_control_tui.discovery import (
    DiscoveryManager,
    build_discovery_response,
    parse_discovery_request,
    route_aware_local_ip,
)


class DiscoveryProtocolTests(unittest.TestCase):
    def test_parse_discovery_request_accepts_valid_payload(self):
        request = parse_discovery_request(
            b'{"type":"xiaozhi-discovery","version":1,"client_id":"client-1"}'
        )

        self.assertEqual(request.client_id, "client-1")
        self.assertEqual(request.version, 1)

    def test_build_discovery_response_uses_route_aware_ip(self):
        payload = build_discovery_response(
            requester_ip="192.168.1.50",
            server_id="server-1",
            server_name="xiaozhi-bridge",
            host="xiaozhi-bridge",
            websocket_port=8000,
            websocket_path="/xiaozhi/v1/",
            resolve_local_ip=lambda _ip: "192.168.1.15",
        )

        self.assertEqual(payload["server_id"], "server-1")
        self.assertEqual(payload["ws_url"], "ws://192.168.1.15:8000/xiaozhi/v1/")
        self.assertEqual(payload["host"], "xiaozhi-bridge.local")

    @patch("xiaozhi_control_tui.discovery.socket.socket")
    def test_route_aware_local_ip_connects_to_requester(self, socket_mock):
        fake_socket = socket_mock.return_value.__enter__.return_value
        fake_socket.getsockname.return_value = ("192.168.1.15", 49881)

        resolved = route_aware_local_ip("192.168.1.77")

        fake_socket.connect.assert_called_once()
        self.assertEqual(resolved, "192.168.1.15")


class DiscoveryManagerTests(unittest.TestCase):
    def make_manager(self):
        return DiscoveryManager(
            Path(r"C:\bridge-root"),
            Path(r"C:\python.exe"),
            Path(r"C:\logs\discovery-service.log"),
        )

    def test_command_targets_discovery_module(self):
        manager = self.make_manager()

        command = manager.start_command()

        self.assertIn("-m", command)
        self.assertIn("xiaozhi_control_tui.discovery", command)

    def test_stop_command_targets_udp_port(self):
        manager = self.make_manager()

        command = manager.stop_command()

        self.assertIn("24681", " ".join(command))

    def test_server_id_is_ensured_before_start(self):
        with TemporaryDirectory() as tmp:
            bridge_root = Path(tmp)
            env_path = bridge_root / ".env.local"
            manager = DiscoveryManager(bridge_root, Path(r"C:\python.exe"), bridge_root / "discovery.log")

            manager.ensure_server_id(env_path)
            before = env_path.read_text(encoding="utf-8")
            manager.ensure_server_id(env_path)
            after = env_path.read_text(encoding="utf-8")

        self.assertEqual(before, after)
        self.assertIn("XIAOZHI_BRIDGE_SERVER_ID=", after)

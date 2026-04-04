import json
import struct
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from xiaozhi_bridge.protocol import Protocol


class ProtocolTests(unittest.TestCase):
    def test_parse_message_understands_raw_audio_payload(self):
        message_type, payload = Protocol.parse_message(b"\x11\x22\x33")

        self.assertEqual(message_type, "audio")
        self.assertEqual(payload, b"\x11\x22\x33")

    def test_parse_message_understands_binary_protocol_v3_audio(self):
        payload = b"\xaa\xbb\xcc\xdd"
        framed = struct.pack("!BBH", 0, 0, len(payload)) + payload

        message_type, parsed = Protocol.parse_message(framed)

        self.assertEqual(message_type, "audio")
        self.assertEqual(parsed, payload)

    def test_parse_message_understands_binary_protocol_v3_json(self):
        inner = json.dumps({"type": "listen", "state": "start"}).encode("utf-8")
        framed = struct.pack("!BBH", 1, 0, len(inner)) + inner

        message_type, parsed = Protocol.parse_message(framed)

        self.assertEqual(message_type, "json")
        self.assertEqual(parsed["type"], "listen")
        self.assertEqual(parsed["state"], "start")

    def test_hello_response_uses_requested_protocol_version(self):
        response = json.loads(
            Protocol.create_hello_response(
                "session-1",
                version=1,
                server_id="server-1",
                server_name="xiaozhi-bridge",
            )
        )

        self.assertEqual(response["type"], "hello")
        self.assertEqual(response["version"], 1)
        self.assertEqual(response["session_id"], "session-1")
        self.assertEqual(response["server_id"], "server-1")
        self.assertEqual(response["server_name"], "xiaozhi-bridge")


if __name__ == "__main__":
    unittest.main()

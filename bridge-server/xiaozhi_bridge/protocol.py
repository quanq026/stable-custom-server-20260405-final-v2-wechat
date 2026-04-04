import json
import struct


class Protocol:
    @staticmethod
    def parse_message(data):
        """
        Parse incoming message from WebSocket.
        Returns:
            - ('json', dict) if it's a JSON text message
            - ('audio', bytes) if it's binary audio data
            - (None, None) if invalid
        """
        if isinstance(data, str):
            try:
                return "json", json.loads(data)
            except json.JSONDecodeError:
                return None, None

        if isinstance(data, bytes):
            parsed = Protocol._try_parse_binary_protocol_v3(data)
            if parsed is not None:
                return parsed
            return "audio", data

        return None, None

    @staticmethod
    def _try_parse_binary_protocol_v3(data):
        if len(data) < 4:
            return None

        packet_type, reserved, payload_size = struct.unpack("!BBH", data[:4])
        if reserved != 0 or payload_size != len(data) - 4 or packet_type not in (0, 1):
            return None

        payload = data[4:]
        if packet_type == 0:
            return "audio", payload

        try:
            return "json", json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

    @staticmethod
    def create_hello_response(
        session_id,
        version=1,
        sample_rate=16000,
        channels=1,
        frame_duration=60,
        server_id=None,
        server_name=None,
    ):
        payload = {
            "type": "hello",
            "transport": "websocket",
            "version": version,
            "audio_params": {
                "format": "opus",
                "sample_rate": sample_rate,
                "channels": channels,
                "frame_duration": frame_duration,
            },
            "session_id": session_id,
        }
        if server_id:
            payload["server_id"] = server_id
        if server_name:
            payload["server_name"] = server_name
        return json.dumps(payload)

    @staticmethod
    def create_tts_start():
        return json.dumps({"type": "tts", "state": "start"})

    @staticmethod
    def create_tts_stop():
        return json.dumps({"type": "tts", "state": "stop"})

    @staticmethod
    def create_tts_sentence_start(text):
        return json.dumps({"type": "tts", "state": "sentence_start", "text": text})

    @staticmethod
    def create_stt_text(text, session_id):
        return json.dumps({"type": "stt", "text": text, "session_id": session_id})

    @staticmethod
    def wrap_audio_payload(payload, version):
        if version == 3:
            return struct.pack("!BBH", 0, 0, len(payload)) + payload
        return payload

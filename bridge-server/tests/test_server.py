import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xiaozhi_bridge.server import XiaozhiServer


class _FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send(self, message):
        self.sent.append(message)


class ServerBehaviorTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_tts_packet_stream_paces_packets_and_sends_stop(self):
        async def packet_stream():
            yield b"a"
            yield b"b"

        server = XiaozhiServer.__new__(XiaozhiServer)
        server.protocol_version = 1
        server.last_tts_stop_time = 0.0
        server.logger = SimpleNamespace(info=lambda *args, **kwargs: None, warning=lambda *args, **kwargs: None)
        server.config = type("Config", (), {"frame_duration": 60})()

        ws = _FakeWebSocket()

        with patch("xiaozhi_bridge.server.asyncio.sleep", new=AsyncMock()) as sleep_mock, \
             patch("xiaozhi_bridge.server.time.monotonic", return_value=42.0):
            count = await XiaozhiServer._stream_tts_packet_stream(server, ws, packet_stream())

        self.assertEqual(count, 2)
        self.assertEqual(ws.sent[:2], [b"a", b"b"])
        self.assertEqual(ws.sent[-1], '{"type": "tts", "state": "stop"}')
        self.assertEqual(server.last_tts_stop_time, 42.0)
        self.assertEqual(sleep_mock.await_count, 2)

    def test_should_ignore_recent_tts_echo_when_similarity_is_high(self):
        server = XiaozhiServer.__new__(XiaozhiServer)
        server.logger = SimpleNamespace(info=lambda *args, **kwargs: None)
        server.config = type(
            "Config",
            (),
            {"tts_echo_guard_ms": 1200, "echo_similarity_threshold": 0.75},
        )()
        server.last_assistant_text = "Xin chao, toi la Xiaozhi."
        server.last_tts_stop_time = 10.0

        ignored = XiaozhiServer._should_ignore_transcript(server, "Xin chao toi la Xiaozhi", 10.8)

        self.assertTrue(ignored)

    def test_should_not_ignore_transcript_after_guard_window_expires(self):
        server = XiaozhiServer.__new__(XiaozhiServer)
        server.logger = SimpleNamespace(info=lambda *args, **kwargs: None)
        server.config = type(
            "Config",
            (),
            {"tts_echo_guard_ms": 1200, "echo_similarity_threshold": 0.75},
        )()
        server.last_assistant_text = "Xin chao, toi la Xiaozhi."
        server.last_tts_stop_time = 10.0

        ignored = XiaozhiServer._should_ignore_transcript(server, "Xin chao toi la Xiaozhi", 11.5)

        self.assertFalse(ignored)

    async def test_stream_tts_audio_paces_packets_and_sends_stop(self):
        server = XiaozhiServer.__new__(XiaozhiServer)
        server.protocol_version = 1
        server.last_tts_stop_time = 0.0
        server.logger = SimpleNamespace(info=lambda *args, **kwargs: None, warning=lambda *args, **kwargs: None)
        server.config = type("Config", (), {"frame_duration": 60})()

        ws = _FakeWebSocket()
        packets = [b"a", b"b", b"c"]

        with patch("xiaozhi_bridge.server.asyncio.sleep", new=AsyncMock()) as sleep_mock:
            count = await XiaozhiServer._stream_tts_audio(server, ws, packets)

        self.assertEqual(count, 3)
        self.assertEqual(ws.sent[:3], packets)
        self.assertEqual(ws.sent[-1], '{"type": "tts", "state": "stop"}')
        self.assertEqual(sleep_mock.await_count, 3)
        sleep_mock.assert_any_await(0.06)

    async def test_process_speech_uses_streaming_tts_path(self):
        async def mp3_stream():
            yield b"mp3"

        async def opus_stream():
            yield b"pkt"

        server = XiaozhiServer.__new__(XiaozhiServer)
        server.logger = SimpleNamespace(
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            exception=lambda *args, **kwargs: None,
        )
        server.session_id = "session-1"
        server.protocol_version = 1
        server.audio_buffer = bytearray(b"pcm")
        server.last_assistant_text = ""
        server.last_tts_stop_time = 0.0
        server.config = type(
            "Config",
            (),
            {
                "frame_duration": 60,
                "channels": 1,
                "sample_rate": 16000,
                "log_dir": REPO_ROOT / "tmp-tests",
                "tts_echo_guard_ms": 1200,
                "echo_similarity_threshold": 0.75,
            },
        )()
        server.asr = type("Asr", (), {"transcribe": lambda self, _: "xin chao"})()
        server.llm = type(
            "Llm",
            (),
            {
                "start_session": lambda self, session_id: None,
                "end_session": lambda self, session_id: None,
                "get_response": AsyncMock(return_value="xin chao"),
            },
        )()
        server.tts = type("Tts", (), {"stream_audio": lambda self, text: mp3_stream()})()
        server.audio_utils = type("Audio", (), {"stream_mp3_to_opus_packets": lambda self, stream: opus_stream()})()

        ws = _FakeWebSocket()

        with patch("xiaozhi_bridge.server.asyncio.get_running_loop") as get_loop, \
             patch.object(XiaozhiServer, "_stream_tts_packet_stream", new=AsyncMock(return_value=1)) as stream_mock:
            fake_loop = type("Loop", (), {"run_in_executor": lambda self, executor, func, *args: asyncio.Future()})()
            get_loop.return_value = fake_loop
            fut1 = asyncio.Future()
            fut1.set_result("xin chao")
            fake_loop.run_in_executor = lambda executor, func, *args: fut1
            await XiaozhiServer.process_speech(server, ws)

        stream_mock.assert_awaited_once()
        self.assertIn('"type": "tts", "state": "sentence_start"', "\n".join(str(item) for item in ws.sent))

    async def test_process_speech_uses_fallback_when_llm_response_is_empty(self):
        server = XiaozhiServer.__new__(XiaozhiServer)
        server.logger = SimpleNamespace(
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            exception=lambda *args, **kwargs: None,
        )
        server.session_id = "session-1"
        server.protocol_version = 1
        server.audio_buffer = bytearray(b"pcm")
        server.last_assistant_text = ""
        server.last_tts_stop_time = 0.0
        server.config = type(
            "Config",
            (),
            {
                "frame_duration": 60,
                "channels": 1,
                "sample_rate": 16000,
                "log_dir": REPO_ROOT / "tmp-tests",
                "tts_echo_guard_ms": 1200,
                "echo_similarity_threshold": 0.75,
            },
        )()
        server.asr = type("Asr", (), {"transcribe": lambda self, _: "xin chao"})()
        server.llm = type("Llm", (), {"get_response": AsyncMock(return_value="   ")})()

        async def mp3_stream():
            yield b"mp3"

        async def opus_stream():
            yield b"pkt"

        server.tts = type("Tts", (), {"stream_audio": lambda self, text: mp3_stream()})()
        server.audio_utils = type("Audio", (), {"stream_mp3_to_opus_packets": lambda self, stream: opus_stream()})()

        ws = _FakeWebSocket()

        with patch("xiaozhi_bridge.server.asyncio.get_running_loop") as get_loop, \
             patch.object(XiaozhiServer, "_stream_tts_packet_stream", new=AsyncMock(return_value=1)) as stream_mock:
            fake_loop = type("Loop", (), {"run_in_executor": lambda self, executor, func, *args: asyncio.Future()})()
            get_loop.return_value = fake_loop
            # first executor call for ASR
            fut1 = asyncio.Future(); fut1.set_result("xin chao")
            fake_loop.run_in_executor = lambda executor, func, *args: fut1
            await XiaozhiServer.process_speech(server, ws)

        joined = "\n".join(str(item) for item in ws.sent)
        self.assertIn('"type": "stt"', joined)
        self.assertIn('"type": "tts", "state": "sentence_start"', joined)
        self.assertIn("Xin loi, toi chua co cau tra loi phu hop.", joined)
        stream_mock.assert_awaited_once()

    async def test_process_speech_skips_llm_when_recent_tts_echo_is_detected(self):
        server = XiaozhiServer.__new__(XiaozhiServer)
        server.logger = SimpleNamespace(
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            exception=lambda *args, **kwargs: None,
        )
        server.session_id = "session-1"
        server.protocol_version = 1
        server.audio_buffer = bytearray(b"pcm")
        server.last_assistant_text = "Xin chao toi la Xiaozhi"
        server.last_tts_stop_time = 10.0
        server.config = type(
            "Config",
            (),
            {
                "frame_duration": 60,
                "channels": 1,
                "sample_rate": 16000,
                "log_dir": REPO_ROOT / "tmp-tests",
                "tts_echo_guard_ms": 1200,
                "echo_similarity_threshold": 0.75,
            },
        )()
        server.asr = type("Asr", (), {"transcribe": lambda self, _: "Xin chao, toi la Xiaozhi"})()
        server.llm = type("Llm", (), {"get_response": AsyncMock(return_value="khong duoc goi")})()
        server.tts = type("Tts", (), {"generate_audio": AsyncMock(return_value=None)})()
        server.audio_utils = type("Audio", (), {"mp3_to_opus_packets": lambda self, _: [b"pkt"]})()

        ws = _FakeWebSocket()

        with patch("xiaozhi_bridge.server.asyncio.get_running_loop") as get_loop, \
             patch("xiaozhi_bridge.server.time.monotonic", return_value=10.8):
            fake_loop = type("Loop", (), {"run_in_executor": lambda self, executor, func, *args: asyncio.Future()})()
            get_loop.return_value = fake_loop
            fut1 = asyncio.Future()
            fut1.set_result("Xin chao, toi la Xiaozhi")
            fake_loop.run_in_executor = lambda executor, func, *args: fut1
            await XiaozhiServer.process_speech(server, ws)

        self.assertEqual(ws.sent, [])
        server.llm.get_response.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()

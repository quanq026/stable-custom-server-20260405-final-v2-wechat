import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from xiaozhi_bridge.server import XiaozhiServer


class _FakeWebSocket:
    def __init__(self):
        self.sent = []

    async def send(self, message):
        self.sent.append(message)


class HallucinationFilterTests(unittest.IsolatedAsyncioTestCase):
    def test_should_ignore_known_outro_hallucination(self):
        server = XiaozhiServer.__new__(XiaozhiServer)

        ignored = XiaozhiServer._should_ignore_hallucinated_transcript(
            server,
            "Hãy đăng ký kênh để ủng hộ kênh của mình nhé.",
        )

        self.assertTrue(ignored)

    def test_should_not_ignore_normal_question(self):
        server = XiaozhiServer.__new__(XiaozhiServer)

        ignored = XiaozhiServer._should_ignore_hallucinated_transcript(server, "Bạn là ai?")

        self.assertFalse(ignored)

    async def test_process_speech_skips_llm_for_known_outro_hallucination(self):
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
        server.asr = type("Asr", (), {"transcribe": lambda self, _: "Hãy đăng ký kênh để ủng hộ kênh của mình nhé."})()
        server.llm = type("Llm", (), {"get_response": AsyncMock(return_value="khong duoc goi")})()
        server.tts = type("Tts", (), {"stream_audio": lambda self, text: None})()
        server.audio_utils = type("Audio", (), {"stream_mp3_to_opus_packets": lambda self, stream: iter(())})()

        ws = _FakeWebSocket()

        with patch("xiaozhi_bridge.server.asyncio.get_running_loop") as get_loop:
            fake_loop = type("Loop", (), {"run_in_executor": lambda self, executor, func, *args: asyncio.Future()})()
            get_loop.return_value = fake_loop
            fut1 = asyncio.Future()
            fut1.set_result("Hãy đăng ký kênh để ủng hộ kênh của mình nhé.")
            fake_loop.run_in_executor = lambda executor, func, *args: fut1
            await XiaozhiServer.process_speech(server, ws)

        self.assertEqual(ws.sent, [])
        server.llm.get_response.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()

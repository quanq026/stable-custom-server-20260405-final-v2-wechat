import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock


REPO_ROOT = Path(r"C:\QuanNewData\xiaozhi\Xiaozhi-ESP32-Bridge-Server\.worktrees\codex\bridge-server-lan")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from xiaozhi_bridge.server import XiaozhiServer


class TurnTakingTests(unittest.IsolatedAsyncioTestCase):
    def _make_server(self):
        server = XiaozhiServer.__new__(XiaozhiServer)
        server.logger = SimpleNamespace(
            info=lambda *args, **kwargs: None,
            warning=lambda *args, **kwargs: None,
            exception=lambda *args, **kwargs: None,
        )
        server.config = SimpleNamespace(
            frame_duration=60,
            channels=1,
            sample_rate=16000,
            log_dir=REPO_ROOT / "tmp-tests",
            tts_echo_guard_ms=1200,
            echo_similarity_threshold=0.75,
            max_reply_chars=120,
            max_reply_sentences=2,
            drop_audio_while_processing=True,
            drop_audio_while_tts=True,
        )
        server.audio_utils = SimpleNamespace(
            decode_opus=lambda _: struct.pack("4h", 1000, 1000, 1000, 1000)
        )
        return server

    async def test_handle_audio_drops_frames_while_processing_turn(self):
        server = self._make_server()
        state = SimpleNamespace(
            is_processing_turn=True,
            is_tts_streaming=False,
            ignore_audio_until=0.0,
            is_speaking=False,
            audio_buffer=bytearray(),
            silence_counter=0,
        )
        websocket = object()
        server.process_speech = AsyncMock()

        await XiaozhiServer.handle_audio(server, websocket, b"opus", state)

        self.assertEqual(state.audio_buffer, bytearray())
        server.process_speech.assert_not_awaited()

    async def test_handle_audio_drops_frames_while_tts_is_streaming(self):
        server = self._make_server()
        state = SimpleNamespace(
            is_processing_turn=False,
            is_tts_streaming=True,
            ignore_audio_until=0.0,
            is_speaking=False,
            audio_buffer=bytearray(),
            silence_counter=0,
        )
        websocket = object()
        server.process_speech = AsyncMock()

        await XiaozhiServer.handle_audio(server, websocket, b"opus", state)

        self.assertEqual(state.audio_buffer, bytearray())
        server.process_speech.assert_not_awaited()

    def test_postprocess_response_text_limits_and_strips_user_echo(self):
        server = self._make_server()

        cleaned = XiaozhiServer._postprocess_response_text(
            server,
            "Tên bạn là gì? Tên bạn là gì? Tôi là Xiaozhi. Tôi có thể giúp bạn học tiếng Anh hôm nay.",
            "Tên bạn là gì?",
        )

        self.assertEqual(cleaned, "Tôi là Xiaozhi. Tôi có thể giúp bạn học tiếng Anh hôm nay.")


if __name__ == "__main__":
    unittest.main()

import sys
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from xiaozhi_bridge.llm_client import LLMClient


class ConversationRetentionTests(unittest.IsolatedAsyncioTestCase):
    def _make_config(self):
        return SimpleNamespace(
            lm_studio_url="http://localhost:1234/v1",
            lm_studio_api_key="lm-studio",
            model_name="qwen3-1.7b",
            system_prompt="Ban la tro ly ho tro ky thuat.",
            context_tail_messages=4,
            session_summary_max_chars=200,
            conversation_idle_timeout_seconds=3600,
            conversation_cleanup_interval_seconds=300,
        )

    async def test_same_device_reuses_conversation_across_reconnect(self):
        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Tra loi moi"))]
        )
        fake_create = AsyncMock(return_value=fake_response)
        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))

        with patch("xiaozhi_bridge.llm_client.AsyncOpenAI", return_value=fake_client):
            client = LLMClient(self._make_config())

        client.start_session("s1", device_id="dev-1")
        client.append_user_message("s1", "Ban la ai")
        client.append_assistant_message("s1", "Toi la Mono")
        client.end_session("s1")

        client.start_session("s2", device_id="dev-1")
        messages = client.build_messages("s2")

        self.assertIn({"role": "user", "content": "Ban la ai"}, messages)
        self.assertIn({"role": "assistant", "content": "Toi la Mono"}, messages)
        self.assertIn("s2", client.active_sessions)
        self.assertNotIn("s1", client.active_sessions)

    async def test_missing_device_id_falls_back_to_connection_scoped_context(self):
        with patch("xiaozhi_bridge.llm_client.AsyncOpenAI"):
            client = LLMClient(self._make_config())

        client.start_session("s1")
        client.append_user_message("s1", "Lan 1")
        client.append_assistant_message("s1", "Phan hoi 1")
        client.end_session("s1")

        client.start_session("s2")
        messages = client.build_messages("s2")

        self.assertEqual(messages, [{"role": "system", "content": client.system_prompt}])

    async def test_cleanup_drops_idle_conversation_after_timeout(self):
        with patch("xiaozhi_bridge.llm_client.AsyncOpenAI"):
            client = LLMClient(self._make_config())

        base_time = 1000.0
        with patch("xiaozhi_bridge.llm_client.time.monotonic", return_value=base_time):
            client.start_session("s1", device_id="dev-1")
            client.append_user_message("s1", "Xin chao")
            client.append_assistant_message("s1", "Chao ban")
            client.end_session("s1")

        with patch("xiaozhi_bridge.llm_client.time.monotonic", return_value=base_time + 3599):
            client.cleanup_expired_conversations()
        self.assertIn("dev-1", client.conversations)

        with patch("xiaozhi_bridge.llm_client.time.monotonic", return_value=base_time + 3601):
            client.cleanup_expired_conversations()
        self.assertNotIn("dev-1", client.conversations)


if __name__ == "__main__":
    unittest.main()

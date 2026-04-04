import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch


REPO_ROOT = Path(r"C:\QuanNewData\xiaozhi\Xiaozhi-ESP32-Bridge-Server\.worktrees\codex\bridge-server-lan")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


from xiaozhi_bridge.llm_client import LLMClient


class LLMClientSessionTests(unittest.IsolatedAsyncioTestCase):
    def _make_config(self):
        return SimpleNamespace(
            lm_studio_url="http://localhost:1234/v1",
            lm_studio_api_key="lm-studio",
            model_name="qwen3-1.7b",
            system_prompt=(
                "Ban la tro ly AI noi tieng Viet. "
                "Khong lap lai cau hoi cua nguoi dung. "
                "Tra loi truc tiep, toi da 2 cau ngan."
            ),
            context_tail_messages=2,
            session_summary_max_chars=80,
        )

    async def test_new_session_does_not_inherit_other_session_history(self):
        with patch("xiaozhi_bridge.llm_client.AsyncOpenAI"):
            client = LLMClient(self._make_config())

        client.start_session("s1")
        client.append_user_message("s1", "Xin chao")
        client.append_assistant_message("s1", "Chao ban")
        client.append_user_message("s1", "Hom nay may gio")
        client.append_assistant_message("s1", "Bay gio la 9 gio")

        client.start_session("s2")
        messages = client.build_messages("s2")

        self.assertEqual(messages, [{"role": "system", "content": client.system_prompt}])

    async def test_summary_and_tail_are_kept_per_session(self):
        with patch("xiaozhi_bridge.llm_client.AsyncOpenAI"):
            client = LLMClient(self._make_config())

        client.start_session("s1")
        client.append_user_message("s1", "Lan 1")
        client.append_assistant_message("s1", "Phan hoi 1")
        client.append_user_message("s1", "Lan 2")
        client.append_assistant_message("s1", "Phan hoi 2")
        client.append_user_message("s1", "Lan 3")
        client.append_assistant_message("s1", "Phan hoi 3")

        state = client.sessions["s1"]
        built = client.build_messages("s1")

        self.assertTrue(state.summary)
        self.assertLessEqual(len(state.tail_messages), 2)
        self.assertEqual(built[0]["content"], client.system_prompt)
        self.assertIn("Lan 3", str(built))

    async def test_get_response_uses_session_messages_and_tracks_last_texts(self):
        fake_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Toi la Xiaozhi."))]
        )
        fake_create = AsyncMock(return_value=fake_response)
        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=fake_create)))

        with patch("xiaozhi_bridge.llm_client.AsyncOpenAI", return_value=fake_client):
            client = LLMClient(self._make_config())

        client.start_session("s1")
        reply = await client.get_response("s1", "Ten ban la gi")

        self.assertEqual(reply, "Toi la Xiaozhi.")
        messages = fake_create.await_args.kwargs["messages"]
        self.assertIn("Khong lap lai cau hoi", messages[0]["content"])
        self.assertEqual(client.sessions["s1"].last_user_text, "Ten ban la gi")
        self.assertEqual(client.sessions["s1"].last_assistant_text, "Toi la Xiaozhi.")


if __name__ == "__main__":
    unittest.main()

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from xiaozhi_control_tui.env_store import ensure_server_id, load_env, save_env


class EnvStoreTests(unittest.TestCase):
    def test_load_env_merges_defaults_when_file_missing(self):
        with TemporaryDirectory() as tmp:
            values = load_env(Path(tmp) / ".env.local")
        self.assertEqual(values["XIAOZHI_BRIDGE_MODEL_NAME"], "qwen3-1.7b")
        self.assertEqual(values["XIAOZHI_BRIDGE_ASR_MODEL"], "large-v3")

    def test_save_env_persists_updates(self):
        with TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env.local"
            save_env(env_path, {"XIAOZHI_BRIDGE_MODEL_NAME": "qwen2.5-14b-instruct-1m"})
            values = load_env(env_path)
        self.assertEqual(values["XIAOZHI_BRIDGE_MODEL_NAME"], "qwen2.5-14b-instruct-1m")

    def test_save_env_round_trips_multiline_system_prompt(self):
        with TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env.local"
            prompt = "Line one.\nLine two."
            save_env(env_path, {"XIAOZHI_BRIDGE_SYSTEM_PROMPT": prompt})
            values = load_env(env_path)
            raw = env_path.read_text(encoding="utf-8")
        self.assertEqual(values["XIAOZHI_BRIDGE_SYSTEM_PROMPT"], prompt)
        self.assertIn("XIAOZHI_BRIDGE_SYSTEM_PROMPT=Line one.\\nLine two.", raw)

    def test_ensure_server_id_generates_and_persists(self):
        with TemporaryDirectory() as tmp:
            env_path = Path(tmp) / ".env.local"
            first = ensure_server_id(env_path)
            second = ensure_server_id(env_path)
            values = load_env(env_path)
        self.assertEqual(first, second)
        self.assertEqual(values["XIAOZHI_BRIDGE_SERVER_ID"], first)
        self.assertGreaterEqual(len(first), 32)

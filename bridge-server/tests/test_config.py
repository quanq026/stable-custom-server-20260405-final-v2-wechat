import importlib
import os
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


class ConfigTests(unittest.TestCase):
    def tearDown(self):
        for key in [
            "XIAOZHI_BRIDGE_HOST",
            "XIAOZHI_BRIDGE_PORT",
            "XIAOZHI_BRIDGE_LM_STUDIO_URL",
            "XIAOZHI_BRIDGE_MODEL_NAME",
            "XIAOZHI_BRIDGE_SYSTEM_PROMPT",
            "XIAOZHI_BRIDGE_CONTEXT_TAIL_MESSAGES",
            "XIAOZHI_BRIDGE_SESSION_SUMMARY_MAX_CHARS",
            "XIAOZHI_BRIDGE_MAX_REPLY_CHARS",
            "XIAOZHI_BRIDGE_MAX_REPLY_SENTENCES",
            "XIAOZHI_BRIDGE_DROP_AUDIO_WHILE_PROCESSING",
            "XIAOZHI_BRIDGE_DROP_AUDIO_WHILE_TTS",
            "XIAOZHI_BRIDGE_TTS_ECHO_GUARD_MS",
            "XIAOZHI_BRIDGE_ECHO_SIMILARITY_THRESHOLD",
            "XIAOZHI_BRIDGE_TTS_VOICE",
            "XIAOZHI_BRIDGE_ASR_MODEL",
            "XIAOZHI_BRIDGE_ASR_LANGUAGE",
            "XIAOZHI_BRIDGE_ASR_DEVICE",
            "XIAOZHI_BRIDGE_ASR_COMPUTE_TYPE",
            "XIAOZHI_BRIDGE_LOG_DIR",
            "XIAOZHI_BRIDGE_DISCOVERY_ENABLE",
            "XIAOZHI_BRIDGE_DISCOVERY_HOST",
            "XIAOZHI_BRIDGE_DISCOVERY_PORT",
            "XIAOZHI_BRIDGE_SERVER_ID",
        ]:
            os.environ.pop(key, None)
        sys.modules.pop("xiaozhi_bridge.config", None)

    def test_defaults_are_vietnamese_and_local_first(self):
        from xiaozhi_bridge.config import BridgeConfig

        config = BridgeConfig.from_env()

        self.assertEqual(config.host, "0.0.0.0")
        self.assertEqual(config.port, 8000)
        self.assertEqual(config.lm_studio_url, "http://localhost:1234/v1")
        self.assertEqual(config.model_name, "qwen3-1.7b")
        self.assertEqual(config.tts_voice, "vi-VN-HoaiMyNeural")
        self.assertEqual(config.asr_model, "large-v3")
        self.assertEqual(config.asr_language, "vi")
        self.assertEqual(config.asr_device, "cuda")
        self.assertEqual(config.asr_compute_type, "float16")
        self.assertTrue(config.discovery_enable)
        self.assertEqual(config.discovery_host, "xiaozhi-bridge")
        self.assertEqual(config.discovery_port, 24681)
        self.assertTrue(config.server_id)
        self.assertEqual(config.context_tail_messages, 6)
        self.assertEqual(config.session_summary_max_chars, 600)
        self.assertEqual(config.max_reply_chars, 120)
        self.assertEqual(config.max_reply_sentences, 2)
        self.assertTrue(config.drop_audio_while_processing)
        self.assertTrue(config.drop_audio_while_tts)
        self.assertEqual(config.tts_echo_guard_ms, 1200)
        self.assertAlmostEqual(config.echo_similarity_threshold, 0.75)
        self.assertIn("do not repeat or paraphrase", config.system_prompt.lower())

    def test_environment_overrides_take_effect(self):
        os.environ["XIAOZHI_BRIDGE_HOST"] = "127.0.0.1"
        os.environ["XIAOZHI_BRIDGE_PORT"] = "9001"
        os.environ["XIAOZHI_BRIDGE_LM_STUDIO_URL"] = "http://192.168.1.20:1234/v1"
        os.environ["XIAOZHI_BRIDGE_MODEL_NAME"] = "custom-model"
        os.environ["XIAOZHI_BRIDGE_SYSTEM_PROMPT"] = "custom prompt"
        os.environ["XIAOZHI_BRIDGE_CONTEXT_TAIL_MESSAGES"] = "4"
        os.environ["XIAOZHI_BRIDGE_SESSION_SUMMARY_MAX_CHARS"] = "320"
        os.environ["XIAOZHI_BRIDGE_MAX_REPLY_CHARS"] = "80"
        os.environ["XIAOZHI_BRIDGE_MAX_REPLY_SENTENCES"] = "1"
        os.environ["XIAOZHI_BRIDGE_DROP_AUDIO_WHILE_PROCESSING"] = "false"
        os.environ["XIAOZHI_BRIDGE_DROP_AUDIO_WHILE_TTS"] = "false"
        os.environ["XIAOZHI_BRIDGE_TTS_ECHO_GUARD_MS"] = "1800"
        os.environ["XIAOZHI_BRIDGE_ECHO_SIMILARITY_THRESHOLD"] = "0.9"
        os.environ["XIAOZHI_BRIDGE_TTS_VOICE"] = "vi-VN-NamMinhNeural"
        os.environ["XIAOZHI_BRIDGE_ASR_MODEL"] = "small"
        os.environ["XIAOZHI_BRIDGE_ASR_LANGUAGE"] = "en"
        os.environ["XIAOZHI_BRIDGE_ASR_DEVICE"] = "cpu"
        os.environ["XIAOZHI_BRIDGE_ASR_COMPUTE_TYPE"] = "int8"
        os.environ["XIAOZHI_BRIDGE_DISCOVERY_ENABLE"] = "false"
        os.environ["XIAOZHI_BRIDGE_DISCOVERY_HOST"] = "lab-bridge"
        os.environ["XIAOZHI_BRIDGE_DISCOVERY_PORT"] = "24682"
        os.environ["XIAOZHI_BRIDGE_SERVER_ID"] = "server-123"
        os.environ["XIAOZHI_BRIDGE_LOG_DIR"] = str(REPO_ROOT / "tmp")

        from xiaozhi_bridge.config import BridgeConfig

        config = BridgeConfig.from_env()

        self.assertEqual(config.host, "127.0.0.1")
        self.assertEqual(config.port, 9001)
        self.assertEqual(config.lm_studio_url, "http://192.168.1.20:1234/v1")
        self.assertEqual(config.model_name, "custom-model")
        self.assertEqual(config.system_prompt, "custom prompt")
        self.assertEqual(config.context_tail_messages, 4)
        self.assertEqual(config.session_summary_max_chars, 320)
        self.assertEqual(config.max_reply_chars, 80)
        self.assertEqual(config.max_reply_sentences, 1)
        self.assertFalse(config.drop_audio_while_processing)
        self.assertFalse(config.drop_audio_while_tts)
        self.assertEqual(config.tts_echo_guard_ms, 1800)
        self.assertAlmostEqual(config.echo_similarity_threshold, 0.9)
        self.assertEqual(config.tts_voice, "vi-VN-NamMinhNeural")
        self.assertEqual(config.asr_model, "small")
        self.assertEqual(config.asr_language, "en")
        self.assertEqual(config.asr_device, "cpu")
        self.assertEqual(config.asr_compute_type, "int8")
        self.assertFalse(config.discovery_enable)
        self.assertEqual(config.discovery_host, "lab-bridge")
        self.assertEqual(config.discovery_port, 24682)
        self.assertEqual(config.server_id, "server-123")
        self.assertTrue(str(config.log_dir).endswith("tmp"))

    def test_system_prompt_env_decodes_escaped_newlines(self):
        os.environ["XIAOZHI_BRIDGE_SYSTEM_PROMPT"] = "line one\\nline two"

        from xiaozhi_bridge.config import BridgeConfig

        config = BridgeConfig.from_env()

        self.assertEqual(config.system_prompt, "line one\nline two")


if __name__ == "__main__":
    unittest.main()

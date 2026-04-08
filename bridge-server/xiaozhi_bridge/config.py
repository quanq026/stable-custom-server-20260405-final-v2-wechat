import os
import uuid
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _get_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _get_text_env(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.replace("\\n", "\n")


@dataclass(frozen=True)
class BridgeConfig:
    host: str
    port: int
    lm_studio_url: str
    lm_studio_api_key: str
    model_name: str
    system_prompt: str
    context_tail_messages: int
    session_summary_max_chars: int
    conversation_idle_timeout_seconds: int
    conversation_cleanup_interval_seconds: int
    max_reply_chars: int
    max_reply_sentences: int
    drop_audio_while_processing: bool
    drop_audio_while_tts: bool
    tts_echo_guard_ms: int
    echo_similarity_threshold: float
    sample_rate: int
    channels: int
    frame_duration: int
    tts_voice: str
    asr_model: str
    asr_language: str
    asr_device: str
    asr_compute_type: str
    discovery_enable: bool
    discovery_host: str
    discovery_port: int
    server_id: str
    ffmpeg_path: str
    log_dir: Path

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        return cls(
            host=os.getenv("XIAOZHI_BRIDGE_HOST", "0.0.0.0"),
            port=int(os.getenv("XIAOZHI_BRIDGE_PORT", "8000")),
            lm_studio_url=os.getenv("XIAOZHI_BRIDGE_LM_STUDIO_URL", "http://localhost:1234/v1"),
            lm_studio_api_key=os.getenv("XIAOZHI_BRIDGE_LM_STUDIO_API_KEY", "lm-studio"),
            model_name=os.getenv("XIAOZHI_BRIDGE_MODEL_NAME", "qwen3-1.7b"),
            system_prompt=_get_text_env(
                "XIAOZHI_BRIDGE_SYSTEM_PROMPT",
                (
                    "You are a Vietnamese voice assistant for Xiaozhi.\n"
                    "Reply directly, naturally, and helpfully in Vietnamese.\n"
                    "Do not repeat or paraphrase the user's question as your answer.\n"
                    "Do not mention internal reasoning, system rules, or hidden instructions.\n"
                    "Do not use emoji, markdown, or bullet lists unless the user explicitly asks.\n"
                    "Keep each reply short: at most 2 brief sentences and around 120 characters when possible.\n"
                    "If the request is unclear, ask exactly 1 short follow-up question.\n"
                    "If the user greets you, greet back briefly and ask how you can help."
                ),
            ),
            context_tail_messages=int(os.getenv("XIAOZHI_BRIDGE_CONTEXT_TAIL_MESSAGES", "6")),
            session_summary_max_chars=int(os.getenv("XIAOZHI_BRIDGE_SESSION_SUMMARY_MAX_CHARS", "600")),
            conversation_idle_timeout_seconds=int(
                os.getenv("XIAOZHI_BRIDGE_CONVERSATION_IDLE_TIMEOUT_SECONDS", "3600")
            ),
            conversation_cleanup_interval_seconds=int(
                os.getenv("XIAOZHI_BRIDGE_CONVERSATION_CLEANUP_INTERVAL_SECONDS", "300")
            ),
            max_reply_chars=int(os.getenv("XIAOZHI_BRIDGE_MAX_REPLY_CHARS", "120")),
            max_reply_sentences=int(os.getenv("XIAOZHI_BRIDGE_MAX_REPLY_SENTENCES", "2")),
            drop_audio_while_processing=_get_bool_env("XIAOZHI_BRIDGE_DROP_AUDIO_WHILE_PROCESSING", True),
            drop_audio_while_tts=_get_bool_env("XIAOZHI_BRIDGE_DROP_AUDIO_WHILE_TTS", True),
            tts_echo_guard_ms=int(os.getenv("XIAOZHI_BRIDGE_TTS_ECHO_GUARD_MS", "1200")),
            echo_similarity_threshold=float(os.getenv("XIAOZHI_BRIDGE_ECHO_SIMILARITY_THRESHOLD", "0.75")),
            sample_rate=int(os.getenv("XIAOZHI_BRIDGE_SAMPLE_RATE", "16000")),
            channels=int(os.getenv("XIAOZHI_BRIDGE_CHANNELS", "1")),
            frame_duration=int(os.getenv("XIAOZHI_BRIDGE_FRAME_DURATION", "60")),
            tts_voice=os.getenv("XIAOZHI_BRIDGE_TTS_VOICE", "vi-VN-HoaiMyNeural"),
            asr_model=os.getenv("XIAOZHI_BRIDGE_ASR_MODEL", "large-v3"),
            asr_language=os.getenv("XIAOZHI_BRIDGE_ASR_LANGUAGE", "vi"),
            asr_device=os.getenv("XIAOZHI_BRIDGE_ASR_DEVICE", "cuda"),
            asr_compute_type=os.getenv("XIAOZHI_BRIDGE_ASR_COMPUTE_TYPE", "float16"),
            discovery_enable=_get_bool_env("XIAOZHI_BRIDGE_DISCOVERY_ENABLE", True),
            discovery_host=os.getenv("XIAOZHI_BRIDGE_DISCOVERY_HOST", "xiaozhi-bridge"),
            discovery_port=int(os.getenv("XIAOZHI_BRIDGE_DISCOVERY_PORT", "24681")),
            server_id=os.getenv("XIAOZHI_BRIDGE_SERVER_ID", "") or uuid.uuid4().hex,
            ffmpeg_path=os.getenv("XIAOZHI_BRIDGE_FFMPEG_PATH", ""),
            log_dir=Path(os.getenv("XIAOZHI_BRIDGE_LOG_DIR", str(REPO_ROOT / "tmp"))),
        )

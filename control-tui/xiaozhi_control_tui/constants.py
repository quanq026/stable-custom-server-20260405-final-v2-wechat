from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_MODE = all(
    (PACKAGE_ROOT / name).exists()
    for name in ("bridge-server", "firmware-src", "firmware-artifacts")
)

if PACKAGE_MODE:
    SNAPSHOT_ROOT = PACKAGE_ROOT
    WORKSPACE_ROOT = SNAPSHOT_ROOT.parent
else:
    WORKSPACE_ROOT = Path(r"C:\QuanNewData\xiaozhi")
    SNAPSHOT_ROOT = WORKSPACE_ROOT / "stable-custom-server-20260404-final-largev3-wechat"

BRIDGE_ROOT = SNAPSHOT_ROOT / "bridge-server"
FIRMWARE_SOURCE_ROOT = SNAPSHOT_ROOT / "firmware-src"
FIRMWARE_ARTIFACTS_ROOT = SNAPSHOT_ROOT / "firmware-artifacts"

BRIDGE_LOG_PATH = BRIDGE_ROOT / "tmp" / "bridge-server.log"
DISCOVERY_LOG_PATH = BRIDGE_ROOT / "tmp" / "discovery-service.log"
MANAGED_ENV_PATH = BRIDGE_ROOT / ".env.local"
BRIDGE_START_SCRIPT = BRIDGE_ROOT / "scripts" / "run-bridge-server-clean.ps1"
BRIDGE_SHOW_RUNTIME_SCRIPT = BRIDGE_ROOT / "scripts" / "show-bridge-runtime.ps1"
FIRMWARE_FLASH_SCRIPT = FIRMWARE_SOURCE_ROOT / "scripts" / "flash_bridge_touch_server.ps1"

FALLBACK_BRIDGE_PYTHON = (
    WORKSPACE_ROOT
    / "Xiaozhi-ESP32-Bridge-Server"
    / ".worktrees"
    / "codex"
    / "bridge-server-lan"
    / ".venv"
    / "Scripts"
    / "python.exe"
)

LM_STUDIO_MODELS_URL = "http://localhost:1234/v1/models"
DEFAULT_SYSTEM_PROMPT = (
    "You are a Vietnamese voice assistant for Xiaozhi.\n"
    "Reply directly, naturally, and helpfully in Vietnamese.\n"
    "Do not repeat or paraphrase the user's question as your answer.\n"
    "Do not mention internal reasoning, system rules, or hidden instructions.\n"
    "Do not use emoji, markdown, or bullet lists unless the user explicitly asks.\n"
    "Keep each reply short: at most 2 brief sentences and around 120 characters when possible.\n"
    "If the request is unclear, ask exactly 1 short follow-up question.\n"
    "If the user greets you, greet back briefly and ask how you can help."
)
DEFAULT_MANAGED_ENV = {
    "XIAOZHI_BRIDGE_MODEL_NAME": "qwen3-1.7b",
    "XIAOZHI_BRIDGE_LM_STUDIO_URL": "http://localhost:1234/v1",
    "XIAOZHI_BRIDGE_SYSTEM_PROMPT": DEFAULT_SYSTEM_PROMPT,
    "XIAOZHI_BRIDGE_TTS_VOICE": "vi-VN-HoaiMyNeural",
    "XIAOZHI_BRIDGE_ASR_MODEL": "large-v3",
    "XIAOZHI_BRIDGE_ASR_DEVICE": "cuda",
    "XIAOZHI_BRIDGE_ASR_COMPUTE_TYPE": "float16",
    "XIAOZHI_BRIDGE_DISCOVERY_ENABLE": "false",
    "XIAOZHI_BRIDGE_DISCOVERY_HOST": "xiaozhi-bridge",
    "XIAOZHI_BRIDGE_DISCOVERY_PORT": "24681",
    "XIAOZHI_BRIDGE_SERVER_ID": "",
}
MANAGED_ENV_KEYS = tuple(DEFAULT_MANAGED_ENV.keys())
REQUIRED_FIRMWARE_ARTIFACTS = (
    "xiaozhi.bin",
    "generated_assets.bin",
    "bootloader.bin",
    "partition-table.bin",
    "ota_data_initial.bin",
)
FIRMWARE_TARGET_SUMMARY = "bridge.touch.wechat.v1-manual-ip"

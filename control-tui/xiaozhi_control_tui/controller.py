from typing import Callable

from .bridge import BridgeManager
from .discovery import DiscoveryManager
from .constants import DEFAULT_MANAGED_ENV, FIRMWARE_TARGET_SUMMARY, REQUIRED_FIRMWARE_ARTIFACTS
from .env_store import ensure_server_id, load_env, save_env
from .firmware import FirmwareManager
from .lmstudio import LMStudioClient
from .models import CommandResult, FlashPlan, RuntimeStatus
from .runtime import detect_lan_ip_candidates, detect_serial_ports, get_bridge_processes, get_discovery_processes


class ControlController:
    def __init__(
        self,
        *,
        env_path,
        firmware_artifacts_root,
        bridge_log_path,
        bridge_manager: BridgeManager,
        discovery_manager: DiscoveryManager,
        firmware_manager: FirmwareManager,
        lmstudio_client: LMStudioClient,
    ):
        self.env_path = env_path
        self.firmware_artifacts_root = firmware_artifacts_root
        self.bridge_log_path = bridge_log_path
        self.bridge_manager = bridge_manager
        self.discovery_manager = discovery_manager
        self.firmware_manager = firmware_manager
        self.lmstudio_client = lmstudio_client
        self.banner = "Ready"
        self.log_messages: list[str] = []
        self.last_status: RuntimeStatus | None = None

    def append_log(self, line: str) -> None:
        self.log_messages.append(line)

    def managed_env(self) -> dict[str, str]:
        ensure_server_id(self.env_path)
        return load_env(self.env_path)

    def save_runtime_settings(self, updates: dict[str, str]) -> dict[str, str]:
        saved = save_env(self.env_path, updates)
        self.banner = "Saved runtime settings"
        return saved

    def save_model_selection(self, model_name: str) -> dict[str, str]:
        saved = self.save_runtime_settings({"XIAOZHI_BRIDGE_MODEL_NAME": model_name})
        self.banner = f"Saved model: {model_name}"
        return saved

    def refresh_status(self) -> RuntimeStatus:
        env = self.managed_env()
        bridge_processes = get_bridge_processes()
        lan_ip_candidates = detect_lan_ip_candidates()
        firmware_artifacts_ready = all(
            (self.firmware_artifacts_root / name).exists() for name in REQUIRED_FIRMWARE_ARTIFACTS
        )
        try:
            bridge_python_path = str(self.bridge_manager.resolved_python())
        except FileNotFoundError:
            bridge_python_path = "MISSING"

        status = RuntimeStatus(
            bridge_up=bool(bridge_processes),
            bridge_processes=bridge_processes,
            connection_mode="Manual IP (v1)",
            preferred_laptop_ip=lan_ip_candidates[0] if lan_ip_candidates else "",
            laptop_ipv4_candidates=lan_ip_candidates,
            discovery_up=False,
            discovery_enabled=False,
            discovery_processes=[],
            discovery_host="",
            discovery_port=0,
            server_id="",
            lm_studio_reachable=self.lmstudio_client.is_reachable(),
            configured_model=env.get("XIAOZHI_BRIDGE_MODEL_NAME", DEFAULT_MANAGED_ENV["XIAOZHI_BRIDGE_MODEL_NAME"]),
            asr_mode=(
                f"{env.get('XIAOZHI_BRIDGE_ASR_MODEL', DEFAULT_MANAGED_ENV['XIAOZHI_BRIDGE_ASR_MODEL'])} / "
                f"{env.get('XIAOZHI_BRIDGE_ASR_DEVICE', DEFAULT_MANAGED_ENV['XIAOZHI_BRIDGE_ASR_DEVICE'])} / "
                f"{env.get('XIAOZHI_BRIDGE_ASR_COMPUTE_TYPE', DEFAULT_MANAGED_ENV['XIAOZHI_BRIDGE_ASR_COMPUTE_TYPE'])}"
            ),
            tts_voice=env.get("XIAOZHI_BRIDGE_TTS_VOICE", DEFAULT_MANAGED_ENV["XIAOZHI_BRIDGE_TTS_VOICE"]),
            firmware_target=FIRMWARE_TARGET_SUMMARY,
            serial_ports=detect_serial_ports(),
            bridge_log_exists=self.bridge_log_path.exists(),
            firmware_artifacts_ready=firmware_artifacts_ready,
            bridge_python_path=bridge_python_path,
        )
        self.last_status = status
        return status

    def health_check(self) -> RuntimeStatus:
        status = self.refresh_status()
        self.banner = "Health check complete"
        return status

    def list_models(self) -> list[str]:
        return self.lmstudio_client.list_models()

    def prepare_flash_plan(self) -> FlashPlan:
        return FlashPlan(
            ports=detect_serial_ports(),
            artifact_summary=FIRMWARE_TARGET_SUMMARY,
        )

    def execute_action(self, action_name: str, func: Callable[..., object], *args, **kwargs):
        self.append_log(f"[{action_name}] started")
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            self.banner = f"{action_name} failed: {exc}"
            self.append_log(self.banner)
            raise
        self.banner = f"{action_name} completed"
        self.append_log(f"[{action_name}] completed")
        return result

    def start_bridge(self, on_line=None):
        return self.execute_action("Start Bridge", self._start_stack, on_line)

    def stop_bridge(self, on_line=None):
        return self.execute_action("Stop Bridge", self._stop_stack, on_line)

    def restart_bridge(self, on_line=None):
        return self.execute_action("Restart Bridge", self._restart_stack, on_line)

    def build_firmware(self, on_line=None):
        return self.execute_action("Build Firmware", self.firmware_manager.build, on_line)

    def flash_firmware(self, port: str, on_line=None):
        if not port:
            raise ValueError("Flash requires explicit COM-port confirmation")
        return self.execute_action("Flash Firmware", self.firmware_manager.flash, port, on_line)

    def fresh_flash_firmware(self, port: str, on_line=None):
        if not port:
            raise ValueError("Fresh Flash requires explicit COM-port confirmation")
        return self.execute_action("Fresh Flash", self.firmware_manager.fresh_flash, port, on_line)

    def status_lines(self) -> list[str]:
        status = self.last_status or self.refresh_status()
        lines = [
            f"Bridge: {'UP' if status.bridge_up else 'DOWN'}",
            f"Connection mode: {status.connection_mode}",
            f"Laptop IP: {status.preferred_laptop_ip or 'not found'}",
            f"LM Studio: {'UP' if status.lm_studio_reachable else 'DOWN'}",
            f"Model: {status.configured_model}",
            f"ASR: {status.asr_mode}",
            f"TTS: {status.tts_voice}",
            f"Firmware target: {status.firmware_target}",
            f"Bridge log: {'present' if status.bridge_log_exists else 'missing'}",
            f"Artifacts: {'ready' if status.firmware_artifacts_ready else 'missing'}",
            f"Bridge Python: {status.bridge_python_path}",
            "Serial ports:",
        ]
        if status.bridge_python_path == "MISSING":
            lines.append("  - create bridge-server\\.venv before starting bridge")
        if status.serial_ports:
            lines.extend([f"  - {port.device}: {port.description}" for port in status.serial_ports])
        else:
            lines.append("  - none detected")
        if len(status.laptop_ipv4_candidates) > 1:
            lines.append("Other LAN IPs:")
            lines.extend([f"  - {item}" for item in status.laptop_ipv4_candidates[1:]])
        if status.bridge_processes:
            lines.extend([f"PID {proc.pid} on {proc.port}" for proc in status.bridge_processes])
        return lines

    def _start_stack(self, on_line=None) -> CommandResult:
        bridge_result = self.bridge_manager.start(on_line=on_line)
        if bridge_result.exit_code != 0:
            return bridge_result
        guidance = ["Discovery disabled in v1 mode"]
        if self.last_status is None:
            self.refresh_status()
        if self.last_status and self.last_status.preferred_laptop_ip:
            guidance.append(f"Use laptop IP on device portal: {self.last_status.preferred_laptop_ip}")
            if on_line:
                on_line(guidance[-1])
        if on_line:
            on_line(guidance[0])
        return CommandResult(
            exit_code=bridge_result.exit_code,
            output=bridge_result.output + guidance,
        )

    def _stop_stack(self, on_line=None) -> CommandResult:
        bridge_result = self.bridge_manager.stop(on_line=on_line)
        return CommandResult(
            exit_code=bridge_result.exit_code,
            output=bridge_result.output,
        )

    def _restart_stack(self, on_line=None) -> CommandResult:
        stop_result = self._stop_stack(on_line=on_line)
        start_result = self._start_stack(on_line=on_line)
        return CommandResult(
            exit_code=start_result.exit_code,
            output=stop_result.output + start_result.output,
        )

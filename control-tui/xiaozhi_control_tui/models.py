from dataclasses import dataclass, field


@dataclass(slots=True)
class SerialPortInfo:
    device: str
    description: str


@dataclass(slots=True)
class BridgeProcessInfo:
    port: int
    pid: int
    executable: str = ""
    command_line: str = ""


@dataclass(slots=True)
class RuntimeStatus:
    bridge_up: bool
    bridge_processes: list[BridgeProcessInfo] = field(default_factory=list)
    connection_mode: str = "Manual IP (v1)"
    preferred_laptop_ip: str = ""
    laptop_ipv4_candidates: list[str] = field(default_factory=list)
    discovery_up: bool = False
    discovery_enabled: bool = True
    discovery_processes: list[BridgeProcessInfo] = field(default_factory=list)
    discovery_host: str = ""
    discovery_port: int = 24681
    server_id: str = ""
    lm_studio_reachable: bool = False
    configured_model: str = ""
    asr_mode: str = ""
    tts_voice: str = ""
    firmware_target: str = ""
    serial_ports: list[SerialPortInfo] = field(default_factory=list)
    bridge_log_exists: bool = False
    firmware_artifacts_ready: bool = False
    bridge_python_path: str = ""


@dataclass(slots=True)
class FlashPlan:
    ports: list[SerialPortInfo]
    artifact_summary: str


@dataclass(slots=True)
class CommandResult:
    exit_code: int
    output: list[str] = field(default_factory=list)

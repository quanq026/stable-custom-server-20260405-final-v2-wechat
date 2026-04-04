from pathlib import Path
from typing import Any

from serial.tools import list_ports

from .constants import FALLBACK_BRIDGE_PYTHON
from .models import BridgeProcessInfo, SerialPortInfo
from .process_utils import powershell_command, run_capture_json


def parse_bridge_processes(payload: Any) -> list[BridgeProcessInfo]:
    if not payload:
        return []
    if isinstance(payload, dict):
        payload = [payload]

    processes: list[BridgeProcessInfo] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        processes.append(
            BridgeProcessInfo(
                port=int(item.get("Port", 0)),
                pid=int(item.get("PID", 0)),
                executable=str(item.get("Executable", "") or ""),
                command_line=str(item.get("CommandLine", "") or ""),
            )
        )
    return processes


def _listening_process_script(port: int, protocol: str) -> str:
    if protocol.upper() == "UDP":
        endpoint_cmd = f"Get-NetUDPEndpoint -LocalPort {port} -ErrorAction SilentlyContinue"
    else:
        endpoint_cmd = f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue"

    return f"""
    $items = @(
      {endpoint_cmd} |
        ForEach-Object {{
          $process = Get-CimInstance Win32_Process -Filter "ProcessId = $($_.OwningProcess)"
          [PSCustomObject]@{{
            Port = $_.LocalPort
            PID = $_.OwningProcess
            Executable = $process.ExecutablePath
            CommandLine = $process.CommandLine
          }}
        }}
    )
    @($items) | ConvertTo-Json -Compress
    """


def get_bridge_processes(port: int = 8000) -> list[BridgeProcessInfo]:
    script = _listening_process_script(port, "TCP")
    return parse_bridge_processes(run_capture_json(powershell_command(script)))


def get_discovery_processes(port: int = 24681) -> list[BridgeProcessInfo]:
    script = _listening_process_script(port, "UDP")
    return parse_bridge_processes(run_capture_json(powershell_command(script)))


def detect_serial_ports() -> list[SerialPortInfo]:
    ports = []
    for port in list_ports.comports():
        ports.append(SerialPortInfo(device=port.device, description=port.description or port.name))
    return sorted(ports, key=lambda item: item.device)


def resolve_bridge_python(primary_root: Path, fallback: Path = FALLBACK_BRIDGE_PYTHON) -> Path | None:
    primary = primary_root / ".venv" / "Scripts" / "python.exe"
    if primary.exists():
        return primary
    if fallback.exists():
        return fallback
    return None

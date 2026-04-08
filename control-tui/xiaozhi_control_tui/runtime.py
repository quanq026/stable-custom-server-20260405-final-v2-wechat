from dataclasses import dataclass
import ipaddress
from pathlib import Path
from typing import Any

from serial.tools import list_ports

from .constants import FALLBACK_BRIDGE_PYTHON
from .models import BridgeProcessInfo, SerialPortInfo
from .process_utils import powershell_command, run_capture_json


@dataclass(slots=True, frozen=True)
class LanIpCandidate:
    interface_alias: str
    address: str
    has_default_gateway: bool


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


def filter_processes_by_marker(processes: list[BridgeProcessInfo], marker: str) -> list[BridgeProcessInfo]:
    lowered_marker = marker.lower()
    return [item for item in processes if lowered_marker in item.command_line.lower()]


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
    processes = parse_bridge_processes(run_capture_json(powershell_command(script)))
    return filter_processes_by_marker(processes, "xiaozhi_bridge.server")


def get_discovery_processes(port: int = 24681) -> list[BridgeProcessInfo]:
    script = _listening_process_script(port, "UDP")
    processes = parse_bridge_processes(run_capture_json(powershell_command(script)))
    return filter_processes_by_marker(processes, "xiaozhi_control_tui.discovery")


def detect_serial_ports() -> list[SerialPortInfo]:
    ports = []
    for port in list_ports.comports():
        ports.append(SerialPortInfo(device=port.device, description=port.description or port.name))
    return sorted(ports, key=lambda item: item.device)


def _is_private_ipv4(address: str) -> bool:
    try:
        parsed = ipaddress.ip_address(address)
    except ValueError:
        return False
    return parsed.version == 4 and parsed.is_private and not parsed.is_link_local and not parsed.is_loopback


def parse_lan_ip_candidates(payload: Any) -> list[LanIpCandidate]:
    if not payload:
        return []
    if isinstance(payload, dict):
        payload = [payload]

    candidates: list[LanIpCandidate] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        interface_alias = str(item.get("InterfaceAlias", "") or "")
        has_default_gateway = bool(item.get("HasDefaultGateway", False))
        addresses = item.get("IPv4Addresses", [])
        if not isinstance(addresses, list):
            continue
        for address in addresses:
            text = str(address or "").strip()
            if _is_private_ipv4(text):
                candidates.append(
                    LanIpCandidate(
                        interface_alias=interface_alias,
                        address=text,
                        has_default_gateway=has_default_gateway,
                    )
                )
    return candidates


def choose_preferred_lan_ip(candidates: list[LanIpCandidate]) -> str:
    if not candidates:
        return ""
    ordered = sorted(
        candidates,
        key=lambda item: (
            0 if item.has_default_gateway else 1,
            0 if item.address.startswith("192.168.") else 1,
            0 if item.address.startswith("10.") else 1,
            item.interface_alias.lower(),
            item.address,
        ),
    )
    return ordered[0].address


def detect_lan_ip_candidates() -> list[str]:
    script = """
    $items = @(
      Get-NetIPConfiguration -Detailed -ErrorAction SilentlyContinue |
        Where-Object { $_.IPv4Address } |
        ForEach-Object {
          [PSCustomObject]@{
            InterfaceAlias = $_.InterfaceAlias
            HasDefaultGateway = $null -ne $_.IPv4DefaultGateway
            IPv4Addresses = @($_.IPv4Address | ForEach-Object { $_.IPAddress })
          }
        }
    )
    @($items) | ConvertTo-Json -Compress
    """
    candidates = parse_lan_ip_candidates(run_capture_json(powershell_command(script)))
    preferred = choose_preferred_lan_ip(candidates)
    ordered = []
    if preferred:
        ordered.append(preferred)
    for candidate in candidates:
        if candidate.address not in ordered:
            ordered.append(candidate.address)
    return ordered


def resolve_bridge_python(primary_root: Path, fallback: Path = FALLBACK_BRIDGE_PYTHON) -> Path | None:
    primary = primary_root / ".venv" / "Scripts" / "python.exe"
    if primary.exists():
        return primary
    if fallback.exists():
        return fallback
    return None

import argparse
import json
import logging
import os
import signal
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from zeroconf import IPVersion, ServiceInfo, Zeroconf

from .env_store import ensure_server_id, load_env
from .models import CommandResult
from .process_utils import powershell_command, run_subprocess
from .runtime import get_discovery_processes


DISCOVERY_START_TIMEOUT_SECONDS = 20
DISCOVERY_POLL_INTERVAL_SECONDS = 0.5
DISCOVERY_SERVICE_TYPE = "_xiaozhi-bridge._tcp.local."
DISCOVERY_REQUEST_TYPE = "xiaozhi-discovery"
DISCOVERY_RESPONSE_TYPE = "xiaozhi-discovery-response"


@dataclass(slots=True)
class DiscoveryRequest:
    version: int
    client_id: str


def parse_discovery_request(payload: bytes | str) -> DiscoveryRequest:
    try:
        data = json.loads(payload.decode("utf-8") if isinstance(payload, bytes) else payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid discovery request payload") from exc

    if data.get("type") != DISCOVERY_REQUEST_TYPE or int(data.get("version", 0)) != 1:
        raise ValueError("Unsupported discovery request")

    client_id = str(data.get("client_id", "")).strip()
    if not client_id:
        raise ValueError("Missing discovery client_id")
    return DiscoveryRequest(version=1, client_id=client_id)


def route_aware_local_ip(requester_ip: str, requester_port: int = 9) -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect((requester_ip, requester_port))
        return probe.getsockname()[0]


def guess_mdns_ip() -> str:
    try:
        return route_aware_local_ip("8.8.8.8", 53)
    except OSError:
        addresses: list[str] = []
        for family, _, _, _, sockaddr in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            if family == socket.AF_INET and sockaddr:
                ip = sockaddr[0]
                if ip and not ip.startswith("127."):
                    addresses.append(ip)
        if not addresses:
            raise RuntimeError("Could not determine local IPv4 address for mDNS")
        return sorted(set(addresses))[0]


def build_discovery_response(
    *,
    requester_ip: str,
    server_id: str,
    server_name: str,
    host: str,
    websocket_port: int,
    websocket_path: str,
    resolve_local_ip=route_aware_local_ip,
) -> dict[str, object]:
    local_ip = resolve_local_ip(requester_ip)
    normalized_path = websocket_path if websocket_path.startswith("/") else f"/{websocket_path}"
    return {
        "type": DISCOVERY_RESPONSE_TYPE,
        "version": 1,
        "server_id": server_id,
        "server_name": server_name,
        "ws_url": f"ws://{local_ip}:{websocket_port}{normalized_path}",
        "host": f"{host}.local",
        "port": websocket_port,
        "path": normalized_path,
    }


class DiscoveryResponder:
    def __init__(
        self,
        *,
        server_id: str,
        server_name: str,
        host: str,
        discovery_port: int,
        websocket_port: int,
        websocket_path: str,
        logger: logging.Logger,
    ):
        self.server_id = server_id
        self.server_name = server_name
        self.host = host
        self.discovery_port = discovery_port
        self.websocket_port = websocket_port
        self.websocket_path = websocket_path
        self.logger = logger
        self.stop_event = threading.Event()
        self.udp_socket: socket.socket | None = None
        self.udp_thread: threading.Thread | None = None
        self.zeroconf: Zeroconf | None = None
        self.service_info: ServiceInfo | None = None

    def start(self) -> None:
        self._start_mdns()
        self.udp_thread = threading.Thread(target=self._udp_loop, name="xiaozhi-discovery-udp", daemon=True)
        self.udp_thread.start()
        self.logger.info(
            "Discovery responder started host=%s.local discovery_port=%s websocket_port=%s",
            self.host,
            self.discovery_port,
            self.websocket_port,
        )

    def wait(self) -> None:
        while not self.stop_event.wait(0.5):
            continue

    def stop(self) -> None:
        self.stop_event.set()
        if self.udp_socket is not None:
            try:
                self.udp_socket.close()
            except OSError:
                pass
            self.udp_socket = None
        if self.udp_thread is not None:
            self.udp_thread.join(timeout=2)
            self.udp_thread = None
        if self.zeroconf is not None:
            if self.service_info is not None:
                try:
                    self.zeroconf.unregister_service(self.service_info)
                except Exception:
                    self.logger.exception("Failed to unregister mDNS service")
            self.zeroconf.close()
            self.zeroconf = None
            self.service_info = None
        self.logger.info("Discovery responder stopped")

    def _start_mdns(self) -> None:
        address = socket.inet_aton(guess_mdns_ip())
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        self.service_info = ServiceInfo(
            DISCOVERY_SERVICE_TYPE,
            f"{self.server_name}.{DISCOVERY_SERVICE_TYPE}",
            addresses=[address],
            port=self.websocket_port,
            properties={
                b"path": self.websocket_path.encode("utf-8"),
                b"server_id": self.server_id.encode("utf-8"),
                b"server_name": self.server_name.encode("utf-8"),
            },
            server=f"{self.host}.local.",
        )
        self.zeroconf.register_service(self.service_info)

    def _udp_loop(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket = sock
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self.discovery_port))
        sock.settimeout(0.5)
        while not self.stop_event.is_set():
            try:
                payload, addr = sock.recvfrom(2048)
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                request = parse_discovery_request(payload)
                response = build_discovery_response(
                    requester_ip=addr[0],
                    server_id=self.server_id,
                    server_name=self.server_name,
                    host=self.host,
                    websocket_port=self.websocket_port,
                    websocket_path=self.websocket_path,
                )
                sock.sendto(json.dumps(response).encode("utf-8"), addr)
                self.logger.info(
                    "Responded to discovery request client_id=%s requester=%s ws_url=%s",
                    request.client_id,
                    addr[0],
                    response["ws_url"],
                )
            except ValueError:
                self.logger.debug("Ignored invalid discovery request from %s", addr[0])
            except Exception:
                self.logger.exception("Discovery response error for requester=%s", addr[0])


class DiscoveryManager:
    def __init__(self, bridge_root: Path, python_path: Path, log_path: Path):
        self.bridge_root = bridge_root
        self.python_path = python_path
        self.log_path = log_path
        self.package_root = Path(__file__).resolve().parents[1]

    @property
    def env_path(self) -> Path:
        return self.bridge_root / ".env.local"

    def ensure_server_id(self, env_path: Path | None = None) -> str:
        return ensure_server_id(env_path or self.env_path)

    def start_command(self) -> list[str]:
        self.ensure_server_id()
        return [
            str(self.python_path),
            "-m",
            "xiaozhi_control_tui.discovery",
            "--env",
            str(self.env_path),
            "--log",
            str(self.log_path),
        ]

    def stop_command(self) -> list[str]:
        port = int(load_env(self.env_path).get("XIAOZHI_BRIDGE_DISCOVERY_PORT", "24681"))
        script = """
        Get-CimInstance Win32_Process |
            Where-Object { $_.CommandLine -like '*xiaozhi_control_tui.discovery*' } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

        Get-NetUDPEndpoint -LocalPort __DISCOVERY_PORT__ -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique |
            ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }

        Write-Output 'Discovery responder stopped'
        exit 0
        """
        return powershell_command(script.replace("__DISCOVERY_PORT__", str(port)))

    def start(self, on_line=None) -> CommandResult:
        if on_line:
            on_line("Starting discovery responder...")

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_handle = self.log_path.open("a", encoding="utf-8")
        env = os.environ.copy()
        python_path = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{self.package_root}{os.pathsep}{python_path}" if python_path else str(self.package_root)
        )
        process = subprocess.Popen(
            self.start_command(),
            cwd=str(self.package_root),
            env=env,
            stdout=stdout_handle,
            stderr=subprocess.STDOUT,
        )
        stdout_handle.close()

        output = ["Starting discovery responder..."]
        port = int(load_env(self.env_path).get("XIAOZHI_BRIDGE_DISCOVERY_PORT", "24681"))
        deadline = time.time() + DISCOVERY_START_TIMEOUT_SECONDS
        while time.time() < deadline:
            if get_discovery_processes(port):
                success_line = f"Discovery responder running on UDP {port}"
                output.append(success_line)
                if on_line:
                    on_line(success_line)
                return CommandResult(exit_code=0, output=output)

            exit_code = process.poll()
            if exit_code is not None and exit_code != 0:
                failure_line = f"Discovery responder exited early with code {exit_code}"
                output.append(failure_line)
                if on_line:
                    on_line(failure_line)
                return CommandResult(exit_code=exit_code, output=output)

            time.sleep(DISCOVERY_POLL_INTERVAL_SECONDS)

        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        raise TimeoutError(f"Discovery responder failed to start on UDP {port} within timeout")

    def stop(self, on_line=None) -> CommandResult:
        port = int(load_env(self.env_path).get("XIAOZHI_BRIDGE_DISCOVERY_PORT", "24681"))
        exit_code, output = run_subprocess(self.stop_command(), cwd=self.bridge_root, on_line=on_line)
        if not get_discovery_processes(port):
            exit_code = 0
            if "Discovery responder stopped" not in output:
                output.append("Discovery responder stopped")
        return CommandResult(exit_code=exit_code, output=output)

    def restart(self, on_line=None) -> CommandResult:
        stop_result = self.stop(on_line=on_line)
        start_result = self.start(on_line=on_line)
        return CommandResult(
            exit_code=start_result.exit_code,
            output=stop_result.output + start_result.output,
        )


def _configure_logging(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
        force=True,
    )
    return logging.getLogger("xiaozhi_control_tui.discovery")


def run_service(env_path: Path, log_path: Path) -> None:
    env = load_env(env_path)
    server_id = ensure_server_id(env_path)
    host = env.get("XIAOZHI_BRIDGE_DISCOVERY_HOST", "xiaozhi-bridge").strip() or "xiaozhi-bridge"
    discovery_port = int(env.get("XIAOZHI_BRIDGE_DISCOVERY_PORT", "24681"))
    websocket_port = int(env.get("XIAOZHI_BRIDGE_PORT", "8000"))
    logger = _configure_logging(log_path)

    responder = DiscoveryResponder(
        server_id=server_id,
        server_name=host,
        host=host,
        discovery_port=discovery_port,
        websocket_port=websocket_port,
        websocket_path="/xiaozhi/v1/",
        logger=logger,
    )

    def handle_signal(_signum, _frame):
        responder.stop_event.set()

    for sig_name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        sig = getattr(signal, sig_name, None)
        if sig is not None:
            signal.signal(sig, handle_signal)

    responder.start()
    try:
        responder.wait()
    finally:
        responder.stop()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Xiaozhi bridge discovery responder")
    parser.add_argument("--env", required=True, help="Path to .env.local")
    parser.add_argument("--log", required=True, help="Path to discovery log")
    args = parser.parse_args(argv)

    run_service(Path(args.env), Path(args.log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

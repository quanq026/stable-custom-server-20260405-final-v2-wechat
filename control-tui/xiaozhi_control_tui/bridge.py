import os
import subprocess
import time
from pathlib import Path

from .models import CommandResult
from .process_utils import powershell_command, powershell_file_command, run_subprocess
from .runtime import get_bridge_processes, resolve_bridge_python


START_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 1


class BridgeManager:
    def __init__(self, bridge_root: Path, start_script: Path, fallback_python: Path):
        self.bridge_root = bridge_root
        self.start_script = start_script
        self.fallback_python = fallback_python

    def resolved_python(self) -> Path:
        python_path = resolve_bridge_python(self.bridge_root, self.fallback_python)
        if python_path is None:
            raise FileNotFoundError("Bridge Python runtime not found")
        return python_path

    def start(self, on_line=None) -> CommandResult:
        command = powershell_file_command(
            self.start_script,
            "-WorktreeRoot",
            str(self.bridge_root),
            "-PythonPath",
            str(self.resolved_python()),
        )
        if on_line:
            on_line("Starting bridge server...")

        process = subprocess.Popen(
            command,
            cwd=str(self.bridge_root),
            env=os.environ.copy(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        output = ["Starting bridge server..."]
        deadline = time.time() + START_TIMEOUT_SECONDS
        while time.time() < deadline:
            if get_bridge_processes():
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                success_line = "Bridge server running on port 8000"
                output.append(success_line)
                if on_line:
                    on_line(success_line)
                return CommandResult(exit_code=0, output=output)

            exit_code = process.poll()
            if exit_code is not None and exit_code != 0:
                failure_line = f"Bridge start script exited early with code {exit_code}"
                output.append(failure_line)
                if on_line:
                    on_line(failure_line)
                return CommandResult(exit_code=exit_code, output=output)

            time.sleep(POLL_INTERVAL_SECONDS)

        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()

        raise TimeoutError("Bridge server failed to start on port 8000 within timeout")

    def stop(self, on_line=None) -> CommandResult:
        script = """
        Get-CimInstance Win32_Process |
            Where-Object { $_.CommandLine -like '*xiaozhi_bridge.server*' } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

        Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique |
            ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }

        Write-Output 'Bridge server stopped'
        exit 0
        """
        exit_code, output = run_subprocess(powershell_command(script), on_line=on_line)
        if not get_bridge_processes():
            exit_code = 0
            if "Bridge server stopped" not in output:
                output.append("Bridge server stopped")
        return CommandResult(exit_code=exit_code, output=output)

    def restart(self, on_line=None) -> CommandResult:
        stop_result = self.stop(on_line=on_line)
        start_result = self.start(on_line=on_line)
        return CommandResult(
            exit_code=start_result.exit_code,
            output=stop_result.output + start_result.output,
        )

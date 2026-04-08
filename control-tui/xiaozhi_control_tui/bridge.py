import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .models import CommandResult
from .process_utils import powershell_command, powershell_file_command, run_subprocess
from .runtime import get_bridge_processes, resolve_bridge_python


START_TIMEOUT_SECONDS = 60
POLL_INTERVAL_SECONDS = 1
POST_START_VERIFY_POLLS = 3


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

    @property
    def stderr_log_path(self) -> Path:
        return self.bridge_root / "tmp" / "bridge-clean.err.log"

    def _tail_error_log(self, max_lines: int = 40) -> list[str]:
        path = self.stderr_log_path
        if not path.exists():
            return []
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            return []
        tail = [line for line in lines[-max_lines:] if line.strip()]
        if not tail:
            return []
        return ["--- bridge stderr ---", *tail]

    def _ensure_opus_dll(self, venv_root: Path, on_line=None) -> None:
        scripts_dir = venv_root / "Scripts"
        target = scripts_dir / "opus.dll"
        if target.exists():
            return

        av_libs = venv_root / "Lib" / "site-packages" / "av.libs"
        if not av_libs.exists():
            return

        candidates = sorted(av_libs.glob("libopus-*.dll"))
        if not candidates:
            return

        shutil.copyfile(candidates[0], target)
        if on_line:
            on_line(f"Provisioned opus.dll from {candidates[0].name}")

    def ensure_runtime(self, on_line=None) -> Path:
        python_path = resolve_bridge_python(self.bridge_root, self.fallback_python)
        if python_path is not None:
            return python_path

        bootstrap_python = Path(sys.executable)
        venv_root = self.bridge_root / ".venv"
        venv_python = venv_root / "Scripts" / "python.exe"
        requirements = self.bridge_root / "requirements.txt"

        if on_line:
            on_line("Bridge runtime missing. Bootstrapping .venv...")

        steps = [
            ([str(bootstrap_python), "-m", "venv", str(venv_root)], "Creating bridge virtual environment..."),
            ([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], "Upgrading pip..."),
            ([str(venv_python), "-m", "pip", "install", "-r", str(requirements)], "Installing bridge dependencies..."),
        ]

        for command, message in steps:
            if on_line:
                on_line(message)
            exit_code, output = run_subprocess(command, cwd=self.bridge_root, on_line=on_line)
            if exit_code != 0:
                raise RuntimeError(
                    f"Bridge runtime bootstrap failed at step: {message}"
                )

        self._ensure_opus_dll(venv_root, on_line=on_line)

        python_path = resolve_bridge_python(self.bridge_root, self.fallback_python)
        if python_path is None:
            raise RuntimeError("Bridge runtime bootstrap completed but python.exe was not found")
        return python_path

    def start(self, on_line=None) -> CommandResult:
        self.stop(on_line=on_line)
        python_path = self.ensure_runtime(on_line=on_line)
        command = powershell_file_command(
            self.start_script,
            "-WorktreeRoot",
            str(self.bridge_root),
            "-PythonPath",
            str(python_path),
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
                stable = True
                for _ in range(POST_START_VERIFY_POLLS):
                    time.sleep(POLL_INTERVAL_SECONDS)
                    if not get_bridge_processes():
                        stable = False
                        break
                if not stable:
                    failure_line = "Bridge listener disappeared during post-start verification"
                    output.append(failure_line)
                    output.extend(self._tail_error_log())
                    if on_line:
                        on_line(failure_line)
                        for line in self._tail_error_log():
                            on_line(line)
                    return CommandResult(exit_code=1, output=output)
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
                output.extend(self._tail_error_log())
                if on_line:
                    on_line(failure_line)
                    for line in self._tail_error_log():
                        on_line(line)
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
            Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -like '*xiaozhi_bridge.server*' } |
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

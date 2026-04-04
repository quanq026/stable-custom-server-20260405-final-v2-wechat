import json
import os
import subprocess
from pathlib import Path
from typing import Callable


LineCallback = Callable[[str], None]


def powershell_file_command(script_path: Path, *args: str) -> list[str]:
    command = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ]
    command.extend(arg for arg in args if arg)
    return command


def powershell_command(script: str) -> list[str]:
    return [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]


def run_subprocess(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    on_line: LineCallback | None = None,
) -> tuple[int, list[str]]:
    process = subprocess.Popen(
        command,
        cwd=str(cwd) if cwd else None,
        env=env or os.environ.copy(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    output: list[str] = []
    assert process.stdout is not None
    for line in process.stdout:
        cleaned = line.rstrip()
        output.append(cleaned)
        if on_line:
            on_line(cleaned)

    process.wait()
    return process.returncode, output


def run_capture_json(command: list[str], *, cwd: Path | None = None) -> object:
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    stdout = result.stdout.strip()
    return json.loads(stdout) if stdout else []

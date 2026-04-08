from pathlib import Path

from .models import CommandResult
from .process_utils import powershell_file_command, run_subprocess


class FirmwareManager:
    def __init__(self, project_root: Path, flash_script: Path):
        self.project_root = project_root
        self.flash_script = flash_script

    def build_command(self) -> list[str]:
        return powershell_file_command(self.flash_script)

    def flash_command(self, port: str, erase_flash: bool = False) -> list[str]:
        if not port:
            raise ValueError("COM port is required for flashing")
        args = ["-Port", port]
        if erase_flash:
            args.append("-EraseFlash")
        return powershell_file_command(self.flash_script, *args)

    def build(self, on_line=None) -> CommandResult:
        exit_code, output = run_subprocess(self.build_command(), cwd=self.project_root, on_line=on_line)
        return CommandResult(exit_code=exit_code, output=output)

    def flash(self, port: str, on_line=None) -> CommandResult:
        exit_code, output = run_subprocess(self.flash_command(port), cwd=self.project_root, on_line=on_line)
        return CommandResult(exit_code=exit_code, output=output)

    def fresh_flash(self, port: str, on_line=None) -> CommandResult:
        exit_code, output = run_subprocess(
            self.flash_command(port, erase_flash=True),
            cwd=self.project_root,
            on_line=on_line,
        )
        return CommandResult(exit_code=exit_code, output=output)

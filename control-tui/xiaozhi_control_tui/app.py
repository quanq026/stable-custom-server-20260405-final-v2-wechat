import sys
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, RichLog, Static, TextArea

from .bridge import BridgeManager
from .constants import (
    BRIDGE_LOG_PATH,
    BRIDGE_ROOT,
    BRIDGE_START_SCRIPT,
    DISCOVERY_LOG_PATH,
    FALLBACK_BRIDGE_PYTHON,
    FIRMWARE_ARTIFACTS_ROOT,
    FIRMWARE_FLASH_SCRIPT,
    FIRMWARE_SOURCE_ROOT,
    LM_STUDIO_MODELS_URL,
    MANAGED_ENV_PATH,
)
from .controller import ControlController
from .discovery import DiscoveryManager
from .firmware import FirmwareManager
from .lmstudio import LMStudioClient


class SelectOptionScreen(ModalScreen[str | None]):
    def __init__(self, title: str, options: list[str]):
        super().__init__()
        self.title = title
        self.options = options

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label(self.title, id="dialog-title"),
            ListView(*[ListItem(Label(option), name=option) for option in self.options], id="dialog-list"),
            Horizontal(Button("Confirm", id="confirm"), Button("Cancel", id="cancel"), id="dialog-actions"),
            id="dialog",
        )

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#confirm")
    def confirm(self) -> None:
        list_view = self.query_one("#dialog-list", ListView)
        if list_view.index is None:
            self.dismiss(None)
            return
        self.dismiss(self.options[list_view.index])


class RuntimeSettingsScreen(ModalScreen[dict[str, str] | None]):
    def __init__(self, values: dict[str, str]):
        super().__init__()
        self.values = values

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Runtime Settings", id="dialog-title"),
            Label("LM Studio URL"),
            Input(self.values.get("XIAOZHI_BRIDGE_LM_STUDIO_URL", ""), id="lm_url"),
            Label("TTS Voice"),
            Input(self.values.get("XIAOZHI_BRIDGE_TTS_VOICE", ""), id="tts_voice"),
            Label("ASR Model"),
            Input(self.values.get("XIAOZHI_BRIDGE_ASR_MODEL", ""), id="asr_model"),
            Label("ASR Device"),
            Input(self.values.get("XIAOZHI_BRIDGE_ASR_DEVICE", ""), id="asr_device"),
            Label("ASR Compute Type"),
            Input(self.values.get("XIAOZHI_BRIDGE_ASR_COMPUTE_TYPE", ""), id="asr_compute"),
            Horizontal(Button("Save", id="confirm"), Button("Cancel", id="cancel"), id="dialog-actions"),
            id="dialog",
        )

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#confirm")
    def confirm(self) -> None:
        self.dismiss(
            {
                "XIAOZHI_BRIDGE_LM_STUDIO_URL": self.query_one("#lm_url", Input).value.strip(),
                "XIAOZHI_BRIDGE_TTS_VOICE": self.query_one("#tts_voice", Input).value.strip(),
                "XIAOZHI_BRIDGE_ASR_MODEL": self.query_one("#asr_model", Input).value.strip(),
                "XIAOZHI_BRIDGE_ASR_DEVICE": self.query_one("#asr_device", Input).value.strip(),
                "XIAOZHI_BRIDGE_ASR_COMPUTE_TYPE": self.query_one("#asr_compute", Input).value.strip(),
            }
        )


class SystemPromptScreen(ModalScreen[str | None]):
    def __init__(self, prompt_text: str):
        super().__init__()
        self.prompt_text = prompt_text

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Edit System Prompt", id="dialog-title"),
            Static("Prompt is saved into .env.local and applied after bridge restart.", id="prompt-summary"),
            TextArea(self.prompt_text, id="prompt-editor"),
            Horizontal(Button("Save", id="confirm"), Button("Cancel", id="cancel"), id="dialog-actions"),
            id="dialog",
        )

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#confirm")
    def confirm(self) -> None:
        self.dismiss(self.query_one("#prompt-editor", TextArea).text.strip())


class FlashConfirmScreen(ModalScreen[str | None]):
    def __init__(self, ports: list[str], artifact_summary: str):
        super().__init__()
        self.ports = ports
        self.artifact_summary = artifact_summary

    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Confirm Flash", id="dialog-title"),
            Static(f"Firmware target: {self.artifact_summary}\nSelect COM port to flash.", id="flash-summary"),
            ListView(*[ListItem(Label(port), name=port) for port in self.ports], id="dialog-list"),
            Horizontal(Button("Flash", id="confirm"), Button("Cancel", id="cancel"), id="dialog-actions"),
            id="dialog",
        )

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#confirm")
    def confirm(self) -> None:
        list_view = self.query_one("#dialog-list", ListView)
        if list_view.index is None:
            self.dismiss(None)
            return
        self.dismiss(self.ports[list_view.index])


class XiaozhiControlApp(App):
    CSS = """
    Screen { layout: vertical; }
    #banner { height: 3; padding: 0 1; background: $accent 15%; }
    #body { height: 1fr; layout: horizontal; }
    #status-panel, #log-panel, #actions-panel { border: round $accent; padding: 1; }
    #status-panel { width: 36; }
    #actions-panel { width: 28; }
    #log-panel { width: 1fr; }
    #dialog { width: 80; height: auto; padding: 1 2; border: round $accent; background: $surface; }
    #dialog-list { height: 12; margin: 1 0; }
    #prompt-editor { height: 16; margin: 1 0; }
    Button { width: 1fr; margin: 0 0 1 0; }
    """

    BINDINGS = [("q", "quit", "Quit"), ("r", "refresh", "Refresh")]

    def __init__(self, controller: ControlController | None = None):
        super().__init__()
        self.controller = controller or ControlController(
            env_path=MANAGED_ENV_PATH,
            firmware_artifacts_root=FIRMWARE_ARTIFACTS_ROOT,
            bridge_log_path=BRIDGE_LOG_PATH,
            bridge_manager=BridgeManager(BRIDGE_ROOT, BRIDGE_START_SCRIPT, FALLBACK_BRIDGE_PYTHON),
            discovery_manager=DiscoveryManager(BRIDGE_ROOT, Path(sys.executable), DISCOVERY_LOG_PATH),
            firmware_manager=FirmwareManager(FIRMWARE_SOURCE_ROOT, FIRMWARE_FLASH_SCRIPT),
            lmstudio_client=LMStudioClient(LM_STUDIO_MODELS_URL),
        )
        self._log_offset = 0
        self._action_running = False

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("Ready", id="banner")
        yield Horizontal(
            Static(id="status-panel"),
            RichLog(id="log-panel", wrap=True, highlight=False, markup=False),
            VerticalScroll(
                Button("Start Bridge", id="start-bridge"),
                Button("Stop Bridge", id="stop-bridge"),
                Button("Restart Bridge", id="restart-bridge"),
                Button("Health Check", id="health-check"),
                Button("Select Model", id="select-model"),
                Button("System Prompt", id="system-prompt"),
                Button("Runtime Settings", id="runtime-settings"),
                Button("Build Firmware", id="build-firmware"),
                Button("Flash Firmware", id="flash-firmware"),
                Button("Refresh Status", id="refresh-status"),
                id="actions-panel",
            ),
            id="body",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(2.5, self._refresh_bridge_log)
        self.call_after_refresh(self.refresh_status_view)

    def action_refresh(self) -> None:
        self.refresh_status_view()

    def _append_log(self, line: str) -> None:
        self.query_one("#log-panel", RichLog).write(line)

    def _set_banner(self, text: str) -> None:
        self.query_one("#banner", Static).update(text)

    def refresh_status_view(self) -> None:
        self.controller.refresh_status()
        self.query_one("#status-panel", Static).update("\n".join(self.controller.status_lines()))
        self._set_banner(self.controller.banner)

    def _refresh_bridge_log(self) -> None:
        if self._action_running or not BRIDGE_LOG_PATH.exists():
            return
        with BRIDGE_LOG_PATH.open("r", encoding="utf-8", errors="replace") as handle:
            handle.seek(self._log_offset)
            chunk = handle.read()
            self._log_offset = handle.tell()
        for line in chunk.splitlines():
            self._append_log(line)

    def _thread_log(self, line: str) -> None:
        self.call_from_thread(self._append_log, line)

    @work(thread=True, exclusive=True)
    def _run_action(self, action_name: str, func, *args) -> None:
        self._action_running = True
        try:
            func(*args, on_line=self._thread_log)
        except Exception as exc:
            self.call_from_thread(self._set_banner, f"{action_name} failed: {exc}")
            self.call_from_thread(self._append_log, f"{action_name} failed: {exc}")
        else:
            self.call_from_thread(self._set_banner, self.controller.banner)
        finally:
            self._action_running = False
            self.call_from_thread(self.refresh_status_view)

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "start-bridge":
            self._run_action("Start Bridge", self.controller.start_bridge)
        elif button_id == "stop-bridge":
            self._run_action("Stop Bridge", self.controller.stop_bridge)
        elif button_id == "restart-bridge":
            self._run_action("Restart Bridge", self.controller.restart_bridge)
        elif button_id == "health-check":
            self._run_action("Health Check", self.controller.health_check)
        elif button_id == "build-firmware":
            self._run_action("Build Firmware", self.controller.build_firmware)
        elif button_id == "refresh-status":
            self.refresh_status_view()
        elif button_id == "select-model":
            self._open_model_selector()
        elif button_id == "system-prompt":
            self._open_system_prompt()
        elif button_id == "runtime-settings":
            self._open_runtime_settings()
        elif button_id == "flash-firmware":
            self._open_flash_confirm()

    def _open_model_selector(self) -> None:
        try:
            models = self.controller.list_models()
        except Exception as exc:
            self._set_banner(f"Select Model failed: {exc}")
            self._append_log(f"Select Model failed: {exc}")
            return

        def apply_choice(choice: str | None) -> None:
            if not choice:
                return
            self.controller.save_model_selection(choice)
            self._set_banner(f"Saved model: {choice}. Restart bridge to apply.")
            self.refresh_status_view()

        self.push_screen(SelectOptionScreen("Select LM Studio Model", models), apply_choice)

    def _open_runtime_settings(self) -> None:
        values = self.controller.managed_env()

        def apply_settings(result: dict[str, str] | None) -> None:
            if not result:
                return
            self.controller.save_runtime_settings(result)
            self._set_banner("Saved runtime settings. Restart bridge to apply.")
            self.refresh_status_view()

        self.push_screen(RuntimeSettingsScreen(values), apply_settings)

    def _open_system_prompt(self) -> None:
        values = self.controller.managed_env()
        prompt_text = values.get("XIAOZHI_BRIDGE_SYSTEM_PROMPT", "")

        def apply_prompt(result: str | None) -> None:
            if not result:
                return
            self.controller.save_runtime_settings({"XIAOZHI_BRIDGE_SYSTEM_PROMPT": result})
            self._set_banner("Saved system prompt. Restart bridge to apply.")
            self.refresh_status_view()

        self.push_screen(SystemPromptScreen(prompt_text), apply_prompt)

    def _open_flash_confirm(self) -> None:
        plan = self.controller.prepare_flash_plan()
        ports = [port.device for port in plan.ports]
        if not ports:
            self._set_banner("No serial ports detected")
            self._append_log("No serial ports detected")
            return

        def do_flash(choice: str | None) -> None:
            if not choice:
                return
            self._run_action("Flash Firmware", self.controller.flash_firmware, choice)

        self.push_screen(FlashConfirmScreen(ports, plan.artifact_summary), do_flash)

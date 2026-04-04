# Xiaozhi Control TUI

Terminal UI to manage the current locked Xiaozhi baseline only:

- bridge server start, stop, restart
- LM Studio health and model selection
- system prompt editing
- persistent runtime overrides in `.env.local`
- firmware build
- firmware flash with explicit COM-port confirmation
- live bridge log tailing

Managed baseline:

- In packaged mode, this TUI manages the snapshot folder that contains it.
- In workspace mode, it falls back to the original snapshot paths on the current machine.

## Run

From PowerShell:

```powershell
cd C:\QuanNewData\xiaozhi\xiaozhi-control-tui
.\run-xiaozhi-control-tui.ps1
```

Or from `cmd.exe`:

```cmd
cd C:\QuanNewData\xiaozhi\xiaozhi-control-tui
run-xiaozhi-control-tui.cmd
```

The launcher creates a local `.venv` for the TUI if needed and installs:

- `textual`
- `httpx`
- `pyserial`

## Layout

The app has 3 persistent panels:

- `Status`
- `Logs`
- `Actions`

There is no always-visible config panel. Model selection, runtime settings, and flash confirmation use modal dialogs.

## Runtime overrides

The TUI persists bridge runtime overrides to:

- `.\bridge-server\.env.local` when run from the packaged snapshot
- the original snapshot path when run from the standalone workspace copy

Managed keys in v1:

- `XIAOZHI_BRIDGE_MODEL_NAME`
- `XIAOZHI_BRIDGE_LM_STUDIO_URL`
- `XIAOZHI_BRIDGE_SYSTEM_PROMPT`
- `XIAOZHI_BRIDGE_TTS_VOICE`
- `XIAOZHI_BRIDGE_ASR_MODEL`
- `XIAOZHI_BRIDGE_ASR_DEVICE`
- `XIAOZHI_BRIDGE_ASR_COMPUTE_TYPE`

The TUI does not edit `config.py`.

## System prompt

Use the `System Prompt` action in the TUI to edit the bridge assistant prompt in a dedicated modal editor. The value is saved into `.env.local` and applied after a bridge restart.

## Bridge runtime note

The final snapshot does not currently ship with its own bridge `.venv`. The TUI resolves bridge Python in this order:

1. `XIAOZHI_BRIDGE_PYTHON`
2. snapshot `.venv\Scripts\python.exe`
3. the known working bridge runtime from the original bridge worktree

This makes the TUI usable immediately on the current machine without copying the whole bridge virtual environment into the final snapshot.

## Flash behavior

`Flash Firmware` never runs immediately. The flow is:

1. scan serial ports
2. choose a COM port
3. confirm flash target
4. run the existing bridge-touch-WeChat flash script

This tool manages only the current bridge-based baseline. It does not manage the older `xiaozhi-esp32-server` stack and does not support multiple profiles yet.

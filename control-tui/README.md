# Xiaozhi Control TUI

Terminal UI to manage the current locked Xiaozhi baseline only:

- bridge server start, stop, restart
- LM Studio health and model selection
- system prompt editing
- persistent runtime overrides in `.env.local`
- current laptop LAN IP guidance for the device Wi-Fi portal
- firmware build
- firmware flash with explicit COM-port confirmation
- live bridge log tailing

Managed baseline:

- In packaged mode, this TUI manages the snapshot folder that contains it.
- In workspace mode, it falls back to the original snapshot paths on the current machine.

## Run

From PowerShell:

```powershell
cd C:\QuanNewData\xiaozhi\stable-custom-server-20260405-final-v1-wechat\control-tui
.\run-xiaozhi-control-tui.ps1
```

Or from `cmd.exe`:

```cmd
cd C:\QuanNewData\xiaozhi\stable-custom-server-20260405-final-v1-wechat\control-tui
run-xiaozhi-control-tui.cmd
```

The launcher creates a local `.venv` for the TUI if needed and installs:

- `textual`
- `httpx`
- `pyserial`

On first `Start Bridge`, the TUI also bootstraps `bridge-server\.venv` automatically if it is missing.

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

## Connection mode

This `v1` baseline does not use discovery. The TUI shows:

- `Connection mode: Manual IP (v1)`
- `Laptop IP: ...`

Use that IP in the device Wi-Fi portal together with the target `SSID` and `password`. The firmware stores:

- `bridge_lan.server_ip`
- `websocket.url = ws://<server_ip>:8000/xiaozhi/v1/`
- `websocket.version = 1`

## Before starting a conversation

1. Open `LM Studio`.
2. Load the configured chat model, usually `qwen3-1.7b`.
3. Confirm local server is available on `http://localhost:1234`.
4. In the TUI, press `Start Bridge`.

If the bridge reaches ASR but `LM Studio` has no loaded model, the chat request can fail with `HTTP 400 Bad Request`.

## System prompt

Use the `System Prompt` action in the TUI to edit the bridge assistant prompt in a dedicated modal editor. The value is saved into `.env.local` and applied after a bridge restart.

## Bridge runtime note

The final snapshot can bootstrap its own bridge `.venv` on demand. The TUI resolves bridge Python in this order:

1. `XIAOZHI_BRIDGE_PYTHON`
2. snapshot `.venv\Scripts\python.exe`
3. create snapshot `.venv` automatically on first bridge start

## Flash behavior

`Flash Firmware` never runs immediately. The flow is:

1. scan serial ports
2. choose a COM port
3. confirm flash target
4. run the existing bridge-touch-WeChat flash script

This tool manages only the current bridge-based baseline. It does not manage the older `xiaozhi-esp32-server` stack and does not support multiple profiles yet.

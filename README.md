## Final Stable Snapshot V1 Manual IP

This folder is the packaged baseline of the custom Xiaozhi setup as of `2026-04-05`.

### Locked Baseline

- Firmware UI: WeChat message style
- Firmware transport: bridge mode over WebSocket with manual laptop IP provisioning
- Firmware extras:
  - touch enabled
  - landscape UI
  - left-zone volume gesture
  - middle-zone history scroll
  - right-zone brightness gesture
- Bridge runtime:
  - ASR: `faster-whisper large-v3`
  - ASR device: `cpu`
  - ASR compute type: `int8`
  - LLM: `LM Studio`
  - TTS: streamed `Edge-TTS`
- Connection model:
  - device Wi-Fi portal stores `SSID`, `password`, and `server_ip`
  - firmware writes `ws://<server_ip>:8000/xiaozhi/v1/` into NVS
  - no mDNS or UDP discovery in the default runtime path

### Contents

- `bridge-server`
  - Source snapshot of the active bridge runtime baseline
  - Includes:
    - Mono prompt support
    - overlap guard
    - streaming TTS path
    - GPU `large-v3` runtime fix
    - manual-IP `.env.local`
- `control-tui`
  - Textual TUI for:
    - start/stop/restart bridge
    - health check
    - model and prompt management
    - firmware build
    - firmware flash
    - showing the current laptop LAN IP for the device portal
- `firmware-src`
  - Source snapshot of the active firmware clone
  - Includes:
    - bridge mode
    - manual-IP Wi-Fi portal field
    - WeChat UI
    - landscape orientation
    - touch gesture zones
- `firmware-artifacts`
  - Ready-to-flash binaries and scripts copied from the current build

### Restore Procedure

1. Start `LM Studio`.
2. In `LM Studio`, load the chat model configured in `.env.local`:
   - default: `qwen3-1.7b`
3. Start the operator TUI from:
   - `C:\QuanNewData\xiaozhi\stable-custom-server-20260405-final-v1-wechat\control-tui`
4. Recommended launcher:
   - `run-xiaozhi-control-tui.ps1`
5. In the TUI:
   - start the bridge
   - read the `Laptop IP` shown in the status panel
   - open the device Wi-Fi portal and enter `SSID`, `password`, and that `Laptop IP`
   - flash firmware if needed

### Daily Operator Checklist

1. Open `LM Studio`.
2. Confirm the target model is loaded and local server is enabled on `http://localhost:1234`.
3. Open `control-tui` and press `Start Bridge`.
4. Confirm in `Status`:
   - `Bridge: UP`
   - `LM Studio: UP`
   - `Connection mode: Manual IP (v1)`
   - `Laptop IP: ...`
5. On the device portal, enter:
   - `SSID`
   - `password`
   - `Laptop IP`
6. Test with a short phrase such as `Xin chào`.

### First-Run Notes

- `control-tui` creates its own `.venv` automatically on first run.
- `Start Bridge` also bootstraps `bridge-server\.venv` automatically if it is missing.
- The first bridge start can take noticeably longer because Python dependencies are installed on demand.
- `Edge-TTS` requires Internet access.
- If `LM Studio` server is running but the chat model is not loaded, the bridge can connect but replies will fail with `HTTP 400 Bad Request`.

### Notes

- This snapshot is source + artifact focused.
- Python virtual environments may be created automatically on first use.
- This is a rebuilt `v1` rollback from the `v2` codebase, not a byte-identical restore of the original lost snapshot.

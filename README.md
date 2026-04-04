## Final Stable Snapshot V2

This folder is the packaged baseline of the custom Xiaozhi setup as of `2026-04-05`.

### Locked Baseline

- Firmware UI: WeChat message style
- Firmware transport: bridge mode over WebSocket with multi-layer server discovery
- Firmware extras:
  - touch enabled
  - landscape UI
  - left-zone volume gesture
  - middle-zone history scroll
  - right-zone brightness gesture
- Bridge runtime:
  - ASR: `faster-whisper large-v3`
  - ASR device: `cuda`
  - ASR compute type: `float16`
  - LLM: `LM Studio`
  - TTS: streamed `Edge-TTS`
- Discovery runtime:
  - mDNS hostname: `xiaozhi-bridge.local`
  - UDP discovery port: `24681`
  - stable server identity persisted in `.env.local`

### Contents

- `bridge-server`
  - Source snapshot of the active bridge runtime baseline
  - Includes:
    - Mono prompt support
    - overlap guard
    - streaming TTS path
    - GPU `large-v3` runtime fix
    - hello response server identity fields
    - discovery-managed `.env.local`
- `control-tui`
  - Textual TUI for:
    - start/stop/restart bridge
    - health check
    - model and prompt management
    - firmware build
    - firmware flash
    - discovery responder lifecycle
- `firmware-src`
  - Source snapshot of the active firmware clone
  - Includes:
    - bridge mode
    - multi-layer server discovery
    - WeChat UI
    - landscape orientation
    - touch gesture zones
- `firmware-artifacts`
  - Ready-to-flash binaries and scripts copied from the current build

### Restore Procedure

1. Start `LM Studio` and load the chat model you want to use.
2. Start the operator TUI from:
   - `C:\QuanNewData\xiaozhi\stable-custom-server-20260405-final-v2-wechat\control-tui`
3. Recommended launcher:
   - `run-xiaozhi-control-tui.ps1`
4. In the TUI:
   - start the bridge
   - confirm LM Studio is reachable
   - flash firmware if needed

### Notes

- This snapshot is source + artifact focused.
- Python virtual environments were not copied into this folder.
- Discovery is on-demand: the board resolves the bridge when starting a turn.
- The older snapshot remains separate at:
  - `C:\QuanNewData\xiaozhi\stable-custom-server-20260404-final-largev3-wechat`

Antigravityのテストで生成した**小智ESP32**デバイスと**LM Studio**を接続するためのPython製WebSocketサーバーです。

## コンポーネント
- **Server**: `xiaozhi_bridge/server.py` (WebSocketサーバー)
- **Protocol**: `xiaozhi_bridge/protocol.py` (小智 v3プロトコルの処理)
- **Audio**: `xiaozhi_bridge/audio_utils.py` (Opus <-> PCM変換)
- **ASR**: Faster-Whisper (ローカル音声認識)
- **TTS**: Edge-TTS (オンライン音声合成)
- **LLM**: LM Studio (ローカルOpenAI互換API)

## セットアップ
1.  **依存関係のインストール**:
    ```bash
    ./run.sh
    ```
    (または手動で: `pip install -r requirements.txt`)

2.  **LM Studioの起動**:
    - モデルをロードしてください。OpenAI互換APIをアクティブにしてください。
    - ポート`1234`でローカルサーバーを開始してください。サーバー側でポート （8000） の受信（TCP）を許可してください。

3.  **ブリッジサーバーの実行**:
    ```bash
    ./run.sh
    ```

4.  **デバイスの設定**:
    小智ESP32をこのサーバーに向けるには、ビルド/書き込みの前にファームウェアのソースコードを変更する必要があります。
    
    `xiaozhi-esp32/main/protocols/websocket_protocol.cc` を開き、`OpenAudioChannel` メソッド（85行目付近）を修正してください：

    ```cpp
    bool WebsocketProtocol::OpenAudioChannel() {
        Settings settings("websocket", false);
        // 元のコード: std::string url = settings.GetString("url");
        
        // コンピュータのIPアドレスに向けるように修正:
        std::string url = "ws://192.168.1.100:8000"; 
        
        std::string token = settings.GetString("token");
        // ...
    }
    ```
    *`192.168.1.100` の部分は、実際のLAN IPアドレスに置き換えてください。*

    また、`xiaozhi-esp32/main/application.cc` 480行目付近を開き、`

   ```cpp

   // 変更前
   
    if (ota_->HasMqttConfig()) {
        protocol_ = std::make_unique<MqttProtocol>();
    } else if (ota_->HasWebsocketConfig()) {
        protocol_ = std::make_unique<WebsocketProtocol>();
    } else {
        ESP_LOGW(TAG, "No protocol specified in the OTA config, using MQTT");
        protocol_ = std::make_unique<MqttProtocol>();
    }

   // 変更後
   
   // Force WebSocket protocol for local server connection
   ESP_LOGI(TAG, "Using WebSocket protocol (forced)");
   protocol_ = std::make_unique<WebsocketProtocol>();
   ```    
   
   に変更してください。
   この変更により、デバイス起動時に必ず WebSocket モードで動作し、
   指定されたローカル IP アドレス（172.20.10.5 など）のサーバーを探しに行くようになっています。
   
   その後、ファームウェアを再ビルドして（https://github.com/dinosauria123/Xiaozhi-ESP32-Bridge-Server/blob/main/merged-binary.bin
   ）書き込んでください：
   ```bash    
    esptool --chip esp32s3 write_flash 0x0 merged-binary.bin
   ```
改造した小智ESP32のソースコードは
https://github.com/dinosauria123/xiaozhi-esp32-local
にあります。


## 検証
- `python test_client.py` を実行して、サーバーへの到達性とプロトコルの動作を確認できます。

## 検証結果
`test_client.py` を実行して、サーバーの実装を検証しました。

**サーバーログ:**
```
New connection from ('127.0.0.1', 50976)
Received JSON: {'type': 'hello', ...}
Sent Hello response
```
**クライアントログ:**
```
Connected!
Sent Hello
Received: {"type": "hello", ...}
Handshake successful!
```

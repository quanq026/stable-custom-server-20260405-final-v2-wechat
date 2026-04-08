#include "websocket_protocol.h"
#include "bridge_discovery.h"
#include "device_identity.h"
#include "discovered_server_cache.h"
#include "json_frame_utils.h"
#include "board.h"
#include "system_info.h"
#include "application.h"
#include "settings.h"

#include <cstring>
#include <cJSON.h>
#include <esp_log.h>
#include <arpa/inet.h>
#include "assets/lang_config.h"

#define TAG "WS"

WebsocketProtocol::WebsocketProtocol() {
    event_group_handle_ = xEventGroupCreate();
}

WebsocketProtocol::~WebsocketProtocol() {
    vEventGroupDelete(event_group_handle_);
}

bool WebsocketProtocol::Start() {
    // Only connect to server when audio channel is needed
    return true;
}

bool WebsocketProtocol::SendAudio(std::unique_ptr<AudioStreamPacket> packet) {
    if (websocket_ == nullptr || !websocket_->IsConnected()) {
        return false;
    }

    if (version_ == 2) {
        std::string serialized;
        serialized.resize(sizeof(BinaryProtocol2) + packet->payload.size());
        auto bp2 = (BinaryProtocol2*)serialized.data();
        bp2->version = htons(version_);
        bp2->type = 0;
        bp2->reserved = 0;
        bp2->timestamp = htonl(packet->timestamp);
        bp2->payload_size = htonl(packet->payload.size());
        memcpy(bp2->payload, packet->payload.data(), packet->payload.size());

        return websocket_->Send(serialized.data(), serialized.size(), true);
    } else if (version_ == 3) {
        std::string serialized;
        serialized.resize(sizeof(BinaryProtocol3) + packet->payload.size());
        auto bp3 = (BinaryProtocol3*)serialized.data();
        bp3->type = 0;
        bp3->reserved = 0;
        bp3->payload_size = htons(packet->payload.size());
        memcpy(bp3->payload, packet->payload.data(), packet->payload.size());

        return websocket_->Send(serialized.data(), serialized.size(), true);
    } else {
        return websocket_->Send(packet->payload.data(), packet->payload.size(), true);
    }
}

bool WebsocketProtocol::SendText(const std::string& text) {
    if (websocket_ == nullptr || !websocket_->IsConnected()) {
        return false;
    }

    if (!websocket_->Send(text)) {
        ESP_LOGE(TAG, "Failed to send text: %s", text.c_str());
        SetError(Lang::Strings::SERVER_ERROR);
        return false;
    }

    return true;
}

bool WebsocketProtocol::IsAudioChannelOpened() const {
    return websocket_ != nullptr && websocket_->IsConnected() && !error_occurred_ && !IsTimeout();
}

void WebsocketProtocol::CloseAudioChannel() {
    websocket_.reset();
}

bool WebsocketProtocol::OpenAudioChannel() {
    Settings settings("websocket", false);
    pending_discovered_server_cache_.reset();
    connected_ws_url_.clear();
    connected_server_id_.clear();
    connected_server_name_.clear();
    std::string url = settings.GetString("url");
    std::string token = settings.GetString("token");
    version_ = settings.GetInt("version", 1);
    if (version_ <= 0) {
        version_ = 1;
    }
#if CONFIG_BRIDGE_MODE_ENABLE
#if CONFIG_BRIDGE_DISCOVERY_ENABLE
    BridgeDiscoveryManager discovery_manager;
    BridgeDiscoveryResult discovery_result;
#endif
    bool discovery_used = false;
#if CONFIG_BRIDGE_DISCOVERY_ENABLE
    if (url.empty() && discovery_manager.Resolve(discovery_result)) {
        discovery_used = true;
        url = discovery_result.ws_url;
        connected_server_id_ = discovery_result.server_id;
        connected_server_name_ = discovery_result.server_name;
    }
#endif
    if (url.empty()) {
        url = CONFIG_BRIDGE_WEBSOCKET_URL;
    }
    if (url.empty()) {
        ESP_LOGE(TAG, "Missing websocket.url in settings and no bridge fallback is configured");
        SetError(Lang::Strings::SERVER_NOT_CONNECTED);
        return false;
    }
    pending_discovered_server_cache_ = PrepareDiscoveredServerCache(
        discovery_used,
        url,
        connected_server_id_,
        connected_server_name_
    );
#endif

    error_occurred_ = false;
    connected_ws_url_ = url;

    auto network = Board::GetInstance().GetNetwork();
    websocket_ = network->CreateWebSocket(1);
    if (websocket_ == nullptr) {
        ESP_LOGE(TAG, "Failed to create websocket");
        return false;
    }

    if (!token.empty()) {
        // If token not has a space, add "Bearer " prefix
        if (token.find(" ") == std::string::npos) {
            token = "Bearer " + token;
        }
    websocket_->SetHeader("Authorization", token.c_str());
    }
    websocket_->SetHeader("Protocol-Version", std::to_string(version_).c_str());
    const std::string device_id = BuildStableDeviceId(SystemInfo::GetMacAddress());
    websocket_->SetHeader("Device-Id", device_id.c_str());
    websocket_->SetHeader("Client-Id", Board::GetInstance().GetUuid().c_str());

    websocket_->OnData([this](const char* data, size_t len, bool binary) {
        if (binary) {
            if (on_incoming_audio_ != nullptr) {
                if (version_ == 2) {
                    BinaryProtocol2* bp2 = (BinaryProtocol2*)data;
                    bp2->version = ntohs(bp2->version);
                    bp2->type = ntohs(bp2->type);
                    bp2->timestamp = ntohl(bp2->timestamp);
                    bp2->payload_size = ntohl(bp2->payload_size);
                    auto payload = (uint8_t*)bp2->payload;
                    on_incoming_audio_(std::make_unique<AudioStreamPacket>(AudioStreamPacket{
                        .sample_rate = server_sample_rate_,
                        .frame_duration = server_frame_duration_,
                        .timestamp = bp2->timestamp,
                        .payload = std::vector<uint8_t>(payload, payload + bp2->payload_size)
                    }));
                } else if (version_ == 3) {
                    BinaryProtocol3* bp3 = (BinaryProtocol3*)data;
                    bp3->type = bp3->type;
                    bp3->payload_size = ntohs(bp3->payload_size);
                    auto payload = (uint8_t*)bp3->payload;
                    on_incoming_audio_(std::make_unique<AudioStreamPacket>(AudioStreamPacket{
                        .sample_rate = server_sample_rate_,
                        .frame_duration = server_frame_duration_,
                        .timestamp = 0,
                        .payload = std::vector<uint8_t>(payload, payload + bp3->payload_size)
                    }));
                } else {
                    on_incoming_audio_(std::make_unique<AudioStreamPacket>(AudioStreamPacket{
                        .sample_rate = server_sample_rate_,
                        .frame_duration = server_frame_duration_,
                        .timestamp = 0,
                        .payload = std::vector<uint8_t>((uint8_t*)data, (uint8_t*)data + len)
                    }));
                }
            }
        } else {
            // Parse JSON data
            std::string json_text = CopyJsonFrameText(data, len);
            auto root = cJSON_Parse(json_text.c_str());
            if (root == nullptr) {
                ESP_LOGE(TAG, "Failed to parse websocket JSON payload len=%u", static_cast<unsigned>(len));
                return;
            }
            auto type = cJSON_GetObjectItem(root, "type");
            if (cJSON_IsString(type)) {
                if (strcmp(type->valuestring, "hello") == 0) {
                    ParseServerHello(root);
                } else {
                    if (on_incoming_json_ != nullptr) {
                        on_incoming_json_(root);
                    }
                }
            } else {
                ESP_LOGE(TAG, "Missing message type, data len=%u", static_cast<unsigned>(len));
            }
            cJSON_Delete(root);
        }
        last_incoming_time_ = std::chrono::steady_clock::now();
    });

    websocket_->OnDisconnected([this]() {
        ESP_LOGI(TAG, "Websocket disconnected");
        if (on_audio_channel_closed_ != nullptr) {
            on_audio_channel_closed_();
        }
    });

    ESP_LOGI(TAG, "Connecting to websocket server: %s with version: %d", url.c_str(), version_);
    bool connected = websocket_->Connect(url.c_str());
#if CONFIG_BRIDGE_MODE_ENABLE && CONFIG_BRIDGE_DISCOVERY_ENABLE
    if (!connected && discovery_result.from_mdns && discovery_manager.ResolveUdpFallback(discovery_result)) {
            ESP_LOGW(TAG, "mDNS candidate connect failed, retrying with UDP-discovered ws_url=%s", discovery_result.ws_url.c_str());
            connected_ws_url_ = discovery_result.ws_url;
            connected_server_id_ = discovery_result.server_id;
            connected_server_name_ = discovery_result.server_name;
            connected = websocket_->Connect(discovery_result.ws_url.c_str());
        }
#endif
    if (!connected) {
        ESP_LOGE(TAG, "Failed to connect to websocket server, code=%d", websocket_->GetLastError());
        SetError(Lang::Strings::SERVER_NOT_CONNECTED);
        return false;
    }

    // Send hello message to describe the client
    auto message = GetHelloMessage();
    if (!SendText(message)) {
        return false;
    }

    // Wait for server hello
    EventBits_t bits = xEventGroupWaitBits(event_group_handle_, WEBSOCKET_PROTOCOL_SERVER_HELLO_EVENT, pdTRUE, pdFALSE, pdMS_TO_TICKS(10000));
    if (!(bits & WEBSOCKET_PROTOCOL_SERVER_HELLO_EVENT)) {
        ESP_LOGE(TAG, "Failed to receive server hello");
        SetError(Lang::Strings::SERVER_TIMEOUT);
        return false;
    }

    if (pending_discovered_server_cache_.has_value()) {
        pending_discovered_server_cache_->ws_url = connected_ws_url_;
        pending_discovered_server_cache_->server_id = connected_server_id_;
        pending_discovered_server_cache_->server_name = connected_server_name_;
        CacheDiscoveredServer(*pending_discovered_server_cache_);
        pending_discovered_server_cache_.reset();
    }

    if (on_audio_channel_opened_ != nullptr) {
        on_audio_channel_opened_();
    }

    return true;
}

std::string WebsocketProtocol::GetHelloMessage() {
    // keys: message type, version, audio_params (format, sample_rate, channels)
    cJSON* root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "type", "hello");
    cJSON_AddNumberToObject(root, "version", version_);
    cJSON* features = cJSON_CreateObject();
#if CONFIG_USE_SERVER_AEC
    cJSON_AddBoolToObject(features, "aec", true);
#endif
    cJSON_AddBoolToObject(features, "mcp", true);
    cJSON_AddItemToObject(root, "features", features);
    cJSON_AddStringToObject(root, "transport", "websocket");
    cJSON* audio_params = cJSON_CreateObject();
    cJSON_AddStringToObject(audio_params, "format", "opus");
    cJSON_AddNumberToObject(audio_params, "sample_rate", 16000);
    cJSON_AddNumberToObject(audio_params, "channels", 1);
    cJSON_AddNumberToObject(audio_params, "frame_duration", OPUS_FRAME_DURATION_MS);
    cJSON_AddItemToObject(root, "audio_params", audio_params);
    cJSON_AddStringToObject(root, "device_id", BuildStableDeviceId(SystemInfo::GetMacAddress()).c_str());
    auto json_str = cJSON_PrintUnformatted(root);
    std::string message(json_str);
    cJSON_free(json_str);
    cJSON_Delete(root);
    return message;
}

void WebsocketProtocol::ParseServerHello(const cJSON* root) {
    auto transport = cJSON_GetObjectItem(root, "transport");
    if (transport == nullptr || strcmp(transport->valuestring, "websocket") != 0) {
        ESP_LOGE(TAG, "Unsupported transport: %s", transport->valuestring);
        return;
    }

    auto session_id = cJSON_GetObjectItem(root, "session_id");
    if (cJSON_IsString(session_id)) {
        session_id_ = session_id->valuestring;
        ESP_LOGI(TAG, "Session ID: %s", session_id_.c_str());
    }

    auto server_id = cJSON_GetObjectItem(root, "server_id");
    if (cJSON_IsString(server_id)) {
        connected_server_id_ = server_id->valuestring;
    }

    auto server_name = cJSON_GetObjectItem(root, "server_name");
    if (cJSON_IsString(server_name)) {
        connected_server_name_ = server_name->valuestring;
    }

    auto audio_params = cJSON_GetObjectItem(root, "audio_params");
    if (cJSON_IsObject(audio_params)) {
        auto sample_rate = cJSON_GetObjectItem(audio_params, "sample_rate");
        if (cJSON_IsNumber(sample_rate)) {
            server_sample_rate_ = sample_rate->valueint;
        }
        auto frame_duration = cJSON_GetObjectItem(audio_params, "frame_duration");
        if (cJSON_IsNumber(frame_duration)) {
            server_frame_duration_ = frame_duration->valueint;
        }
    }

    ESP_LOGI(
        TAG,
        "Parsed server hello session_id=%s server_id=%s server_name=%s sample_rate=%d frame_duration=%d",
        session_id_.c_str(),
        connected_server_id_.c_str(),
        connected_server_name_.c_str(),
        server_sample_rate_,
        server_frame_duration_
    );

    xEventGroupSetBits(event_group_handle_, WEBSOCKET_PROTOCOL_SERVER_HELLO_EVENT);
}

void WebsocketProtocol::CacheDiscoveredServer(const DiscoveredServerCacheEntry& entry) {
    if (entry.ws_url.empty()) {
        return;
    }

    Settings settings("bridge_discovery", true);
    if (!entry.server_id.empty()) {
        settings.SetString("server_id", entry.server_id);
    }
    if (!entry.server_name.empty()) {
        settings.SetString("server_name", entry.server_name);
    }
    settings.SetString("ws_url", entry.ws_url);
}

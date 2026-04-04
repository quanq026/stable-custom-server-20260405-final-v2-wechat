#include "bridge_discovery.h"

#include "board.h"
#include "settings.h"

#include <cJSON.h>
#include <esp_log.h>
#include <lwip/netdb.h>
#include <lwip/sockets.h>
#include <sys/select.h>

#define TAG "BridgeDiscovery"

namespace {

constexpr int kDiscoveryReceiveTimeoutMs = 400;
constexpr int kDiscoveryAttempts = 2;

}  // namespace

bool BridgeDiscoveryManager::Resolve(BridgeDiscoveryResult& out_result) {
#if CONFIG_BRIDGE_DISCOVERY_ENABLE
    const std::string preferred_server_id = LoadPreferredServerId();
    if (TryResolveMdns(out_result)) {
        if (!preferred_server_id.empty()) {
            std::vector<BridgeDiscoveryCandidate> candidates;
            if (QueryUdpCandidates(candidates)) {
                auto selected = SelectBridgeDiscoveryCandidate(candidates, preferred_server_id);
                if (selected.has_value() && selected->server_id == preferred_server_id) {
                    out_result.ws_url = selected->ws_url;
                    out_result.server_id = selected->server_id;
                    out_result.server_name = selected->server_name;
                    out_result.from_mdns = false;
                    ESP_LOGI(TAG, "Preferred server matched via UDP discovery server_id=%s url=%s", out_result.server_id.c_str(), out_result.ws_url.c_str());
                }
            }
        }
        return true;
    }
    return ResolveUdpFallback(out_result);
#else
    (void)out_result;
    return false;
#endif
}

bool BridgeDiscoveryManager::ResolveUdpFallback(BridgeDiscoveryResult& out_result) {
    std::vector<BridgeDiscoveryCandidate> candidates;
    if (!QueryUdpCandidates(candidates)) {
        return false;
    }

    auto selected = SelectBridgeDiscoveryCandidate(candidates, LoadPreferredServerId());
    if (!selected.has_value()) {
        return false;
    }

    out_result.ws_url = selected->ws_url;
    out_result.server_id = selected->server_id;
    out_result.server_name = selected->server_name;
    out_result.from_mdns = false;
    ESP_LOGI(TAG, "Selected UDP discovery candidate server_id=%s url=%s", out_result.server_id.c_str(), out_result.ws_url.c_str());
    return true;
}

std::string BridgeDiscoveryManager::LoadPreferredServerId() const {
    Settings settings("bridge_discovery", false);
    return settings.GetString("server_id");
}

bool BridgeDiscoveryManager::TryResolveMdns(BridgeDiscoveryResult& out_result) {
    std::string host_label = NormalizeHostLabel(CONFIG_BRIDGE_DISCOVERY_HOST);
    addrinfo hints = {};
    hints.ai_family = AF_INET;
    addrinfo* result = nullptr;
    int ret = getaddrinfo(host_label.c_str(), nullptr, &hints, &result);
    if (ret != 0 || result == nullptr) {
        ESP_LOGW(TAG, "mDNS lookup failed for %s: %d", host_label.c_str(), ret);
        if (result != nullptr) {
            freeaddrinfo(result);
        }
        return false;
    }

    freeaddrinfo(result);
    out_result.ws_url = BuildWebsocketUrl(host_label);
    out_result.server_name = CONFIG_BRIDGE_DISCOVERY_HOST;
    out_result.from_mdns = true;
    ESP_LOGI(TAG, "mDNS resolved %s -> %s", host_label.c_str(), out_result.ws_url.c_str());
    return true;
}

bool BridgeDiscoveryManager::QueryUdpCandidates(std::vector<BridgeDiscoveryCandidate>& candidates) {
    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
    if (sock < 0) {
        ESP_LOGE(TAG, "Failed to create UDP discovery socket");
        return false;
    }

    int broadcast = 1;
    setsockopt(sock, SOL_SOCKET, SO_BROADCAST, &broadcast, sizeof(broadcast));

    timeval timeout = {};
    timeout.tv_sec = 0;
    timeout.tv_usec = kDiscoveryReceiveTimeoutMs * 1000;
    setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout));

    sockaddr_in dest = {};
    dest.sin_family = AF_INET;
    dest.sin_port = htons(CONFIG_BRIDGE_DISCOVERY_PORT);
    dest.sin_addr.s_addr = INADDR_BROADCAST;

    cJSON* request = cJSON_CreateObject();
    cJSON_AddStringToObject(request, "type", "xiaozhi-discovery");
    cJSON_AddNumberToObject(request, "version", 1);
    cJSON_AddStringToObject(request, "client_id", Board::GetInstance().GetUuid().c_str());
    char* request_text = cJSON_PrintUnformatted(request);
    std::string payload = request_text ? request_text : "";
    cJSON_free(request_text);
    cJSON_Delete(request);

    char recv_buffer[768];
    for (int attempt = 0; attempt < kDiscoveryAttempts; ++attempt) {
        sendto(sock, payload.data(), payload.size(), 0, reinterpret_cast<sockaddr*>(&dest), sizeof(dest));

        while (true) {
            sockaddr_in source = {};
            socklen_t source_len = sizeof(source);
            int received = recvfrom(sock, recv_buffer, sizeof(recv_buffer) - 1, 0, reinterpret_cast<sockaddr*>(&source), &source_len);
            if (received <= 0) {
                break;
            }

            recv_buffer[received] = '\0';
            BridgeDiscoveryCandidate candidate;
            if (ParseUdpCandidate(recv_buffer, candidate)) {
                candidates.push_back(candidate);
            }
        }
    }

    close(sock);
    return !candidates.empty();
}

bool BridgeDiscoveryManager::ParseUdpCandidate(const char* payload, BridgeDiscoveryCandidate& candidate) {
    cJSON* root = cJSON_Parse(payload);
    if (root == nullptr) {
        return false;
    }

    auto cleanup = [&root]() {
        cJSON_Delete(root);
    };

    cJSON* type = cJSON_GetObjectItem(root, "type");
    cJSON* version = cJSON_GetObjectItem(root, "version");
    cJSON* server_id = cJSON_GetObjectItem(root, "server_id");
    cJSON* server_name = cJSON_GetObjectItem(root, "server_name");
    cJSON* ws_url = cJSON_GetObjectItem(root, "ws_url");
    if (!cJSON_IsString(type) || strcmp(type->valuestring, "xiaozhi-discovery-response") != 0 ||
        !cJSON_IsNumber(version) || version->valueint != 1 ||
        !cJSON_IsString(server_id) || !cJSON_IsString(server_name) || !cJSON_IsString(ws_url)) {
        cleanup();
        return false;
    }

    candidate.server_id = server_id->valuestring;
    candidate.server_name = server_name->valuestring;
    candidate.ws_url = ws_url->valuestring;
    cleanup();
    return !candidate.server_id.empty() && !candidate.ws_url.empty();
}

std::string BridgeDiscoveryManager::NormalizeHostLabel(const std::string& host) {
    if (host.size() >= 6 && host.compare(host.size() - 6, 6, ".local") == 0) {
        return host;
    }
    return host + ".local";
}

std::string BridgeDiscoveryManager::BuildWebsocketUrl(const std::string& host_or_ip) {
    std::string path = CONFIG_BRIDGE_WEBSOCKET_PATH;
    if (path.empty() || path.front() != '/') {
        path = "/" + path;
    }
    return "ws://" + host_or_ip + ":" + std::to_string(CONFIG_BRIDGE_WEBSOCKET_PORT) + path;
}

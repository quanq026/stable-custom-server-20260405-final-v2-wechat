#include "manual_bridge_config.h"

#include <cctype>
#include <sstream>
#include <vector>

namespace {

std::string Trim(const std::string& value) {
    auto start = value.begin();
    while (start != value.end() && std::isspace(static_cast<unsigned char>(*start))) {
        ++start;
    }

    auto end = value.end();
    while (end != start && std::isspace(static_cast<unsigned char>(*(end - 1)))) {
        --end;
    }

    return std::string(start, end);
}

std::vector<std::string> Split(const std::string& value, char delimiter) {
    std::vector<std::string> parts;
    std::stringstream stream(value);
    std::string item;
    while (std::getline(stream, item, delimiter)) {
        parts.push_back(item);
    }
    return parts;
}

std::string NormalizePath(const std::string& websocket_path) {
    if (websocket_path.empty()) {
        return "/";
    }
    if (websocket_path.front() == '/') {
        return websocket_path;
    }
    return "/" + websocket_path;
}

}  // namespace

bool IsValidBridgeServerIp(const std::string& server_ip) {
    auto trimmed = Trim(server_ip);
    if (trimmed.empty()) {
        return false;
    }

    auto parts = Split(trimmed, '.');
    if (parts.size() != 4) {
        return false;
    }

    for (const auto& part : parts) {
        if (part.empty() || part.size() > 3) {
            return false;
        }
        int value = 0;
        for (char ch : part) {
            if (!std::isdigit(static_cast<unsigned char>(ch))) {
                return false;
            }
            value = value * 10 + (ch - '0');
        }
        if (value < 0 || value > 255) {
            return false;
        }
    }

    return true;
}

std::string BuildBridgeWebsocketUrl(const std::string& server_ip, int websocket_port, const std::string& websocket_path) {
    return "ws://" + Trim(server_ip) + ":" + std::to_string(websocket_port) + NormalizePath(websocket_path);
}

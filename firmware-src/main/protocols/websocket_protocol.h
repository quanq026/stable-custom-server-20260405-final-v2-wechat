#ifndef _WEBSOCKET_PROTOCOL_H_
#define _WEBSOCKET_PROTOCOL_H_


#include "protocol.h"
#include "discovered_server_cache.h"

#include <web_socket.h>
#include <freertos/FreeRTOS.h>
#include <freertos/event_groups.h>
#include <optional>

#define WEBSOCKET_PROTOCOL_SERVER_HELLO_EVENT (1 << 0)

class WebsocketProtocol : public Protocol {
public:
    WebsocketProtocol();
    ~WebsocketProtocol();

    bool Start() override;
    bool SendAudio(std::unique_ptr<AudioStreamPacket> packet) override;
    bool OpenAudioChannel() override;
    void CloseAudioChannel() override;
    bool IsAudioChannelOpened() const override;

private:
    EventGroupHandle_t event_group_handle_;
    std::unique_ptr<WebSocket> websocket_;
    int version_ = 1;
    std::string connected_ws_url_;
    std::string connected_server_id_;
    std::string connected_server_name_;
    std::optional<DiscoveredServerCacheEntry> pending_discovered_server_cache_;

    void ParseServerHello(const cJSON* root);
    void CacheDiscoveredServer(const DiscoveredServerCacheEntry& entry);
    bool SendText(const std::string& text) override;
    std::string GetHelloMessage();
};

#endif

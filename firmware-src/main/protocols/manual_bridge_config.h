#ifndef _MANUAL_BRIDGE_CONFIG_H_
#define _MANUAL_BRIDGE_CONFIG_H_

#include <string>

bool IsValidBridgeServerIp(const std::string& server_ip);
std::string BuildBridgeWebsocketUrl(const std::string& server_ip, int websocket_port, const std::string& websocket_path);

#endif

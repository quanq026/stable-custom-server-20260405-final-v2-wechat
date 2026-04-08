#include "../main/protocols/manual_bridge_config.h"

#include <cassert>

int main() {
    assert(IsValidBridgeServerIp("192.168.1.15"));
    assert(IsValidBridgeServerIp("10.0.0.9"));
    assert(!IsValidBridgeServerIp(""));
    assert(!IsValidBridgeServerIp("192.168.1"));
    assert(!IsValidBridgeServerIp("192.168.1.999"));
    assert(!IsValidBridgeServerIp("xiaozhi-bridge.local"));

    assert(BuildBridgeWebsocketUrl("192.168.1.15", 8000, "/xiaozhi/v1/") == "ws://192.168.1.15:8000/xiaozhi/v1/");
    assert(BuildBridgeWebsocketUrl("10.0.0.9", 8000, "xiaozhi/v1/") == "ws://10.0.0.9:8000/xiaozhi/v1/");

    return 0;
}

#include "../main/protocols/discovered_server_cache.h"

#include <cassert>

int main() {
    auto no_discovery = PrepareDiscoveredServerCache(
        false,
        "ws://192.168.1.15:8000/xiaozhi/v1/",
        "server-a",
        "xiaozhi-bridge"
    );
    assert(!no_discovery.has_value());

    auto empty_url = PrepareDiscoveredServerCache(true, "", "server-a", "xiaozhi-bridge");
    assert(!empty_url.has_value());

    auto valid = PrepareDiscoveredServerCache(
        true,
        "ws://192.168.1.15:8000/xiaozhi/v1/",
        "server-a",
        "xiaozhi-bridge"
    );
    assert(valid.has_value());
    assert(valid->ws_url == "ws://192.168.1.15:8000/xiaozhi/v1/");
    assert(valid->server_id == "server-a");
    assert(valid->server_name == "xiaozhi-bridge");

    return 0;
}

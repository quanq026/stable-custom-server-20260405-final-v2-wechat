#include "discovered_server_cache.h"

std::optional<DiscoveredServerCacheEntry> PrepareDiscoveredServerCache(
    bool discovery_used,
    const std::string& ws_url,
    const std::string& server_id,
    const std::string& server_name
) {
    if (!discovery_used || ws_url.empty()) {
        return std::nullopt;
    }

    DiscoveredServerCacheEntry entry;
    entry.ws_url = ws_url;
    entry.server_id = server_id;
    entry.server_name = server_name;
    return entry;
}

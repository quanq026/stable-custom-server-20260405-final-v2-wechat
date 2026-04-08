#ifndef DISCOVERED_SERVER_CACHE_H
#define DISCOVERED_SERVER_CACHE_H

#include <optional>
#include <string>

struct DiscoveredServerCacheEntry {
    std::string ws_url;
    std::string server_id;
    std::string server_name;
};

std::optional<DiscoveredServerCacheEntry> PrepareDiscoveredServerCache(
    bool discovery_used,
    const std::string& ws_url,
    const std::string& server_id,
    const std::string& server_name
);

#endif

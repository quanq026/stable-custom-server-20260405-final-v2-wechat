#ifndef BRIDGE_DISCOVERY_LOGIC_H
#define BRIDGE_DISCOVERY_LOGIC_H

#include <optional>
#include <string>
#include <vector>

struct BridgeDiscoveryCandidate {
    std::string server_id;
    std::string server_name;
    std::string ws_url;
};

std::optional<BridgeDiscoveryCandidate> SelectBridgeDiscoveryCandidate(
    const std::vector<BridgeDiscoveryCandidate>& candidates,
    const std::string& preferred_server_id
);

#endif

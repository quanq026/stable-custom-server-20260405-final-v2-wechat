#include "bridge_discovery_logic.h"

std::optional<BridgeDiscoveryCandidate> SelectBridgeDiscoveryCandidate(
    const std::vector<BridgeDiscoveryCandidate>& candidates,
    const std::string& preferred_server_id
) {
    if (candidates.empty()) {
        return std::nullopt;
    }

    if (!preferred_server_id.empty()) {
        for (const auto& candidate : candidates) {
            if (candidate.server_id == preferred_server_id) {
                return candidate;
            }
        }
    }

    return candidates.front();
}

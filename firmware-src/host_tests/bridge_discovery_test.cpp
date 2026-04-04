#include "../main/protocols/bridge_discovery_logic.h"

#include <cassert>
#include <vector>

int main() {
    std::vector<BridgeDiscoveryCandidate> empty_candidates;
    assert(!SelectBridgeDiscoveryCandidate(empty_candidates, "preferred").has_value());

    std::vector<BridgeDiscoveryCandidate> one_candidate = {
        BridgeDiscoveryCandidate{"server-a", "xiaozhi-bridge", "ws://192.168.1.15:8000/xiaozhi/v1/"}
    };
    auto picked_single = SelectBridgeDiscoveryCandidate(one_candidate, "");
    assert(picked_single.has_value());
    assert(picked_single->server_id == "server-a");

    std::vector<BridgeDiscoveryCandidate> multiple_candidates = {
        BridgeDiscoveryCandidate{"server-a", "xiaozhi-bridge-a", "ws://192.168.1.15:8000/xiaozhi/v1/"},
        BridgeDiscoveryCandidate{"server-b", "xiaozhi-bridge-b", "ws://192.168.1.20:8000/xiaozhi/v1/"},
    };
    auto picked_preferred = SelectBridgeDiscoveryCandidate(multiple_candidates, "server-b");
    assert(picked_preferred.has_value());
    assert(picked_preferred->server_id == "server-b");
    assert(picked_preferred->ws_url == "ws://192.168.1.20:8000/xiaozhi/v1/");

    auto picked_first = SelectBridgeDiscoveryCandidate(multiple_candidates, "missing");
    assert(picked_first.has_value());
    assert(picked_first->server_id == "server-a");

    return 0;
}

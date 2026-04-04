#ifndef BRIDGE_DISCOVERY_H
#define BRIDGE_DISCOVERY_H

#include "bridge_discovery_logic.h"

#include <string>
#include <vector>

struct BridgeDiscoveryResult {
    std::string ws_url;
    std::string server_id;
    std::string server_name;
    bool from_mdns = false;
};

class BridgeDiscoveryManager {
public:
    bool Resolve(BridgeDiscoveryResult& out_result);
    bool ResolveUdpFallback(BridgeDiscoveryResult& out_result);

private:
    std::string LoadPreferredServerId() const;
    bool TryResolveMdns(BridgeDiscoveryResult& out_result);
    bool QueryUdpCandidates(std::vector<BridgeDiscoveryCandidate>& candidates);
    static bool ParseUdpCandidate(const char* payload, BridgeDiscoveryCandidate& candidate);
    static std::string NormalizeHostLabel(const std::string& host);
    static std::string BuildWebsocketUrl(const std::string& host_or_ip);
};

#endif

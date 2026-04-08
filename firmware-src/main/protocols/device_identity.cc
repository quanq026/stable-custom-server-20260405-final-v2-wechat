#include "device_identity.h"

#include <algorithm>
#include <cctype>

std::string BuildStableDeviceId(const std::string& mac_address) {
    std::string trimmed;
    trimmed.reserve(mac_address.size());
    for (char ch : mac_address) {
        if (!std::isspace(static_cast<unsigned char>(ch))) {
            trimmed.push_back(static_cast<char>(std::tolower(static_cast<unsigned char>(ch))));
        }
    }

    return trimmed;
}

#include "json_frame_utils.h"

std::string CopyJsonFrameText(const char* data, size_t len) {
    if (data == nullptr || len == 0) {
        return {};
    }
    return std::string(data, len);
}

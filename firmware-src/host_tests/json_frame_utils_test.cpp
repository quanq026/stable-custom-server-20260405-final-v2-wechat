#include "../main/protocols/json_frame_utils.h"

#include <cassert>
#include <cstring>

int main() {
    const char expected[] = "{\"type\":\"hello\",\"transport\":\"websocket\"}";
    char raw_frame[sizeof(expected) + 8] = {};
    std::memcpy(raw_frame, expected, sizeof(expected) - 1);
    std::memcpy(raw_frame + sizeof(expected) - 1, "TRAILING", 8);

    std::string copied = CopyJsonFrameText(raw_frame, sizeof(expected) - 1);
    assert(copied == expected);
    assert(copied.size() == sizeof(expected) - 1);
    assert(copied.c_str()[copied.size()] == '\0');

    return 0;
}

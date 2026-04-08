#include "../main/protocols/device_identity.h"

#include <cassert>

int main() {
    assert(BuildStableDeviceId("AA:BB:CC:DD:EE:FF") == "aa:bb:cc:dd:ee:ff");
    assert(BuildStableDeviceId(" 12:34:56:78:9A:BC ") == "12:34:56:78:9a:bc");
    return 0;
}

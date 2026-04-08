#ifndef DEVICE_IDENTITY_H_
#define DEVICE_IDENTITY_H_

#include <string>

std::string BuildStableDeviceId(const std::string& mac_address);

#endif  // DEVICE_IDENTITY_H_

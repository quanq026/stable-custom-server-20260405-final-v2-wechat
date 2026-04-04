#include "volume_gesture.h"

#include <algorithm>
#include <cstdlib>

TouchZone TouchZoneRouter::Route(int x) const {
    if (config_.screen_width <= 0) {
        return TouchZone::kNone;
    }

    int clamped_x = std::clamp(x, 0, config_.screen_width - 1);
    int left_width = (config_.screen_width * std::clamp(config_.left_percent, 0, 100)) / 100;
    int middle_width = (config_.screen_width * std::clamp(config_.middle_percent, 0, 100)) / 100;
    int middle_end = std::min(config_.screen_width, left_width + middle_width);

    if (clamped_x < left_width) {
        return TouchZone::kVolume;
    }
    if (clamped_x < middle_end) {
        return TouchZone::kHistory;
    }
    return TouchZone::kBrightness;
}

bool VolumeGestureTracker::Begin(int x, int y, int current_volume) {
    (void)x;
    Reset();
    active_ = true;
    start_y_ = y;
    base_volume_ = ClampVolume(current_volume);
    last_volume_ = base_volume_;
    return true;
}

std::optional<int> VolumeGestureTracker::Update(int, int y) {
    if (!active_) {
        return std::nullopt;
    }

    int delta_y = start_y_ - y;
    if (std::abs(delta_y) < config_.min_drag_px) {
        return std::nullopt;
    }

    int steps = delta_y / config_.drag_step_px;
    int proposed_volume = ClampVolume(base_volume_ - (steps * config_.volume_step));
    if (proposed_volume == last_volume_) {
        return std::nullopt;
    }

    last_volume_ = proposed_volume;
    return proposed_volume;
}

void VolumeGestureTracker::End() {
    active_ = false;
}

void VolumeGestureTracker::Reset() {
    active_ = false;
    start_y_ = 0;
    base_volume_ = 0;
    last_volume_ = 0;
}

int VolumeGestureTracker::ClampVolume(int volume) const {
    return std::clamp(volume, config_.min_volume, config_.max_volume);
}

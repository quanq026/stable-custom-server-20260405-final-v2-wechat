#ifndef ES3N28P_VOLUME_GESTURE_H_
#define ES3N28P_VOLUME_GESTURE_H_

#include <optional>

enum class TouchZone {
    kNone,
    kVolume,
    kHistory,
    kBrightness,
};

struct TouchZoneRouterConfig {
    int screen_width = 320;
    int left_percent = 33;
    int middle_percent = 34;
};

class TouchZoneRouter {
public:
    explicit TouchZoneRouter(const TouchZoneRouterConfig& config) : config_(config) {}

    TouchZone Route(int x) const;

private:
    TouchZoneRouterConfig config_;
};

struct VolumeGestureConfig {
    int screen_width = 240;
    int edge_percent = 20;
    int drag_step_px = 16;
    int volume_step = 5;
    int min_drag_px = 24;
    int min_volume = 0;
    int max_volume = 100;
};

class VolumeGestureTracker {
public:
    explicit VolumeGestureTracker(const VolumeGestureConfig& config) : config_(config) {}

    bool Begin(int x, int y, int current_volume);
    std::optional<int> Update(int x, int y);
    void End();
    void Reset();
    bool active() const { return active_; }

private:
    VolumeGestureConfig config_;
    bool active_ = false;
    int start_y_ = 0;
    int base_volume_ = 0;
    int last_volume_ = 0;

    int ClampVolume(int volume) const;
};

#endif

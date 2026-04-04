#include "../main/boards/es3n28p-lcd28/volume_gesture.h"

#include <cassert>

int main() {
    VolumeGestureConfig config;
    config.screen_width = 240;
    config.edge_percent = 20;
    config.drag_step_px = 16;
    config.volume_step = 5;
    config.min_drag_px = 24;

    VolumeGestureTracker tracker(config);
    TouchZoneRouterConfig router_config;
    router_config.screen_width = 320;
    router_config.left_percent = 33;
    router_config.middle_percent = 34;
    TouchZoneRouter router(router_config);

    assert(router.Route(10) == TouchZone::kVolume);
    assert(router.Route(140) == TouchZone::kHistory);
    assert(router.Route(280) == TouchZone::kBrightness);

    assert(tracker.Begin(10, 200, 50));
    auto unchanged = tracker.Update(220, 185);
    assert(!unchanged.has_value());

    auto decreased = tracker.Update(220, 168);
    assert(decreased.has_value());
    assert(*decreased == 40);

    tracker.End();

    tracker.Reset();
    assert(tracker.Begin(230, 200, 95));
    auto clamped_max = tracker.Update(230, 280);
    assert(clamped_max.has_value());
    assert(*clamped_max == 100);

    tracker.End();

    tracker.Reset();
    assert(tracker.Begin(230, 200, 5));
    auto clamped_min = tracker.Update(230, 120);
    assert(clamped_min.has_value());
    assert(*clamped_min == 0);

    tracker.End();
    return 0;
}

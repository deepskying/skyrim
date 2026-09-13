#pragma once

namespace durability_hud {
// A page can mount before Meridian installs its window bridge. Probe from the
// existing game-thread ticker until a real ready reply arrives; never focus UI.
inline constexpr const char* kReadyProbe = R"JS(
if (window.DurabilityManager &&
    typeof window.DurabilityManager.reportReady === 'function' &&
    typeof window.DurabilityManager.updateEquippedHud === 'function' &&
    typeof window.durabilityManagerAction === 'function') {
    window.DurabilityManager.reportReady();
}
)JS";
}

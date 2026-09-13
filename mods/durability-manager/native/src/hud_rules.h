#pragma once
#include <cmath>

namespace durability_hud {
inline bool ShouldDisplay(bool worn, bool weapon, float current, float maximum, unsigned threshold)
{
    return worn && std::isfinite(current) && std::isfinite(maximum) && maximum > 0 &&
        (weapon || current * 100.0F / maximum < threshold);
}
}

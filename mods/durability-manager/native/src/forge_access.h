#pragma once

#include <cmath>
#include <cstdint>

namespace workshop
{
    inline constexpr float kRadius = 600.0F;
    struct Location
    {
        std::uint32_t cell = 0;
        std::uint32_t world = 0;
        bool interior = false;
    };

    // Interior coordinates are local to their cell; exterior coordinates can
    // cross cell boundaries, but never cross into another worldspace.
    inline bool IsNearby(float squaredDistance, const Location& player, const Location& station, bool available)
    {
        if (!available || !player.cell || !station.cell || !std::isfinite(squaredDistance) ||
            squaredDistance < 0.0F || squaredDistance > kRadius * kRadius) return false;
        if (player.interior || station.interior) return player.interior && station.interior && player.cell == station.cell;
        return player.world != 0 && player.world == station.world;
    }
}

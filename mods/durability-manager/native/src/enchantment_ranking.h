#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <optional>
#include <random>

namespace enhancement
{
    inline double EffectPower(float magnitude, std::uint32_t duration, float baseCost,
        bool noMagnitude, bool noDuration, bool soulTrap, bool hidden)
    {
        if (hidden) return 0.0;
        // Soul trapping is a utility with a capture window, not damage per hit.
        // The window contributes up to 30 points to a baseline score of 30.
        if (soulTrap) return 30.0 + (noDuration ? 0.0 : static_cast<double>((std::min)(duration, 60U)) * 0.5);
        const auto effectiveMagnitude = noMagnitude ? 1.0 : (std::max)(1.0, std::abs(static_cast<double>(magnitude)));
        const auto effectiveDuration = noDuration ? 1.0 : 1.0 + static_cast<double>((std::min)(duration, 300U)) / 30.0;
        return effectiveMagnitude * effectiveDuration * std::sqrt((std::max)(0.1, std::abs(static_cast<double>(baseCost))));
    }

    inline bool MatchesTier(std::optional<std::uint8_t> fixedTier, std::size_t tier)
    {
        return !fixedTier || *fixedTier == tier;
    }

    inline double CandidateWeight(std::size_t index, std::size_t count, double target, bool fixedTier)
    {
        const auto position = count > 1 ? static_cast<double>(index) / static_cast<double>(count - 1) : target;
        // Keep manually pinned utilities reachable even when their numerical
        // power is far from the normal percentile for the chosen tier.
        return (std::max)(fixedTier ? 0.25 : 0.02, 1.0 - std::abs(position - target) / 0.25);
    }

    inline std::optional<std::size_t> AvailableTier(std::size_t requested,
        const std::array<bool, 4>& available, std::mt19937& random)
    {
        if (requested < available.size() && available[requested]) return requested;
        constexpr std::array<double, 4> weights{42, 33, 18, 7};
        std::array<double, 4> usable{};
        double total = 0;
        for (std::size_t i = 0; i < usable.size(); ++i) {
            usable[i] = available[i] ? weights[i] : 0;
            total += usable[i];
        }
        if (total == 0) return std::nullopt;
        return std::discrete_distribution<std::size_t>(usable.begin(), usable.end())(random);
    }
}

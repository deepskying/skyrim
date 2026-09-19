#pragma once
#include <algorithm>
#include <cstdint>
#include <vector>

namespace companion::outfit {
struct Candidate {
    std::size_t index;
    std::uint32_t mask;
    bool locked, worn;
};
// Input is shuffled first. Locked clothing wins; unworn copies win within each tier.
// Manual requests may fill uncovered slots with unlocked clothing.
inline std::vector<std::size_t> Select(std::vector<Candidate> candidates, std::uint32_t protectedSlots, bool fallback) {
    std::stable_sort(candidates.begin(), candidates.end(), [](const auto& a, const auto& b) {
        if (a.locked != b.locked) return a.locked > b.locked;
        return a.worn < b.worn;
    });
    std::vector<std::size_t> result;
    for (const auto& item : candidates) {
        if ((!item.locked && !fallback) || !item.mask || (protectedSlots & item.mask)) continue;
        protectedSlots |= item.mask;
        result.push_back(item.index);
    }
    return result;
}
}

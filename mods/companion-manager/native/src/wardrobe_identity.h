#pragma once
#include <cstdint>
#include <unordered_set>

namespace companion::rules
{
// One snapshot row per addressable inventory instance means one unique key per instance.
// Equipping an item makes the engine copy the pack stack's ExtraUniqueID onto the worn copy,
// so the same identity can describe two different instances. The pack stack keeps its identity
// (locks, favorites and saved outfits already point at it) and the equipped copy takes a new
// one; whichever row already carries the equipped state is the row that yields.
inline bool KeepsExistingIdentity(bool existingEquipped)
{
    return !existingEquipped;
}

// Lowest identity this item has not handed out yet. 0 reports an exhausted 16-bit space; the
// caller must then drop the duplicate row instead of emitting an ambiguous key.
inline std::uint16_t FirstFreeUniqueID(const std::unordered_set<std::uint16_t> &used)
{
    for (std::uint32_t id = 1; id <= 0xFFFF; ++id)
    {
        const auto candidate = static_cast<std::uint16_t>(id);
        if (!used.contains(candidate))
            return candidate;
    }
    return 0;
}
} // namespace companion::rules

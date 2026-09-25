#pragma once
#include <cstdint>
#include <unordered_set>

namespace companion::rules
{
// One snapshot row per addressable inventory instance means one unique key per instance.
// Equipping an item makes the engine copy the pack stack's ExtraUniqueID onto the worn copy,
// so the same identity can describe two different instances. Whichever row yields takes a fresh
// id; the other keeps the key it already had.
//
// A saved outfit is the one thing that cannot follow a reassignment: it stores the key it
// captured, so moving that key to a copy the set does not describe leaves the set pointing at an
// instance it never named. Saved sets are captured from worn gear, so while a set still
// references the key the worn copy keeps it and the pack stack - the copy no set names - takes
// the new id. Without a reference the pack stack keeps its identity, because locks, favorites and
// an unsaved outfit all follow the stock row, and the worn copy is the row that yields.
inline bool KeepsExistingIdentity(bool existingEquipped, bool incomingEquipped, bool keyReferenced)
{
    if (keyReferenced && existingEquipped != incomingEquipped)
        return existingEquipped;
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

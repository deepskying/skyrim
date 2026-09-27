#pragma once
#include <cstdint>

namespace companion::helmet
{
// Actor biped slots are numbered 30..61 and an armour record stores them as bits 0..31. 30 is the
// classic head slot, 31 hair, 32 body, 42 the circlet slot and 43 the ears.
constexpr std::uint32_t SlotBit(unsigned slot)
{
    return slot >= 30 && slot <= 61 ? 1u << (slot - 30) : 0u;
}
inline constexpr std::uint32_t HeadSlot = SlotBit(30);
inline constexpr std::uint32_t HairSlot = SlotBit(31);
inline constexpr std::uint32_t BodySlot = SlotBit(32);
inline constexpr std::uint32_t CircletSlot = SlotBit(42);
inline constexpr std::uint32_t EarSlot = SlotBit(43);

// Headwear is a piece that covers the head or the circlet slot. This load order puts helmets in 42
// so a wig can stay in 31, which is why 31 alone (hair), 43 (earrings) and the extension slots the
// hair accessories use are deliberately not headwear: "no helmets" must never take a wig or a pair
// of earrings off with it.
//
// A hood that belongs to a whole robe is written with the body slot as well. Taking that off would
// strip the body armour too, so a multi-slot piece that also covers the body is never headwear -
// the companion keeps the robe and only loses what is purely worn on the head.
constexpr bool Headwear(std::uint32_t mask)
{
    return (mask & (HeadSlot | CircletSlot)) != 0 && (mask & BodySlot) == 0;
}

// The engine auto-equips the best head piece a follower owns as soon as looting hands them one, and
// every outfit path in this mod can hand one over as well. One decision answers both: may this
// piece stay on / go on? Quest gear and the character skin are never touched, because the game
// will not give them up and the rest of the mod treats them as protected as well.
constexpr bool Blocked(bool allowed, bool protectedItem, std::uint32_t mask)
{
    return !allowed && !protectedItem && Headwear(mask);
}
} // namespace companion::helmet

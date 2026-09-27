#include "../src/helmet_rules.h"
#include "check.h"
#include <iostream>

using namespace companion::helmet;

int main()
{
    // An armour record stores slots 30..61 as bits 0..31, so each slot keeps its own bit and
    // anything outside the range cannot describe a piece at all.
    CHECK(SlotBit(30) == 0x1u);
    CHECK(SlotBit(31) == 0x2u);
    CHECK(SlotBit(32) == 0x4u);
    CHECK(SlotBit(39) == 0x200u);
    CHECK(SlotBit(42) == 0x1000u);
    CHECK(SlotBit(43) == 0x2000u);
    CHECK(SlotBit(61) == 0x80000000u);
    CHECK(SlotBit(29) == 0u);
    CHECK(SlotBit(62) == 0u);
    CHECK(HeadSlot == 0x1u);
    CHECK(HairSlot == 0x2u);
    CHECK(BodySlot == 0x4u);
    CHECK(CircletSlot == 0x1000u);
    CHECK(EarSlot == 0x2000u);

    // The masks below are the ones this load order actually writes, read out of the wardrobe log.
    // Helmets sit in the circlet slot so a wig can stay in the hair slot, which is exactly why the
    // head and circlet bits decide this and the hair bit does not.
    CHECK(Headwear(0x1002u));  // 铁制头盔 / 玻璃头盔: hair + circlet
    CHECK(Headwear(0x3003u));  // 钢板头盔: head + hair + circlet + ears
    CHECK(Headwear(0x1000u));  // 头环 / 帽子 / 面纱 / 花环 / 兜帽: circlet only
    CHECK(Headwear(0x1u));     // a plain head-slot piece is still a helmet
    CHECK(!Headwear(0x1006u)); // 梭默兜帽法袍: hood plus body, so the robe stays on
    CHECK(!Headwear(0x4u));    // body armour
    CHECK(!Headwear(0x2u));    // 假发 smp_bellaw: hair
    CHECK(!Headwear(0x2000u)); // 耳环: ears
    CHECK(!Headwear(0x800000u)); // 头发配饰: an extension slot
    CHECK(!Headwear(0x20000u));  // 背环 halo
    CHECK(!Headwear(0x20u));   // necklace
    CHECK(!Headwear(0x40u));   // ring
    CHECK(!Headwear(0x80u));   // boots
    CHECK(!Headwear(0x200u));  // shield
    CHECK(!Headwear(0u));

    // The guard and every outfit path share one decision: a forbidden helmet is blocked, an allowed
    // one is left alone, and quest gear or the character skin is never touched either way.
    CHECK(Blocked(false, false, 0x1002u));
    CHECK(Blocked(false, false, 0x1000u));
    CHECK(!Blocked(true, false, 0x1002u));
    CHECK(!Blocked(false, true, 0x1002u));
    CHECK(!Blocked(false, false, 0x2u));
    CHECK(!Blocked(false, false, 0x1006u));
    CHECK(!Blocked(false, false, 0u));

    std::cout << "helmet rules passed.\n";
}

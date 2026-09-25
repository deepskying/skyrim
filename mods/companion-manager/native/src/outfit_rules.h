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
constexpr bool UseSaved(std::size_t count,int chance,int roll) {
    return count>0&&roll>=0&&roll<100&&roll<chance;
}
constexpr std::uint32_t SlotBit(unsigned slot) {
    return slot>=30&&slot<=61&&slot!=39 ? 1u<<(slot-30) : 0u;
}
constexpr bool EligiblePart(unsigned slot,std::uint32_t mask,std::uint32_t protectedSlots,bool protectedItem,bool worn) {
    return slot>=30&&slot<=61&&slot!=39&&!protectedItem&&!worn&&
        (mask&(1u<<(slot-30)))&&!(mask&protectedSlots);
}
// Random changes draw on favorited gear only, so one rule describes the whole pool. Multi-slot
// pieces qualify for each slot they cover.
constexpr bool EligibleFavoriteRow(std::uint32_t mask,std::uint32_t protectedSlots,bool protectedItem,bool worn,bool favorite) {
    return favorite&&!protectedItem&&!worn&&mask!=0&&!(mask&protectedSlots);
}
inline bool CanUnlockReplacement(bool manual, bool worn, bool protectedItem,
                                 std::uint32_t mask, std::uint32_t replacing) {
    return manual && worn && !protectedItem && (mask & replacing) != 0;
}
// A whole-set request takes off every outfit piece the set does not name, so the companion ends up
// wearing the set instead of a mix. Quest gear, the actor's skin and the named pieces stay on.
constexpr bool StripBeforeWear(bool outfitPiece,bool protectedItem,bool namedBySet) {
    return outfitPiece&&!protectedItem&&!namedBySet;
}
// A saved set names one instance by key. When that identity is gone - the engine re-issues it
// after a temper round trip duplicates it - the only safe stand-in is the same base form carrying
// the same enchantment signature: another enchantment, or the same one at a different charge, is
// a different item, and a worn copy is already in use.
struct EnchantSignature {
    std::uint32_t form{};
    std::uint16_t charge{};
    bool enchanted{};
};
constexpr bool SameEnchantment(const EnchantSignature& a,const EnchantSignature& b) {
    return a.enchanted==b.enchanted&&(!a.enchanted||(a.form==b.form&&a.charge==b.charge));
}
constexpr bool FallbackInstance(const EnchantSignature& saved,const EnchantSignature& row,bool worn) {
    return !worn&&SameEnchantment(saved,row);
}
// The wear page toggles one named instance. It covers every playable armor record that occupies a
// slot - jewelry and shields included - while the outfit generator deliberately leaves both alone.
constexpr bool Toggleable(std::uint32_t mask,bool playable) { return playable&&mask!=0; }
// A swap takes off exactly the worn pieces it replaces. Gear the game protects (quest items, the
// actor's skin) blocks the swap instead of being removed behind the player's back.
constexpr bool ReplacedBySwap(std::uint32_t wornMask,std::uint32_t targetMask,bool protectedItem) {
    return !protectedItem&&(wornMask&targetMask)!=0;
}
constexpr bool SwapProtected(std::uint32_t wornMask,std::uint32_t targetMask,bool protectedItem) {
    return protectedItem&&(wornMask&targetMask)!=0;
}
// Manual changes prefer unworn clothing, then locked clothing. Input is shuffled first.
// Manual requests may fill uncovered slots with unlocked clothing.
inline std::vector<std::size_t> Select(std::vector<Candidate> candidates, std::uint32_t protectedSlots, bool fallback) {
    std::stable_sort(candidates.begin(), candidates.end(), [fallback](const auto& a, const auto& b) {
        if (fallback && a.worn != b.worn) return a.worn < b.worn;
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
enum class Result { Pending, Changed, Partial, NoCandidates, NoSavedSets, NoSelection, Unchanged, Unconfirmed };
inline bool Changed(Result result) { return result == Result::Changed || result == Result::Partial; }
// The random-set dialogue line only ever uses a saved set; with none it reports back instead of
// recombining the collection.
constexpr bool HasSavedSet(std::size_t count) { return count > 0; }
constexpr std::size_t SavedSetPick(std::size_t count, std::size_t roll) { return count ? roll % count : 0; }
inline Result Confirmation(std::size_t requested, std::size_t confirmed) {
    if (!confirmed) return Result::Unconfirmed;
    return confirmed == requested ? Result::Changed : Result::Partial;
}
inline Result PollConfirmation(std::size_t requested, std::size_t confirmed, bool expired) {
    if (requested && confirmed == requested) return Result::Changed;
    return expired ? Confirmation(requested,confirmed) : Result::Pending;
}
inline const char* Message(Result result) {
    switch (result) {
    case Result::Pending: return "正在确认换装，请稍候";
    case Result::Changed: return "已确认更换穿搭";
    case Result::Partial: return "已更换部分服饰，其余未确认穿上；请刷新检查";
    case Result::NoCandidates: return "没有可用的收藏服饰：请先在库存中收藏要参与随机穿搭的服饰";
    case Result::NoSavedSets: return "还没有保存的套装：请先在伙伴穿搭面板保存一套";
    case Result::NoSelection: return "没有符合条件的服饰：请检查槽位冲突、物品保护及收藏状态";
    case Result::Unchanged: return "没有选出不同的服饰，当前可用搭配已穿戴";
    default: return "已尝试穿戴新服饰，但未确认成功；请刷新检查，诊断已记录";
    }
}
}

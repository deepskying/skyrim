#pragma once
#include "crafting_plan.h"
#include <span>

namespace crafting {
enum class MaterialKind { unsupported, ingredient, potion, poison, food };

// One alchemy effect as the matching rules see it. Actor values stay plain ints so the
// header is testable without the game headers, and so modded actor values (CACO's
// "intelligence" is the destruction power modifier) are handled by value.
struct EffectSample {
    bool known;
    int archetype;
    int primaryAV;
    int secondaryAV;
    float magnitude;
    std::uint32_t duration;
};

// Only numeric archetypes charge. Several overhauls rewrite vanilla alchemy effects as
// DualValueModifier, so the second actor value has to be read as well.
inline constexpr int archetypeValueModifier = 0, archetypeDualValueModifier = 5, archetypePeakValueModifier = 34;

// Utility actor values say nothing about a projectile, so no percentage makes them charge.
inline bool UtilityActorValue(int av) {
    switch (av) {
    case 54:  // invisibility
    case 55:  // night eye
    case 56:  // detect life range
    case 57:  // water breathing
    case 58:  // water walking
    case 59:  // ignore crippled limbs
    case 88:  // telekinesis
        return true;
    default:
        return false;
    }
}

// Actor values that charge an arrow family at full weight. Every other numeric actor
// value that is not utility above still charges through GenericPercent.
inline bool FamilyActorValue(int family, int av) {
    switch (family) {
    case 0:  return av == 41 || av == 149;                                                   // fire: 抗火＋毁灭系
    case 1:  return av == 43 || av == 149;                                                   // ice: 抗冰＋毁灭系
    case 2:  return av == 42 || av == 149;                                                   // shock: 抗电＋毁灭系
    case 3:  return av == 40 || av == 45;                                                    // poison: 抗毒＋抗疾病
    case 4:  return av == 24 || av == 27 || av == 155;                                       // blood: 生命
    case 5:  return av == 24 || av == 27 || av == 155 || av == 151;                          // holy: 生命＋恢复系
    case 6:  return av == 26 || av == 29 || av == 157 || av == 30;                            // wind: 耐力＋速度
    case 7:  return av == 26 || av == 29 || av == 157;                                       // water: 耐力
    case 8:  return av == 26 || av == 29 || av == 157 || av == 32 || av == 39 || av == 147;   // earth: 耐力＋负重／护甲／变化系
    case 9:  return av == 25 || av == 28 || av == 156 || av == 150;                           // dark: 魔法值＋幻术系
    case 10: return av == 25 || av == 28 || av == 156 || av == 148 || av == 152;              // soul: 魔法值＋召唤／附魔
    case 11: return av == 25 || av == 28 || av == 156 || av == 44;                            // arcane: 魔法值＋魔法抗性
    default: return false;
    }
}

inline const char* FamilyMaterialName(int family) {
    switch (family) {
    case 0:  return "抗火／弱火／毁灭系";
    case 1:  return "抗冰／弱冰／毁灭系";
    case 2:  return "抗电／弱电／毁灭系";
    case 3:  return "抗毒／弱毒／抗疾病";
    case 4:  return "生命／生命恢复";
    case 5:  return "生命／生命恢复／恢复系";
    case 6:  return "耐力／耐力恢复／速度";
    case 7:  return "耐力／耐力恢复";
    case 8:  return "耐力／耐力恢复／负重／护甲／变化系";
    case 9:  return "魔法值／魔法恢复／幻术系";
    case 10: return "魔法值／魔法恢复／召唤系／附魔系";
    case 11: return "魔法值／魔法恢复／魔法抗性";
    default: return "任意数值型功效";
    }
}

// Weight of numeric effects that belong to no family. Read from MagicArrows.ini; 0 turns
// the fallback off, 100 accepts every numeric effect at full strength.
inline int GenericPercent = 50;

inline int EffectWeight(const EffectSample& effect, int family, int genericPercent) {
    const int values[]{effect.primaryAV, effect.archetype == archetypeDualValueModifier ? effect.secondaryAV : -1};
    int weight = 0;
    for (int av : values) {
        if (av < 0 || UtilityActorValue(av)) continue;
        if (FamilyActorValue(family, av)) return 100;
        if (genericPercent > weight) weight = genericPercent;
    }
    return weight;
}

inline int SampleUnits(const EffectSample& effect, int family, int genericPercent) {
    if (effect.archetype != archetypeValueModifier && effect.archetype != archetypeDualValueModifier && effect.archetype != archetypePeakValueModifier) return 0;
    const int weight = EffectWeight(effect, family, genericPercent);
    if (weight <= 0) return 0;
    const int charge = EffectCharge(effect.magnitude, effect.duration);
    if (charge <= 0) return 0;
    const int scaled = static_cast<int>((static_cast<long long>(charge) * weight + 99) / 100);
    return std::max(1, std::min(scaled, materialUnitCap));
}

// The strongest single matching effect charges the material; effects never add up.
inline int MaterialUnits(MaterialKind kind, std::span<const EffectSample> effects, int family, int genericPercent = GenericPercent) {
    if (kind != MaterialKind::ingredient && kind != MaterialKind::potion && kind != MaterialKind::poison) return 0;
    int units = 0;
    for (const auto& effect : effects) {
        // Ingredients still need the player to have discovered that effect.
        if (kind == MaterialKind::ingredient && !effect.known) continue;
        units = std::max(units, SampleUnits(effect, family, genericPercent));
    }
    return units;
}
}

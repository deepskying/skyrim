#pragma once
#include "crafting_plan.h"
#include <span>

namespace crafting {
enum class MaterialKind { unsupported, ingredient, potion, poison, food };
struct ChargeEffect {
    bool known;
    bool matching;
    float magnitude;
    std::uint32_t duration;
};
inline int MaterialUnits(MaterialKind kind, std::span<const ChargeEffect> effects) {
    if (kind != MaterialKind::ingredient && kind != MaterialKind::potion && kind != MaterialKind::poison) return 0;
    int units = 0;
    for (const auto& effect : effects) {
        if (!effect.matching || (kind == MaterialKind::ingredient && !effect.known)) continue;
        units = std::max(units, EffectCharge(effect.magnitude, effect.duration));
    }
    return units;
}
}

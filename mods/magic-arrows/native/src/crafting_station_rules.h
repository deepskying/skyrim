#pragma once

namespace crafting_access {
template <class HasKeyword>
bool IsEnchantingStation(bool enchantingBench, HasKeyword hasKeyword) {
    return enchantingBench || hasKeyword("isEnchanting") || hasKeyword("WICraftingEnchanting");
}
}

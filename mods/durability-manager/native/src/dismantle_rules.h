#pragma once
#include <cstdint>
namespace dismantle_rules {
// Never recycle a batch's entire ingredient cost from a single output item.
constexpr std::int32_t MaterialYield(std::int32_t ingredientCount, std::uint16_t outputs) {
    if (ingredientCount <= 0 || outputs == 0) return 0;
    const auto perItem = ingredientCount / outputs;
    return perItem == 0 ? 0 : perItem < 2 ? 1 : perItem / 2;
}
}

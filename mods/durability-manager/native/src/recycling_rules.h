#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>
#include <optional>

namespace recycling {
struct StackPart {
    std::uintptr_t extra = 0;
    std::uint16_t unique = 0;
    std::int32_t count = 0;
    bool operator==(const StackPart&) const = default;
};
// A displayed row may contain several extra lists and an untagged remainder.
// Only the lists actually in that row may be consumed, never other same-base rows.
inline std::optional<std::vector<StackPart>> ResolveStack(
    std::int32_t rowCount, std::int32_t total, std::vector<StackPart> row, const std::vector<StackPart>& live) {
    if (rowCount <= 0 || rowCount > total) return std::nullopt;
    std::int64_t tagged = 0, selected = 0;
    for (const auto& part : live) {
        if (!part.extra || part.count <= 0) return std::nullopt;
        tagged += part.count;
    }
    std::sort(row.begin(), row.end(), [](const auto& a, const auto& b) { return a.extra < b.extra; });
    for (std::size_t i = 0; i < row.size(); ++i) {
        const auto& part = row[i];
        if (!part.extra || part.count <= 0 || (i && row[i - 1].extra == part.extra) ||
            std::find(live.begin(), live.end(), part) == live.end()) return std::nullopt;
        selected += part.count;
    }
    const auto plain = static_cast<std::int64_t>(rowCount) - selected;
    if (plain < 0 || tagged > total || plain > total - tagged) return std::nullopt;
    if (plain) row.push_back({0, 0, static_cast<std::int32_t>(plain)});
    return row;
}
inline std::int32_t ConsumeCount(std::int32_t selected, bool ammunition, bool entireStack) {
    if (selected <= 0) return 0;
    const auto unit = ammunition ? 10 : 1;
    return entireStack ? (std::min)(selected, 10000) / unit * unit : selected >= unit ? unit : 0;
}
inline std::int32_t RecipeYield(std::int32_t ingredient, std::uint32_t produced, std::int32_t consumed) {
    if (ingredient <= 0 || produced == 0 || consumed <= 0) return 0;
    const auto yield = static_cast<std::int64_t>(ingredient) * consumed / (2LL * produced);
    return yield > (std::numeric_limits<std::int32_t>::max)() ? 0 : static_cast<std::int32_t>(yield);
}
inline std::int32_t WeightedYield(float weight, double ratio, std::int32_t consumed) {
    if (!std::isfinite(weight) || weight < 0 || !std::isfinite(ratio) || ratio <= 0 || consumed <= 0) return 0;
    const auto amount = std::ceil((std::max)(1.0, static_cast<double>(weight)) * ratio) * consumed;
    return amount > (std::numeric_limits<std::int32_t>::max)() ? 0 : static_cast<std::int32_t>(amount);
}
}

#include "../../../magic-arrows/native/src/crafting_station_rules.h"
#include "../../../durability-manager/native/src/forge_access.h"
#include <cassert>
#include <initializer_list>
#include <string_view>
#include <iostream>

int main() {
    const auto station = [](bool enchantingBench, std::initializer_list<std::string_view> keywords) {
        return crafting_access::IsEnchantingStation(enchantingBench, [&](std::string_view keyword) {
            for (auto value : keywords) if (value == keyword) return true;
            return false;
        });
    };
    // Skyrim.esm BAD0D and D5501: enchanting WBDT, isEnchanting/WICraftingEnchanting.
    assert(station(true, {"isEnchanting", "WICraftingEnchanting"}));
    // Skyrim.esm E7AEA DisenchantmentFont01 has enchanting WBDT without keywords.
    assert(station(true, {}));
    // Keyword fallback for custom objects, independently of the furniture type.
    assert(station(false, {"isEnchanting"}));
    assert(station(false, {"WICraftingEnchanting"}));
    assert(!station(false, {}));
    assert(!station(false, {"CraftingSmithingForge"}));
    assert(!station(false, {"CraftingAlchemy"}));
    assert(!station(false, {"MagicDisallowEnchanting"}));
    const workshop::Location room{1, 0, true}, otherRoom{2, 0, true};
    assert(workshop::IsNearby(600.f * 600.f, room, room, true));
    assert(!workshop::IsNearby(601.f * 601.f, room, room, true));
    assert(!workshop::IsNearby(1.f, room, otherRoom, true));
    assert(!workshop::IsNearby(1.f, room, room, false));
    std::cout << "Enchanting station identification and proximity regression checks passed.\n";
}

#include "../src/reinforced_name.h"
#include <cassert>
#include <string>

using durability::name::AlreadyReinforced;
using durability::name::CleanStoredBaseline;
using durability::name::Reinforced;
using durability::name::StripDecorations;
using durability::name::StripQualityMarkers;

int main()
{
    // The old writer appended its suffix to whatever was already stored, marker and all. Forty rounds
    // of that pipeline must still normalise back to one clean "name +1".
    std::string polluted = "[Army] Modern City Shorts I";
    for (int i = 0; i < 40; ++i) polluted += " +1 (上等)";
    assert(polluted.size() > 400);
    assert(Reinforced(polluted, 1) == "[Army] Modern City Shorts I +1");
    assert(Reinforced(Reinforced(polluted, 3), 3) == "[Army] Modern City Shorts I +3");
    // Level zero (a removed enhancement) returns the clean base name.
    assert(Reinforced(polluted, 0) == "[Army] Modern City Shorts I");
    // Existing levels are replaced, not appended.
    assert(Reinforced("钢剑 +2", 4) == "钢剑 +4");
    assert(Reinforced("钢剑 (上等)", 1) == "钢剑 +1");
    assert(Reinforced("钢剑 +1 (上等)", 4) == "钢剑 +4");
    // The engine marker can sit on either side of our own level.
    assert(StripDecorations("钢剑 +4 (上等)") == "钢剑");
    assert(StripDecorations("钢剑 (上等) +4") == "钢剑");
    // Names that merely look numeric or bracketed stay untouched.
    assert(StripDecorations("铁剑 +") == "铁剑 +");
    assert(StripDecorations("铁剑 +1a") == "铁剑 +1a");
    assert(StripDecorations("药水 (2) (3)") == "药水 (2) (3)"); // engine markers have no digits-only body
    assert(StripDecorations("未命名") == "未命名");
    // Comparing two names keeps the level and only drops the engine marker.
    assert(StripQualityMarkers("钢剑 +4 (上等)") == "钢剑 +4");
    // The sync skips a name that already means the level, marker and all...
    assert(AlreadyReinforced("钢剑 +1 (上等)", "钢剑 +1"));
    assert(AlreadyReinforced("钢剑 +4", "钢剑 +4 (上等)"));
    // ...but a stale level is a real difference again, so "+1" stops surviving "+4".
    assert(!AlreadyReinforced("钢剑 +1 (上等)", "钢剑 +2"));
    assert(!AlreadyReinforced("钢剑 +1", "钢剑 +4"));
    // Repairing a stored baseline only touches names our own suffix polluted, never the player's text.
    assert(CleanStoredBaseline("飞蛾背包 - 蓝紫色 +1 (上等)") == "飞蛾背包 - 蓝紫色");
    assert(CleanStoredBaseline("圣光剑 (净化)") == "圣光剑 (净化)");
    assert(CleanStoredBaseline("[Army] Modern City Shorts I") == "[Army] Modern City Shorts I");
    return 0;
}

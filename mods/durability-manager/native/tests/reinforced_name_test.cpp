#include "../src/reinforced_name.h"
#include <cassert>
#include <string>

using durability::name::AlreadyReinforced;
using durability::name::Reinforced;
using durability::name::StripDecorations;

int main()
{
    // Re-applying a level never grows the name, however polluted the stored one is.
    std::string polluted = "[Army] Modern City Shorts I";
    for (int i = 0; i < 40; ++i) polluted = Reinforced(polluted, 1) + " (上等)";
    assert(polluted.size() > 400);
    assert(Reinforced(polluted, 1) == "[Army] Modern City Shorts I +1");
    assert(Reinforced(Reinforced(polluted, 3), 3) == "[Army] Modern City Shorts I +3");
    // Level zero (a removed enhancement) returns the clean base name.
    assert(Reinforced(polluted, 0) == "[Army] Modern City Shorts I");
    // Existing levels are replaced, not appended.
    assert(Reinforced("钢剑 +2", 4) == "钢剑 +4");
    assert(Reinforced("钢剑 (上等)", 1) == "钢剑 +1");
    // Names that merely look numeric or bracketed stay untouched.
    assert(StripDecorations("铁剑 +") == "铁剑 +");
    assert(StripDecorations("铁剑 +1a") == "铁剑 +1a");
    assert(StripDecorations("药水 (2) (3)") == "药水 (2) (3)"); // engine markers have no digits-only body
    assert(StripDecorations("未命名") == "未命名");
    // The sync skips a name that already means the level, marker and all.
    assert(AlreadyReinforced("钢剑 +1 (上等)", "钢剑 +1"));
    assert(!AlreadyReinforced("钢剑 +1 (上等)", "钢剑 +2"));
    return 0;
}

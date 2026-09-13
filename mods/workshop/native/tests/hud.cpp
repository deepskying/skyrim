#include "../../../durability-manager/native/src/hud_rules.h"
#include <cassert>
#include <limits>

int main()
{
    using durability_hud::ShouldDisplay;
    assert(ShouldDisplay(true, true, 100, 100, 30));
    assert(ShouldDisplay(true, true, 0, 100, 30));
    assert(!ShouldDisplay(false, true, 10, 100, 30));
    assert(!ShouldDisplay(false, false, 10, 100, 30));
    assert(ShouldDisplay(true, false, 29.9F, 100, 30));
    assert(!ShouldDisplay(true, false, 30, 100, 30));
    assert(!ShouldDisplay(true, false, 80, 100, 30));
    assert(ShouldDisplay(true, false, 55, 200, 30));
    assert(!ShouldDisplay(true, false, 55, 200, 20));
    assert(!ShouldDisplay(true, true, 10, 0, 30));
    assert(!ShouldDisplay(true, true, std::numeric_limits<float>::infinity(), 100, 30));
    assert(!ShouldDisplay(true, true, 10, std::numeric_limits<float>::quiet_NaN(), 30));
}

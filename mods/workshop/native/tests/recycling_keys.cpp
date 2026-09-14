#include "../../../durability-manager/native/src/recycling_keys.h"
#include "../../../durability-manager/native/src/recycling_rules.h"
#include <cassert>
int main() {
    using recycling::StackPart;
    const std::vector<StackPart> live{{101, 1, 1}, {102, 2, 1}, {103, 3, 4}};
    const auto merged = recycling::ResolveStack(2, 6, {{102, 2, 1}, {101, 1, 1}}, live);
    assert(merged && merged->size() == 2 && merged->front().extra == 101);
    // An untagged row can coexist with an enchanted/tempered row of the same form.
    const auto plain = recycling::ResolveStack(3, 9, {}, live);
    assert(plain && plain->size() == 1 && plain->front().extra == 0 && plain->front().count == 3);
    const auto mixed = recycling::ResolveStack(5, 9, {{101, 1, 1}, {102, 2, 1}}, live);
    assert(mixed && mixed->size() == 3 && mixed->back().count == 3);
    assert(!recycling::ResolveStack(4, 9, {}, live)); // Cannot borrow from another row.
    assert(!recycling::ResolveStack(1, 6, {{104, 4, 1}}, live)); // Stale identity.
    assert(!recycling::ResolveStack(1, 6, {{101, 9, 1}}, live)); // Reused pointer.
    assert(!recycling::ResolveStack(2, 6, {{101, 1, 1}, {101, 1, 1}}, live));
    assert(!recycling::ResolveStack(3, 6, {{103, 3, 4}}, live));
    assert(!recycling::ResolveStack(0, 6, {}, live));
    recycling::Capture capture;
    assert(capture.Feed(0xB8, true).key == 0);
    auto result = capture.Feed(0xB8, false);
    assert(result.key == 0xB8 && result.safety == 0xB8);
    capture.Reset(); capture.Feed(0x9D, true);
    result = capture.Feed(0xD3, true);
    assert(result.key == 0xD3 && result.safety == 0x9D);
    capture.Reset(); capture.Feed(0x2A, true); capture.Feed(0xB8, true);
    assert(capture.Feed(0x20, true).invalid);
    assert(capture.Feed(0xB8, false).key == 0);
    assert(capture.Feed(0x2A, false).invalid);
    assert(capture.Feed(0x1C, true).invalid);
    result = capture.Feed(0x20, true);
    assert(result.key == 0x20 && result.safety == 0x20);
    assert(!recycling::Allowed(0) && !recycling::Allowed(0x100));
    assert(recycling::ConsumeCount(9, true, false) == 0);
    assert(recycling::ConsumeCount(29, true, true) == 20);
    assert(recycling::ConsumeCount(29, true, false) == 10);
    assert(recycling::ConsumeCount(5, false, false) == 1);
    assert(recycling::ConsumeCount(15000, false, true) == 10000);
    assert(recycling::ConsumeCount(-1, false, true) == 0);
    assert(recycling::RecipeYield(6, 3, 1) == 1);
    assert(recycling::RecipeYield(1, 100, 10) == 0);
    assert(recycling::RecipeYield(10, 0, 1) == 0);
    assert(recycling::RecipeYield(INT32_MAX, 1, INT32_MAX) == 0);
    assert(recycling::WeightedYield(35, .05, 2) == 4);
    assert(recycling::WeightedYield(0, .01, 3) == 3);
    assert(recycling::WeightedYield(-1, .1, 1) == 0);
    assert(recycling::WeightedYield(INFINITY, .1, 1) == 0);
}

#include "../src/input_rules.h"
#include <cassert>

int main()
{
    using companion::IsOpeningChord;
    assert(IsOpeningChord(0x21, true, true, false, false, true, false));
    assert(!IsOpeningChord(0x21, true, false, false, false, true, false)); // plain F
    assert(!IsOpeningChord(0x21, false, true, false, false, true, false)); // repeat/release
    assert(!IsOpeningChord(0x21, true, true, true, false, true, false));
    assert(!IsOpeningChord(0x21, true, true, false, true, true, false));
    assert(!IsOpeningChord(0x21, true, true, false, false, false, false)); // menus/loading
    assert(!IsOpeningChord(0x21, true, true, false, false, true, true)); // another focused view
    assert(!IsOpeningChord(0x1F, true, true, false, false, true, false)); // old Shift+S
    assert(!IsOpeningChord(0x1E, true, true, false, false, true, false)); // old Shift+A
}

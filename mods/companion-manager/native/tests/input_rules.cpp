#include "../src/input_rules.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "check.h"

int main()
{
    using companion::IsOpeningChord;
    CHECK(IsOpeningChord(0x21, true, true, false, false, true, false));
    CHECK(!IsOpeningChord(0x21, true, false, false, false, true, false)); // plain F
    CHECK(!IsOpeningChord(0x21, false, true, false, false, true, false)); // repeat/release
    CHECK(!IsOpeningChord(0x21, true, true, true, false, true, false));
    CHECK(!IsOpeningChord(0x21, true, true, false, true, true, false));
    CHECK(!IsOpeningChord(0x21, true, true, false, false, false, false)); // menus/loading
    CHECK(!IsOpeningChord(0x21, true, true, false, false, true, true)); // another focused view
    CHECK(!IsOpeningChord(0x1F, true, true, false, false, true, false)); // old Shift+S
    CHECK(!IsOpeningChord(0x1E, true, true, false, false, true, false)); // old Shift+A
}

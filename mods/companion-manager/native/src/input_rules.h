#pragma once
#include <cstdint>

namespace companion
{
// Pure matching rule shared by the native sink and regression tests.
constexpr bool IsOpeningChord(std::uint32_t key, bool down, bool shift, bool ctrl, bool alt, bool gameplay,
                              bool otherFocus)
{
    return key == 0x21 && down && shift && !ctrl && !alt && gameplay && !otherFocus;
}
} // namespace companion

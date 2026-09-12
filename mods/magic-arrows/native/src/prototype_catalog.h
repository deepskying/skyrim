#pragma once
namespace prototypes {
struct Entry {RE::FormID id;const char* family;};
inline constexpr std::array<Entry,12> entries{{
    {0x800,"blood"},
    {0x810,"holy"},
    {0x820,"soul"},
    {0xA00,"fire"},
    {0xA10,"ice"},
    {0xA20,"shock"},
    {0xA30,"poison"},
    {0xA40,"wind"},
    {0xA50,"water"},
    {0xA60,"earth"},
    {0xA70,"dark"},
    {0xA80,"arcane"},
}};
}

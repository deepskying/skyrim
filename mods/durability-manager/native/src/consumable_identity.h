#pragma once
#include <cstdint>
namespace workshop_potions {
// Dynamic forms have no plugin-local identity. Never dereference their missing TESFile.
template <class File>
constexpr std::uint32_t SourceLocalID(std::uint32_t id, const File* file) {
    if (!file || (id >> 24) == 0xFF) return 0;
    return id & (file->IsLight() ? 0xFFFu : 0xFFFFFFu);
}
}

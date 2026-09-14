#pragma once
#include <cstdint>
#include <set>

namespace recycling {
inline bool Modifier(std::uint32_t key) {
    return key == 0x2A || key == 0x36 || key == 0x1D || key == 0x9D || key == 0x38 || key == 0xB8;
}
inline bool Allowed(std::uint32_t key) {
    // Letters, function keys, Delete, Space, and left/right modifiers.
    return (key >= 0x10 && key <= 0x19) || (key >= 0x1E && key <= 0x26) ||
        (key >= 0x2C && key <= 0x32) || (key >= 0x3B && key <= 0x44) ||
        key == 0x57 || key == 0x58 || key == 0xD3 || key == 0x39 || Modifier(key);
}
struct Result { std::uint32_t key = 0, safety = 0; bool invalid = false; };
class Capture {
public:
    void Reset() { modifiers.clear(); rejected = false; }
    Result Feed(std::uint32_t key, bool down) {
        if (Modifier(key)) {
            if (down) { modifiers.insert(key); if (modifiers.size() > 1) rejected = true; return {}; }
            const bool held = modifiers.erase(key) != 0;
            if (!held || !modifiers.empty()) return {};
            if (rejected) { Reset(); return {0, 0, true}; }
            return {key, key};
        }
        if (!down) return {};
        if (modifiers.empty()) rejected = false;
        if (!Allowed(key) || rejected || modifiers.size() > 1) { rejected = true; return {0, 0, true}; }
        return {key, modifiers.empty() ? key : *modifiers.begin()};
    }
private:
    std::set<std::uint32_t> modifiers;
    bool rejected = false;
};
}

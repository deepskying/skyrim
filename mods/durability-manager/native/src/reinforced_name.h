#pragma once
#include <algorithm>
#include <string>
#include <string_view>

// Item names carry two kinds of trailing decoration: our own " +N" enhancement level and the
// tempering marker the game appends at display time (" (上等)"). Both can end up inside the stored
// name, and a sync that treats a decorated name as its baseline stacks them until the length cap.
// Every name the mod writes is therefore built from the *stripped* name, which makes re-applying a
// level idempotent: strip(strip(x) + " +N") == strip(x).
namespace durability::name {

inline std::string StripDecorations(std::string a_name)
{
    for (;;)
    {
        const auto end = a_name.find_last_not_of(' ');
        if (end == std::string::npos) return {};
        a_name.resize(end + 1);
        if (a_name.size() > 3 && a_name.back() == ')')
        {
            const auto open = a_name.rfind(" (");
            if (open == std::string::npos) return a_name;
            const auto inner = a_name.substr(open + 2, a_name.size() - open - 3);
            if (inner.empty() || inner.find('(') != std::string::npos || inner.find(')') != std::string::npos) return a_name;
            a_name.resize(open);
            continue;
        }
        const auto plus = a_name.rfind(" +");
        if (plus == std::string::npos) return a_name;
        const auto digits = a_name.substr(plus + 2);
        if (digits.empty() || !std::all_of(digits.begin(), digits.end(), [](unsigned char c) { return c >= '0' && c <= '9'; }))
            return a_name;
        a_name.resize(plus);
    }
}

inline std::string Reinforced(std::string_view a_baseline, std::uint32_t a_level)
{
    auto clean = StripDecorations(std::string(a_baseline));
    if (a_level == 0) return clean;
    return clean + " +" + std::to_string(a_level);
}

// True when the stored name already means this level, so the sync can leave it alone instead of
// rewriting the same name (and fighting another writer) on every update.
inline bool AlreadyReinforced(std::string_view a_stored, std::string_view a_target)
{
    return StripDecorations(std::string(a_stored)) == StripDecorations(std::string(a_target));
}

} // namespace durability::name

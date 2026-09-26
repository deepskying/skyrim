#pragma once
#include <algorithm>
#include <cstdint>
#include <string>
#include <string_view>
#include <utility>

// Item names carry two kinds of trailing decoration: our own " +N" enhancement level and the
// tempering marker the game appends at display time (" (上等)"). Both can end up inside the stored
// name, and a sync that treats a decorated name as its baseline stacks them until the length cap.
// Every name the mod writes is therefore built from the *stripped* name, which makes re-applying a
// level idempotent: strip(strip(x) + " +N") == strip(x).
//
// The two decorations are stripped separately because they mean different things: the engine marker
// is display-only noise that may be present or absent for the same stored name, while our "+N" is
// state the mod owns and has to keep in sync with the stored level.
namespace durability::name {
namespace detail {

[[nodiscard]] inline bool IsDigits(std::string_view a_text)
{
    return !a_text.empty() &&
           std::all_of(a_text.begin(), a_text.end(), [](unsigned char a_character) { return a_character >= '0' && a_character <= '9'; });
}

// Decoration checks only ever look at the end of the real name.
inline void TrimTrailingSpaces(std::string& a_name)
{
    const auto end = a_name.find_last_not_of(' ');
    a_name.resize(end == std::string::npos ? 0 : end + 1);
}

// Removes one trailing engine quality marker (" (上等)", " (Superior)", ...). Its body must carry
// more than digits: the engine never numbers its markers, while real names such as "药水 (2)" keep
// their numbers.
[[nodiscard]] inline bool StripQualityMarker(std::string& a_name)
{
    if (a_name.size() <= 3 || a_name.back() != ')') return false;
    const auto open = a_name.rfind(" (");
    if (open == std::string::npos) return false;
    const std::string_view inner{ a_name.data() + open + 2, a_name.size() - open - 3 };
    if (inner.empty() || inner.find('(') != std::string_view::npos || inner.find(')') != std::string_view::npos) return false;
    if (IsDigits(inner)) return false;
    a_name.resize(open);
    return true;
}

// Removes one trailing " +N" level suffix. A bare "+" or a name such as "铁剑 +1a" stays untouched.
[[nodiscard]] inline bool StripLevelSuffix(std::string& a_name)
{
    const auto plus = a_name.rfind(" +");
    if (plus == std::string::npos) return false;
    if (!IsDigits(std::string_view{ a_name }.substr(plus + 2))) return false;
    a_name.resize(plus);
    return true;
}

} // namespace detail

// Drops every engine quality marker. Our own level stays, so two names can be compared by the level
// they claim even when the engine rendered one of them with a marker.
inline std::string StripQualityMarkers(std::string a_name)
{
    for (;;)
    {
        detail::TrimTrailingSpaces(a_name);
        if (!detail::StripQualityMarker(a_name)) return a_name;
    }
}

// Drops both decorations, however many rounds of them a name accumulated.
inline std::string StripDecorations(std::string a_name)
{
    for (;;)
    {
        detail::TrimTrailingSpaces(a_name);
        if (detail::StripQualityMarker(a_name)) continue;
        if (detail::StripLevelSuffix(a_name)) continue;
        return a_name;
    }
}

// Repairs a *stored* baseline. Only a name that already carries our own "+N" is rebuilt from its
// stripped form, so a half-broken save is fixed while a name the player typed by hand - including
// its own brackets - is left alone.
inline std::string CleanStoredBaseline(std::string a_name)
{
    if (StripQualityMarkers(a_name) == StripDecorations(a_name)) return a_name;
    return StripDecorations(std::move(a_name));
}

inline std::string Reinforced(std::string_view a_baseline, std::uint32_t a_level)
{
    auto clean = StripDecorations(std::string(a_baseline));
    if (a_level == 0) return clean;
    return clean + " +" + std::to_string(a_level);
}

// True when the stored name already means this level, so the sync can leave it alone instead of
// rewriting the same name (and fighting another writer) on every update. The engine marker is
// ignored, our own level is not: a stale "+1" has to be rewritten once the item reaches "+4".
inline bool AlreadyReinforced(std::string_view a_stored, std::string_view a_target)
{
    return StripQualityMarkers(std::string(a_stored)) == StripQualityMarkers(std::string(a_target));
}

} // namespace durability::name

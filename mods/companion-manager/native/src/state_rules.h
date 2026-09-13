#pragma once
#include "capacity.h"
#include <cmath>
#include <nlohmann/json.hpp>
#include <stdexcept>
namespace companion::rules
{
using json = nlohmann::json;
// Only a completed vanilla human recruitment is eligible for automatic handoff.
constexpr bool DialogueRecruitmentReady(bool dialogueOpen, bool teammate, bool usable,
                                       bool ownedSlot, std::size_t managedCount, float followerCount)
{
    return !dialogueOpen && teammate && usable && followerCount == 1.0f &&
           (ownedSlot || managedCount < MemberCapacity);
}
// Existing teammates can be enrolled without clearing aliases owned by another quest.
// Unrelated NPCs with quest packages must still be left to their quest.
constexpr bool ForeignPackagesBlockRecruitment(bool teammate, bool foreignPackages)
{
    return foreignPackages && !teammate;
}
inline bool Integer(const json &v, std::int64_t lo, std::int64_t hi)
{
    return v.is_number_integer() && v >= lo && v <= hi;
}
inline void ApplyGrowthDefault(json &member, bool scalesWithPlayer, bool joining = false)
{
    if (member.at("active").get<bool>() && (joining || !member.value("growthDefaultApplied", false)))
    {
        member["raised"] = scalesWithPlayer && member.at("originalMax").get<int>() > 0;
        member["growthDefaultApplied"] = true;
    }
}
constexpr int GrowthCap(int original, bool raised)
{
    return raised && original > 0 && original < 300 ? 300 : original;
}
inline bool ValidSetting(const std::string &key, const json &value)
{
    if (key == "opacity")
        return Integer(value, 55, 96);
    if (key == "font")
        return Integer(value, 14, 18);
    if (key == "distance")
        return Integer(value, 0, 2);
    return (key == "notifications" || key == "sandbox") && value.is_boolean();
}
inline void ValidateSettings(const json &prefs)
{
    for (const auto *key : {"opacity", "font", "distance", "sandbox", "notifications"})
        if (!prefs.contains(key) || !ValidSetting(key, prefs.at(key)))
            throw std::runtime_error("Invalid settings");
}
inline void ValidateMember(const json &row)
{
    if (!Integer(row.at("slot"), 0, MemberCapacity - 1))
        throw std::runtime_error("Invalid slot");
    for (const auto *key : {"actor", "base"})
        if (!Integer(row.at(key), 1, 0xFFFFFFFF))
            throw std::runtime_error("Invalid form ID");
    for (const auto *key :
         {"active", "waiting", "sandbox", "leash", "passive", "raised", "protection", "originalEssential"})
        if (!row.at(key).is_boolean())
            throw std::runtime_error("Invalid flag");
    for (const auto *key : {"originalWaiting", "aggression", "confidence"})
        if (!row.at(key).is_number() || !std::isfinite(row.at(key).get<float>()))
            throw std::runtime_error("Invalid actor value");
    if (!Integer(row.at("originalMax"), 0, 65535))
        throw std::runtime_error("Invalid level cap");
    if (row.contains("growthDefaultApplied") && !row.at("growthDefaultApplied").is_boolean())
        throw std::runtime_error("Invalid growth preference");
    if (!row.at("home").is_string() || row.at("home").get_ref<const std::string &>().size() > 4096)
        throw std::runtime_error("Invalid home");
    for (const auto *key : {"learned", "disabled", "outfit"})
    {
        if (!row.at(key).is_array() || row.at(key).size() > 4096)
            throw std::runtime_error("Invalid form list");
        for (const auto &id : row.at(key))
            if (!Integer(id, 1, 0xFFFFFFFF))
                throw std::runtime_error("Invalid form ID");
    }
}
constexpr int Mode(bool active, bool waiting, bool sandbox, bool home, int distance)
{
    if (!active)
        return home ? 5 : 0;
    if (waiting)
        return sandbox ? 4 : 3;
    return distance * 10 + (sandbox ? 2 : 1);
}
} // namespace companion::rules

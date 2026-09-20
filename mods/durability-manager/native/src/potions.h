#pragma once
#include <nlohmann/json.hpp>
#include <atomic>
#include "consumable_identity.h"

namespace workshop_potions {
using json = nlohmann::json;
inline std::atomic<bool> active = false;
inline bool foodMode = false;
inline std::uint64_t token = 0;
inline ULONGLONG lastUse = 0;
inline void Reset() { active = false; ++token; lastUse = 0; }
inline bool IsPotion(RE::AlchemyItem* item) {
    return item && !item->IsDeleted() && !item->IsIgnored() && item->IsFood() == foodMode;
}
inline std::string Name(RE::TESForm* item) {
    const char* name = item ? item->GetName() : nullptr;
    return name && *name ? name : "未命名药水";
}
inline std::string Trait(RE::EffectSetting* effect, RE::ActorValue av) {
    using AV = RE::ActorValue;
    using A = RE::EffectArchetype;
    if (effect->IsDetrimental() || effect->IsHostile()) return "harmful";
    const auto archetype = effect->GetArchetype();
    if (archetype == A::kCureDisease) return "cure-disease";
    if (archetype == A::kCurePoison) return "cure-poison";
    if (archetype == A::kInvisibility) return "invisibility";
    if (archetype == A::kNightEye) return "night-eye";
    // Scripted effects are not assumed to restore/fortify an actor value.
    if (archetype != A::kValueModifier && archetype != A::kPeakValueModifier && archetype != A::kDualValueModifier) return "other";
    if (av == AV::kHealth || av == AV::kMagicka || av == AV::kStamina) {
        const auto prefix = archetype == A::kPeakValueModifier ? "fortify-" : "restore-";
        return std::string(prefix) + (av == AV::kHealth ? "health" : av == AV::kMagicka ? "magicka" : "stamina");
    }
    switch (av) {
    case AV::kHealRate: case AV::kHealRateMult: return "regen-health";
    case AV::kMagickaRate: case AV::kMagickaRateMult: return "regen-magicka";
    case AV::kStaminaRate: case AV::kStaminaRateMult: return "regen-stamina";
    case AV::kResistFire: return "resist-fire";
    case AV::kResistFrost: return "resist-frost";
    case AV::kResistShock: return "resist-shock";
    case AV::kResistMagic: return "resist-magic";
    case AV::kPoisonResist: return "resist-poison";
    case AV::kResistDisease: return "resist-disease";
    case AV::kDamageResist: return "armor";
    case AV::kCarryWeight: return "carry";
    case AV::kWaterBreathing: return "water-breathing";
    case AV::kSpeedMult: return "speed";
    default: break;
    }
    const int value = static_cast<int>(av);
    if (value >= 6 && value <= 23) return "skill-" + std::to_string(value - 6);
    if (value >= 96 && value <= 113) return "skill-" + std::to_string(value - 96);
    if (value >= 135 && value <= 152) return "skill-" + std::to_string(value - 135);
    return "other";
}
inline json Effects(RE::AlchemyItem* item) {
    json result = json::array();
    using F = RE::EffectSetting::EffectSettingData::Flag;
    for (auto* effect : item->effects) {
        auto* base = effect ? effect->baseEffect : nullptr;
        if (!base || base->data.flags.all(F::kHideInUI)) continue;
        json traits = json::array({Trait(base, base->data.primaryAV)});
        if (base->GetArchetype() == RE::EffectArchetype::kDualValueModifier) {
            auto secondary = Trait(base, base->data.secondaryAV);
            if (secondary != "other" && secondary != traits[0].get<std::string>()) traits.push_back(secondary);
        }
        const float magnitude = effect->GetMagnitude();
        result.push_back({{"id",base->GetFormID()}, {"name",Name(base)}, {"traits",traits},
            {"description",base->magicItemDescription.c_str() ? base->magicItemDescription.c_str() : ""},
            {"magnitude",std::isfinite(magnitude) ? magnitude : 0.f}, {"duration",effect->GetDuration()},
            {"area",effect->GetArea()}, {"hasMagnitude",!base->data.flags.all(F::kNoMagnitude)},
            {"hasDuration",!base->data.flags.all(F::kNoDuration)},
            {"harmful",base->IsDetrimental() || base->IsHostile()}, {"conditional",effect->conditions.head != nullptr || base->conditions.head != nullptr}});
    }
    return result;
}
inline json Keywords(RE::AlchemyItem* item) {
    json result = json::array();
    for (std::uint32_t i = 0; i < item->numKeywords; ++i) {
        auto* keyword = item->keywords[i];
        if (keyword && keyword->GetFormEditorID()) result.push_back(keyword->GetFormEditorID());
    }
    return result;
}
inline json Snapshot(std::string message = {}, std::uint64_t requestID = 0, bool ok = false) {
    json rows = json::array();
    auto* player = RE::PlayerCharacter::GetSingleton();
    if (player && player->GetParentCell() && player->GetParentCell()->IsAttached()) {
        for (auto& [base, value] : player->GetInventory()) {
            auto* item = base ? base->As<RE::AlchemyItem>() : nullptr;
            auto& [count, entry] = value;
            if (!IsPotion(item) || count <= 0 || !entry) continue;
            const bool quest = entry->IsQuestObject();
            const char* display = entry->GetDisplayName();
            auto* file = item->GetFile(0);
            rows.push_back({{"id",item->GetFormID()}, {"name",display && *display ? display : Name(item)},
                {"localId",SourceLocalID(item->GetFormID(), file)}, {"keywords",Keywords(item)}, {"poison",item->IsPoison()}, {"count",count}, {"weight",entry->GetWeight()}, {"value",entry->GetValue()},
                {"source",file ? std::string(file->GetFilename()) : "自制药水"}, {"effects",Effects(item)},
                {"usable",!item->IsPoison() && !quest && !player->IsDead()}, {"reason",item->IsPoison() ? "请在游戏背包中为武器涂毒" : quest ? "任务物品不可使用" : player->IsDead() ? "角色当前无法使用" : ""}});
        }
    }
    std::sort(rows.begin(),rows.end(),[](const json& a,const json& b) {
        if (a["name"] == b["name"]) return a["id"].get<RE::FormID>() < b["id"].get<RE::FormID>();
        return a["name"].get<std::string>() < b["name"].get<std::string>();
    });
    return {{"items",rows},{"token",++token},{"message",message},{"reply",{{"requestID",requestID},{"ok",ok}}}};
}
inline std::pair<bool,std::string> Drink(RE::FormID id, std::uint64_t expectedToken) {
    if (!active || expectedToken != token) return {false,"物品清单已变化，请重新选择后使用。"};
    ++token; // A snapshot authorizes at most one attempt, including rejected attempts.
    const auto now = GetTickCount64();
    if (now - lastUse < 400) return {false,"操作过快，请稍后再使用。"};
    auto* player = RE::PlayerCharacter::GetSingleton();
    auto* item = RE::TESForm::LookupByID<RE::AlchemyItem>(id);
    if (!player || player->IsDead() || !player->GetParentCell() || !player->GetParentCell()->IsAttached() || !IsPotion(item) || item->IsPoison())
        return {false,"当前无法使用此物品。"};
    auto inventory = player->GetInventory();
    auto it = inventory.find(item);
    if (it == inventory.end() || it->second.first <= 0 || !it->second.second || it->second.second->IsQuestObject())
        return {false,"物品已耗尽或属于任务物品。"};
    const int before = it->second.first;
    const auto name = Name(item);
    lastUse = now;
    // Let the engine apply every effect and consume the item. Never remove it twice.
    const bool accepted = player->DrinkPotion(item, nullptr);
    auto afterInventory = player->GetInventory();
    auto after = afterInventory.find(item);
    const int remaining = after == afterInventory.end() ? 0 : after->second.first;
    logger::info("Potion use id={:08X} accepted={} before={} after={} paused={}",id,accepted,before,remaining,RE::UI::GetSingleton()->GameIsPaused());
    if (accepted && remaining == before - 1) return {true,std::string(foodMode ? "已食用：" : "已饮用：") + name};
    return {false,"游戏未确认单次使用完成，已刷新库存；请检查当前效果。"};
}
}

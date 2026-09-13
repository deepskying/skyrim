#include "snapshot.h"
#include "manager.h"
#include "spell_details.h"
#include <cmath>
#include <limits>

namespace companion
{
using json = nlohmann::json;
namespace
{
std::string Text(const char *value, const char *fallback)
{
    return value && *value ? value : fallback;
}

std::string ID(RE::FormID id)
{
    return std::format("{:08X}", id);
}

json Resource(RE::Actor *actor, RE::ActorValue value)
{
    const auto current = (std::max)(0.0f, actor->AsActorValueOwner()->GetActorValue(value));
    const auto damage = actor->GetActorValueModifier(RE::ACTOR_VALUE_MODIFIERS::kDamage, value);
    const auto maximum = (std::max)(current, current - damage);
    return json::array({static_cast<int>(std::round(current)), static_cast<int>(std::round(maximum))});
}

const char *School(RE::ActorValue skill)
{
    switch (skill)
    {
    case RE::ActorValue::kAlteration:
        return "变化系";
    case RE::ActorValue::kConjuration:
        return "召唤系";
    case RE::ActorValue::kDestruction:
        return "毁灭系";
    case RE::ActorValue::kIllusion:
        return "幻术系";
    case RE::ActorValue::kRestoration:
        return "恢复系";
    default:
        return "其他";
    }
}

class Spells final : public RE::Actor::ForEachSpellVisitor
{
  public:
    explicit Spells(RE::Actor *actor) : owner(actor)
    {
    }
    RE::BSContainer::ForEachResult Visit(RE::SpellItem *spell) override
    {
        if (!spell || spell->GetSpellType() != RE::MagicSystem::SpellType::kSpell ||
            !seen.insert(spell->GetFormID()).second)
            return RE::BSContainer::ForEachResult::kContinue;
        if (items.size() >= 512)
        {
            truncated = true;
            return RE::BSContainer::ForEachResult::kStop;
        }
        items.push_back({{"id", ID(spell->GetFormID())},
                         {"name", Text(spell->GetFullName(), "未命名法术")},
                         {"school", School(spell->GetAssociatedSkill())},
                         {"description", SpellDescription(spell)},
                         {"cost", (std::max)(0, static_cast<int>(spell->CalculateMagickaCost(owner)))},
                         {"enabled", true}});
        return RE::BSContainer::ForEachResult::kContinue;
    }
    RE::Actor *owner;
    std::unordered_set<RE::FormID> seen;
    json items = json::array();
    bool truncated = false;
};

std::optional<int> Distance(RE::Actor *actor, RE::Actor *player)
{
    const auto sameCell = actor->GetParentCell() && actor->GetParentCell() == player->GetParentCell();
    const auto sameWorld = actor->GetWorldspace() && actor->GetWorldspace() == player->GetWorldspace();
    if (!sameCell && !sameWorld)
        return std::nullopt;
    const auto delta = actor->GetPosition() - player->GetPosition();
    // Skyrim units are approximately 1.428 cm. Cross-world coordinates are not comparable.
    return static_cast<int>(std::round(delta.Length() / 70.0f));
}

json ReadActor(RE::Actor *actor, RE::Actor *player)
{
    const auto base = actor->GetActorBase();
    const auto race = actor->GetRace();
    const auto location = actor->GetCurrentLocation();
    const auto cell = actor->GetParentCell();
    const auto distance = Distance(actor, player);
    Spells spells(actor);
    actor->VisitSpells(spells);
    for (const auto id : DisabledSpells(actor->GetFormID()))
    {
        if (auto *spell = RE::TESForm::LookupByID<RE::SpellItem>(id))
        {
            bool exists = false;
            for (auto &s : spells.items)
                if (s["id"] == ID(id))
                {
                    s["enabled"] = false;
                    exists = true;
                }
            if (!exists && spells.items.size() < 512)
                spells.items.push_back({{"id", ID(id)},
                                        {"name", Text(spell->GetFullName(), "未命名法术")},
                                        {"school", School(spell->GetAssociatedSkill())},
                                        {"description", SpellDescription(spell)},
                                        {"cost", (std::max)(0, static_cast<int>(spell->CalculateMagickaCost(actor)))},
                                        {"enabled", false}});
        }
    }
    json gear = json::array();
    bool gearTruncated = false;
    for (auto &[item, entry] : actor->GetInventory())
    {
        if (!item || entry.first <= 0)
            continue;
        if (gear.size() >= 512)
        {
            gearTruncated = true;
            break;
        }
        gear.push_back({{"id", ID(item->GetFormID())},
                        {"name", Text(entry.second ? entry.second->GetDisplayName() : item->GetName(), "未命名物品")},
                        {"slot", item->As<RE::TESObjectWEAP>()   ? "武器"
                                 : item->As<RE::TESObjectARMO>() ? "护甲"
                                                                 : "物品"},
                        {"count", entry.first},
                        {"quest", entry.second && entry.second->IsQuestObject()},
                        {"equipped", entry.second && entry.second->IsWorn()}});
    }
    std::sort(gear.begin(), gear.end(), [](const json &a, const json &b) {
        if (a["equipped"] != b["equipped"])
            return a["equipped"].get<bool>();
        return a["id"].get<std::string>() < b["id"].get<std::string>();
    });
    json row = {{"id", ID(actor->GetFormID())},
                {"name", Text(actor->GetDisplayFullName(), "未命名人物")},
                {"en", ID(actor->GetFormID())},
                {"role", Text(base && base->npcClass ? base->npcClass->GetFullName() : nullptr, "未分类")},
                {"race", Text(race ? race->GetFullName() : nullptr, "未知种族")},
                {"level", actor->GetLevel()},
                {"mark", actor->IsPlayerTeammate() ? "伴" : "人"},
                {"tint", actor->IsPlayerTeammate() ? "mint" : "blue"},
                {"group", actor->IsPlayerTeammate() ? "party" : "nearby"},
                {"limited", true},
                {"waiting", actor->AsActorValueOwner()->GetActorValue(RE::ActorValue::kWaitingForPlayer) > 0},
                {"passive", false},
                {"sandbox", false},
                {"leash", false},
                {"essential", actor->IsEssential()},
                {"distance", distance ? json(*distance) : json(nullptr)},
                {"home", "未设置"},
                {"location", Text(location ? location->GetFullName()
                                  : cell   ? cell->GetFullName()
                                           : nullptr,
                                  "未知位置")},
                {"health", Resource(actor, RE::ActorValue::kHealth)},
                {"magicka", Resource(actor, RE::ActorValue::kMagicka)},
                {"stamina", Resource(actor, RE::ActorValue::kStamina)},
                {"spells", spells.items},
                {"gear", gear},
                {"raised", false},
                {"inCombat", actor->IsInCombat()},
                {"levelCap", base && base->HasPCLevelMult() ? json(base->actorData.calcLevelMax) : json(nullptr)},
                {"detailsTruncated", gearTruncated || spells.truncated}};
    DescribeActor(actor, row);
    row["skills"] = json::array();
    for (const auto &[name, value] :
         std::array<std::pair<const char *, RE::ActorValue>, 18>{{{"单手", RE::ActorValue::kOneHanded},
                                                                  {"双手", RE::ActorValue::kTwoHanded},
                                                                  {"弓术", RE::ActorValue::kArchery},
                                                                  {"重甲", RE::ActorValue::kHeavyArmor},
                                                                  {"轻甲", RE::ActorValue::kLightArmor},
                                                                  {"毁灭", RE::ActorValue::kDestruction},
                                                                  {"恢复", RE::ActorValue::kRestoration},
                                                                  {"召唤", RE::ActorValue::kConjuration},
                                                                  {"格挡", RE::ActorValue::kBlock},
                                                                  {"变化", RE::ActorValue::kAlteration},
                                                                  {"幻术", RE::ActorValue::kIllusion},
                                                                  {"附魔", RE::ActorValue::kEnchanting},
                                                                  {"锻造", RE::ActorValue::kSmithing},
                                                                  {"炼金", RE::ActorValue::kAlchemy},
                                                                  {"潜行", RE::ActorValue::kSneak},
                                                                  {"开锁", RE::ActorValue::kLockpicking},
                                                                  {"扒窃", RE::ActorValue::kPickpocket},
                                                                  {"口才", RE::ActorValue::kSpeech}}})
        row["skills"].push_back({{"name", name}, {"value", actor->AsActorValueOwner()->GetActorValue(value)}});
    row["resistances"] = json::array();
    for (const auto &[name, value] :
         std::array<std::pair<const char *, RE::ActorValue>, 4>{{{"火焰", RE::ActorValue::kResistFire},
                                                                 {"冰霜", RE::ActorValue::kResistFrost},
                                                                 {"闪电", RE::ActorValue::kResistShock},
                                                                 {"魔法", RE::ActorValue::kResistMagic}}})
        row["resistances"].push_back({{"name", name}, {"value", actor->AsActorValueOwner()->GetActorValue(value)}});
    row["attributes"] = json::array();
    for (const auto &[name, value] :
         std::array<std::pair<const char *, RE::ActorValue>, 6>{{{"护甲值", RE::ActorValue::kDamageResist},
                                                                 {"负重上限", RE::ActorValue::kCarryWeight},
                                                                 {"移动速度倍率", RE::ActorValue::kSpeedMult},
                                                                 {"生命恢复", RE::ActorValue::kHealRate},
                                                                 {"法力恢复", RE::ActorValue::kMagickaRate},
                                                                 {"耐力恢复", RE::ActorValue::kStaminaRate}}})
        row["attributes"].push_back({{"name", name}, {"value", actor->AsActorValueOwner()->GetActorValue(value)}});
    return row;
}
} // namespace

json CollectSnapshot()
{
    json result = {{"version", 2},
                   {"mode", "game"},
                   {"followers", json::array()},
                   {"location", "未进入游戏"},
                   {"truncated", false},
                   {"ready", false},
                   {"session", SessionToken()},
                   {"settings", ManagerSettings()},
                   {"inventory", json::array()},
                   {"managerAvailable", Controller() != nullptr}};
    auto *player = RE::PlayerCharacter::GetSingleton();
    auto *processes = RE::ProcessLists::GetSingleton();
    if (!player || !player->GetParentCell() || !processes)
        return result;
    const auto location = player->GetCurrentLocation();
    result["location"] = Text(location ? location->GetFullName() : player->GetParentCell()->GetFullName(), "当前位置");
    result["ready"] = true;
    result["inventory"] = PlayerInventory();
    std::vector<RE::Actor *> candidates;
    std::unordered_set<RE::FormID> seen;
    const auto registered = RegisteredActors();
    const std::unordered_set<RE::FormID> owned(registered.begin(), registered.end());
    for (const auto id : registered)
        if (auto *actor = RE::TESForm::LookupByID<RE::Actor>(id))
            if (actor->GetActorBase() && seen.insert(id).second)
                candidates.push_back(actor);
    processes->ForAllActors([&](RE::Actor *actor) {
        if (!actor || actor == player || !actor->GetActorBase() || actor->IsDisabled() || actor->IsDead() ||
            !seen.insert(actor->GetFormID()).second)
            return RE::BSContainer::ForEachResult::kContinue;
        const auto distance = Distance(actor, player);
        if (actor->IsPlayerTeammate() || (distance && *distance <= 60))
            candidates.push_back(actor);
        return RE::BSContainer::ForEachResult::kContinue;
    });
    std::sort(candidates.begin(), candidates.end(), [&](RE::Actor *a, RE::Actor *b) {
        if (owned.contains(a->GetFormID()) != owned.contains(b->GetFormID()))
            return owned.contains(a->GetFormID());
        if (a->IsPlayerTeammate() != b->IsPlayerTeammate())
            return a->IsPlayerTeammate();
        const auto da = Distance(a, player).value_or((std::numeric_limits<int>::max)());
        const auto db = Distance(b, player).value_or((std::numeric_limits<int>::max)());
        return da == db ? a->GetFormID() < b->GetFormID() : da < db;
    });
    if (candidates.size() > 64)
    {
        candidates.resize(64);
        result["truncated"] = true;
    }
    for (auto *actor : candidates)
        result["followers"].push_back(ReadActor(actor, player));
    return result;
}
} // namespace companion

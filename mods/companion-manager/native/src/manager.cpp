#include "manager.h"
#include "spell_details.h"
#include "state_rules.h"
#include <atomic>
#include <charconv>
#include <chrono>
#include <thread>

namespace companion
{
namespace
{
constexpr std::size_t slots = 32;
RE::TESQuest *quest = nullptr;
RE::TESFaction *modeFaction = nullptr;
std::recursive_mutex lock;
std::unordered_map<RE::FormID, json> members;
json settings = {{"opacity", 82}, {"font", 15}, {"notifications", true}, {"sandbox", true}, {"distance", 1}};
std::atomic_bool ready = false, tickQueued = false;
bool commandPending = false;
std::unordered_set<std::string> requests;
std::uint64_t epoch = 1;
std::string token = std::to_string(GetTickCount64()) + "-1";
std::jthread worker;

std::string ID(RE::FormID id)
{
    return std::format("{:08X}", id);
}
RE::FormID ParseID(const json &request, const char *key)
{
    const auto value = request.at(key).get<std::string>();
    if (value.size() != 8)
        throw std::runtime_error("无效的对象标识");
    RE::FormID result = 0;
    const auto parsed = std::from_chars(value.data(), value.data() + value.size(), result, 16);
    if (parsed.ec != std::errc{} || parsed.ptr != value.data() + value.size() || !result)
        throw std::runtime_error("无效的对象标识");
    return result;
}
RE::BGSRefAlias *Alias(int slot)
{
    if (!quest)
        return nullptr;
    for (auto *alias : quest->aliases)
        if (alias && alias->aliasID == static_cast<unsigned>(slot) && alias->GetVMTypeID() == RE::BGSRefAlias::VMTYPEID)
            return static_cast<RE::BGSRefAlias *>(alias);
    return nullptr;
}
RE::Actor *Actor(RE::FormID id)
{
    return RE::TESForm::LookupByID<RE::Actor>(id);
}
bool Knows(RE::Actor *actor, RE::SpellItem *spell)
{
    struct Finder : RE::Actor::ForEachSpellVisitor
    {
        RE::SpellItem *target;
        bool found = false;
        explicit Finder(RE::SpellItem *s) : target(s)
        {
        }
        RE::BSContainer::ForEachResult Visit(RE::SpellItem *s) override
        {
            if (s == target)
            {
                found = true;
                return RE::BSContainer::ForEachResult::kStop;
            }
            return RE::BSContainer::ForEachResult::kContinue;
        }
    } finder(spell);
    actor->VisitSpells(finder);
    return finder.found;
}
bool Contains(const json &array, RE::FormID id)
{
    return std::find(array.begin(), array.end(), id) != array.end();
}
void Erase(json &array, RE::FormID id)
{
    auto i = std::find(array.begin(), array.end(), id);
    if (i != array.end())
        array.erase(i);
}
void CheckActor(RE::Actor *actor)
{
    if (!actor || actor == RE::PlayerCharacter::GetSingleton() || actor->IsDisabled() || actor->IsDead())
        throw std::runtime_error("人物当前不可操作");
    if (actor->GetCurrentScene())
        throw std::runtime_error("人物正在参与剧情场景，请稍后再试");
}
std::string RecruitReason(RE::Actor *actor)
{
    if (!quest || !modeFaction)
        return "管理数据插件未加载";
    if (!actor || !actor->GetActorBase() || actor->IsDead() || actor->IsDisabled())
        return "人物当前不可用";
    if (actor->GetCurrentScene())
        return "人物正在参与剧情场景";
    if (actor->IsChild() || !actor->GetActorBase()->IsUnique())
        return "仅支持非儿童的独立 NPC，避免修改共享角色模板";
    if (actor->IsHostileToActor(RE::PlayerCharacter::GetSingleton()) || actor->IsInCombat())
        return "无法招募敌对或交战中的人物";
    if (auto *extra = actor->extraList.GetByType<RE::ExtraAliasInstanceArray>())
    {
        RE::BSReadLockGuard read(extra->lock);
        for (auto *instance : extra->aliases)
            if (instance && instance->quest != quest && instance->instancedPackages &&
                rules::ForeignPackagesBlockRecruitment(actor->IsPlayerTeammate(),
                                                        !instance->instancedPackages->empty()))
                return "人物仍受其他任务 AI 包控制，暂不接管";
    }
    return {};
}
int FreeSlot()
{
    for (int i = 0; i < static_cast<int>(slots); ++i)
    {
        auto *alias = Alias(i);
        if (!alias || alias->GetReference())
            continue;
        bool used = false;
        for (const auto &[id, r] : members)
        {
            static_cast<void>(id);
            if (r["slot"] == i)
            {
                used = true;
                break;
            }
        }
        if (!used)
            return i;
    }
    throw std::runtime_error("32 个名册槽位已满，请先从名册中释放一位同伴");
}
class Callback final : public RE::BSScript::IStackCallbackFunctor
{
  public:
    explicit Callback(std::function<void(bool)> fn) : done(std::move(fn))
    {
    }
    void operator()(RE::BSScript::Variable value) override
    {
        const bool ok = value.IsBool() && value.GetBool();
        if (auto *tasks = SKSE::GetTaskInterface())
            tasks->AddTask([fn = std::move(done), ok] { fn(ok); });
    }
    void SetObject(const RE::BSTSmartPointer<RE::BSScript::Object> &) override
    {
    }
    std::function<void(bool)> done;
};
template <class... Args> void Call(const char *name, std::function<void(bool)> done, Args... args)
{
    auto *vm = RE::BSScript::Internal::VirtualMachine::GetSingleton();
    if (!vm || !quest)
    {
        done(false);
        return;
    }
    const auto handle =
        vm->GetObjectHandlePolicy()->GetHandleForObject(static_cast<RE::VMTypeID>(RE::FormType::Quest), quest);
    RE::BSTSmartPointer<RE::BSScript::IStackCallbackFunctor> callback{new Callback(done)};
    if (!vm->DispatchMethodCall(handle, "CMController", name, RE::MakeFunctionArguments(std::move(args)...), callback))
        done(false);
}
int Mode(const json &r)
{
    return rules::Mode(r["active"].get<bool>(), r["waiting"].get<bool>(), r["sandbox"].get<bool>(),
                       !r["home"].get<std::string>().empty(), settings["distance"].get<int>());
}
void Apply(RE::Actor *actor, json &r)
{
    if (!actor || !modeFaction)
        return;
    actor->AddToFaction(modeFaction, static_cast<std::int8_t>(Mode(r)));
    auto *av = actor->AsActorValueOwner();
    av->SetBaseActorValue(RE::ActorValue::kWaitingForPlayer, r["active"].get<bool>()
                                                                 ? (r["waiting"].get<bool>() ? 1.0f : 0.0f)
                                                                 : r["originalWaiting"].get<float>());
    av->SetBaseActorValue(RE::ActorValue::kAggression, r["passive"].get<bool>() ? 0 : r["aggression"].get<float>());
    av->SetBaseActorValue(RE::ActorValue::kConfidence, r["passive"].get<bool>() ? 0 : r["confidence"].get<float>());
    if (r["passive"].get<bool>() && actor->IsInCombat())
        actor->StopCombat();
    auto *base = actor->GetActorBase();
    if (base)
    {
        if (r["protection"].get<bool>())
            base->actorData.actorBaseFlags.set(RE::ACTOR_BASE_DATA::Flag::kEssential);
        else
            base->actorData.actorBaseFlags.reset(RE::ACTOR_BASE_DATA::Flag::kEssential);
    }
    if (base && base->HasPCLevelMult())
    {
        base->actorData.calcLevelMax = static_cast<std::uint16_t>(
            r["raised"].get<bool>() ? (std::max)(r["originalMax"].get<int>(), 300) : r["originalMax"].get<int>());
        static_cast<void>(actor->GetCalcLevel(true));
    }
    for (const auto &value : r["learned"])
    {
        auto *spell = RE::TESForm::LookupByID<RE::SpellItem>(value.get<RE::FormID>());
        if (spell && !Contains(r["disabled"], spell->GetFormID()) && !Knows(actor, spell))
            actor->AddSpell(spell);
    }
    for (const auto &value : r["disabled"])
    {
        auto *spell = RE::TESForm::LookupByID<RE::SpellItem>(value.get<RE::FormID>());
        if (spell && Knows(actor, spell))
            actor->RemoveSpell(spell);
    }
    actor->EvaluatePackage(false, false);
}
void Restore(RE::Actor *actor, const json &r, bool spells)
{
    if (!actor)
        return;
    auto *av = actor->AsActorValueOwner();
    av->SetBaseActorValue(RE::ActorValue::kAggression, r["aggression"].get<float>());
    av->SetBaseActorValue(RE::ActorValue::kConfidence, r["confidence"].get<float>());
    av->SetBaseActorValue(RE::ActorValue::kWaitingForPlayer, r["originalWaiting"].get<float>());
    if (auto *base = actor->GetActorBase())
        base->actorData.calcLevelMax = static_cast<std::uint16_t>(r["originalMax"].get<int>());
    if (modeFaction)
        actor->RemoveFromFaction(modeFaction);
    if (spells)
        for (const auto &v : r["disabled"])
            if (auto *spell = RE::TESForm::LookupByID<RE::SpellItem>(v.get<RE::FormID>()))
                if (!Knows(actor, spell))
                    actor->AddSpell(spell);
    actor->EvaluatePackage(false, false);
}
void Equip(RE::Actor *actor, RE::FormID id, bool equipped)
{
    auto *item = RE::TESForm::LookupByID<RE::TESBoundObject>(id);
    if (!item || (!item->As<RE::TESObjectWEAP>() && !item->As<RE::TESObjectARMO>()))
        throw std::runtime_error("仅武器与护甲支持装备操作");
    if (!actor->Is3DLoaded())
        throw std::runtime_error("请先将人物召回附近，再调整装备");
    auto inventory = actor->GetInventory();
    const auto it = inventory.find(item);
    if (it == inventory.end() || it->second.first <= 0 || !it->second.second)
        throw std::runtime_error("物品已不在人物背包中");
    auto *entry = it->second.second.get();
    if (entry->IsQuestObject())
        throw std::runtime_error("任务物品不允许调整");
    // Ambiguous enchanted/tempered stacks require instance selection; never target a random copy.
    if (it->second.first > 1 && entry->extraLists &&
        std::distance(entry->extraLists->begin(), entry->extraLists->end()) > 1)
        throw std::runtime_error("同类物品包含多个独立实例，请先通过背包交易拆分");
    RE::ExtraDataList *extra = nullptr;
    if (entry->extraLists)
        for (auto *candidate : *entry->extraLists)
            if (candidate && (!extra || candidate->HasType<RE::ExtraWorn>() || candidate->HasType<RE::ExtraWornLeft>()))
                extra = candidate;
    auto *manager = RE::ActorEquipManager::GetSingleton();
    if (!manager)
        throw std::runtime_error("装备管理器未就绪");
    if (equipped)
        manager->EquipObject(actor, item, extra, 1, nullptr, false, true, false, true);
    else
        manager->UnequipObject(actor, item, extra, 1, nullptr, false, true, false, true);
    const auto after = actor->GetInventory();
    const auto found = after.find(item);
    const bool worn = found != after.end() && found->second.second && found->second.second->IsWorn();
    if (worn != equipped)
        throw std::runtime_error("引擎未确认装备变化，请刷新后检查");
}
void Tick()
{
    std::scoped_lock guard(lock);
    if (!ready || commandPending)
        return;
    auto *ui = RE::UI::GetSingleton();
    auto *player = RE::PlayerCharacter::GetSingleton();
    if (!ui || ui->GameIsPaused() || !player || !player->GetParentCell())
        return;
    for (auto &[id, r] : members)
        if (auto *actor = Actor(id))
        {
            if (actor->IsDead() || actor->IsDisabled() || actor->GetCurrentScene())
                continue;
            for (const auto &value : r["disabled"])
                if (auto *spell = RE::TESForm::LookupByID<RE::SpellItem>(value.get<RE::FormID>()))
                    if (Knows(actor, spell))
                        actor->RemoveSpell(spell);
            if (r["passive"].get<bool>() && actor->IsInCombat())
                actor->StopCombat();
            if (r["active"].get<bool>() && !r["waiting"].get<bool>() && r["leash"].get<bool>() &&
                !actor->IsInCombat() && !player->IsInCombat())
            {
                const bool same = actor->GetParentCell() == player->GetParentCell() ||
                                  (actor->GetWorldspace() && actor->GetWorldspace() == player->GetWorldspace());
                if (!same || (actor->GetPosition() - player->GetPosition()).Length() > 7000)
                    actor->MoveTo(player);
            }
        }
}
} // namespace

RE::TESQuest *Controller()
{
    return quest;
}
std::string SessionToken()
{
    std::scoped_lock guard(lock);
    return token;
}
json ManagerSettings()
{
    std::scoped_lock guard(lock);
    return settings;
}
std::vector<RE::FormID> RegisteredActors()
{
    std::scoped_lock guard(lock);
    std::vector<RE::FormID> out;
    for (const auto &[id, r] : members)
    {
        static_cast<void>(r);
        out.push_back(id);
    }
    return out;
}
std::vector<RE::FormID> DisabledSpells(RE::FormID id)
{
    std::scoped_lock guard(lock);
    return members.contains(id) ? members.at(id)["disabled"].get<std::vector<RE::FormID>>() : std::vector<RE::FormID>{};
}

void InitializeManager()
{
    auto *data = RE::TESDataHandler::GetSingleton();
    quest = data->LookupForm<RE::TESQuest>(0x800, "CompanionManager.esp");
    modeFaction = data->LookupForm<RE::TESFaction>(0x801, "CompanionManager.esp");
    if (!quest || !modeFaction)
    {
        logger::error("CompanionManager.esp missing; commands disabled.");
        return;
    }
    quest->Start();
    worker = std::jthread([](std::stop_token stop) {
        while (!stop.stop_requested())
        {
            std::this_thread::sleep_for(std::chrono::seconds(1));
            if (ready && !tickQueued.exchange(true))
                if (auto *tasks = SKSE::GetTaskInterface())
                    tasks->AddTask([] {
                        tickQueued = false;
                        Tick();
                    });
        }
    });
}
void SetGameReady(bool value)
{
    std::scoped_lock guard(lock);
    ready = value;
    commandPending = false;
    requests.clear();
    ++epoch;
    token = std::to_string(GetTickCount64()) + "-" + std::to_string(epoch);
    if (value)
        for (auto &[id, r] : members)
            if (auto *actor = Actor(id))
                Apply(actor, r);
}

void RegisterSerialization()
{
    auto *ser = SKSE::GetSerializationInterface();
    if (!ser)
        return;
    ser->SetUniqueID(0x434D4752); // CMGR, distinct from the old spell manager
    ser->SetSaveCallback([](SKSE::SerializationInterface *s) {
        std::scoped_lock guard(lock);
        json rows = json::array();
        for (const auto &[id, r] : members)
        {
            auto row = r;
            row["actor"] = id;
            rows.push_back(row);
        }
        const auto bytes = json{{"members", rows}, {"settings", settings}}.dump();
        if (bytes.size() > 4 * 1024 * 1024 || !s->OpenRecord(0x44415441, 1) ||
            !s->WriteRecordData(bytes.data(), static_cast<std::uint32_t>(bytes.size())))
            logger::error("Could not save Companion Manager state.");
    });
    ser->SetRevertCallback([](SKSE::SerializationInterface *) {
        std::scoped_lock guard(lock);
        ready = false;
        commandPending = false;
        ++epoch;
        // Base edits are process-wide; restore before the next save is applied.
        for (const auto &[id, r] : members)
        {
            static_cast<void>(id);
            if (auto *base = RE::TESForm::LookupByID<RE::TESNPC>(r["base"].get<RE::FormID>()))
            {
                base->actorData.calcLevelMax = static_cast<std::uint16_t>(r["originalMax"].get<int>());
                if (r["originalEssential"].get<bool>())
                    base->actorData.actorBaseFlags.set(RE::ACTOR_BASE_DATA::Flag::kEssential);
                else
                    base->actorData.actorBaseFlags.reset(RE::ACTOR_BASE_DATA::Flag::kEssential);
            }
        }
        members.clear();
        settings = {{"opacity", 82}, {"font", 15}, {"notifications", true}, {"sandbox", true}, {"distance", 1}};
    });
    ser->SetLoadCallback([](SKSE::SerializationInterface *s) {
        std::scoped_lock guard(lock);
        std::uint32_t type = 0, version = 0, length = 0;
        while (s->GetNextRecordInfo(type, version, length))
        {
            if (type != 0x44415441 || version != 1 || length > 4 * 1024 * 1024)
                continue;
            try
            {
                std::string bytes(length, '\0');
                if (s->ReadRecordData(bytes.data(), length) != length)
                    throw std::runtime_error("Truncated record");
                const auto data = json::parse(bytes);
                const auto &rows = data.at("members");
                if (!rows.is_array() || rows.size() > slots)
                    throw std::runtime_error("Invalid member count");
                std::unordered_map<RE::FormID, json> loaded;
                std::unordered_set<int> usedSlots;
                for (auto row : rows)
                {
                    rules::ValidateMember(row);
                    const int slot = row.at("slot").get<int>();
                    if (!usedSlots.insert(slot).second)
                        throw std::runtime_error("Duplicate slot");
                    RE::FormID actor = 0, base = 0;
                    const bool resolved = s->ResolveFormID(row.at("actor").get<RE::FormID>(), actor) &&
                                          s->ResolveFormID(row.at("base").get<RE::FormID>(), base);
                    for (const auto *key : {"learned", "disabled", "outfit"})
                    {
                        if (!row.at(key).is_array() || row[key].size() > 4096)
                            throw std::runtime_error("Invalid form list");
                        json forms = json::array();
                        for (const auto &old : row[key])
                        {
                            RE::FormID id = 0;
                            if (s->ResolveFormID(old.get<RE::FormID>(), id) && !Contains(forms, id))
                                forms.push_back(id);
                        }
                        row[key] = std::move(forms);
                    }
                    auto *reference = resolved ? Actor(actor) : nullptr;
                    if (reference && reference->GetActorBase() && reference->GetActorBase()->GetFormID() == base)
                    {
                        row["base"] = base;
                        row.erase("actor");
                        if (!loaded.emplace(actor, std::move(row)).second)
                            throw std::runtime_error("Duplicate actor");
                    }
                }
                auto prefs = data.at("settings");
                rules::ValidateSettings(prefs);
                members = std::move(loaded);
                settings = std::move(prefs);
            }
            catch (const std::exception &error)
            {
                logger::error("Rejected invalid co-save: {}", error.what());
            }
        }
    });
}

void DescribeActor(RE::Actor *actor, json &row)
{
    std::scoped_lock guard(lock);
    const auto it = members.find(actor->GetFormID());
    const bool managed = it != members.end();
    row["managed"] = managed;
    row["limited"] = !managed;
    row["canRecruit"] = !managed && RecruitReason(actor).empty();
    row["reason"] = managed ? "" : RecruitReason(actor);
    row["canRaise"] = false;
    row["originalMax"] = 0;
    row["presetCount"] = 0;
    row["dead"] = actor->IsDead();
    row["unavailable"] = actor->IsDisabled() || actor->GetCurrentScene() != nullptr;
    if (!managed)
        return;
    const auto &r = it->second;
    row["group"] = r["active"].get<bool>() ? "party" : "registry";
    for (const auto *key : {"waiting", "sandbox", "leash", "passive", "raised"})
        row[key] = r[key];
    row["essential"] = r["protection"];
    row["home"] = r["home"].get<std::string>().empty() ? "未设置" : r["home"].get<std::string>();
    row["presetCount"] = r["outfit"].size();
    row["originalMax"] = r["originalMax"];
    row["canRaise"] = actor->GetActorBase()->HasPCLevelMult() && r["originalMax"].get<int>() > 0;
}

json PlayerInventory()
{
    json items = json::array();
    auto *player = RE::PlayerCharacter::GetSingleton();
    if (!player)
        return items;
    auto inventory = player->GetInventory();
    std::vector<RE::TESBoundObject *> ordered;
    for (const auto &[item, entry] : inventory)
        if (item && entry.first > 0 && entry.second)
            ordered.push_back(item);
    std::sort(ordered.begin(), ordered.end(), [](auto *a, auto *b) {
        const auto *ba = a->template As<RE::TESObjectBOOK>();
        const auto *bb = b->template As<RE::TESObjectBOOK>();
        const bool sa = ba && ba->TeachesSpell(), sb = bb && bb->TeachesSpell();
        return sa != sb ? sa : a->GetFormID() < b->GetFormID();
    });
    for (auto *item : ordered)
    {
        auto &entry = inventory.at(item);
        if (item && entry.first > 0 && entry.second)
        {
            if (items.size() >= 512)
                break;
            auto *book = item->As<RE::TESObjectBOOK>();
            auto *spell = book && book->TeachesSpell() ? book->GetSpell() : nullptr;
            RE::BSString bookText;
            if (book && spell)
                book->GetDescription(bookText, book);
            items.push_back(
                {{"id", ID(item->GetFormID())},
                 {"name", item->GetName() ? item->GetName() : "未命名物品"},
                 {"count", entry.first},
                 {"quest", entry.second->IsQuestObject()},
                 {"equipped", entry.second->IsWorn()},
                 {"spellId",
                  spell && spell->GetSpellType() == RE::MagicSystem::SpellType::kSpell ? ID(spell->GetFormID()) : ""},
                 {"spellName", spell && spell->GetFullName() ? spell->GetFullName() : ""},
                 {"description", std::string(bookText.c_str()).substr(0, 8192)},
                 {"spellDescription", SpellDescription(spell)},
                 {"school", SpellSchool(spell)},
                 {"cost", spell ? (std::max)(0, static_cast<int>(spell->CalculateMagickaCost(player))) : 0}});
        }
    }
    return items;
}

void ExecuteCommand(const json &request, Completion complete)
{
    std::scoped_lock guard(lock);
    try
    {
        complete = [reply = complete,
                    op = request.value("command", std::string{}),
                    actor = request.value("actorId", std::string{})](bool ok, const std::string &message) {
            logger::info("Command {} actor={} ok={}: {}", op, actor, ok, message);
            reply(ok, message);
        };
        if (!ready || !quest || !modeFaction)
            throw std::runtime_error("管理系统未就绪，请确认 ESP 已启用并进入存档");
        if (request.value("session", std::string{}) != token)
            throw std::runtime_error("存档状态已变化，请刷新后重试");
        if (commandPending)
            throw std::runtime_error("上一条指令仍在执行，请等待结果");
        const auto requestID = request.at("requestId").get<std::string>();
        if (requestID.empty() || requestID.size() > 64 || requests.contains(requestID))
            throw std::runtime_error("重复或无效的指令，未再次执行");
        requests.insert(requestID);
        const auto op = request.at("command").get<std::string>();
        if (op == "settings")
        {
            const auto key = request.at("key").get<std::string>();
            const auto value = request.at("value");
            if (!rules::ValidSetting(key, value))
                throw std::runtime_error("设置项或数值无效");
            settings[key] = value;
            if (key == "distance")
                for (auto &[id, r] : members)
                    if (auto *a = Actor(id))
                        Apply(a, r);
            complete(true, "设置已保存到当前存档");
            return;
        }
        if (op == "group")
        {
            const auto action = request.at("action").get<std::string>();
            if (action != "wait" && action != "follow" && action != "summon")
                throw std::runtime_error("队伍指令无效");
            int count = 0, skipped = 0;
            for (auto &[id, r] : members)
                if (r["active"].get<bool>())
                {
                    auto *a = Actor(id);
                    if (!a || a->IsDead() || a->IsDisabled() || a->GetCurrentScene())
                    {
                        ++skipped;
                        continue;
                    }
                    if (action == "summon")
                        a->MoveTo(RE::PlayerCharacter::GetSingleton());
                    else
                    {
                        r["waiting"] = action == "wait";
                        Apply(a, r);
                    }
                    ++count;
                }
            complete(true, std::format("已处理 {} 位同伴，跳过 {} 位不可操作人物", count, skipped));
            return;
        }
        const auto id = ParseID(request, "actorId");
        auto *actor = Actor(id);
        if (op == "forget" && actor && members.contains(id))
        {
        }
        else
            CheckActor(actor);
        const auto thisEpoch = epoch;
        auto finish = [complete, thisEpoch](bool ok, const std::string &message) {
            std::scoped_lock guard(lock);
            if (thisEpoch != epoch)
                return;
            commandPending = false;
            complete(ok, message);
        };
        if (op == "recruit" || op == "adopt")
        {
            if (op == "adopt" && (members.contains(id) || !actor->IsPlayerTeammate()))
                throw std::runtime_error("队伍状态已变化，请刷新后重新选择人物");
            if (op == "recruit" && !members.contains(id) && actor->IsPlayerTeammate())
                throw std::runtime_error("此人物已经在队伍中，请使用「纳入同行管理」");
            const bool newlyTracked = !members.contains(id);
            logger::info("Enrolling actor={} teammate={} new={}", ID(id), actor->IsPlayerTeammate(), newlyTracked);
            if (!members.contains(id))
            {
                const auto reason = RecruitReason(actor);
                if (!reason.empty())
                    throw std::runtime_error(reason);
                auto *av = actor->AsActorValueOwner();
                auto *base = actor->GetActorBase();
                members[id] = {{"slot", FreeSlot()},
                               {"base", base->GetFormID()},
                               {"active", false},
                               {"waiting", false},
                               {"sandbox", settings["sandbox"]},
                               {"leash", true},
                               {"passive", false},
                               {"raised", false},
                               {"protection", base->IsEssential()},
                               {"originalEssential", base->IsEssential()},
                               {"originalMax", base->actorData.calcLevelMax},
                               {"originalWaiting", av->GetBaseActorValue(RE::ActorValue::kWaitingForPlayer)},
                               {"aggression", av->GetBaseActorValue(RE::ActorValue::kAggression)},
                               {"confidence", av->GetBaseActorValue(RE::ActorValue::kConfidence)},
                               {"home", ""},
                               {"learned", json::array()},
                               {"disabled", json::array()},
                               {"outfit", json::array()}};
            }
            else if (members[id]["active"].get<bool>())
                throw std::runtime_error("人物已经在队伍中");
            else if (const auto reason = RecruitReason(actor); !reason.empty())
                throw std::runtime_error(reason);
            const auto slot = members[id]["slot"].get<int>();
            commandPending = true;
            Call(
                "BindSlot",
                [id, slot, finish, thisEpoch, newlyTracked](bool ok) {
                    std::scoped_lock guard(lock);
                    if (thisEpoch != epoch)
                        return;
                    ok = ok && Alias(slot) && Alias(slot)->GetActorReference() == Actor(id);
                    if (ok && members.contains(id))
                    {
                        auto &r = members[id];
                        r["active"] = true;
                        r["waiting"] = false;
                        Apply(Actor(id), r);
                    }
                    else if (newlyTracked)
                        members.erase(id);
                    finish(ok, ok ? "已纳入同行管理，行为与法术操作已开放"
                                  : "接管失败，未取得随从槽位；请确认 Scripts/CMController.pex 未被覆盖");
                },
                actor, slot, true);
            return;
        }
        auto found = members.find(id);
        if (found == members.end())
            throw std::runtime_error("请先点击人物详情顶部的「纳入同行管理」");
        auto &r = found->second;
        const int slot = r["slot"].get<int>();
        if (!Alias(slot) || Alias(slot)->GetActorReference() != actor)
            throw std::runtime_error("人物槽位与存档记录不匹配，请重新载入完整存档");
        if (op == "dismiss")
        {
            commandPending = true;
            Call(
                "BindSlot",
                [id, finish, thisEpoch](bool ok) {
                    std::scoped_lock guard(lock);
                    if (thisEpoch != epoch)
                        return;
                    if (ok)
                    {
                        auto &r = members.at(id);
                        r["active"] = false;
                        r["waiting"] = false;
                        Apply(Actor(id), r);
                    }
                    finish(ok, ok ? "已离队并保留在名册中" : "离队失败");
                },
                actor, slot, false);
            return;
        }
        if (op == "forget")
        {
            if (r["active"].get<bool>() && !actor->IsDead())
                throw std::runtime_error("请先解散，再释放名册记录");
            commandPending = true;
            const bool essential = r["originalEssential"].get<bool>();
            Call(
                "SetProtection",
                [id, slot, finish, thisEpoch](bool ok) {
                    std::scoped_lock guard(lock);
                    if (thisEpoch != epoch)
                        return;
                    if (!ok)
                    {
                        finish(false, "恢复保护状态失败，已保留名册记录");
                        return;
                    }
                    Restore(Actor(id), members.at(id), true);
                    Call(
                        "ReleaseSlot",
                        [id, finish, thisEpoch](bool released) {
                            std::scoped_lock guard(lock);
                            if (thisEpoch != epoch)
                                return;
                            if (released)
                                members.erase(id);
                            finish(released, released ? "已释放名册并恢复原始行为，已学会的法术保留"
                                                      : "释放槽位失败，已保留记录");
                        },
                        slot);
                },
                slot, essential);
            return;
        }
        if (op == "home")
        {
            const bool clear = request.at("clear").get<bool>();
            const auto *player = RE::PlayerCharacter::GetSingleton();
            const auto *loc = player->GetCurrentLocation();
            const auto *cell = player->GetParentCell();
            std::string name;
            if (!clear)
            {
                if (loc && loc->GetFullName())
                    name = loc->GetFullName();
                if (name.empty() && cell && cell->GetFullName())
                    name = cell->GetFullName();
                if (name.empty())
                    name = "自定义居所";
            }
            commandPending = true;
            Call(
                "SetHome",
                [id, name, finish, thisEpoch](bool ok) {
                    std::scoped_lock guard(lock);
                    if (thisEpoch != epoch)
                        return;
                    if (ok)
                    {
                        auto &r = members.at(id);
                        r["home"] = name;
                        Apply(Actor(id), r);
                    }
                    finish(ok, ok ? "居所已更新" : "居所设置失败");
                },
                slot, clear);
            return;
        }
        if (op == "protection")
        {
            const bool enabled = request.at("value").get<bool>();
            commandPending = true;
            Call(
                "SetProtection",
                [id, enabled, finish, thisEpoch](bool ok) {
                    std::scoped_lock guard(lock);
                    if (thisEpoch != epoch)
                        return;
                    if (ok)
                        members.at(id)["protection"] = enabled;
                    finish(ok, ok ? "死亡保护已更新" : "保护状态更新失败");
                },
                slot, enabled);
            return;
        }
        if (op == "wait" || op == "sandbox" || op == "leash" || op == "passive" || op == "levelCap")
        {
            const bool value = request.at("value").get<bool>();
            const char *key = op == "wait" ? "waiting" : op == "levelCap" ? "raised" : op.c_str();
            if (op == "levelCap" && (!actor->GetActorBase()->HasPCLevelMult() || r["originalMax"].get<int>() == 0))
                throw std::runtime_error("此人物不适用等级上限覆盖");
            r[key] = value;
            Apply(actor, r);
            complete(true, "人物设置已更新");
            return;
        }
        if (op == "summon")
        {
            actor->MoveTo(RE::PlayerCharacter::GetSingleton());
            complete(true, "已召回，队伍归属未改变");
            return;
        }
        if (op == "teach")
        {
            const auto bookID = ParseID(request, "entityId");
            auto *book = RE::TESForm::LookupByID<RE::TESObjectBOOK>(bookID);
            auto *spell = book && book->TeachesSpell() ? book->GetSpell() : nullptr;
            if (!spell || spell->GetSpellType() != RE::MagicSystem::SpellType::kSpell)
                throw std::runtime_error("所选物品不是可学习的法术书");
            if (Knows(actor, spell) || Contains(r["disabled"], spell->GetFormID()))
                throw std::runtime_error("此人物已经学会该法术");
            auto *player = RE::PlayerCharacter::GetSingleton();
            auto inv = player->GetInventory();
            const auto it = inv.find(book);
            if (it == inv.end() || it->second.first < 1 || !it->second.second || it->second.second->IsQuestObject())
                throw std::runtime_error("法术书不可用或属于任务物品");
            if (!actor->AddSpell(spell) || !Knows(actor, spell))
                throw std::runtime_error("学习失败，未消耗法术书");
            const auto before = it->second.first;
            player->RemoveItem(book, 1, RE::ITEM_REMOVE_REASON::kRemove, nullptr, nullptr);
            const auto after = player->GetInventory();
            const int count = after.contains(book) ? after.at(book).first : 0;
            if (count != before - 1)
            {
                actor->RemoveSpell(spell);
                throw std::runtime_error("法术书扣除未确认，已撤回教学");
            }
            r["learned"].push_back(spell->GetFormID());
            complete(true, "已传授法术并消耗一本法术书");
            return;
        }
        if (op == "spell")
        {
            const auto spellID = ParseID(request, "entityId");
            auto *spell = RE::TESForm::LookupByID<RE::SpellItem>(spellID);
            const bool enabled = request.at("value").get<bool>();
            if (!spell || spell->GetSpellType() != RE::MagicSystem::SpellType::kSpell)
                throw std::runtime_error("法术无效");
            if (enabled)
            {
                if (!Contains(r["disabled"], spellID))
                    throw std::runtime_error("此法术未被本模组禁用");
                actor->AddSpell(spell);
                if (!Knows(actor, spell))
                    throw std::runtime_error("恢复法术失败");
                Erase(r["disabled"], spellID);
            }
            else
            {
                if (!Knows(actor, spell))
                    throw std::runtime_error("人物并未掌握此法术");
                actor->RemoveSpell(spell);
                if (Knows(actor, spell))
                    throw std::runtime_error("禁用法术失败");
                if (!Contains(r["disabled"], spellID))
                    r["disabled"].push_back(spellID);
            }
            complete(true, enabled ? "法术已恢复" : "法术已禁用，可随时恢复");
            return;
        }
        if (op == "equip")
        {
            Equip(actor, ParseID(request, "entityId"), request.at("value").get<bool>());
            complete(true, "装备状态已更新");
            return;
        }
        if (op == "transfer")
        {
            auto *item = RE::TESForm::LookupByID<RE::TESBoundObject>(ParseID(request, "entityId"));
            const int count = request.at("count").get<int>();
            if (!item || count < 1 || count > 10000)
                throw std::runtime_error("物品或数量无效");
            const bool give = request.at("give").get<bool>();
            RE::Actor *from = give ? RE::PlayerCharacter::GetSingleton() : actor;
            RE::Actor *to = give ? actor : RE::PlayerCharacter::GetSingleton();
            auto inv = from->GetInventory();
            const auto it = inv.find(item);
            if (it == inv.end() || it->second.first < count || !it->second.second)
                throw std::runtime_error("物品数量不足");
            if (it->second.second->IsQuestObject() || it->second.second->IsWorn())
                throw std::runtime_error("任务物品或已装备物品不能直接转移");
            RE::ExtraDataList *extra = nullptr;
            if (it->second.second->extraLists && !it->second.second->extraLists->empty())
            {
                if (it->second.first != 1 || count != 1 ||
                    std::distance(it->second.second->extraLists->begin(), it->second.second->extraLists->end()) != 1)
                    throw std::runtime_error("同类物品有多个实例，请通过背包交易拆分后转移");
                extra = it->second.second->extraLists->front();
            }
            const auto destination = to->GetInventory();
            const auto beforeTo = destination.contains(item) ? destination.at(item).first : 0;
            const auto before = it->second.first;
            from->RemoveItem(item, count, RE::ITEM_REMOVE_REASON::kStoreInContainer, extra, to);
            const auto after = from->GetInventory();
            const int remain = after.contains(item) ? after.at(item).first : 0;
            const auto received = to->GetInventory();
            const auto afterTo = received.contains(item) ? received.at(item).first : 0;
            if (remain != before - count || afterTo != beforeTo + count)
                throw std::runtime_error("物品转移未完整确认，请检查双方背包，不要重复点击");
            complete(true, "物品已转移");
            return;
        }
        if (op == "saveOutfit")
        {
            r["outfit"] = json::array();
            for (const auto &[item, entry] : actor->GetInventory())
                if (item && entry.second && entry.second->IsWorn())
                    r["outfit"].push_back(item->GetFormID());
            complete(true, "当前穿戴已保存为个人套装");
            return;
        }
        if (op == "applyOutfit")
        {
            if (r["outfit"].empty())
                throw std::runtime_error("请先保存一套穿戴");
            const auto inventory = actor->GetInventory();
            for (const auto &value : r["outfit"])
            {
                auto *item = RE::TESForm::LookupByID<RE::TESBoundObject>(value.get<RE::FormID>());
                if (!item || !inventory.contains(item) || inventory.at(item).first < 1)
                    throw std::runtime_error("套装物品缺失，未开始换装");
            }
            int done = 0, failed = 0;
            for (const auto &[item, entry] : inventory)
                if (item && entry.second && entry.second->IsWorn() && !Contains(r["outfit"], item->GetFormID()))
                    try
                    {
                        Equip(actor, item->GetFormID(), false);
                    }
                    catch (const std::exception &)
                    {
                        ++failed;
                    }
            for (const auto &value : r["outfit"])
                try
                {
                    Equip(actor, value.get<RE::FormID>(), true);
                    ++done;
                }
                catch (const std::exception &)
                {
                    ++failed;
                }
            complete(failed == 0, std::format("套装已装备 {} 件，{} 件缺失或不可操作", done, failed));
            return;
        }
        throw std::runtime_error("未知指令");
    }
    catch (const std::exception &error)
    {
        complete(false, error.what());
    }
}
} // namespace companion

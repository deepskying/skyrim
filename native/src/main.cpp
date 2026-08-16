#include "PrismaUI_API.h"
#include "input_handler.h"

namespace
{
    using json = nlohmann::json;

    PRISMA_UI_API::IVPrismaUI1* g_prisma = nullptr;
    PrismaView g_view = 0;
    using TaughtSpellMap = std::unordered_map<RE::FormID, std::unordered_set<RE::FormID>>;
    TaughtSpellMap g_taughtSpells;
    std::mutex g_taughtSpellsLock;

    constexpr std::uint32_t FourCC(char a, char b, char c, char d)
    {
        return static_cast<std::uint32_t>(a) |
               (static_cast<std::uint32_t>(b) << 8) |
               (static_cast<std::uint32_t>(c) << 16) |
               (static_cast<std::uint32_t>(d) << 24);
    }

    constexpr std::uint32_t kSerializationID = FourCC('F', 'S', 'B', 'M');
    constexpr std::uint32_t kRecordType = FourCC('S', 'P', 'L', 'S');
    constexpr std::uint32_t kRecordVersion = 1;
    constexpr std::uint32_t kMaxFollowersPerSave = 2048;
    constexpr std::uint32_t kMaxSpellsPerFollower = 1024;

    [[nodiscard]] std::string NormalizeKeyName(std::string a_value)
    {
        a_value.erase(std::remove_if(a_value.begin(), a_value.end(), [](unsigned char a_character) {
            return std::isspace(a_character) != 0;
        }), a_value.end());
        std::transform(a_value.begin(), a_value.end(), a_value.begin(), [](unsigned char a_character) {
            return static_cast<char>(std::toupper(a_character));
        });
        return a_value;
    }

    [[nodiscard]] std::optional<std::uint32_t> ParseKeyCode(const std::string& a_value)
    {
        const auto key = NormalizeKeyName(a_value);
        static constexpr std::array<std::uint32_t, 26> letterScanCodes{
            0x1E, 0x30, 0x2E, 0x20, 0x12, 0x21, 0x22, 0x23, 0x17, 0x24, 0x25, 0x26, 0x32,
            0x31, 0x18, 0x19, 0x10, 0x13, 0x1F, 0x14, 0x16, 0x2F, 0x11, 0x2D, 0x15, 0x2C
        };
        if (key.size() == 1 && key[0] >= 'A' && key[0] <= 'Z') return letterScanCodes[key[0] - 'A'];
        if (key.size() == 1 && key[0] >= '1' && key[0] <= '9') return 0x02 + (key[0] - '1');
        if (key == "0") return 0x0B;
        if (key == "ESC" || key == "ESCAPE") return 0x01;
        if (key == "SPACE") return 0x39;
        if (key == "TAB") return 0x0F;
        if (key == "ENTER") return 0x1C;
        if (key == "F11") return 0x57;
        if (key == "F12") return 0x58;
        if (key.size() == 2 && key[0] == 'F' && key[1] >= '1' && key[1] <= '9') return 0x3A + (key[1] - '0');
        if (key.size() == 3 && key == "F10") return 0x44;
        try {
            std::size_t charactersRead = 0;
            const auto code = std::stoul(key, &charactersRead, 0);
            if (charactersRead == key.size() && code <= 0xFF) return static_cast<std::uint32_t>(code);
        }
        catch (const std::exception&) {}
        return std::nullopt;
    }

    [[nodiscard]] bool ParseConfigBool(const std::string& a_value, bool a_fallback)
    {
        const auto value = NormalizeKeyName(a_value);
        if (value == "TRUE" || value == "YES" || value == "ON" || value == "1") return true;
        if (value == "FALSE" || value == "NO" || value == "OFF" || value == "0") return false;
        return a_fallback;
    }

    [[nodiscard]] std::string DescribeHotkey(const HotkeyConfig& a_hotkey)
    {
        std::string description;
        if (a_hotkey.requireCtrl) description += "Ctrl+";
        if (a_hotkey.requireAlt) description += "Alt+";
        if (a_hotkey.requireShift) description += "Shift+";
        description += "scan code 0x";
        char buffer[3]{};
        std::snprintf(buffer, sizeof(buffer), "%02X", a_hotkey.keyCode);
        description += buffer;
        return description;
    }

    [[nodiscard]] HotkeyConfig LoadHotkeyConfig()
    {
        HotkeyConfig hotkey;
        try {
            const auto modulePath = REL::Module::get().filePath();
            const auto configPath = std::filesystem::path(modulePath.data()).parent_path() / "Data" / "SKSE" / "Plugins" / "FollowerSpellbookManager.ini";
            std::ifstream configFile(configPath);
            if (!configFile) {
                logger::warn("Hotkey configuration was not found at {}; using Shift+S.", configPath.string());
                return hotkey;
            }

            bool inHotkeySection = false;
            std::string line;
            while (std::getline(configFile, line)) {
                if (const auto comment = line.find_first_of(";#"); comment != std::string::npos) line.erase(comment);
                const auto normalizedLine = NormalizeKeyName(line);
                if (normalizedLine.empty()) continue;
                if (normalizedLine.front() == '[' && normalizedLine.back() == ']') {
                    inHotkeySection = normalizedLine == "[HOTKEY]";
                    continue;
                }
                if (!inHotkeySection) continue;

                const auto separator = line.find('=');
                if (separator == std::string::npos) continue;
                const auto setting = NormalizeKeyName(line.substr(0, separator));
                const auto value = line.substr(separator + 1);
                if (setting == "KEY") {
                    if (const auto parsed = ParseKeyCode(value)) {
                        hotkey.keyCode = *parsed;
                    } else {
                        logger::warn("Invalid Hotkey.Key '{}' in {}; using S.", value, configPath.string());
                    }
                } else if (setting == "SHIFT") {
                    hotkey.requireShift = ParseConfigBool(value, hotkey.requireShift);
                } else if (setting == "CTRL") {
                    hotkey.requireCtrl = ParseConfigBool(value, hotkey.requireCtrl);
                } else if (setting == "ALT") {
                    hotkey.requireAlt = ParseConfigBool(value, hotkey.requireAlt);
                }
            }
            logger::info("Follower Spellbook Manager hotkey: {} (read from {}).", DescribeHotkey(hotkey), configPath.string());
        }
        catch (const std::exception& error) {
            logger::warn("Could not read FollowerSpellbookManager.ini; using Shift+S. {}", error.what());
        }
        return hotkey;
    }

    [[nodiscard]] std::string SchoolName(RE::ActorValue a_skill)
    {
        switch (a_skill) {
        case RE::ActorValue::kAlteration: return "Alteration";
        case RE::ActorValue::kConjuration: return "Conjuration";
        case RE::ActorValue::kDestruction: return "Destruction";
        case RE::ActorValue::kIllusion: return "Illusion";
        case RE::ActorValue::kRestoration: return "Restoration";
        default: return "Other";
        }
    }

    class SpellCollector final : public RE::Actor::ForEachSpellVisitor
    {
    public:
        explicit SpellCollector(RE::Actor* a_actor) : _actor(a_actor) {}

        RE::BSContainer::ForEachResult Visit(RE::SpellItem* a_spell) override
        {
            if (!a_spell || a_spell->GetSpellType() != RE::MagicSystem::SpellType::kSpell) {
                return RE::BSContainer::ForEachResult::kContinue;
            }
            _spells.push_back({
                { "id", a_spell->GetFormID() },
                { "name", a_spell->GetFullName() ? a_spell->GetFullName() : "Unnamed spell" },
                { "school", SchoolName(a_spell->GetAssociatedSkill()) },
                { "cost", static_cast<int>(a_spell->CalculateMagickaCost(_actor)) }
            });
            return RE::BSContainer::ForEachResult::kContinue;
        }

        [[nodiscard]] const json& Spells() const { return _spells; }

    private:
        RE::Actor* _actor;
        json _spells = json::array();
    };

    [[nodiscard]] bool KnowsSpell(RE::Actor* a_actor, RE::SpellItem* a_spell)
    {
        if (!a_actor || !a_spell) return false;
        class Finder final : public RE::Actor::ForEachSpellVisitor
        {
        public:
            explicit Finder(RE::SpellItem* a_target) : target(a_target) {}
            RE::BSContainer::ForEachResult Visit(RE::SpellItem* a_spell) override
            {
                if (a_spell == target) {
                    found = true;
                    return RE::BSContainer::ForEachResult::kStop;
                }
                return RE::BSContainer::ForEachResult::kContinue;
            }
            RE::SpellItem* target;
            bool found = false;
        } finder(a_spell);
        a_actor->VisitSpells(finder);
        return finder.found;
    }

    void TrackTaughtSpell(RE::Actor* a_actor, RE::SpellItem* a_spell)
    {
        if (!a_actor || !a_spell) return;
        std::scoped_lock lock(g_taughtSpellsLock);
        g_taughtSpells[a_actor->GetFormID()].insert(a_spell->GetFormID());
    }

    void ReapplyTrackedSpells(RE::Actor* a_actor)
    {
        if (!a_actor) return;
        std::vector<RE::FormID> spellIDs;
        {
            std::scoped_lock lock(g_taughtSpellsLock);
            const auto found = g_taughtSpells.find(a_actor->GetFormID());
            if (found == g_taughtSpells.end()) return;
            spellIDs.assign(found->second.begin(), found->second.end());
        }
        for (const auto spellID : spellIDs) {
            const auto spell = RE::TESForm::LookupByID<RE::SpellItem>(spellID);
            if (spell && !KnowsSpell(a_actor, spell)) a_actor->AddSpell(spell);
        }
    }

    void ReapplyAllTrackedSpells()
    {
        TaughtSpellMap saved;
        {
            std::scoped_lock lock(g_taughtSpellsLock);
            saved = g_taughtSpells;
        }
        for (const auto& [actorID, spellIDs] : saved) {
            const auto actor = RE::TESForm::LookupByID<RE::Actor>(actorID);
            if (actor && actor->IsPlayerTeammate()) ReapplyTrackedSpells(actor);
        }
    }

    void SaveTaughtSpells(SKSE::SerializationInterface* a_serialization)
    {
        TaughtSpellMap saved;
        {
            std::scoped_lock lock(g_taughtSpellsLock);
            saved = g_taughtSpells;
        }
        if (!a_serialization->OpenRecord(kRecordType, kRecordVersion)) return;
        const auto followerCount = static_cast<std::uint32_t>(saved.size());
        if (!a_serialization->WriteRecordData(followerCount)) return;
        for (const auto& [actorID, spellIDs] : saved) {
            const auto spellCount = static_cast<std::uint32_t>(spellIDs.size());
            if (!a_serialization->WriteRecordData(actorID) || !a_serialization->WriteRecordData(spellCount)) return;
            for (const auto spellID : spellIDs) {
                if (!a_serialization->WriteRecordData(spellID)) return;
            }
        }
    }

    void LoadTaughtSpells(SKSE::SerializationInterface* a_serialization)
    {
        TaughtSpellMap restored;
        std::uint32_t type = 0;
        std::uint32_t version = 0;
        std::uint32_t length = 0;
        while (a_serialization->GetNextRecordInfo(type, version, length)) {
            if (type != kRecordType || version != kRecordVersion) {
                std::vector<std::byte> ignored(length);
                a_serialization->ReadRecordData(ignored.data(), length);
                continue;
            }

            std::uint32_t followerCount = 0;
            if (a_serialization->ReadRecordData(followerCount) != sizeof(followerCount) || followerCount > kMaxFollowersPerSave) break;
            for (std::uint32_t i = 0; i < followerCount; ++i) {
                RE::FormID oldActorID = 0;
                std::uint32_t spellCount = 0;
                if (a_serialization->ReadRecordData(oldActorID) != sizeof(oldActorID) ||
                    a_serialization->ReadRecordData(spellCount) != sizeof(spellCount) ||
                    spellCount > kMaxSpellsPerFollower) {
                    break;
                }
                RE::FormID actorID = 0;
                const bool actorResolved = a_serialization->ResolveFormID(oldActorID, actorID);
                for (std::uint32_t j = 0; j < spellCount; ++j) {
                    RE::FormID oldSpellID = 0;
                    if (a_serialization->ReadRecordData(oldSpellID) != sizeof(oldSpellID)) break;
                    RE::FormID spellID = 0;
                    if (actorResolved && a_serialization->ResolveFormID(oldSpellID, spellID)) restored[actorID].insert(spellID);
                }
            }
        }
        std::scoped_lock lock(g_taughtSpellsLock);
        g_taughtSpells = std::move(restored);
    }

    void RevertTaughtSpells(SKSE::SerializationInterface*)
    {
        std::scoped_lock lock(g_taughtSpellsLock);
        g_taughtSpells.clear();
    }

    [[nodiscard]] json CollectFollowers()
    {
        json followers = json::array();
        std::unordered_set<RE::FormID> seen;
        const auto player = RE::PlayerCharacter::GetSingleton();
        const auto processes = RE::ProcessLists::GetSingleton();
        if (!player || !processes) return followers;

        processes->ForAllActors([&](RE::Actor* a_actor) {
            if (!a_actor || a_actor == player || !a_actor->IsPlayerTeammate() || !seen.insert(a_actor->GetFormID()).second) {
                return RE::BSContainer::ForEachResult::kContinue;
            }
            ReapplyTrackedSpells(a_actor);
            SpellCollector spells(a_actor);
            a_actor->VisitSpells(spells);
            followers.push_back({
                { "id", a_actor->GetFormID() },
                { "name", a_actor->GetDisplayFullName() ? a_actor->GetDisplayFullName() : "Unnamed follower" },
                { "maxMagicka", (std::max)(0, static_cast<int>(a_actor->AsActorValueOwner()->GetPermanentActorValue(RE::ActorValue::kMagicka))) },
                { "spells", spells.Spells() }
            });
            return RE::BSContainer::ForEachResult::kContinue;
        });
        return followers;
    }

    [[nodiscard]] json CollectTomes()
    {
        json tomes = json::array();
        const auto player = RE::PlayerCharacter::GetSingleton();
        if (!player) return tomes;

        for (const auto& [item, entry] : player->GetInventory()) {
            const auto book = item ? item->As<RE::TESObjectBOOK>() : nullptr;
            if (!book || entry.first <= 0 || !book->TeachesSpell()) continue;
            const auto spell = book->GetSpell();
            if (!spell || spell->GetSpellType() != RE::MagicSystem::SpellType::kSpell) continue;
            tomes.push_back({
                { "id", book->GetFormID() },
                { "name", book->GetFullName() ? book->GetFullName() : "Unnamed tome" },
                { "spellId", spell->GetFormID() },
                { "spellName", spell->GetFullName() ? spell->GetFullName() : "Unnamed spell" },
                { "school", SchoolName(spell->GetAssociatedSkill()) },
                { "cost", static_cast<int>(spell->CalculateMagickaCost(player)) },
                { "count", entry.first }
            });
        }
        return tomes;
    }

    void SendState(std::string_view a_message = {})
    {
        if (!g_prisma || !g_view) return;
        const json state = {
            { "followers", CollectFollowers() },
            { "tomes", CollectTomes() },
            { "message", a_message }
        };
        const auto payload = state.dump();
        const auto script = "window.FollowerSpellbook && window.FollowerSpellbook.receiveState(" + payload + ");";
        g_prisma->Invoke(g_view, script.c_str());
    }

    void LearnTome(const json& a_request)
    {
        const auto actorID = a_request.value("actorId", 0u);
        const auto bookID = a_request.value("tomeId", 0u);
        const auto actor = RE::TESForm::LookupByID<RE::Actor>(actorID);
        const auto book = RE::TESForm::LookupByID<RE::TESObjectBOOK>(bookID);
        const auto player = RE::PlayerCharacter::GetSingleton();

        if (!actor || !book || !player || !actor->IsPlayerTeammate()) {
            SendState("The selected follower or spell tome is no longer available.");
            return;
        }
        const auto spell = book->GetSpell();
        if (!spell || !book->TeachesSpell() || spell->GetSpellType() != RE::MagicSystem::SpellType::kSpell) {
            SendState("That item is not a spell tome.");
            return;
        }
        if (KnowsSpell(actor, spell)) {
            SendState("This follower already knows that spell.");
            return;
        }

        const auto inventory = player->GetInventory();
        const auto found = inventory.find(book);
        if (found == inventory.end() || found->second.first < 1) {
            SendState("You no longer have this spell tome.");
            return;
        }
        if (!actor->AddSpell(spell)) {
            SendState("The follower could not learn that spell.");
            return;
        }

        const auto previousCount = found->second.first;
        player->RemoveItem(book, 1, RE::ITEM_REMOVE_REASON::kRemove, nullptr, nullptr);
        const auto afterRemoval = player->GetInventory();
        const auto after = afterRemoval.find(book);
        const auto remainingCount = after == afterRemoval.end() ? 0 : after->second.first;
        if (remainingCount >= previousCount) {
            actor->RemoveSpell(spell);
            SendState("The spell tome could not be consumed, so the lesson was cancelled.");
            return;
        }
        TrackTaughtSpell(actor, spell);
        SendState(std::string(actor->GetDisplayFullName()) + " learned " + spell->GetFullName() + ".");
    }

    void HandleUIAction(const char* a_data)
    {
        try {
            const auto request = json::parse(a_data ? a_data : "{}");
            const auto type = request.value("type", "");
            if (type == "learn") LearnTome(request);
            else if (type == "close") {
                g_prisma->Unfocus(g_view);
                g_prisma->Hide(g_view);
            }
            else SendState();
        }
        catch (const std::exception& error) {
            logger::warn("Rejected Prisma UI request: {}", error.what());
            SendState("The panel request was invalid.");
        }
    }

    void TogglePanel()
    {
        if (!g_prisma || !g_view) return;
        if (g_prisma->HasFocus(g_view)) {
            g_prisma->Unfocus(g_view);
            g_prisma->Hide(g_view);
            return;
        }
        g_prisma->Show(g_view);
        g_prisma->Focus(g_view, true);
        SendState();
    }

    bool ClosePanel()
    {
        if (!g_prisma || !g_view || !g_prisma->HasFocus(g_view)) return false;
        g_prisma->Unfocus(g_view);
        g_prisma->Hide(g_view);
        return true;
    }

    void OnSKSEMessage(SKSE::MessagingInterface::Message* a_message)
    {
        if (a_message->type == SKSE::MessagingInterface::kPostLoadGame) {
            if (const auto tasks = SKSE::GetTaskInterface()) tasks->AddTask(ReapplyAllTrackedSpells);
            return;
        }
        if (a_message->type != SKSE::MessagingInterface::kDataLoaded) return;

        g_prisma = PRISMA_UI_API::RequestPluginAPI();
        if (!g_prisma) {
            logger::critical("Prisma UI v1 is unavailable; Follower Spellbook Manager will remain disabled.");
            return;
        }
        g_view = g_prisma->CreateView("FollowerSpellbookManager/index.html", [](PrismaView) { SendState(); });
        g_prisma->RegisterJSListener(g_view, "followerSpellbookAction", HandleUIAction);
        g_prisma->Hide(g_view);

        auto input = InputHandler::GetSingleton();
        input->SetHotkey(LoadHotkeyConfig());
        input->SetToggleCallback(TogglePanel);
        input->SetEscapeCallback(ClosePanel);
        input->RegisterSink();
        logger::info("Follower Spellbook Manager loaded.");
    }
}

extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Load(const SKSE::LoadInterface* a_skse)
{
    REL::Module::reset();
    const auto messaging = reinterpret_cast<SKSE::MessagingInterface*>(
        a_skse->QueryInterface(SKSE::LoadInterface::kMessaging));
    if (!messaging) return false;

    SKSE::Init(a_skse);
    if (const auto serialization = SKSE::GetSerializationInterface()) {
        serialization->SetUniqueID(kSerializationID);
        serialization->SetSaveCallback(SaveTaughtSpells);
        serialization->SetLoadCallback(LoadTaughtSpells);
        serialization->SetRevertCallback(RevertTaughtSpells);
    }
    messaging->RegisterListener("SKSE", OnSKSEMessage);
    return true;
}

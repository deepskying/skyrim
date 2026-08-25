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
    using DisabledSpellMap = std::unordered_map<RE::FormID, std::unordered_set<RE::FormID>>;
    DisabledSpellMap g_disabledSpells;
    std::mutex g_disabledSpellsLock;

    struct LevelOverride
    {
        RE::FormID baseFormID = 0;
        std::uint16_t originalMax = 0;
    };
    using LevelOverrideMap = std::unordered_map<RE::FormID, LevelOverride>;
    LevelOverrideMap g_levelOverrides;
    std::mutex g_levelOverridesLock;

    struct LevelScalingConfig
    {
        std::uint16_t maxLevel = 300;
    };
    LevelScalingConfig g_levelScaling;

    constexpr std::uint32_t FourCC(char a, char b, char c, char d)
    {
        return static_cast<std::uint32_t>(a) |
               (static_cast<std::uint32_t>(b) << 8) |
               (static_cast<std::uint32_t>(c) << 16) |
               (static_cast<std::uint32_t>(d) << 24);
    }

    constexpr std::uint32_t kSerializationID = FourCC('F', 'S', 'B', 'M');
    constexpr std::uint32_t kRecordType = FourCC('S', 'P', 'L', 'S');
    constexpr std::uint32_t kDisabledRecordType = FourCC('D', 'S', 'P', 'L');
    constexpr std::uint32_t kLevelRecordType = FourCC('L', 'V', 'L', 'S');
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

    [[nodiscard]] LevelScalingConfig LoadLevelScalingConfig()
    {
        LevelScalingConfig config;
        try {
            const auto modulePath = REL::Module::get().filePath();
            const auto configPath = std::filesystem::path(modulePath.data()).parent_path() / "Data" / "SKSE" / "Plugins" / "FollowerSpellbookManager.ini";
            std::ifstream configFile(configPath);
            if (!configFile) return config;

            bool inLevelSection = false;
            std::string line;
            while (std::getline(configFile, line)) {
                if (const auto comment = line.find_first_of(";#"); comment != std::string::npos) line.erase(comment);
                const auto normalizedLine = NormalizeKeyName(line);
                if (normalizedLine.empty()) continue;
                if (normalizedLine.front() == '[' && normalizedLine.back() == ']') {
                    inLevelSection = normalizedLine == "[LEVELSCALING]";
                    continue;
                }
                if (!inLevelSection) continue;

                const auto separator = line.find('=');
                if (separator == std::string::npos) continue;
                const auto setting = NormalizeKeyName(line.substr(0, separator));
                const auto value = NormalizeKeyName(line.substr(separator + 1));
                if (setting != "MAXLEVEL") continue;
                try {
                    const auto parsed = std::stoul(value);
                    if (parsed >= 1 && parsed <= 1000) config.maxLevel = static_cast<std::uint16_t>(parsed);
                    else logger::warn("LevelScaling.MaxLevel must be between 1 and 1000; using 300.");
                }
                catch (const std::exception&) {
                    logger::warn("Invalid LevelScaling.MaxLevel '{}'; using 300.", value);
                }
            }
        }
        catch (const std::exception& error) {
            logger::warn("Could not read level scaling configuration; using max level 300. {}", error.what());
        }
        logger::info("Follower level scaling target: {}.", config.maxLevel);
        return config;
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

    [[nodiscard]] std::string SpellDescription(RE::SpellItem* a_spell)
    {
        if (!a_spell) return {};
        RE::BSString description;
        RE::MagicSystem::GetMagicItemDescription(description, a_spell, "", "");
        return description.c_str() ? description.c_str() : "";
    }

    [[nodiscard]] std::string ActorClassName(RE::Actor* a_actor)
    {
        const auto actorBase = a_actor ? a_actor->GetActorBase() : nullptr;
        const auto actorClass = actorBase ? actorBase->npcClass : nullptr;
        const auto name = actorClass ? actorClass->GetFullName() : nullptr;
        return name && name[0] != '\0' ? name : "Unclassified";
    }

    [[nodiscard]] json ActorResource(RE::Actor* a_actor, RE::ActorValue a_value)
    {
        const auto owner = a_actor ? a_actor->AsActorValueOwner() : nullptr;
        if (!owner) return { { "current", 0 }, { "max", 0 } };

        const auto currentValue = (std::max)(0.0f, owner->GetActorValue(a_value));
        const auto damageModifier = a_actor->GetActorValueModifier(RE::ACTOR_VALUE_MODIFIERS::kDamage, a_value);
        const auto maximumValue = (std::max)(currentValue, currentValue - damageModifier);
        return {
            { "current", static_cast<int>(currentValue + 0.5f) },
            { "max", static_cast<int>(maximumValue + 0.5f) }
        };
    }

    [[nodiscard]] std::optional<LevelOverride> GetLevelOverride(RE::FormID a_actorID)
    {
        std::scoped_lock lock(g_levelOverridesLock);
        const auto found = g_levelOverrides.find(a_actorID);
        return found == g_levelOverrides.end() ? std::nullopt : std::optional<LevelOverride>(found->second);
    }

    void ApplyLevelOverride(RE::FormID a_actorID, const LevelOverride& a_override)
    {
        const auto actorBase = RE::TESForm::LookupByID<RE::TESNPC>(a_override.baseFormID);
        if (!actorBase || !actorBase->HasPCLevelMult()) return;
        actorBase->actorData.calcLevelMax = (std::max)(actorBase->actorData.calcLevelMax, (std::max)(a_override.originalMax, g_levelScaling.maxLevel));
        if (const auto actor = RE::TESForm::LookupByID<RE::Actor>(a_actorID)) {
            static_cast<void>(actor->GetCalcLevel(true));
        }
    }

    void RestoreLevelOverride(const LevelOverride& a_override)
    {
        if (const auto actorBase = RE::TESForm::LookupByID<RE::TESNPC>(a_override.baseFormID)) {
            actorBase->actorData.calcLevelMax = a_override.originalMax;
        }
    }

    void ReapplyAllLevelOverrides()
    {
        LevelOverrideMap saved;
        {
            std::scoped_lock lock(g_levelOverridesLock);
            saved = g_levelOverrides;
        }
        for (const auto& [actorID, levelOverride] : saved) ApplyLevelOverride(actorID, levelOverride);
    }

    [[nodiscard]] json ActorLevelScaling(RE::Actor* a_actor)
    {
        const auto actorBase = a_actor ? a_actor->GetActorBase() : nullptr;
        if (!actorBase) {
            return {
                { "playerScaled", false }, { "multiplier", 0.0f }, { "currentMax", 0 },
                { "originalMax", 0 }, { "targetMax", g_levelScaling.maxLevel },
                { "enabled", false }, { "canToggle", false }
            };
        }

        const auto levelOverride = GetLevelOverride(a_actor->GetFormID());
        const auto playerScaled = actorBase->HasPCLevelMult();
        const auto currentMax = actorBase->actorData.calcLevelMax;
        const auto originalMax = levelOverride ? levelOverride->originalMax : currentMax;
        const auto targetMax = (std::max)(originalMax, g_levelScaling.maxLevel);
        const auto canToggle = levelOverride.has_value() || (playerScaled && currentMax != 0 && currentMax < g_levelScaling.maxLevel);
        return {
            { "playerScaled", playerScaled },
            { "multiplier", playerScaled ? static_cast<float>(actorBase->actorData.level) / 1000.0f : 0.0f },
            { "currentMax", currentMax },
            { "originalMax", originalMax },
            { "targetMax", targetMax },
            { "enabled", levelOverride.has_value() },
            { "canToggle", canToggle }
        };
    }

    class SpellCollector final : public RE::Actor::ForEachSpellVisitor
    {
    public:
        SpellCollector(RE::Actor* a_actor, const std::unordered_set<RE::FormID>& a_disabled) :
            _actor(a_actor), _disabled(a_disabled) {}

        RE::BSContainer::ForEachResult Visit(RE::SpellItem* a_spell) override
        {
            if (!a_spell || a_spell->GetSpellType() != RE::MagicSystem::SpellType::kSpell) {
                return RE::BSContainer::ForEachResult::kContinue;
            }
            if (!_seen.insert(a_spell->GetFormID()).second) return RE::BSContainer::ForEachResult::kContinue;
            _spells.push_back({
                { "id", a_spell->GetFormID() },
                { "name", a_spell->GetFullName() ? a_spell->GetFullName() : "Unnamed spell" },
                { "school", SchoolName(a_spell->GetAssociatedSkill()) },
                { "cost", static_cast<int>(a_spell->CalculateMagickaCost(_actor)) },
                { "enabled", !_disabled.contains(a_spell->GetFormID()) }
            });
            return RE::BSContainer::ForEachResult::kContinue;
        }

        void AddDisabledSpells()
        {
            for (const auto spellID : _disabled) {
                if (!_seen.insert(spellID).second) continue;
                const auto spell = RE::TESForm::LookupByID<RE::SpellItem>(spellID);
                if (!spell || spell->GetSpellType() != RE::MagicSystem::SpellType::kSpell) continue;
                _spells.push_back({
                    { "id", spellID },
                    { "name", spell->GetFullName() ? spell->GetFullName() : "Unnamed spell" },
                    { "school", SchoolName(spell->GetAssociatedSkill()) },
                    { "cost", static_cast<int>(spell->CalculateMagickaCost(_actor)) },
                    { "enabled", false }
                });
            }
        }

        [[nodiscard]] const json& Spells() const { return _spells; }

    private:
        RE::Actor* _actor;
        const std::unordered_set<RE::FormID>& _disabled;
        std::unordered_set<RE::FormID> _seen;
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

    [[nodiscard]] std::unordered_set<RE::FormID> DisabledSpellsForActor(RE::FormID a_actorID)
    {
        std::scoped_lock lock(g_disabledSpellsLock);
        const auto found = g_disabledSpells.find(a_actorID);
        return found == g_disabledSpells.end() ? std::unordered_set<RE::FormID>{} : found->second;
    }

    [[nodiscard]] bool IsSpellDisabled(RE::FormID a_actorID, RE::FormID a_spellID)
    {
        std::scoped_lock lock(g_disabledSpellsLock);
        const auto found = g_disabledSpells.find(a_actorID);
        return found != g_disabledSpells.end() && found->second.contains(a_spellID);
    }

    void EnforceDisabledSpells(RE::Actor* a_actor, const std::unordered_set<RE::FormID>& a_spellIDs)
    {
        if (!a_actor) return;
        for (const auto spellID : a_spellIDs) {
            const auto spell = RE::TESForm::LookupByID<RE::SpellItem>(spellID);
            if (spell && KnowsSpell(a_actor, spell)) a_actor->RemoveSpell(spell);
        }
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
            if (spell && !IsSpellDisabled(a_actor->GetFormID(), spellID) && !KnowsSpell(a_actor, spell)) a_actor->AddSpell(spell);
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

    void ReapplyAllDisabledSpells()
    {
        DisabledSpellMap saved;
        {
            std::scoped_lock lock(g_disabledSpellsLock);
            saved = g_disabledSpells;
        }
        for (const auto& [actorID, spellIDs] : saved) {
            const auto actor = RE::TESForm::LookupByID<RE::Actor>(actorID);
            if (actor && actor->IsPlayerTeammate()) EnforceDisabledSpells(actor, spellIDs);
        }
    }

    void SaveState(SKSE::SerializationInterface* a_serialization)
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

        DisabledSpellMap disabled;
        {
            std::scoped_lock lock(g_disabledSpellsLock);
            disabled = g_disabledSpells;
        }
        if (!a_serialization->OpenRecord(kDisabledRecordType, kRecordVersion)) return;
        const auto disabledFollowerCount = static_cast<std::uint32_t>(disabled.size());
        if (!a_serialization->WriteRecordData(disabledFollowerCount)) return;
        for (const auto& [actorID, spellIDs] : disabled) {
            const auto spellCount = static_cast<std::uint32_t>(spellIDs.size());
            if (!a_serialization->WriteRecordData(actorID) || !a_serialization->WriteRecordData(spellCount)) return;
            for (const auto spellID : spellIDs) {
                if (!a_serialization->WriteRecordData(spellID)) return;
            }
        }

        LevelOverrideMap levelOverrides;
        {
            std::scoped_lock lock(g_levelOverridesLock);
            levelOverrides = g_levelOverrides;
        }
        if (!a_serialization->OpenRecord(kLevelRecordType, kRecordVersion)) return;
        const auto overrideCount = static_cast<std::uint32_t>(levelOverrides.size());
        if (!a_serialization->WriteRecordData(overrideCount)) return;
        for (const auto& [actorID, levelOverride] : levelOverrides) {
            if (!a_serialization->WriteRecordData(actorID) ||
                !a_serialization->WriteRecordData(levelOverride.baseFormID) ||
                !a_serialization->WriteRecordData(levelOverride.originalMax)) return;
        }
    }

    void LoadState(SKSE::SerializationInterface* a_serialization)
    {
        TaughtSpellMap restored;
        DisabledSpellMap restoredDisabled;
        LevelOverrideMap restoredLevels;
        std::uint32_t type = 0;
        std::uint32_t version = 0;
        std::uint32_t length = 0;
        while (a_serialization->GetNextRecordInfo(type, version, length)) {
            if (version != kRecordVersion) {
                std::vector<std::byte> ignored(length);
                a_serialization->ReadRecordData(ignored.data(), length);
                continue;
            }

            if (type == kRecordType) {
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
                continue;
            }

            if (type == kDisabledRecordType) {
                std::uint32_t followerCount = 0;
                if (a_serialization->ReadRecordData(followerCount) != sizeof(followerCount) || followerCount > kMaxFollowersPerSave) break;
                for (std::uint32_t i = 0; i < followerCount; ++i) {
                    RE::FormID oldActorID = 0;
                    std::uint32_t spellCount = 0;
                    if (a_serialization->ReadRecordData(oldActorID) != sizeof(oldActorID) ||
                        a_serialization->ReadRecordData(spellCount) != sizeof(spellCount) ||
                        spellCount > kMaxSpellsPerFollower) break;
                    RE::FormID actorID = 0;
                    const bool actorResolved = a_serialization->ResolveFormID(oldActorID, actorID);
                    for (std::uint32_t j = 0; j < spellCount; ++j) {
                        RE::FormID oldSpellID = 0;
                        if (a_serialization->ReadRecordData(oldSpellID) != sizeof(oldSpellID)) break;
                        RE::FormID spellID = 0;
                        if (actorResolved && a_serialization->ResolveFormID(oldSpellID, spellID)) restoredDisabled[actorID].insert(spellID);
                    }
                }
                continue;
            }

            if (type == kLevelRecordType) {
                std::uint32_t overrideCount = 0;
                if (a_serialization->ReadRecordData(overrideCount) != sizeof(overrideCount) || overrideCount > kMaxFollowersPerSave) break;
                for (std::uint32_t i = 0; i < overrideCount; ++i) {
                    RE::FormID oldActorID = 0;
                    RE::FormID oldBaseID = 0;
                    std::uint16_t originalMax = 0;
                    if (a_serialization->ReadRecordData(oldActorID) != sizeof(oldActorID) ||
                        a_serialization->ReadRecordData(oldBaseID) != sizeof(oldBaseID) ||
                        a_serialization->ReadRecordData(originalMax) != sizeof(originalMax)) break;
                    RE::FormID actorID = 0;
                    RE::FormID baseID = 0;
                    if (a_serialization->ResolveFormID(oldActorID, actorID) &&
                        a_serialization->ResolveFormID(oldBaseID, baseID)) {
                        restoredLevels[actorID] = { baseID, originalMax };
                    }
                }
                continue;
            }

            std::vector<std::byte> ignored(length);
            a_serialization->ReadRecordData(ignored.data(), length);
        }
        {
            std::scoped_lock lock(g_taughtSpellsLock);
            g_taughtSpells = std::move(restored);
        }
        {
            std::scoped_lock lock(g_disabledSpellsLock);
            g_disabledSpells = std::move(restoredDisabled);
        }
        {
            std::scoped_lock lock(g_levelOverridesLock);
            g_levelOverrides = std::move(restoredLevels);
        }
    }

    void RevertState(SKSE::SerializationInterface*)
    {
        {
            std::scoped_lock lock(g_taughtSpellsLock);
            g_taughtSpells.clear();
        }
        {
            std::scoped_lock lock(g_disabledSpellsLock);
            g_disabledSpells.clear();
        }
        LevelOverrideMap levelOverrides;
        {
            std::scoped_lock lock(g_levelOverridesLock);
            levelOverrides = std::move(g_levelOverrides);
            g_levelOverrides.clear();
        }
        for (const auto& [actorID, levelOverride] : levelOverrides) {
            static_cast<void>(actorID);
            RestoreLevelOverride(levelOverride);
        }
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
            if (const auto levelOverride = GetLevelOverride(a_actor->GetFormID())) {
                ApplyLevelOverride(a_actor->GetFormID(), *levelOverride);
            }
            ReapplyTrackedSpells(a_actor);
            const auto disabledSpells = DisabledSpellsForActor(a_actor->GetFormID());
            EnforceDisabledSpells(a_actor, disabledSpells);
            SpellCollector spells(a_actor, disabledSpells);
            a_actor->VisitSpells(spells);
            spells.AddDisabledSpells();
            const auto health = ActorResource(a_actor, RE::ActorValue::kHealth);
            const auto magicka = ActorResource(a_actor, RE::ActorValue::kMagicka);
            const auto stamina = ActorResource(a_actor, RE::ActorValue::kStamina);
            followers.push_back({
                { "id", a_actor->GetFormID() },
                { "name", a_actor->GetDisplayFullName() ? a_actor->GetDisplayFullName() : "Unnamed follower" },
                { "className", ActorClassName(a_actor) },
                { "level", a_actor->GetLevel() },
                { "levelScaling", ActorLevelScaling(a_actor) },
                { "maxMagicka", magicka["max"] },
                { "resources", {
                    { "health", health },
                    { "magicka", magicka },
                    { "stamina", stamina }
                } },
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
                { "count", entry.first },
                { "value", (std::max)(0, book->GetGoldValue()) },
                { "description", SpellDescription(spell) }
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

    void SetSpellEnabled(const json& a_request)
    {
        const auto actorID = a_request.value("actorId", 0u);
        const auto spellID = a_request.value("spellId", 0u);
        const auto enabled = a_request.value("enabled", true);
        const auto actor = RE::TESForm::LookupByID<RE::Actor>(actorID);
        const auto spell = RE::TESForm::LookupByID<RE::SpellItem>(spellID);
        if (!actor || !spell || !actor->IsPlayerTeammate() || spell->GetSpellType() != RE::MagicSystem::SpellType::kSpell) {
            SendState("The selected follower or spell is no longer available.");
            return;
        }

        if (enabled) {
            const auto wasDisabled = IsSpellDisabled(actorID, spellID);
            if (!wasDisabled) {
                SendState("That spell is already enabled.");
                return;
            }
            if (!KnowsSpell(actor, spell) && !actor->AddSpell(spell)) {
                SendState("The follower could not restore that spell.");
                return;
            }
            {
                std::scoped_lock lock(g_disabledSpellsLock);
                const auto found = g_disabledSpells.find(actorID);
                if (found != g_disabledSpells.end()) {
                    found->second.erase(spellID);
                    if (found->second.empty()) g_disabledSpells.erase(found);
                }
            }
            SendState(std::string(actor->GetDisplayFullName()) + " enabled " + spell->GetFullName() + ".");
            return;
        }

        if (IsSpellDisabled(actorID, spellID)) {
            SendState("That spell is already disabled.");
            return;
        }
        if (!KnowsSpell(actor, spell) || !actor->RemoveSpell(spell) || KnowsSpell(actor, spell)) {
            SendState("That spell cannot be disabled safely.");
            return;
        }
        {
            std::scoped_lock lock(g_disabledSpellsLock);
            g_disabledSpells[actorID].insert(spellID);
        }
        SendState(std::string(actor->GetDisplayFullName()) + " disabled " + spell->GetFullName() + ".");
    }

    void SetLevelCap(const json& a_request)
    {
        const auto actorID = a_request.value("actorId", 0u);
        const auto enabled = a_request.value("enabled", false);
        const auto actor = RE::TESForm::LookupByID<RE::Actor>(actorID);
        const auto actorBase = actor ? actor->GetActorBase() : nullptr;
        if (!actor || !actorBase || !actor->IsPlayerTeammate()) {
            SendState("The selected follower is no longer available.");
            return;
        }

        if (enabled) {
            if (!actorBase->HasPCLevelMult()) {
                SendState("This follower has a fixed level. Player scaling was not changed.");
                return;
            }
            if (actorBase->actorData.calcLevelMax == 0) {
                SendState("This follower already has no calculated maximum level.");
                return;
            }
            if (actorBase->actorData.calcLevelMax >= g_levelScaling.maxLevel) {
                SendState("This follower already has an equal or higher level cap.");
                return;
            }

            LevelOverride levelOverride;
            {
                std::scoped_lock lock(g_levelOverridesLock);
                const auto [entry, inserted] = g_levelOverrides.try_emplace(actorID, LevelOverride{
                    actorBase->GetFormID(), actorBase->actorData.calcLevelMax
                });
                static_cast<void>(inserted);
                levelOverride = entry->second;
            }
            ApplyLevelOverride(actorID, levelOverride);
            SendState(std::string(actor->GetDisplayFullName()) + " can now scale up to level " + std::to_string(g_levelScaling.maxLevel) + ". Reloading the area may be required to recalculate the current level.");
            return;
        }

        std::optional<LevelOverride> removed;
        {
            std::scoped_lock lock(g_levelOverridesLock);
            const auto found = g_levelOverrides.find(actorID);
            if (found != g_levelOverrides.end()) {
                removed = found->second;
                g_levelOverrides.erase(found);
            }
        }
        if (!removed) {
            SendState("Follower level scaling was already using its original limit.");
            return;
        }
        RestoreLevelOverride(*removed);
        static_cast<void>(actor->GetCalcLevel(true));
        SendState(std::string(actor->GetDisplayFullName()) + " was restored to the original level cap of " + std::to_string(removed->originalMax) + ". Reloading the area may be required.");
    }

    void HandleUIAction(const char* a_data)
    {
        try {
            const auto request = json::parse(a_data ? a_data : "{}");
            const auto type = request.value("type", "");
            if (type == "learn") LearnTome(request);
            else if (type == "spellState") SetSpellEnabled(request);
            else if (type == "levelCap") SetLevelCap(request);
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
            if (const auto tasks = SKSE::GetTaskInterface()) tasks->AddTask([] {
                ReapplyAllTrackedSpells();
                ReapplyAllDisabledSpells();
                ReapplyAllLevelOverrides();
            });
            return;
        }
        if (a_message->type != SKSE::MessagingInterface::kDataLoaded) return;

        g_levelScaling = LoadLevelScalingConfig();
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
        serialization->SetSaveCallback(SaveState);
        serialization->SetLoadCallback(LoadState);
        serialization->SetRevertCallback(RevertState);
    }
    messaging->RegisterListener("SKSE", OnSKSEMessage);
    return true;
}

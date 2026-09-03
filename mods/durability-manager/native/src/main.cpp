#include "PrismaUI_API.h"
#include "input_handler.h"

#include <nlohmann/json.hpp>

namespace
{
    using json = nlohmann::json;

    PRISMA_UI_API::IVPrismaUI1* g_prisma = nullptr;
    PrismaView g_view = 0;

    struct Settings
    {
        HotkeyConfig hotkey{};
        std::uint32_t lowDurabilityThreshold = 30;
        float weaponDisplaySeconds = 3.0F;
        bool enableLowDurabilityWarning = true;
        bool allowEnchantedItemsToBreak = true;
        float bowShotWear = 1.0F;
        float crossbowShotWear = 2.0F;
        float maxWearReduction = 0.70F;
    };

    Settings g_settings{};
    bool g_capturingHotkey = false;
    bool g_panelVisible = false;
    std::uint32_t g_hudSequence = 0;

    struct DurabilitySnapshot
    {
        float current = 100.0F;
        float maximum = 100.0F;
        std::uint32_t enhancementLevel = 0;
        std::int32_t performanceBonus = 0;
        float weightReduction = 0.0F;
        float attackSpeedBonus = 0.0F;
        float wearReduction = 0.0F;
        float chargeBonus = 0.0F;
    };

    // A base FormID identifies an item definition, not a specific copy.  The
    // ExtraUniqueID is persisted with the item by Skyrim and keeps two steel
    // swords from ever sharing enhancement or durability state.
    struct ItemKey
    {
        RE::FormID baseFormID = 0;
        std::uint16_t uniqueID = 0;

        [[nodiscard]] bool operator==(const ItemKey&) const = default;
    };

    struct ItemKeyHash
    {
        [[nodiscard]] std::size_t operator()(const ItemKey& a_key) const noexcept
        {
            return (static_cast<std::size_t>(a_key.baseFormID) << 16U) ^ a_key.uniqueID;
        }
    };

    enum class EnhancementCardType : std::uint8_t { Performance, Weight, Speed, Durability, Wear, Charge, Enchantment };
    enum class EnhancementTier : std::uint8_t { Weak, Standard, Strong, Extreme };

    // The persisted equipment record will use these fields per ItemKey. Keeping
    // the card result as data (not UI behaviour) makes future card packs and
    // third-party material rules additive instead of requiring a UI rewrite.
    struct EnhancementCardState
    {
        EnhancementCardType type{};
        EnhancementTier tier{};
        float rolledValue = 0.0F;
        std::uint32_t successChance = 100;
        std::vector<RE::FormID> requiredMaterials;
    };

    std::unordered_map<ItemKey, DurabilitySnapshot, ItemKeyHash> g_durability;
    std::unordered_set<ItemKey, ItemKeyHash> g_lowDurabilityWarnings;
    std::unordered_map<ItemKey, std::chrono::steady_clock::time_point, ItemKeyHash> g_weaponNotificationTimes;
    std::mutex g_durabilityLock;
    std::uint16_t g_nextGeneratedUniqueID = 1;

    constexpr std::uint32_t kSerializationID = 0x4455524DU;  // "DURM"
    constexpr std::uint32_t kDurabilityRecordType = 0x44555241U;  // "DURA"
    constexpr std::uint32_t kDurabilityRecordVersion = 1;
    constexpr std::uint32_t kMaxDurabilityRecords = 100000;
    constexpr std::string_view kPluginVersion = "0.1.14";
    constexpr int kPanelRenderOrder = 1000;

    [[nodiscard]] std::string Normalize(std::string a_value)
    {
        a_value.erase(std::remove_if(a_value.begin(), a_value.end(), [](unsigned char a_character) {
            return std::isspace(a_character) != 0;
        }), a_value.end());
        std::transform(a_value.begin(), a_value.end(), a_value.begin(), [](unsigned char a_character) {
            return static_cast<char>(std::toupper(a_character));
        });
        return a_value;
    }

    [[nodiscard]] bool ParseBool(const std::string& a_value, const bool a_fallback)
    {
        const auto value = Normalize(a_value);
        if (value == "TRUE" || value == "YES" || value == "ON" || value == "1") return true;
        if (value == "FALSE" || value == "NO" || value == "OFF" || value == "0") return false;
        return a_fallback;
    }

    [[nodiscard]] std::optional<std::uint32_t> ParseKeyCode(const std::string& a_value)
    {
        const auto key = Normalize(a_value);
        static constexpr std::array<std::uint32_t, 26> letterCodes{
            0x1E, 0x30, 0x2E, 0x20, 0x12, 0x21, 0x22, 0x23, 0x17, 0x24, 0x25, 0x26, 0x32,
            0x31, 0x18, 0x19, 0x10, 0x13, 0x1F, 0x14, 0x16, 0x2F, 0x11, 0x2D, 0x15, 0x2C
        };
        if (key.size() == 1 && key[0] >= 'A' && key[0] <= 'Z') return letterCodes[key[0] - 'A'];
        if (key == "ESC" || key == "ESCAPE") return 0x01;
        if (key == "TAB") return 0x0F;
        if (key == "ENTER") return 0x1C;
        if (key == "SPACE") return 0x39;
        if (key.size() == 2 && key[0] == 'F' && key[1] >= '1' && key[1] <= '9') return 0x3A + (key[1] - '0');
        if (key == "F10") return 0x44;
        if (key == "F11") return 0x57;
        if (key == "F12") return 0x58;
        return std::nullopt;
    }

    [[nodiscard]] std::string KeyName(const std::uint32_t a_key)
    {
        static constexpr std::array<std::uint32_t, 26> letterCodes{
            0x1E, 0x30, 0x2E, 0x20, 0x12, 0x21, 0x22, 0x23, 0x17, 0x24, 0x25, 0x26, 0x32,
            0x31, 0x18, 0x19, 0x10, 0x13, 0x1F, 0x14, 0x16, 0x2F, 0x11, 0x2D, 0x15, 0x2C
        };
        for (std::size_t index = 0; index < letterCodes.size(); ++index) {
            if (letterCodes[index] == a_key) return std::string(1, static_cast<char>('A' + index));
        }
        if (a_key >= 0x3B && a_key <= 0x44) return "F" + std::to_string(a_key - 0x3A);
        if (a_key == 0x57) return "F11";
        if (a_key == 0x58) return "F12";
        if (a_key == 0x01) return "Esc";
        if (a_key == 0x0F) return "Tab";
        if (a_key == 0x1C) return "Enter";
        if (a_key == 0x39) return "Space";
        return "Scan " + std::to_string(a_key);
    }

    [[nodiscard]] std::filesystem::path ConfigPath()
    {
        const auto modulePath = REL::Module::get().filePath();
        return std::filesystem::path(modulePath.data()).parent_path() / "Data" / "SKSE" / "Plugins" / "DurabilityManager.ini";
    }

    void WriteConfig()
    {
        std::ofstream configFile(ConfigPath(), std::ios::trunc);
        if (!configFile) {
            logger::warn("Could not write DurabilityManager.ini.");
            return;
        }
        configFile << "; Skyrim Durability Manager configuration. Changes made in the panel apply immediately.\n\n";
        configFile << "[Hotkey]\nKey=" << KeyName(g_settings.hotkey.keyCode) << "\nShift=" << (g_settings.hotkey.requireShift ? "true" : "false")
                   << "\nCtrl=" << (g_settings.hotkey.requireCtrl ? "true" : "false") << "\nAlt=" << (g_settings.hotkey.requireAlt ? "true" : "false");
        configFile << "\n\n[Display]\nLowDurabilityThreshold=" << g_settings.lowDurabilityThreshold
                   << "\nWeaponDisplaySeconds=" << g_settings.weaponDisplaySeconds
                   << "\nEnableLowDurabilityWarning=" << (g_settings.enableLowDurabilityWarning ? "true" : "false");
        configFile << "\n\n[Breakage]\nAllowEnchantedItemsToBreak=" << (g_settings.allowEnchantedItemsToBreak ? "true" : "false") << '\n';
        configFile << "\n[Wear]\nBowShotWear=" << g_settings.bowShotWear
                   << "\nCrossbowShotWear=" << g_settings.crossbowShotWear
                   << "\nMaxWearReduction=" << g_settings.maxWearReduction << '\n';
    }

    void LoadConfig()
    {
        std::ifstream configFile(ConfigPath());
        if (!configFile) {
            logger::warn("DurabilityManager.ini was not found; using Shift+F and a 30% warning threshold.");
            return;
        }
        std::string section;
        std::string line;
        while (std::getline(configFile, line)) {
            if (const auto comment = line.find_first_of(";#"); comment != std::string::npos) line.erase(comment);
            const auto normalizedLine = Normalize(line);
            if (normalizedLine.empty()) continue;
            if (normalizedLine.front() == '[' && normalizedLine.back() == ']') {
                section = normalizedLine;
                continue;
            }
            const auto separator = line.find('=');
            if (separator == std::string::npos) continue;
            const auto key = Normalize(line.substr(0, separator));
            const auto value = line.substr(separator + 1);
            if (section == "[HOTKEY]") {
                if (key == "KEY") {
                    if (const auto parsed = ParseKeyCode(value)) g_settings.hotkey.keyCode = *parsed;
                } else if (key == "SHIFT") g_settings.hotkey.requireShift = ParseBool(value, g_settings.hotkey.requireShift);
                else if (key == "CTRL") g_settings.hotkey.requireCtrl = ParseBool(value, g_settings.hotkey.requireCtrl);
                else if (key == "ALT") g_settings.hotkey.requireAlt = ParseBool(value, g_settings.hotkey.requireAlt);
            } else if (section == "[DISPLAY]") {
                try {
                    if (key == "LOWDURABILITYTHRESHOLD") g_settings.lowDurabilityThreshold = std::clamp<std::uint32_t>(std::stoul(value), 1, 99);
                    else if (key == "WEAPONDISPLAYSECONDS") g_settings.weaponDisplaySeconds = std::clamp(std::stof(value), 0.5F, 10.0F);
                    else if (key == "ENABLELOWDURABILITYWARNING") g_settings.enableLowDurabilityWarning = ParseBool(value, g_settings.enableLowDurabilityWarning);
                } catch (const std::exception&) {
                    logger::warn("Ignoring invalid DurabilityManager.ini value for {}.", key);
                }
            } else if (section == "[BREAKAGE]" && key == "ALLOWENCHANTEDITEMSTOBREAK") {
                g_settings.allowEnchantedItemsToBreak = ParseBool(value, g_settings.allowEnchantedItemsToBreak);
            } else if (section == "[WEAR]") {
                try {
                    if (key == "BOWSHOTWEAR") g_settings.bowShotWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "CROSSBOWSHOTWEAR") g_settings.crossbowShotWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "MAXWEARREDUCTION") g_settings.maxWearReduction = std::clamp(std::stof(value), 0.0F, 0.95F);
                } catch (const std::exception&) {
                    logger::warn("Ignoring invalid DurabilityManager.ini value for {}.", key);
                }
            }
        }
    }

    [[nodiscard]] std::string EquipmentType(const RE::TESBoundObject* a_item)
    {
        if (!a_item) return "装备";
        if (a_item->GetFormType() == RE::FormType::Weapon) return "武器";
        if (const auto armor = a_item->As<RE::TESObjectARMO>()) {
            const auto slots = std::to_underlying(armor->GetSlotMask());
            if (slots & std::to_underlying(RE::BIPED_MODEL::BipedObjectSlot::kHead)) return "头盔";
            if (slots & std::to_underlying(RE::BIPED_MODEL::BipedObjectSlot::kBody)) return "胸甲";
            if (slots & std::to_underlying(RE::BIPED_MODEL::BipedObjectSlot::kHands)) return "手套";
            if (slots & std::to_underlying(RE::BIPED_MODEL::BipedObjectSlot::kFeet)) return "靴子";
            if (slots & std::to_underlying(RE::BIPED_MODEL::BipedObjectSlot::kShield)) return "盾牌";
        }
        return "护甲";
    }

    [[nodiscard]] std::string EquipmentCategory(const RE::TESBoundObject* a_item)
    {
        if (!a_item) return "clothing";
        if (a_item->GetFormType() == RE::FormType::Weapon) return "weapon";
        return a_item->As<RE::TESObjectARMO>() ? "armor" : "clothing";
    }

    [[nodiscard]] float EquipmentWeight(const RE::TESBoundObject* a_item)
    {
        if (const auto* weapon = a_item ? a_item->As<RE::TESObjectWEAP>() : nullptr) return weapon->weight;
        if (const auto* armor = a_item ? a_item->As<RE::TESObjectARMO>() : nullptr) return armor->weight;
        return 0.0F;
    }

    [[nodiscard]] std::string EnchantmentName(const RE::InventoryEntryData* a_entry)
    {
        const auto* enchantment = a_entry ? a_entry->GetEnchantment() : nullptr;
        const auto* name = enchantment ? enchantment->GetFullName() : nullptr;
        return name && name[0] ? name : "";
    }

    [[nodiscard]] RE::ExtraDataList* FindWornExtraList(const RE::InventoryEntryData* a_entry)
    {
        if (!a_entry || !a_entry->extraLists) return nullptr;
        for (auto* extraList : *a_entry->extraLists) {
            if (extraList && extraList->GetWorn()) return extraList;
        }
        return nullptr;
    }

    [[nodiscard]] bool IsUniqueIDInPlayerInventory(const RE::FormID a_baseFormID, const std::uint16_t a_uniqueID)
    {
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!player) return false;
        for (const auto& [item, entry] : player->GetInventory()) {
            if (!item || item->GetFormID() != a_baseFormID || !entry.second || !entry.second->extraLists) continue;
            for (auto* extraList : *entry.second->extraLists) {
                const auto* uniqueID = extraList ? extraList->GetByType<RE::ExtraUniqueID>() : nullptr;
                if (uniqueID && uniqueID->uniqueID == a_uniqueID) return true;
            }
        }
        return false;
    }

    [[nodiscard]] std::optional<ItemKey> EnsureItemKey(RE::InventoryEntryData* a_entry, const RE::TESBoundObject* a_item)
    {
        if (!a_item) return std::nullopt;
        auto* extraList = FindWornExtraList(a_entry);
        if (!extraList) {
            logger::debug("Could not resolve a worn extra-data list for {:08X}; durability was not changed.", a_item->GetFormID());
            return std::nullopt;
        }

        if (const auto* existing = extraList->GetByType<RE::ExtraUniqueID>()) {
            return ItemKey{ a_item->GetFormID(), existing->uniqueID };
        }

        std::uint16_t generatedID = 0;
        bool foundAvailableID = false;
        {
            std::scoped_lock lock(g_durabilityLock);
            // Generated IDs occupy the upper half where possible, and are
            // checked against every currently held instance before use.
            if (g_nextGeneratedUniqueID < 0x8000U) g_nextGeneratedUniqueID = 0x8000U;
            const auto firstCandidate = g_nextGeneratedUniqueID;
            do {
                generatedID = g_nextGeneratedUniqueID++;
                if (g_nextGeneratedUniqueID == 0) g_nextGeneratedUniqueID = 0x8000U;
                if (!g_durability.contains(ItemKey{ a_item->GetFormID(), generatedID }) &&
                    !IsUniqueIDInPlayerInventory(a_item->GetFormID(), generatedID)) {
                    foundAvailableID = true;
                    break;
                }
            } while (g_nextGeneratedUniqueID != firstCandidate);
        }
        if (!foundAvailableID || generatedID == 0) return std::nullopt;

        extraList->Add(new RE::ExtraUniqueID(a_item->GetFormID(), generatedID));
        logger::debug("Assigned durability instance {:08X}:{:04X}.", a_item->GetFormID(), generatedID);
        return ItemKey{ a_item->GetFormID(), generatedID };
    }

    [[nodiscard]] DurabilitySnapshot GetDurability(const ItemKey& a_key)
    {
        std::scoped_lock lock(g_durabilityLock);
        if (const auto found = g_durability.find(a_key); found != g_durability.end()) return found->second;
        return {};
    }

    [[nodiscard]] RE::InventoryEntryData* FindEquippedWeaponEntry(const RE::TESObjectWEAP* a_weapon)
    {
        const auto* player = RE::PlayerCharacter::GetSingleton();
        if (!player || !a_weapon) return nullptr;
        for (const bool leftHand : { false, true }) {
            auto* entry = player->GetEquippedEntryData(leftHand);
            if (entry && entry->object == a_weapon) return entry;
        }
        return nullptr;
    }

    [[nodiscard]] std::string DisplayName(const RE::TESBoundObject* a_item)
    {
        const auto* fullName = a_item ? a_item->As<RE::TESFullName>() : nullptr;
        const auto* name = fullName ? fullName->GetFullName() : nullptr;
        return name && name[0] ? name : "未命名武器";
    }

    void SetPanelVisibilityInView(const bool a_visible)
    {
        if (!g_prisma || !g_view) return;
        const auto* script = a_visible
            ? "window.DurabilityManager&&window.DurabilityManager.setPanelVisible(true);"
            : "window.DurabilityManager&&window.DurabilityManager.setPanelVisible(false);";
        g_prisma->Invoke(g_view, script);
    }

    void LogPanelDOMState(const char* a_result)
    {
        logger::info("Durability Manager DOM state: {}", a_result ? a_result : "<no result>");
    }

    void RequestPanelDOMState()
    {
        if (!g_prisma || !g_view) return;
        g_prisma->Invoke(
            g_view,
            "(()=>{const e=document.querySelector('.forge-shell');const r=e?e.getBoundingClientRect():null;const s=e?getComputedStyle(e):null;return JSON.stringify({bridge:!!window.DurabilityManager,panelAttribute:document.documentElement.dataset.panelVisible||'',shellExists:!!e,display:s?s.display:'missing',visibility:s?s.visibility:'missing',opacity:s?s.opacity:'missing',width:r?r.width:0,height:r?r.height:0,version:document.querySelector('.panel-footer small')?.textContent||''});})()",
            LogPanelDOMState);
    }

    void SendState(std::string_view a_message = {});

    void ShowHUD(
        std::string_view a_kind,
        std::string_view a_title,
        std::string_view a_detail,
        const float a_seconds,
        const std::optional<std::uint32_t> a_current = std::nullopt,
        const std::optional<std::uint32_t> a_maximum = std::nullopt)
    {
        if (!g_prisma || !g_view) return;
        auto message = json{
            { "id", ++g_hudSequence },
            { "kind", a_kind },
            { "title", a_title },
            { "detail", a_detail },
            { "durationMilliseconds", static_cast<std::uint32_t>(a_seconds * 1000.0F) }
        };
        if (a_current && a_maximum) {
            message["current"] = *a_current;
            message["maximum"] = *a_maximum;
        }
        const auto script = "window.DurabilityManager && window.DurabilityManager.showHud(" + message.dump() + ");";
        g_prisma->Invoke(g_view, script.c_str());
    }

    void UpdateLowDurabilityWarning(const RE::TESObjectWEAP* a_weapon, const ItemKey& a_key, const DurabilitySnapshot& a_durability)
    {
        if (!g_settings.enableLowDurabilityWarning || a_durability.maximum <= 0.0F) return;
        const auto percentage = static_cast<std::uint32_t>(std::lround(a_durability.current * 100.0F / a_durability.maximum));
        if (percentage < g_settings.lowDurabilityThreshold) {
            if (g_lowDurabilityWarnings.insert(a_key).second) {
                ShowHUD("warning", "耐久度过低", DisplayName(a_weapon) + "：" + std::to_string(percentage) + "%（请尽快修复）", g_settings.weaponDisplaySeconds);
            }
        } else {
            g_lowDurabilityWarnings.erase(a_key);
        }
    }

    void ShowWeaponDurability(const RE::TESObjectWEAP* a_weapon, RE::InventoryEntryData* a_entry = nullptr)
    {
        if (!a_weapon) return;
        auto* entry = a_entry ? a_entry : FindEquippedWeaponEntry(a_weapon);
        const auto key = EnsureItemKey(entry, a_weapon);
        if (!key) return;
        const auto now = std::chrono::steady_clock::now();
        if (const auto previous = g_weaponNotificationTimes.find(*key); previous != g_weaponNotificationTimes.end() && now - previous->second < std::chrono::milliseconds(250)) return;
        g_weaponNotificationTimes[*key] = now;

        const auto durability = GetDurability(*key);
        const auto current = static_cast<std::uint32_t>(std::lround(durability.current));
        const auto maximum = static_cast<std::uint32_t>(std::lround(durability.maximum));
        ShowHUD("weapon", DisplayName(a_weapon), "当前装备耐久", g_settings.weaponDisplaySeconds, current, maximum);
        UpdateLowDurabilityWarning(a_weapon, *key, durability);
    }

    void ApplyRangedWeaponWear(RE::InventoryEntryData* a_entry, const RE::TESObjectWEAP* a_weapon, const float a_baseWear)
    {
        if (!a_weapon || a_weapon->IsBound()) return;
        const auto key = EnsureItemKey(a_entry, a_weapon);
        if (!key) return;

        DurabilitySnapshot durability;
        float appliedWear = 0.0F;
        {
            std::scoped_lock lock(g_durabilityLock);
            auto& stored = g_durability[*key];
            stored.maximum = (std::max)(1.0F, stored.maximum);
            stored.current = std::clamp(stored.current, 0.0F, stored.maximum);
            const auto reduction = std::clamp(stored.wearReduction, 0.0F, g_settings.maxWearReduction);
            appliedWear = (std::max)(0.1F, a_baseWear * (1.0F - reduction));
            stored.current = (std::max)(0.0F, stored.current - appliedWear);
            durability = stored;
        }
        logger::debug("Ranged shot wore {:08X}:{:04X} by {:.2F}; now {:.2F}/{:.2F}.", key->baseFormID, key->uniqueID, appliedWear, durability.current, durability.maximum);
        UpdateLowDurabilityWarning(a_weapon, *key, durability);
        if (g_panelVisible) SendState();
    }

    class EquipmentEventSink final : public RE::BSTEventSink<RE::TESEquipEvent>, public RE::BSTEventSink<RE::BSAnimationGraphEvent>, public RE::BSTEventSink<RE::TESPlayerBowShotEvent>
    {
    public:
        static EquipmentEventSink* GetSingleton()
        {
            static EquipmentEventSink singleton;
            return std::addressof(singleton);
        }

        void Register()
        {
            if (registered_) return;
            if (auto* source = RE::ScriptEventSourceHolder::GetSingleton()) source->AddEventSink<RE::TESEquipEvent>(this);
            if (auto* source = RE::ScriptEventSourceHolder::GetSingleton()) source->AddEventSink<RE::TESPlayerBowShotEvent>(this);
            if (const auto* player = RE::PlayerCharacter::GetSingleton()) player->AddAnimationGraphEventSink(this);
            registered_ = true;
        }

        RE::BSEventNotifyControl ProcessEvent(const RE::TESEquipEvent* a_event, RE::BSTEventSource<RE::TESEquipEvent>*) override
        {
            const auto* player = RE::PlayerCharacter::GetSingleton();
            if (!a_event || !a_event->equipped || !player || a_event->actor.get() != player) return RE::BSEventNotifyControl::kContinue;
            ShowWeaponDurability(RE::TESForm::LookupByID<RE::TESObjectWEAP>(a_event->baseObject));
            return RE::BSEventNotifyControl::kContinue;
        }

        RE::BSEventNotifyControl ProcessEvent(const RE::TESPlayerBowShotEvent* a_event, RE::BSTEventSource<RE::TESPlayerBowShotEvent>*) override
        {
            if (!a_event) return RE::BSEventNotifyControl::kContinue;
            auto* player = RE::PlayerCharacter::GetSingleton();
            auto* entry = player ? player->GetEquippedEntryData(false) : nullptr;
            const auto* weapon = entry && entry->object ? entry->object->As<RE::TESObjectWEAP>() : nullptr;
            if (!weapon || weapon->GetFormID() != a_event->weapon) return RE::BSEventNotifyControl::kContinue;
            if (weapon->IsBow()) ApplyRangedWeaponWear(entry, weapon, g_settings.bowShotWear);
            else if (weapon->IsCrossbow()) ApplyRangedWeaponWear(entry, weapon, g_settings.crossbowShotWear);
            return RE::BSEventNotifyControl::kContinue;
        }

        RE::BSEventNotifyControl ProcessEvent(const RE::BSAnimationGraphEvent* a_event, RE::BSTEventSource<RE::BSAnimationGraphEvent>*) override
        {
            const auto* player = RE::PlayerCharacter::GetSingleton();
            if (!a_event || !player || a_event->holder != player || Normalize(a_event->tag.c_str()) != "WEAPONDRAW") return RE::BSEventNotifyControl::kContinue;
            const auto* rightHand = player->GetEquippedObject(false);
            const auto* leftHand = player->GetEquippedObject(true);
            const auto* weapon = rightHand ? rightHand->As<RE::TESObjectWEAP>() : nullptr;
            if (!weapon && leftHand) weapon = leftHand->As<RE::TESObjectWEAP>();
            ShowWeaponDurability(weapon);
            return RE::BSEventNotifyControl::kContinue;
        }

    private:
        bool registered_ = false;
    };

    [[nodiscard]] json CollectEquippedItems()
    {
        json equipment = json::array();
        const auto player = RE::PlayerCharacter::GetSingleton();
        if (!player) return equipment;
        const auto inventory = player->GetInventory();
        for (const auto& [item, entry] : inventory) {
            if (!item || entry.first <= 0 || !entry.second || !entry.second->IsWorn()) continue;
            if (item->GetFormType() != RE::FormType::Weapon && item->GetFormType() != RE::FormType::Armor) continue;
            const auto key = EnsureItemKey(entry.second.get(), item);
            if (!key) continue;
            const auto durability = GetDurability(*key);
            const auto* weapon = item->As<RE::TESObjectWEAP>();
            const auto* armor = item->As<RE::TESObjectARMO>();
            const auto enchantment = EnchantmentName(entry.second.get());
            const auto isRangedWeapon = weapon && (weapon->IsBow() || weapon->IsCrossbow()) && !weapon->IsBound();
            const auto rangedBaseWear = weapon && weapon->IsCrossbow() ? g_settings.crossbowShotWear : g_settings.bowShotWear;
            const auto effectiveWearReduction = std::clamp(durability.wearReduction, 0.0F, g_settings.maxWearReduction);
            const auto effectiveRangedWear = (std::max)(0.1F, rangedBaseWear * (1.0F - effectiveWearReduction));
            equipment.push_back({
                { "id", std::to_string(key->baseFormID) + ":" + std::to_string(key->uniqueID) },
                { "name", DisplayName(item) },
                { "slot", EquipmentType(item) },
                { "category", EquipmentCategory(item) },
                { "current", static_cast<std::uint32_t>(std::lround(durability.current)) },
                { "maximum", static_cast<std::uint32_t>(std::lround(durability.maximum)) },
                { "enhancementLevel", durability.enhancementLevel },
                { "damage", weapon ? static_cast<std::int32_t>(weapon->GetAttackDamage()) + durability.performanceBonus : 0 },
                { "armor", armor ? static_cast<std::int32_t>(const_cast<RE::TESObjectARMO*>(armor)->GetArmorRating()) + durability.performanceBonus : 0 },
                { "weight", (std::max)(0.1F, EquipmentWeight(item) - durability.weightReduction) },
                { "attackSpeed", weapon ? (std::min)(weapon->GetSpeed() * 2.0F, weapon->GetSpeed() * (1.0F + durability.attackSpeedBonus)) : 0.0F },
                { "wearRate", isRangedWeapon ? json(effectiveRangedWear) : json(nullptr) },
                { "wearRateLabel", isRangedWeapon ? "每次成功射击" : "尚未启用" },
                { "wearReduction", effectiveWearReduction },
                { "enchantment", enchantment },
                { "enchanted", entry.second->IsEnchanted() },
                { "enchantmentReplaceable", !entry.second->IsQuestObject() },
                { "quest", entry.second->IsQuestObject() },
                { "unique", false },
                { "broken", false },
                { "repairable", false }
            });
        }
        return equipment;
    }

    [[nodiscard]] json CollectState(std::string_view a_message = {})
    {
        return {
            { "version", kPluginVersion },
            { "equipped", CollectEquippedItems() },
            { "repairQueue", json::array() },
            { "forge", {
                { "active", false },
                { "station", "" },
                { "refreshCost", 0 },
                { "refreshes", 0 },
                { "cards", json::array() }
            } },
            { "settings", {
                { "hotkey", { { "key", KeyName(g_settings.hotkey.keyCode) }, { "keyCode", g_settings.hotkey.keyCode }, { "shift", g_settings.hotkey.requireShift }, { "ctrl", g_settings.hotkey.requireCtrl }, { "alt", g_settings.hotkey.requireAlt } } },
                { "lowDurabilityThreshold", g_settings.lowDurabilityThreshold },
                { "weaponDisplaySeconds", g_settings.weaponDisplaySeconds },
                { "enableLowDurabilityWarning", g_settings.enableLowDurabilityWarning },
                { "allowEnchantedItemsToBreak", g_settings.allowEnchantedItemsToBreak }
            } },
            { "capturingHotkey", g_capturingHotkey },
            { "message", a_message }
        };
    }

    void SendState(std::string_view a_message)
    {
        if (!g_prisma || !g_view) return;
        const auto script = "window.DurabilityManager && window.DurabilityManager.receiveState(" + CollectState(a_message).dump() + ");";
        g_prisma->Invoke(g_view, script.c_str());
    }

    void ClosePanel()
    {
        if (!g_prisma || !g_view) return;
        g_panelVisible = false;
        SetPanelVisibilityInView(false);
        g_prisma->Unfocus(g_view);
        logger::info("Durability Manager panel closed.");
    }

    // Save transitions can run while Prisma is updating its render surface.
    // Reset only our own state here; calling Show/Hide/Focus/Invoke from a load
    // notification can leave Prisma's render and focus states out of sync.
    void ResetViewForLoad()
    {
        g_panelVisible = false;
        g_capturingHotkey = false;
    }

    [[nodiscard]] bool CloseFocusedPanel()
    {
        if (!g_prisma || !g_view || !g_prisma->HasFocus(g_view)) return false;
        ClosePanel();
        return true;
    }

    void TogglePanel()
    {
        if (!g_prisma || !g_view || !g_prisma->IsValid(g_view)) {
            logger::warn("Durability Manager panel toggle ignored because the Prisma view is invalid.");
            return;
        }
        logger::info(
            "Durability Manager panel toggle: visible={}, hidden={}, focused={}, order={}.",
            g_panelVisible,
            g_prisma->IsHidden(g_view),
            g_prisma->HasFocus(g_view),
            g_prisma->GetOrder(g_view));
        if (g_panelVisible) {
            ClosePanel();
            return;
        }
        g_panelVisible = true;
        g_prisma->SetOrder(g_view, kPanelRenderOrder);
        SetPanelVisibilityInView(true);
        SendState();
        logger::info("Durability Manager requested panel render at order {}; waiting for the web paint handshake.", g_prisma->GetOrder(g_view));
    }

    [[nodiscard]] bool CaptureHotkey(const std::uint32_t a_key, const bool a_shift, const bool a_ctrl, const bool a_alt)
    {
        if (!g_capturingHotkey || !g_prisma || !g_view || !g_prisma->HasFocus(g_view)) return false;
        const auto keyName = KeyName(a_key);
        if (keyName.starts_with("Scan ") || a_key == 0x01) {
            g_capturingHotkey = false;
            SendState("请选择字母、F 键、Tab、Enter 或 Space。\n");
            return true;
        }
        g_settings.hotkey = { a_key, a_shift, a_ctrl, a_alt };
        InputHandler::GetSingleton()->SetHotkey(g_settings.hotkey);
        WriteConfig();
        g_capturingHotkey = false;
        SendState("快捷键已更新并保存。");
        return true;
    }

    void HandleUIAction(const char* a_data)
    {
        try {
            const auto request = json::parse(a_data ? a_data : "{}");
            const auto type = request.value("type", "");
            if (type == "ready") {
                logger::info(
                    "Durability Manager web bridge {} is ready; restoring panel visibility={}.",
                    request.value("version", "<unknown>"),
                    g_panelVisible);
                if (g_panelVisible) {
                    SetPanelVisibilityInView(true);
                    SendState();
                }
                return;
            }
            if (type == "panelRendered") {
                if (!g_panelVisible) return;
                if (!g_prisma || !g_view || !g_prisma->IsValid(g_view) || !g_prisma->Focus(g_view, true)) {
                    g_panelVisible = false;
                    SetPanelVisibilityInView(false);
                    logger::warn("Durability Manager could not focus its Prisma view after the web paint handshake.");
                    return;
                }
                RequestPanelDOMState();
                logger::info("Durability Manager received the web paint handshake and queued focus.");
            } else if (type == "close") ClosePanel();
            else if (type == "beginHotkeyCapture") {
                g_capturingHotkey = true;
                SendState("请按下新的快捷键组合。");
            } else if (type == "cancelHotkeyCapture") {
                g_capturingHotkey = false;
                SendState("已取消快捷键修改。");
            } else if (type == "saveSettings") {
                g_settings.lowDurabilityThreshold = std::clamp(request.value("lowDurabilityThreshold", g_settings.lowDurabilityThreshold), 1U, 99U);
                g_settings.weaponDisplaySeconds = std::clamp(request.value("weaponDisplaySeconds", g_settings.weaponDisplaySeconds), 0.5F, 10.0F);
                g_settings.enableLowDurabilityWarning = request.value("enableLowDurabilityWarning", g_settings.enableLowDurabilityWarning);
                g_settings.allowEnchantedItemsToBreak = request.value("allowEnchantedItemsToBreak", g_settings.allowEnchantedItemsToBreak);
                WriteConfig();
                SendState("配置已保存至 DurabilityManager.ini。");
            } else if (type == "repair") {
                SendState("修复仅能在锻炉的“修复装备”入口中执行。");
            } else if (type == "hudHidden") return;
            else SendState();
        } catch (const std::exception& error) {
            logger::warn("Rejected Durability Manager panel request: {}", error.what());
            SendState("面板请求无效。");
        }
    }

    void SaveState(SKSE::SerializationInterface* a_serialization)
    {
        if (!a_serialization) return;
        std::vector<std::pair<ItemKey, DurabilitySnapshot>> saved;
        {
            std::scoped_lock lock(g_durabilityLock);
            saved.reserve(g_durability.size());
            for (const auto& entry : g_durability) saved.push_back(entry);
        }
        if (saved.size() > kMaxDurabilityRecords) saved.resize(kMaxDurabilityRecords);
        if (!a_serialization->OpenRecord(kDurabilityRecordType, kDurabilityRecordVersion)) return;

        const auto count = static_cast<std::uint32_t>(saved.size());
        if (!a_serialization->WriteRecordData(count)) return;
        for (const auto& [key, durability] : saved) {
            if (!a_serialization->WriteRecordData(key.baseFormID) ||
                !a_serialization->WriteRecordData(key.uniqueID) ||
                !a_serialization->WriteRecordData(durability.current) ||
                !a_serialization->WriteRecordData(durability.maximum) ||
                !a_serialization->WriteRecordData(durability.enhancementLevel) ||
                !a_serialization->WriteRecordData(durability.performanceBonus) ||
                !a_serialization->WriteRecordData(durability.weightReduction) ||
                !a_serialization->WriteRecordData(durability.attackSpeedBonus) ||
                !a_serialization->WriteRecordData(durability.wearReduction) ||
                !a_serialization->WriteRecordData(durability.chargeBonus)) {
                logger::warn("Could not finish saving durability state.");
                return;
            }
        }
    }

    void LoadState(SKSE::SerializationInterface* a_serialization)
    {
        if (!a_serialization) return;
        std::unordered_map<ItemKey, DurabilitySnapshot, ItemKeyHash> restored;
        std::uint32_t type = 0;
        std::uint32_t version = 0;
        std::uint32_t length = 0;
        while (a_serialization->GetNextRecordInfo(type, version, length)) {
            if (type != kDurabilityRecordType || version != kDurabilityRecordVersion) {
                std::vector<std::byte> ignored(length);
                a_serialization->ReadRecordData(ignored.data(), length);
                continue;
            }

            std::uint32_t count = 0;
            if (a_serialization->ReadRecordData(count) != sizeof(count) || count > kMaxDurabilityRecords) break;
            for (std::uint32_t index = 0; index < count; ++index) {
                RE::FormID savedBaseFormID = 0;
                std::uint16_t uniqueID = 0;
                DurabilitySnapshot durability{};
                if (a_serialization->ReadRecordData(savedBaseFormID) != sizeof(savedBaseFormID) ||
                    a_serialization->ReadRecordData(uniqueID) != sizeof(uniqueID) ||
                    a_serialization->ReadRecordData(durability.current) != sizeof(durability.current) ||
                    a_serialization->ReadRecordData(durability.maximum) != sizeof(durability.maximum) ||
                    a_serialization->ReadRecordData(durability.enhancementLevel) != sizeof(durability.enhancementLevel) ||
                    a_serialization->ReadRecordData(durability.performanceBonus) != sizeof(durability.performanceBonus) ||
                    a_serialization->ReadRecordData(durability.weightReduction) != sizeof(durability.weightReduction) ||
                    a_serialization->ReadRecordData(durability.attackSpeedBonus) != sizeof(durability.attackSpeedBonus) ||
                    a_serialization->ReadRecordData(durability.wearReduction) != sizeof(durability.wearReduction) ||
                    a_serialization->ReadRecordData(durability.chargeBonus) != sizeof(durability.chargeBonus)) {
                    logger::warn("Could not finish loading durability state.");
                    break;
                }
                RE::FormID resolvedBaseFormID = 0;
                if (!a_serialization->ResolveFormID(savedBaseFormID, resolvedBaseFormID)) continue;
                durability.maximum = (std::max)(1.0F, durability.maximum);
                durability.current = std::clamp(durability.current, 0.0F, durability.maximum);
                durability.wearReduction = std::clamp(durability.wearReduction, 0.0F, 0.95F);
                restored[ItemKey{ resolvedBaseFormID, uniqueID }] = durability;
            }
        }
        std::size_t restoredCount = 0;
        {
            std::scoped_lock lock(g_durabilityLock);
            g_durability = std::move(restored);
            g_lowDurabilityWarnings.clear();
            g_weaponNotificationTimes.clear();
            restoredCount = g_durability.size();
        }
        logger::info("Loaded {} durability instance records.", restoredCount);
    }

    void RevertState(SKSE::SerializationInterface*)
    {
        std::scoped_lock lock(g_durabilityLock);
        g_durability.clear();
        g_lowDurabilityWarnings.clear();
        g_weaponNotificationTimes.clear();
        g_nextGeneratedUniqueID = 0x8000U;
    }

    void RecreatePrismaView(std::string_view a_reason)
    {
        if (!g_prisma) return;

        const auto previousView = g_view;
        g_view = 0;
        g_panelVisible = false;
        g_capturingHotkey = false;
        if (previousView && g_prisma->IsValid(previousView)) {
            g_prisma->Destroy(previousView);
            logger::info("Durability Manager destroyed pre-transition Prisma view {}.", previousView);
        }

        g_view = g_prisma->CreateView("DurabilityManager/index.html", [](const PrismaView a_view) {
            g_prisma->SetOrder(a_view, kPanelRenderOrder);
            logger::info("Durability Manager post-transition Prisma DOM is ready: {}.", a_view);
        });
        if (!g_view) {
            logger::critical("Durability Manager Prisma view could not be created after {}.", a_reason);
            return;
        }
        g_prisma->SetOrder(g_view, kPanelRenderOrder);
        g_prisma->RegisterJSListener(g_view, "durabilityManagerAction", HandleUIAction);
        logger::info("Durability Manager created Prisma view {} after {}.", g_view, a_reason);
    }

    void OnSKSEMessage(SKSE::MessagingInterface::Message* a_message)
    {
        if (a_message->type == SKSE::MessagingInterface::kPreLoadGame) {
            logger::info("Durability Manager received PreLoadGame; releasing view state.");
            ResetViewForLoad();
            return;
        }
        if (a_message->type == SKSE::MessagingInterface::kPostLoadGame) {
            ResetViewForLoad();
            RecreatePrismaView("PostLoadGame");
            return;
        }
        if (a_message->type == SKSE::MessagingInterface::kNewGame) {
            ResetViewForLoad();
            RecreatePrismaView("NewGame");
            return;
        }
        if (a_message->type != SKSE::MessagingInterface::kDataLoaded) return;
        g_prisma = PRISMA_UI_API::RequestPluginAPI();
        if (!g_prisma) {
            logger::critical("Prisma UI v1 is unavailable; Durability Manager will remain disabled.");
            return;
        }
        LoadConfig();
        const auto input = InputHandler::GetSingleton();
        input->SetHotkey(g_settings.hotkey);
        input->SetToggleCallback(TogglePanel);
        input->SetEscapeCallback(CloseFocusedPanel);
        input->SetCaptureCallback(CaptureHotkey);
        input->RegisterSink();
        EquipmentEventSink::GetSingleton()->Register();
        logger::info("Durability Manager loaded; Prisma view creation is deferred until PostLoadGame or NewGame.");
    }
}

extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Load(const SKSE::LoadInterface* a_skse)
{
    REL::Module::reset();
    const auto messaging = reinterpret_cast<SKSE::MessagingInterface*>(a_skse->QueryInterface(SKSE::LoadInterface::kMessaging));
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

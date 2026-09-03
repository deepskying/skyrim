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
    };

    Settings g_settings{};
    bool g_capturingHotkey = false;
    bool g_panelVisible = false;
    bool g_hudVisible = false;
    std::uint32_t g_hudSequence = 0;

    struct DurabilitySnapshot
    {
        std::uint32_t current = 100;
        std::uint32_t maximum = 100;
        std::uint32_t enhancementLevel = 0;
        std::int32_t performanceBonus = 0;
        float weightReduction = 0.0F;
        float attackSpeedBonus = 0.0F;
        float wearReduction = 0.0F;
        float chargeBonus = 0.0F;
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

    // This is deliberately kept behind one accessor: the persistence and wear
    // bridge will replace the default snapshot without changing HUD consumers.
    std::unordered_map<RE::FormID, DurabilitySnapshot> g_durability;
    std::unordered_set<RE::FormID> g_lowDurabilityWarnings;
    std::unordered_map<RE::FormID, std::chrono::steady_clock::time_point> g_weaponNotificationTimes;

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

    [[nodiscard]] DurabilitySnapshot GetDurability(const RE::TESBoundObject* a_item)
    {
        if (!a_item) return {};
        if (const auto found = g_durability.find(a_item->GetFormID()); found != g_durability.end()) return found->second;
        return {};
    }

    [[nodiscard]] std::string DisplayName(const RE::TESBoundObject* a_item)
    {
        const auto* fullName = a_item ? a_item->As<RE::TESFullName>() : nullptr;
        const auto* name = fullName ? fullName->GetFullName() : nullptr;
        return name && name[0] ? name : "未命名武器";
    }

    void UpdateViewVisibility()
    {
        if (g_prisma && g_view && !g_panelVisible && !g_hudVisible) g_prisma->Hide(g_view);
    }

    void ShowHUD(std::string_view a_kind, std::string_view a_title, std::string_view a_detail, const float a_seconds)
    {
        if (!g_prisma || !g_view) return;
        const auto message = json{
            { "id", ++g_hudSequence },
            { "kind", a_kind },
            { "title", a_title },
            { "detail", a_detail },
            { "durationMilliseconds", static_cast<std::uint32_t>(a_seconds * 1000.0F) }
        };
        g_hudVisible = true;
        g_prisma->Show(g_view);
        const auto script = "window.DurabilityManager && window.DurabilityManager.showHud(" + message.dump() + ");";
        g_prisma->Invoke(g_view, script.c_str());
    }

    void ShowWeaponDurability(const RE::TESObjectWEAP* a_weapon)
    {
        if (!a_weapon) return;
        const auto now = std::chrono::steady_clock::now();
        const auto formID = a_weapon->GetFormID();
        if (const auto previous = g_weaponNotificationTimes.find(formID); previous != g_weaponNotificationTimes.end() && now - previous->second < std::chrono::milliseconds(250)) return;
        g_weaponNotificationTimes[formID] = now;

        const auto durability = GetDurability(a_weapon);
        const auto percentage = durability.maximum ? (durability.current * 100U / durability.maximum) : 0U;
        ShowHUD("weapon", DisplayName(a_weapon), std::to_string(durability.current) + " / " + std::to_string(durability.maximum) + "  ·  " + std::to_string(percentage) + "%", g_settings.weaponDisplaySeconds);

        if (!g_settings.enableLowDurabilityWarning || !durability.maximum) return;
        if (percentage < g_settings.lowDurabilityThreshold) {
            if (g_lowDurabilityWarnings.insert(formID).second) {
                ShowHUD("warning", "耐久度过低", DisplayName(a_weapon) + "：" + std::to_string(percentage) + "%（请尽快修复）", g_settings.weaponDisplaySeconds);
            }
        } else {
            g_lowDurabilityWarnings.erase(formID);
        }
    }

    class EquipmentEventSink final : public RE::BSTEventSink<RE::TESEquipEvent>, public RE::BSTEventSink<RE::BSAnimationGraphEvent>
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
            const auto durability = GetDurability(item);
            const auto* weapon = item->As<RE::TESObjectWEAP>();
            const auto* armor = item->As<RE::TESObjectARMO>();
            const auto enchantment = EnchantmentName(entry.second.get());
            equipment.push_back({
                { "id", item->GetFormID() },
                { "name", DisplayName(item) },
                { "slot", EquipmentType(item) },
                { "category", EquipmentCategory(item) },
                { "current", durability.current },
                { "maximum", durability.maximum },
                { "enhancementLevel", durability.enhancementLevel },
                { "damage", weapon ? static_cast<std::int32_t>(weapon->GetAttackDamage()) + durability.performanceBonus : 0 },
                { "armor", armor ? static_cast<std::int32_t>(const_cast<RE::TESObjectARMO*>(armor)->GetArmorRating()) + durability.performanceBonus : 0 },
                { "weight", (std::max)(0.1F, EquipmentWeight(item) - durability.weightReduction) },
                { "attackSpeed", weapon ? (std::min)(weapon->GetSpeed() * 2.0F, weapon->GetSpeed() * (1.0F + durability.attackSpeedBonus)) : 0.0F },
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

    void SendState(std::string_view a_message = {})
    {
        if (!g_prisma || !g_view) return;
        const auto script = "window.DurabilityManager && window.DurabilityManager.receiveState(" + CollectState(a_message).dump() + ");";
        g_prisma->Invoke(g_view, script.c_str());
    }

    void ClosePanel()
    {
        if (!g_prisma || !g_view) return;
        g_panelVisible = false;
        g_prisma->Invoke(g_view, "window.DurabilityManager && window.DurabilityManager.setPanelVisible(false);");
        g_prisma->Unfocus(g_view);
        UpdateViewVisibility();
    }

    [[nodiscard]] bool CloseFocusedPanel()
    {
        if (!g_prisma || !g_view || !g_prisma->HasFocus(g_view)) return false;
        ClosePanel();
        return true;
    }

    void TogglePanel()
    {
        if (!g_prisma || !g_view) return;
        if (g_panelVisible) {
            ClosePanel();
            return;
        }
        g_panelVisible = true;
        g_prisma->Show(g_view);
        g_prisma->Invoke(g_view, "window.DurabilityManager && window.DurabilityManager.setPanelVisible(true);");
        g_prisma->Focus(g_view, true);
        SendState();
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
            if (type == "ready") return;
            if (type == "close") ClosePanel();
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
            } else if (type == "hudHidden") {
                if (request.value("id", 0U) == g_hudSequence) {
                    g_hudVisible = false;
                    UpdateViewVisibility();
                }
            } else SendState();
        } catch (const std::exception& error) {
            logger::warn("Rejected Durability Manager panel request: {}", error.what());
            SendState("面板请求无效。");
        }
    }

    void OnSKSEMessage(SKSE::MessagingInterface::Message* a_message)
    {
        if (a_message->type != SKSE::MessagingInterface::kDataLoaded) return;
        g_prisma = PRISMA_UI_API::RequestPluginAPI();
        if (!g_prisma) {
            logger::critical("Prisma UI v1 is unavailable; Durability Manager will remain disabled.");
            return;
        }
        g_view = g_prisma->CreateView("DurabilityManager/index.html");
        if (!g_view) {
            logger::critical("Durability Manager Prisma view could not be created.");
            return;
        }
        g_prisma->RegisterJSListener(g_view, "durabilityManagerAction", HandleUIAction);
        g_prisma->Hide(g_view);
        LoadConfig();
        const auto input = InputHandler::GetSingleton();
        input->SetHotkey(g_settings.hotkey);
        input->SetToggleCallback(TogglePanel);
        input->SetEscapeCallback(CloseFocusedPanel);
        input->SetCaptureCallback(CaptureHotkey);
        input->RegisterSink();
        EquipmentEventSink::GetSingleton()->Register();
        logger::info("Durability Manager loaded.");
    }
}

extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Load(const SKSE::LoadInterface* a_skse)
{
    REL::Module::reset();
    const auto messaging = reinterpret_cast<SKSE::MessagingInterface*>(a_skse->QueryInterface(SKSE::LoadInterface::kMessaging));
    if (!messaging) return false;
    SKSE::Init(a_skse);
    messaging->RegisterListener("SKSE", OnSKSEMessage);
    return true;
}

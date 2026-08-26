#include "PrismaUI_API.h"
#include "input_handler.h"

#include <nlohmann/json.hpp>

namespace
{
    using json = nlohmann::json;

    PRISMA_UI_API::IVPrismaUI1* g_prisma = nullptr;
    PrismaView g_view = 0;

    struct HotkeySettings
    {
        HotkeyConfig openPanel{};
        HotkeyConfig favorite{ 0x21, false, false, false };  // F
        HotkeyConfig activate{ 0x1C, false, false, false };  // Enter
        HotkeyConfig pageToggle{ 0x38, false, false, true }; // Alt
        HotkeyConfig search{ 0x35, false, false, false };    // /
    };

    HotkeySettings g_hotkeys{};
    std::optional<std::string> g_capturingAction;

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
        if (key == "ALT") return 0x38;
        if (key == "SPACE") return 0x39;
        if (key == "TAB") return 0x0F;
        if (key == "ENTER") return 0x1C;
        if (key == "SLASH" || key == "/") return 0x35;
        if (key == "F11") return 0x57;
        if (key == "F12") return 0x58;
        if (key.size() == 2 && key[0] == 'F' && key[1] >= '1' && key[1] <= '9') return 0x3A + (key[1] - '0');
        if (key == "F10") return 0x44;
        try {
            std::size_t consumed = 0;
            const auto value = std::stoul(key, &consumed, 0);
            if (consumed == key.size() && value <= 0xFF) return static_cast<std::uint32_t>(value);
        } catch (const std::exception&) {}
        return std::nullopt;
    }

    [[nodiscard]] bool ParseConfigBool(const std::string& a_value, bool a_fallback)
    {
        const auto value = NormalizeKeyName(a_value);
        if (value == "TRUE" || value == "YES" || value == "ON" || value == "1") return true;
        if (value == "FALSE" || value == "NO" || value == "OFF" || value == "0") return false;
        return a_fallback;
    }

    [[nodiscard]] std::string KeyName(const std::uint32_t a_key)
    {
        static constexpr std::array<std::uint32_t, 26> letterScanCodes{
            0x1E, 0x30, 0x2E, 0x20, 0x12, 0x21, 0x22, 0x23, 0x17, 0x24, 0x25, 0x26, 0x32,
            0x31, 0x18, 0x19, 0x10, 0x13, 0x1F, 0x14, 0x16, 0x2F, 0x11, 0x2D, 0x15, 0x2C
        };
        for (std::size_t index = 0; index < letterScanCodes.size(); ++index) {
            if (letterScanCodes[index] == a_key) return std::string(1, static_cast<char>('A' + index));
        }
        if (a_key >= 0x02 && a_key <= 0x0A) return std::string(1, static_cast<char>('1' + a_key - 0x02));
        if (a_key == 0x0B) return "0";
        if (a_key == 0x01) return "Esc";
        if (a_key == 0x38 || a_key == 0xB8) return "Alt";
        if (a_key == 0x0F) return "Tab";
        if (a_key == 0x1C) return "Enter";
        if (a_key == 0x35) return "/";
        if (a_key == 0x39) return "Space";
        if (a_key >= 0x3B && a_key <= 0x44) return "F" + std::to_string(a_key - 0x3A);
        if (a_key == 0x57) return "F11";
        if (a_key == 0x58) return "F12";
        return "Scan " + std::to_string(a_key);
    }

    [[nodiscard]] std::filesystem::path ConfigPath()
    {
        const auto modulePath = REL::Module::get().filePath();
        return std::filesystem::path(modulePath.data()).parent_path() / "Data" / "SKSE" / "Plugins" / "InventoryManager.ini";
    }

    void ApplyHotkeySetting(HotkeyConfig& a_hotkey, const std::string& a_setting, const std::string& a_value)
    {
        if (a_setting == "KEY") {
            if (const auto parsed = ParseKeyCode(a_value)) a_hotkey.keyCode = *parsed;
        } else if (a_setting == "SHIFT") a_hotkey.requireShift = ParseConfigBool(a_value, a_hotkey.requireShift);
        else if (a_setting == "CTRL") a_hotkey.requireCtrl = ParseConfigBool(a_value, a_hotkey.requireCtrl);
        else if (a_setting == "ALT") a_hotkey.requireAlt = ParseConfigBool(a_value, a_hotkey.requireAlt);
    }

    [[nodiscard]] HotkeySettings LoadHotkeySettings()
    {
        HotkeySettings hotkeys;
        try {
            std::ifstream configFile(ConfigPath());
            if (!configFile) {
                logger::warn("InventoryManager.ini was not found; using Shift+D.");
                return hotkeys;
            }
            HotkeyConfig* activeHotkey = nullptr;
            std::string line;
            while (std::getline(configFile, line)) {
                if (const auto comment = line.find_first_of(";#"); comment != std::string::npos) line.erase(comment);
                const auto normalizedLine = NormalizeKeyName(line);
                if (normalizedLine.empty()) continue;
                if (normalizedLine.front() == '[' && normalizedLine.back() == ']') {
                    if (normalizedLine == "[HOTKEY]" || normalizedLine == "[OPENPANEL]") activeHotkey = std::addressof(hotkeys.openPanel);
                    else if (normalizedLine == "[FAVORITE]") activeHotkey = std::addressof(hotkeys.favorite);
                    else if (normalizedLine == "[ACTIVATE]") activeHotkey = std::addressof(hotkeys.activate);
                    else if (normalizedLine == "[PAGETOGGLE]") activeHotkey = std::addressof(hotkeys.pageToggle);
                    else if (normalizedLine == "[SEARCH]") activeHotkey = std::addressof(hotkeys.search);
                    else activeHotkey = nullptr;
                    continue;
                }
                if (!activeHotkey) continue;
                const auto separator = line.find('=');
                if (separator == std::string::npos) continue;
                const auto setting = NormalizeKeyName(line.substr(0, separator));
                const auto value = line.substr(separator + 1);
                ApplyHotkeySetting(*activeHotkey, setting, value);
            }
        } catch (const std::exception& error) {
            logger::warn("Could not read InventoryManager.ini; using Shift+D. {}", error.what());
        }
        return hotkeys;
    }

    void WriteHotkeyConfig(const HotkeySettings& a_hotkeys)
    {
        const auto writeBinding = [](std::ofstream& a_file, const char* a_section, const HotkeyConfig& a_hotkey) {
            a_file << '[' << a_section << "]\n";
            a_file << "Key=" << KeyName(a_hotkey.keyCode) << "\n";
            a_file << "Shift=" << (a_hotkey.requireShift ? "true" : "false") << "\n";
            a_file << "Ctrl=" << (a_hotkey.requireCtrl ? "true" : "false") << "\n";
            a_file << "Alt=" << (a_hotkey.requireAlt ? "true" : "false") << "\n\n";
        };
        std::ofstream configFile(ConfigPath(), std::ios::trunc);
        if (!configFile) {
            logger::warn("Could not write InventoryManager.ini.");
            return;
        }
        configFile << "; Skyrim Inventory Manager hotkey configuration.\n; Changes made in the panel take effect immediately.\n\n";
        writeBinding(configFile, "Hotkey", a_hotkeys.openPanel);
        writeBinding(configFile, "Favorite", a_hotkeys.favorite);
        writeBinding(configFile, "Activate", a_hotkeys.activate);
        writeBinding(configFile, "PageToggle", a_hotkeys.pageToggle);
        writeBinding(configFile, "Search", a_hotkeys.search);
    }

    [[nodiscard]] json HotkeyJson(const char* a_action, const HotkeyConfig& a_hotkey)
    {
        return {
            { "action", a_action }, { "key", KeyName(a_hotkey.keyCode) }, { "keyCode", a_hotkey.keyCode },
            { "shift", a_hotkey.requireShift }, { "ctrl", a_hotkey.requireCtrl }, { "alt", a_hotkey.requireAlt }
        };
    }

    [[nodiscard]] std::string ItemCategory(const RE::TESBoundObject* a_item)
    {
        if (!a_item) return "misc";
        switch (a_item->GetFormType()) {
        case RE::FormType::Weapon: return "weapons";
        case RE::FormType::Armor: return "armor";
        case RE::FormType::Scroll: return "scrolls";
        case RE::FormType::Ingredient: return "ingredients";
        case RE::FormType::AlchemyItem:
            if (const auto alchemy = a_item->As<RE::AlchemyItem>(); alchemy && alchemy->IsFood()) return "food";
            return "potions";
        default: return "misc";
        }
    }

    [[nodiscard]] std::string ItemIcon(const std::string_view a_category)
    {
        if (a_category == "weapons") return "weapon";
        if (a_category == "armor") return "armor";
        if (a_category == "potions") return "potion";
        if (a_category == "scrolls") return "scroll";
        if (a_category == "food") return "food";
        if (a_category == "ingredients") return "ingredient";
        return "misc";
    }

    [[nodiscard]] std::string ItemDescription(RE::TESBoundObject* a_item)
    {
        const auto description = a_item ? a_item->As<RE::TESDescription>() : nullptr;
        if (!description) return {};
        RE::BSString text;
        description->GetDescription(text, a_item);
        return text.c_str() ? text.c_str() : "";
    }

    [[nodiscard]] json CollectEnchantmentEffects(RE::TESBoundObject* a_item, const RE::InventoryEntryData* a_entry)
    {
        json effects = json::array();
        auto enchantment = a_entry ? a_entry->GetEnchantment() : nullptr;
        if (!enchantment) {
            const auto enchantable = a_item ? a_item->As<RE::TESEnchantableForm>() : nullptr;
            enchantment = enchantable ? enchantable->formEnchanting : nullptr;
        }
        if (!enchantment) return effects;

        for (const auto effect : enchantment->effects) {
            if (!effect || !effect->baseEffect) continue;
            const auto* name = effect->baseEffect->GetFullName();
            json row{ { "name", name && name[0] ? name : "Enchantment effect" } };
            if (const auto magnitude = effect->GetMagnitude(); magnitude != 0.0F) row["magnitude"] = magnitude;
            if (const auto duration = effect->GetDuration(); duration != 0) row["duration"] = duration;
            effects.push_back(std::move(row));
        }
        return effects;
    }

    void AddEquipmentComparison(json& a_row, RE::PlayerCharacter* a_player, RE::TESBoundObject* a_item, const RE::TESObjectREFR::InventoryItemMap& a_inventory)
    {
        if (const auto weapon = a_item->As<RE::TESObjectWEAP>()) {
            const auto equipped = a_player->GetEquippedObject(false);
            const auto equippedWeapon = equipped ? equipped->As<RE::TESObjectWEAP>() : nullptr;
            const auto value = static_cast<float>(weapon->GetAttackDamage());
            const auto equippedValue = equippedWeapon ? static_cast<float>(equippedWeapon->GetAttackDamage()) : 0.0F;
            a_row["statLabel"] = "伤害";
            a_row["statValue"] = value;
            a_row["equippedValue"] = equippedValue;
            a_row["statDelta"] = value - equippedValue;
            return;
        }

        const auto armor = a_item->As<RE::TESObjectARMO>();
        if (!armor) return;
        const auto targetMask = std::to_underlying(armor->GetSlotMask());
        float equippedValue = 0.0F;
        for (const auto& [equippedItem, entry] : a_inventory) {
            if (!equippedItem || !entry.second || !entry.second->IsWorn()) continue;
            const auto equippedArmor = equippedItem->As<RE::TESObjectARMO>();
            if (!equippedArmor || (std::to_underlying(equippedArmor->GetSlotMask()) & targetMask) == 0) continue;
            equippedValue += equippedArmor->GetArmorRating();
        }
        const auto value = armor->GetArmorRating();
        a_row["statLabel"] = "护甲";
        a_row["statValue"] = value;
        a_row["equippedValue"] = equippedValue;
        a_row["statDelta"] = value - equippedValue;
    }

    [[nodiscard]] json CollectInventory()
    {
        json items = json::array();
        const auto player = RE::PlayerCharacter::GetSingleton();
        if (!player) return items;

        const auto inventory = player->GetInventory();
        for (const auto& [item, entry] : inventory) {
            if (!item || entry.first <= 0) continue;
            const auto category = ItemCategory(item);
            const auto* fullName = item->As<RE::TESFullName>();
            const auto* name = fullName ? fullName->GetFullName() : nullptr;
            json row{
                { "id", item->GetFormID() },
                { "name", name && name[0] ? name : "Unnamed item" },
                { "category", category },
                { "icon", ItemIcon(category) },
                { "count", entry.first },
                { "weight", item->GetWeight() },
                { "value", (std::max)(0, item->GetGoldValue()) },
                { "favorited", entry.second && entry.second->IsFavorited() },
                { "equipped", entry.second && entry.second->IsWorn() },
                { "enchanted", entry.second && entry.second->IsEnchanted() },
                { "quest", entry.second && entry.second->IsQuestObject() },
                { "description", ItemDescription(item) },
                { "enchantments", CollectEnchantmentEffects(item, entry.second.get()) }
            };
            AddEquipmentComparison(row, player, item, inventory);
            items.push_back(std::move(row));
        }
        return items;
    }

    [[nodiscard]] std::string MagicCategory(const RE::SpellItem* a_spell)
    {
        if (!a_spell) return "status";
        switch (a_spell->GetSpellType()) {
        case RE::MagicSystem::SpellType::kPower:
        case RE::MagicSystem::SpellType::kLesserPower:
            return "powers";
        case RE::MagicSystem::SpellType::kAbility:
        case RE::MagicSystem::SpellType::kDisease:
            return "status";
        default:
            break;
        }

        switch (a_spell->GetAssociatedSkill()) {
        case RE::ActorValue::kDestruction: return "destruction";
        case RE::ActorValue::kAlteration: return "alteration";
        case RE::ActorValue::kIllusion: return "illusion";
        case RE::ActorValue::kRestoration: return "restoration";
        case RE::ActorValue::kConjuration: return "conjuration";
        default: return "status";
        }
    }

    [[nodiscard]] std::string MagicIcon(const std::string_view a_category)
    {
        if (a_category == "destruction") return "destruction";
        if (a_category == "alteration") return "alteration";
        if (a_category == "illusion") return "illusion";
        if (a_category == "restoration") return "restoration";
        if (a_category == "conjuration") return "conjuration";
        if (a_category == "shouts") return "shout";
        if (a_category == "powers") return "power";
        return "status";
    }

    [[nodiscard]] bool IsMagicFavorited(const RE::TESForm* a_form)
    {
        const auto favorites = RE::MagicFavorites::GetSingleton();
        if (!favorites || !a_form) return false;
        return std::ranges::find(favorites->spells, a_form) != favorites->spells.end();
    }

    [[nodiscard]] bool IsMagicEquipped(const RE::PlayerCharacter* a_player, const RE::TESForm* a_form)
    {
        if (!a_player || !a_form) return false;
        const auto& runtime = a_player->GetActorRuntimeData();
        return runtime.selectedPower == a_form || std::find(std::begin(runtime.selectedSpells), std::end(runtime.selectedSpells), a_form) != std::end(runtime.selectedSpells);
    }

    void AddSpell(json& a_items, std::unordered_set<RE::FormID>& a_seen, RE::SpellItem* a_spell, const RE::PlayerCharacter* a_player)
    {
        if (!a_spell || !a_seen.insert(a_spell->GetFormID()).second) return;
        const auto category = MagicCategory(a_spell);
        const auto* name = a_spell->GetFullName();
        a_items.push_back({
            { "id", a_spell->GetFormID() },
            { "name", name && name[0] ? name : "Unnamed spell" },
            { "category", category },
            { "icon", MagicIcon(category) },
            { "cost", a_spell->CalculateMagickaCost(const_cast<RE::PlayerCharacter*>(a_player)) },
            { "favorited", IsMagicFavorited(a_spell) },
            { "equipped", IsMagicEquipped(a_player, a_spell) },
            { "active", category == "status" }
        });
    }

    void AddActiveStatus(json& a_items, std::unordered_set<RE::FormID>& a_seen, const RE::ActiveEffect* a_effect)
    {
        if (!a_effect) return;
        const auto baseEffect = a_effect->GetBaseObject();
        if (!baseEffect || !a_seen.insert(baseEffect->GetFormID()).second) return;
        const auto* effectName = baseEffect->GetFullName();
        const auto* spellName = a_effect->spell ? a_effect->spell->GetFullName() : nullptr;
        const auto remaining = (std::max)(0.0F, a_effect->duration - a_effect->elapsedSeconds);
        a_items.push_back({
            { "id", baseEffect->GetFormID() },
            { "name", effectName && effectName[0] ? effectName : "Active effect" },
            { "category", "status" },
            { "icon", "status" },
            { "cooldown", remaining },
            { "favorited", false },
            { "equipped", false },
            { "active", true },
            { "description", spellName && spellName[0] ? spellName : "Active effect on the player." }
        });
    }

    [[nodiscard]] json CollectMagic()
    {
        json items = json::array();
        std::unordered_set<RE::FormID> seen;
        const auto player = RE::PlayerCharacter::GetSingleton();
        if (!player) return items;

        if (const auto actorBase = player->GetActorBase()) {
            if (const auto spellList = actorBase->GetSpellList()) {
                for (std::uint32_t index = 0; spellList->spells && index < spellList->numSpells; ++index) {
                    AddSpell(items, seen, spellList->spells[index], player);
                }
                for (std::uint32_t index = 0; spellList->shouts && index < spellList->numShouts; ++index) {
                    const auto shout = spellList->shouts[index];
                    if (!shout || !seen.insert(shout->GetFormID()).second) continue;
                    const auto* name = shout->GetFullName();
                    items.push_back({
                        { "id", shout->GetFormID() },
                        { "name", name && name[0] ? name : "Unnamed shout" },
                        { "category", "shouts" },
                        { "icon", "shout" },
                        { "cooldown", shout->variations[RE::TESShout::VariationID::kThree].recoveryTime },
                        { "favorited", IsMagicFavorited(shout) },
                        { "equipped", IsMagicEquipped(player, shout) }
                    });
                }
            }
        }

        for (const auto spell : player->GetActorRuntimeData().addedSpells) {
            AddSpell(items, seen, spell, player);
        }
        std::unordered_set<RE::FormID> activeEffects;
        if (const auto effects = player->AsMagicTarget()->GetActiveEffectList()) {
            for (const auto effect : *effects) {
                AddActiveStatus(items, activeEffects, effect);
            }
        }
        return items;
    }

    [[nodiscard]] std::int32_t CollectGold(const RE::PlayerCharacter* a_player)
    {
        if (!a_player) return 0;
        // Gold001 is the immutable Skyrim master record. Avoid Actor::GetGoldAmount(),
        // which creates a second full inventory snapshot just to locate this item.
        const auto gold = RE::TESForm::LookupByID<RE::TESObjectMISC>(RE::FormID{ 0x0000000F });
        return gold ? const_cast<RE::PlayerCharacter*>(a_player)->GetItemCount(gold) : 0;
    }

    [[nodiscard]] json CollectState(std::string_view a_message = {})
    {
        const auto player = RE::PlayerCharacter::GetSingleton();
        const auto currentWeight = player ? player->AsActorValueOwner()->GetActorValue(RE::ActorValue::kInventoryWeight) : 0.0F;
        const auto maxWeight = player ? player->AsActorValueOwner()->GetActorValue(RE::ActorValue::kCarryWeight) : 0.0F;
        return {
            { "inventory", CollectInventory() },
            { "magic", CollectMagic() },
            { "player", {
                { "gold", CollectGold(player) },
                { "weight", currentWeight },
                { "weightMax", maxWeight }
            } },
            { "hotkeys", json::array({
                HotkeyJson("open", g_hotkeys.openPanel),
                HotkeyJson("favorite", g_hotkeys.favorite),
                HotkeyJson("activate", g_hotkeys.activate),
                HotkeyJson("pageToggle", g_hotkeys.pageToggle),
                HotkeyJson("search", g_hotkeys.search)
            }) },
            { "capturingAction", g_capturingAction ? json(*g_capturingAction) : json(nullptr) },
            { "message", a_message }
        };
    }

    void SendState(std::string_view a_message = {})
    {
        if (!g_prisma || !g_view) return;
        const auto payload = CollectState(a_message).dump();
        const auto script = "window.InventoryManager && window.InventoryManager.receiveState(" + payload + ");";
        g_prisma->Invoke(g_view, script.c_str());
    }

    void SendStateNextFrame(std::string a_message = {})
    {
        if (const auto task = SKSE::GetTaskInterface()) {
            task->AddTask([message = std::move(a_message)] { SendState(message); });
        } else {
            SendState(a_message);
        }
    }

    void ClosePanel()
    {
        if (!g_prisma || !g_view) return;
        g_prisma->Unfocus(g_view);
        g_prisma->Hide(g_view);
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
        if (g_prisma->HasFocus(g_view)) {
            ClosePanel();
            return;
        }
        g_prisma->Show(g_view);
        g_prisma->Focus(g_view, true);
        SendState();
    }

    [[nodiscard]] bool InvokeFocusedView(const char* a_functionName)
    {
        if (!g_prisma || !g_view || !g_prisma->HasFocus(g_view)) return false;
        const auto script = std::string("window.InventoryManager && window.InventoryManager.") + a_functionName + "();";
        g_prisma->Invoke(g_view, script.c_str());
        return true;
    }

    [[nodiscard]] bool NavigateFocusedView(const std::uint32_t a_key)
    {
        const char* direction = nullptr;
        switch (a_key) {
        case 0x1E:  // A
        case 0xCB:  // Left arrow
            direction = "left";
            break;
        case 0x20:  // D
        case 0xCD:  // Right arrow
            direction = "right";
            break;
        case 0x11:  // W
        case 0xC8:  // Up arrow
            direction = "up";
            break;
        case 0x1F:  // S
        case 0xD0:  // Down arrow
            direction = "down";
            break;
        default:
            return false;
        }
        if (!g_prisma || !g_view || !g_prisma->HasFocus(g_view)) return false;
        const auto script = std::string("window.InventoryManager && window.InventoryManager.navigate(\"") + direction + "\");";
        g_prisma->Invoke(g_view, script.c_str());
        return true;
    }

    [[nodiscard]] HotkeyConfig* FindHotkey(const std::string_view a_action)
    {
        if (a_action == "open") return std::addressof(g_hotkeys.openPanel);
        if (a_action == "favorite") return std::addressof(g_hotkeys.favorite);
        if (a_action == "activate") return std::addressof(g_hotkeys.activate);
        if (a_action == "pageToggle") return std::addressof(g_hotkeys.pageToggle);
        if (a_action == "search") return std::addressof(g_hotkeys.search);
        return nullptr;
    }

    [[nodiscard]] bool CaptureHotkey(const std::uint32_t a_key, const bool a_shift, const bool a_ctrl, const bool a_alt)
    {
        if (!g_capturingAction || !g_prisma || !g_view || !g_prisma->HasFocus(g_view)) return false;
        const auto action = *g_capturingAction;
        const auto hotkey = FindHotkey(action);
        if (!hotkey) {
            g_capturingAction.reset();
            SendState("The requested shortcut is unavailable.");
            return true;
        }
        const auto keyName = KeyName(a_key);
        if (keyName.starts_with("Scan ") || a_key == 0x01) {
            g_capturingAction.reset();
            SendState("Choose a letter, number, F key, Tab, Enter, Space, or Slash.");
            return true;
        }
        if (action != "open" && (a_key == 0x11 || a_key == 0x1E || a_key == 0x1F || a_key == 0x20)) {
            g_capturingAction.reset();
            SendState("W, A, S, and D are reserved for fixed panel navigation.");
            return true;
        }
        *hotkey = { a_key, a_shift, a_ctrl, a_alt };
        if (action == "open") InputHandler::GetSingleton()->SetHotkey(*hotkey);
        else if (action == "pageToggle") InputHandler::GetSingleton()->SetPageToggleHotkey(*hotkey);
        else if (action == "search") InputHandler::GetSingleton()->SetSearchHotkey(*hotkey);
        WriteHotkeyConfig(g_hotkeys);
        g_capturingAction.reset();
        SendState("Shortcut updated.");
        return true;
    }

    [[nodiscard]] std::string ToggleMagicFavorite(RE::FormID a_formID)
    {
        const auto form = RE::TESForm::LookupByID(a_formID);
        const auto favorites = RE::MagicFavorites::GetSingleton();
        if (!form || !favorites) return "Magic item was not found.";
        if (IsMagicFavorited(form)) {
            favorites->RemoveFavorite(form);
            return "Removed from favorites.";
        }
        favorites->SetFavorite(form);
        return "Added to favorites.";
    }

    [[nodiscard]] std::string ToggleInventoryFavorite(RE::FormID a_formID)
    {
        const auto player = RE::PlayerCharacter::GetSingleton();
        const auto item = RE::TESForm::LookupByID<RE::TESBoundObject>(a_formID);
        const auto changes = player ? player->GetInventoryChanges() : nullptr;
        if (!player || !item || !changes || !changes->entryList) return "Inventory item was not found.";

        for (const auto entry : *changes->entryList) {
            if (!entry || entry->object != item) continue;
            RE::ExtraDataList* selectedExtraList = nullptr;
            if (entry->extraLists) {
                for (const auto extraList : *entry->extraLists) {
                    if (!extraList) continue;
                    if (!selectedExtraList || extraList->HasType<RE::ExtraHotkey>()) selectedExtraList = extraList;
                    if (extraList->HasType<RE::ExtraHotkey>()) break;
                }
            }

            if (entry->IsFavorited()) {
                changes->RemoveFavorite(entry, selectedExtraList);
                return "Removed from favorites.";
            }
            changes->SetFavorite(entry, selectedExtraList);
            return "Added to favorites.";
        }
        return "Inventory item was not found.";
    }

    [[nodiscard]] std::string ActivateMagic(RE::FormID a_formID)
    {
        const auto player = RE::PlayerCharacter::GetSingleton();
        const auto manager = RE::ActorEquipManager::GetSingleton();
        const auto form = RE::TESForm::LookupByID(a_formID);
        if (!player || !manager || !form) return "Magic item could not be equipped.";
        if (const auto spell = form->As<RE::SpellItem>()) {
            manager->EquipSpell(player, spell);
            return "Spell equipped.";
        }
        if (const auto shout = form->As<RE::TESShout>()) {
            manager->EquipShout(player, shout);
            return "Shout equipped.";
        }
        return "This status cannot be equipped.";
    }

    [[nodiscard]] std::string ActivateInventoryItem(RE::FormID a_formID)
    {
        const auto player = RE::PlayerCharacter::GetSingleton();
        const auto item = RE::TESForm::LookupByID<RE::TESBoundObject>(a_formID);
        if (!player || !item) return "Inventory item was not found.";

        if (const auto potion = item->As<RE::AlchemyItem>()) {
            player->DrinkPotion(potion, nullptr);
            return potion->IsFood() ? "Food consumed." : "Potion consumed.";
        }

        if (item->GetFormType() == RE::FormType::Weapon || item->GetFormType() == RE::FormType::Armor || item->GetFormType() == RE::FormType::Scroll) {
            const auto manager = RE::ActorEquipManager::GetSingleton();
            if (!manager) return "Equipment manager is unavailable.";
            manager->EquipObject(player, item);
            return item->GetFormType() == RE::FormType::Scroll ? "Scroll equipped." : "Item equipped.";
        }

        return "This item has no safe default action.";
    }

    [[nodiscard]] std::map<RE::TESBoundObject*, std::int32_t> GetSalvageMaterials(RE::TESBoundObject* a_item)
    {
        std::map<RE::TESBoundObject*, std::int32_t> materials;
        const auto dataHandler = RE::TESDataHandler::GetSingleton();
        if (!dataHandler || !a_item) return materials;

        const auto& recipes = dataHandler->GetFormArray<RE::BGSConstructibleObject>();
        const RE::BGSConstructibleObject* bestRecipe = nullptr;
        std::uint32_t bestIngredientCount = 0;
        for (const auto recipe : recipes) {
            if (!recipe || recipe->createdItem != a_item || recipe->requiredItems.numContainerObjects == 0) continue;
            if (recipe->requiredItems.numContainerObjects > bestIngredientCount) {
                bestRecipe = recipe;
                bestIngredientCount = recipe->requiredItems.numContainerObjects;
            }
        }
        if (!bestRecipe) return materials;

        bestRecipe->requiredItems.ForEachContainerObject([&materials](RE::ContainerObject& a_ingredient) {
            if (!a_ingredient.obj || a_ingredient.count <= 0) return RE::BSContainer::ForEachResult::kContinue;
            // Salvage returns half of the matching forge recipe, with at least one of each component.
            materials[a_ingredient.obj] += (std::max)(1, a_ingredient.count / 2);
            return RE::BSContainer::ForEachResult::kContinue;
        });
        return materials;
    }

    [[nodiscard]] std::string DismantleItem(RE::FormID a_formID)
    {
        const auto player = RE::PlayerCharacter::GetSingleton();
        const auto item = RE::TESForm::LookupByID<RE::TESBoundObject>(a_formID);
        if (!player || !item || (item->GetFormType() != RE::FormType::Weapon && item->GetFormType() != RE::FormType::Armor)) {
            return "Only weapons and armor can be dismantled.";
        }

        const auto inventory = player->GetInventory();
        const auto inventoryEntry = inventory.find(item);
        if (inventoryEntry == inventory.end() || inventoryEntry->second.first <= 0) return "This item is no longer in your inventory.";
        if (inventoryEntry->second.second && inventoryEntry->second.second->IsQuestObject()) return "Quest items cannot be dismantled.";

        const auto materials = GetSalvageMaterials(item);
        if (materials.empty()) return "No forge recipe was found, so this item cannot be safely dismantled.";

        player->RemoveItem(item, 1, RE::ITEM_REMOVE_REASON::kRemove, nullptr, nullptr);
        for (const auto& [material, count] : materials) {
            player->AddObjectToContainer(material, nullptr, count, nullptr);
        }
        return "Item dismantled. Materials were returned to your inventory.";
    }

    void HandleUIAction(const char* a_data)
    {
        try {
            const auto request = json::parse(a_data ? a_data : "{}");
            const auto type = request.value("type", "");
            if (type == "close") ClosePanel();
            else if (type == "ready") return;
            else if (type == "beginHotkeyCapture") {
                const auto action = request.value("action", "");
                if (!FindHotkey(action)) {
                    SendState("The requested shortcut is unavailable.");
                    return;
                }
                g_capturingAction = action;
                SendState("Press the new shortcut, or use Cancel to stop listening.");
            } else if (type == "cancelHotkeyCapture") {
                g_capturingAction.reset();
                SendState("Shortcut binding canceled.");
            }
            else if (type == "favorite") {
                if (request.value("page", "") == "magic") {
                    SendState(ToggleMagicFavorite(request.value("id", RE::FormID{ 0 })));
                } else {
                    SendState(ToggleInventoryFavorite(request.value("id", RE::FormID{ 0 })));
                }
            } else if (type == "activate") {
                std::string message;
                if (request.value("page", "") == "magic") {
                    message = ActivateMagic(request.value("id", RE::FormID{ 0 }));
                } else {
                    message = ActivateInventoryItem(request.value("id", RE::FormID{ 0 }));
                }
                SendState(message);
                SendStateNextFrame(std::move(message));
            } else if (type == "dismantle") {
                SendState(DismantleItem(request.value("id", RE::FormID{ 0 })));
            } else SendState();
        } catch (const std::exception& error) {
            logger::warn("Rejected Inventory Manager request: {}", error.what());
            SendState("The panel request was invalid.");
        }
    }

    void OnSKSEMessage(SKSE::MessagingInterface::Message* a_message)
    {
        if (a_message->type != SKSE::MessagingInterface::kDataLoaded) return;
        g_prisma = PRISMA_UI_API::RequestPluginAPI();
        if (!g_prisma) {
            logger::critical("Prisma UI v1 is unavailable; Inventory Manager will remain disabled.");
            return;
        }
        g_view = g_prisma->CreateView("InventoryManager/index.html", [](PrismaView view) {
            logger::info("Inventory Manager view is ready: {}", view);
        });
        if (!g_view) {
            logger::critical("Inventory Manager Prisma view could not be created.");
            return;
        }
        g_prisma->RegisterJSListener(g_view, "inventoryManagerAction", HandleUIAction);
        g_prisma->Hide(g_view);

        const auto input = InputHandler::GetSingleton();
        g_hotkeys = LoadHotkeySettings();
        input->SetHotkey(g_hotkeys.openPanel);
        input->SetPageToggleHotkey(g_hotkeys.pageToggle);
        input->SetSearchHotkey(g_hotkeys.search);
        input->SetToggleCallback(TogglePanel);
        input->SetEscapeCallback(CloseFocusedPanel);
        input->SetPageToggleCallback([] { return InvokeFocusedView("togglePage"); });
        input->SetSearchCallback([] { return InvokeFocusedView("focusSearch"); });
        input->SetNavigationCallback(NavigateFocusedView);
        input->SetCaptureCallback(CaptureHotkey);
        input->RegisterSink();
        logger::info("Inventory Manager loaded.");
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

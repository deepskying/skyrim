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
        float daggerHitWear = 0.35F;
        float swordHitWear = 0.50F;
        float warAxeHitWear = 0.65F;
        float maceHitWear = 0.80F;
        float greatswordHitWear = 0.80F;
        float battleaxeHitWear = 0.95F;
        float warhammerHitWear = 1.10F;
        float powerAttackWearMultiplier = 1.60F;
        float bowShotWear = 1.0F;
        float crossbowShotWear = 2.0F;
        float armorHitWear = 1.0F;
        float clothingHitWear = 1.25F;
        float shieldBlockWear = 1.0F;
        float incomingPowerAttackWearMultiplier = 1.5F;
        float maxWearReduction = 0.70F;
    };

    Settings g_settings{};
    bool g_capturingHotkey = false;
    bool g_panelVisible = false;
    bool g_hudVisible = false;
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
        float performanceBaselineHealth = 1.0F;
        float performanceAppliedHealth = 1.0F;
        std::uint16_t chargeBaselineCapacity = 0;
        std::uint16_t chargeAppliedCapacity = 0;
        bool performanceBridgeInitialized = false;
        bool chargeBridgeInitialized = false;
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

    struct MaterialRequirementState
    {
        RE::FormID formID = 0;
        std::int32_t count = 0;
    };

    // The persisted equipment record will use these fields per ItemKey. Keeping
    // the card result as data (not UI behaviour) makes future card packs and
    // third-party material rules additive instead of requiring a UI rewrite.
    struct EnhancementCardState
    {
        std::string id;
        EnhancementCardType type{};
        EnhancementTier tier{};
        float rolledValue = 0.0F;
        std::uint32_t successChance = 100;
        std::vector<MaterialRequirementState> requiredMaterials;
        std::string blockedReason;
    };

    std::unordered_map<ItemKey, DurabilitySnapshot, ItemKeyHash> g_durability;
    std::unordered_set<ItemKey, ItemKeyHash> g_lowDurabilityWarnings;
    std::unordered_set<ItemKey, ItemKeyHash> g_pendingBreaks;
    std::unordered_map<ItemKey, std::chrono::steady_clock::time_point, ItemKeyHash> g_weaponNotificationTimes;
    std::mutex g_durabilityLock;
    std::uint16_t g_nextGeneratedUniqueID = 1;
    std::uint64_t g_stateEpoch = 0;
    std::uint64_t g_armorHitSequence = 0;

    RE::ObjectRefHandle g_forgeStation;
    std::string g_forgeStationName;
    std::chrono::steady_clock::time_point g_forgeActivatedAt{};
    std::optional<ItemKey> g_forgeSelectedItem;
    std::vector<EnhancementCardState> g_enhancementCards;
    std::uint32_t g_forgeRefreshes = 0;
    std::uint64_t g_cardSequence = 0;
    std::mutex g_forgeLock;

    struct SpeedGraphBridgeState
    {
        float appliedBonus = 0.0F;
        float lastTarget = 0.0F;
        bool initialized = false;
    };

    SpeedGraphBridgeState g_rightSpeedBridge;
    SpeedGraphBridgeState g_leftSpeedBridge;
    bool g_playerRuntimeSyncQueued = false;
    std::mutex g_playerRuntimeLock;

    constexpr std::uint32_t kSerializationID = 0x4455524DU;  // "DURM"
    constexpr std::uint32_t kDurabilityRecordType = 0x44555241U;  // "DURA"
    constexpr std::uint32_t kDurabilityRecordVersion = 2;
    constexpr std::uint32_t kMaxDurabilityRecords = 100000;
    constexpr std::string_view kPluginVersion = "0.1.26";
    constexpr auto kForgeContextLifetime = std::chrono::minutes(2);
    constexpr float kForgeContextMaximumDistance = 600.0F;
    constexpr std::uint32_t kBaseCardRefreshCost = 80;

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
        configFile << "\n[Wear]\nDaggerHitWear=" << g_settings.daggerHitWear
                   << "\nSwordHitWear=" << g_settings.swordHitWear
                   << "\nWarAxeHitWear=" << g_settings.warAxeHitWear
                   << "\nMaceHitWear=" << g_settings.maceHitWear
                   << "\nGreatswordHitWear=" << g_settings.greatswordHitWear
                   << "\nBattleaxeHitWear=" << g_settings.battleaxeHitWear
                   << "\nWarhammerHitWear=" << g_settings.warhammerHitWear
                   << "\nPowerAttackWearMultiplier=" << g_settings.powerAttackWearMultiplier
                   << "\nBowShotWear=" << g_settings.bowShotWear
                   << "\nCrossbowShotWear=" << g_settings.crossbowShotWear
                   << "\nArmorHitWear=" << g_settings.armorHitWear
                   << "\nClothingHitWear=" << g_settings.clothingHitWear
                   << "\nShieldBlockWear=" << g_settings.shieldBlockWear
                   << "\nIncomingPowerAttackWearMultiplier=" << g_settings.incomingPowerAttackWearMultiplier
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
                    if (key == "DAGGERHITWEAR") g_settings.daggerHitWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "SWORDHITWEAR") g_settings.swordHitWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "WARAXEHITWEAR") g_settings.warAxeHitWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "MACEHITWEAR") g_settings.maceHitWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "GREATSWORDHITWEAR") g_settings.greatswordHitWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "BATTLEAXEHITWEAR") g_settings.battleaxeHitWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "WARHAMMERHITWEAR") g_settings.warhammerHitWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "POWERATTACKWEARMULTIPLIER") g_settings.powerAttackWearMultiplier = std::clamp(std::stof(value), 1.0F, 10.0F);
                    else if (key == "BOWSHOTWEAR") g_settings.bowShotWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "CROSSBOWSHOTWEAR") g_settings.crossbowShotWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "ARMORHITWEAR") g_settings.armorHitWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "CLOTHINGHITWEAR") g_settings.clothingHitWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "SHIELDBLOCKWEAR") g_settings.shieldBlockWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "INCOMINGPOWERATTACKWEARMULTIPLIER") g_settings.incomingPowerAttackWearMultiplier = std::clamp(std::stof(value), 1.0F, 10.0F);
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
        if (const auto* armor = a_item->As<RE::TESObjectARMO>()) {
            return const_cast<RE::TESObjectARMO*>(armor)->GetArmorRating() > 0.0F ? "armor" : "clothing";
        }
        return "clothing";
    }

    [[nodiscard]] float EquipmentWeight(const RE::TESBoundObject* a_item)
    {
        if (const auto* weapon = a_item ? a_item->As<RE::TESObjectWEAP>() : nullptr) return weapon->weight;
        if (const auto* armor = a_item ? a_item->As<RE::TESObjectARMO>() : nullptr) return armor->weight;
        return 0.0F;
    }

    [[nodiscard]] std::string EnchantmentName(RE::TESBoundObject* a_item, const RE::ExtraDataList* a_extraList)
    {
        const RE::EnchantmentItem* enchantment = nullptr;
        if (const auto* extraEnchantment = a_extraList ? a_extraList->GetByType<RE::ExtraEnchantment>() : nullptr) {
            enchantment = extraEnchantment->enchantment;
        }
        if (!enchantment) {
            const auto* enchantable = a_item ? a_item->As<RE::TESEnchantableForm>() : nullptr;
            enchantment = enchantable ? enchantable->formEnchanting : nullptr;
        }
        const auto* name = enchantment ? enchantment->GetFullName() : nullptr;
        return name && name[0] ? name : "";
    }

    [[nodiscard]] bool IsProtectedUniqueItem(RE::TESBoundObject* a_item)
    {
        if (!a_item) return false;
        // Skyrim has no universal "unique item" bit for weapons and armor.
        // These standard keywords cover artifacts and items deliberately
        // excluded from generic enchanting without treating every enchanted
        // leveled-list item as unique.
        return a_item->HasKeywordByEditorID("DaedricArtifact") || a_item->HasKeywordByEditorID("MagicDisallowEnchanting");
    }

    [[nodiscard]] bool IsInstanceEnchanted(RE::TESBoundObject* a_item, const RE::ExtraDataList* a_extraList)
    {
        const auto* enchantable = a_item ? a_item->As<RE::TESEnchantableForm>() : nullptr;
        if (enchantable && enchantable->formEnchanting) return true;
        const auto* extraEnchantment = a_extraList ? a_extraList->GetByType<RE::ExtraEnchantment>() : nullptr;
        return extraEnchantment && extraEnchantment->enchantment;
    }

    [[nodiscard]] RE::ExtraDataList* FindWornExtraList(const RE::InventoryEntryData* a_entry)
    {
        if (!a_entry || !a_entry->extraLists) return nullptr;
        for (auto* extraList : *a_entry->extraLists) {
            if (extraList && extraList->GetWorn()) return extraList;
        }
        return nullptr;
    }

    [[nodiscard]] RE::ExtraDataList* FindWornExtraListForHand(
        const RE::InventoryEntryData* a_entry,
        const bool a_leftHand)
    {
        if (!a_entry || !a_entry->extraLists) return nullptr;
        for (auto* extraList : *a_entry->extraLists) {
            if (!extraList) continue;
            if (a_leftHand ? extraList->HasType<RE::ExtraWornLeft>() : extraList->HasType<RE::ExtraWorn>()) {
                return extraList;
            }
        }
        return nullptr;
    }

    [[nodiscard]] RE::ExtraDataList* FindExtraListByKey(const RE::InventoryEntryData* a_entry, const ItemKey& a_key)
    {
        if (!a_entry || !a_entry->extraLists) return nullptr;
        for (auto* extraList : *a_entry->extraLists) {
            const auto* uniqueID = extraList ? extraList->GetByType<RE::ExtraUniqueID>() : nullptr;
            if (uniqueID && uniqueID->uniqueID == a_key.uniqueID) return extraList;
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

    [[nodiscard]] std::optional<std::uint16_t> AllocateUniqueID(const RE::TESBoundObject* a_item)
    {
        if (!a_item) return std::nullopt;
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
        return foundAvailableID && generatedID != 0 ? std::optional{ generatedID } : std::nullopt;
    }

    [[nodiscard]] std::optional<ItemKey> EnsureItemKeyForExtraList(RE::ExtraDataList* a_extraList, const RE::TESBoundObject* a_item)
    {
        if (!a_extraList || !a_item) return std::nullopt;
        if (const auto* existing = a_extraList->GetByType<RE::ExtraUniqueID>()) {
            return ItemKey{ a_item->GetFormID(), existing->uniqueID };
        }
        const auto generatedID = AllocateUniqueID(a_item);
        if (!generatedID) return std::nullopt;

        a_extraList->Add(new RE::ExtraUniqueID(a_item->GetFormID(), *generatedID));
        logger::debug("Assigned durability instance {:08X}:{:04X}.", a_item->GetFormID(), *generatedID);
        return ItemKey{ a_item->GetFormID(), *generatedID };
    }

    [[nodiscard]] std::optional<ItemKey> EnsureItemKey(RE::InventoryEntryData* a_entry, const RE::TESBoundObject* a_item)
    {
        if (!a_item) return std::nullopt;
        auto* extraList = FindWornExtraList(a_entry);
        if (!extraList) {
            logger::debug("Could not resolve a worn extra-data list for {:08X}; durability was not changed.", a_item->GetFormID());
            return std::nullopt;
        }

        return EnsureItemKeyForExtraList(extraList, a_item);
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

    [[nodiscard]] std::string InstanceDisplayName(RE::TESBoundObject* a_item, RE::ExtraDataList* a_extraList)
    {
        const auto* name = a_extraList ? a_extraList->GetDisplayName(a_item) : nullptr;
        return name && name[0] ? name : DisplayName(a_item);
    }

    void SendState(std::string_view a_message = {});

    struct ForgeContext
    {
        bool active = false;
        std::string station;
    };

    [[nodiscard]] std::string ForgeStationName(RE::TESBoundObject* a_station)
    {
        if (!a_station) return {};
        if (a_station->HasKeywordByEditorID("CraftingSmithingSharpeningWheel")) return "磨刀砂轮";
        if (a_station->HasKeywordByEditorID("CraftingSmithingArmorTable")) return "护甲工作台";
        if (a_station->HasKeywordByEditorID("CraftingSmelter")) return "冶炼熔炉";
        if (a_station->HasKeywordByEditorID("CraftingSmithingForge")) return "锻造熔炉";
        return {};
    }

    void ClearForgeContext()
    {
        std::scoped_lock lock(g_forgeLock);
        g_forgeStation.reset();
        g_forgeStationName.clear();
        g_forgeActivatedAt = {};
        g_forgeSelectedItem.reset();
        g_enhancementCards.clear();
        g_forgeRefreshes = 0;
    }

    [[nodiscard]] ForgeContext GetForgeContext()
    {
        RE::ObjectRefHandle stationHandle;
        std::string stationName;
        std::chrono::steady_clock::time_point activatedAt;
        {
            std::scoped_lock lock(g_forgeLock);
            stationHandle = g_forgeStation;
            stationName = g_forgeStationName;
            activatedAt = g_forgeActivatedAt;
        }

        const auto now = std::chrono::steady_clock::now();
        auto station = stationHandle.get();
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!station || !player || activatedAt == std::chrono::steady_clock::time_point{} ||
            now - activatedAt > kForgeContextLifetime || player->GetDistance(station.get()) > kForgeContextMaximumDistance) {
            ClearForgeContext();
            return {};
        }
        return { true, std::move(stationName) };
    }

    void ActivateForgeContext(RE::TESObjectREFR* a_station, std::string a_stationName)
    {
        if (!a_station || a_stationName.empty()) return;
        {
            std::scoped_lock lock(g_forgeLock);
            g_forgeStation = a_station->GetHandle();
            g_forgeStationName = a_stationName;
            g_forgeActivatedAt = std::chrono::steady_clock::now();
            g_forgeSelectedItem.reset();
            g_enhancementCards.clear();
            g_forgeRefreshes = 0;
        }
        const auto notification = a_stationName + "已启用装备工坊；关闭原菜单后按面板快捷键打开。";
        RE::DebugNotification(notification.c_str());
        logger::info("Equipment workshop context activated at {}.", a_stationName);
        if (g_panelVisible) SendState("已进入" + a_stationName + "的装备工坊范围。");
    }

    void UpdateViewVisibility()
    {
        if (g_prisma && g_view && !g_panelVisible && !g_hudVisible) g_prisma->Hide(g_view);
    }

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
        g_hudVisible = true;
        g_prisma->Show(g_view);
        const auto script = "window.DurabilityManager && window.DurabilityManager.showHud(" + message.dump() + ");";
        g_prisma->Invoke(g_view, script.c_str());
    }

    void UpdateLowDurabilityWarning(const RE::TESBoundObject* a_item, const ItemKey& a_key, const DurabilitySnapshot& a_durability)
    {
        if (!g_settings.enableLowDurabilityWarning || a_durability.maximum <= 0.0F) return;
        const auto percentage = static_cast<std::uint32_t>(std::lround(a_durability.current * 100.0F / a_durability.maximum));
        if (percentage < g_settings.lowDurabilityThreshold) {
            if (g_lowDurabilityWarnings.insert(a_key).second) {
                ShowHUD("warning", "耐久度过低", DisplayName(a_item) + "：" + std::to_string(percentage) + "%（请尽快修复）", g_settings.weaponDisplaySeconds);
            }
        } else {
            g_lowDurabilityWarnings.erase(a_key);
        }
    }

    [[nodiscard]] std::map<RE::TESBoundObject*, std::int32_t> GetSalvageMaterials(RE::TESBoundObject* a_item)
    {
        std::map<RE::TESBoundObject*, std::int32_t> materials;
        auto* dataHandler = RE::TESDataHandler::GetSingleton();
        if (!dataHandler || !a_item) return materials;

        const auto& recipes = dataHandler->GetFormArray<RE::BGSConstructibleObject>();
        const RE::BGSConstructibleObject* bestRecipe = nullptr;
        std::uint32_t bestIngredientCount = 0;
        for (const auto* recipe : recipes) {
            if (!recipe || recipe->createdItem != a_item || recipe->requiredItems.numContainerObjects == 0) continue;
            if (recipe->requiredItems.numContainerObjects > bestIngredientCount) {
                bestRecipe = recipe;
                bestIngredientCount = recipe->requiredItems.numContainerObjects;
            }
        }
        if (!bestRecipe) return materials;

        bestRecipe->requiredItems.ForEachContainerObject([&materials](RE::ContainerObject& a_ingredient) {
            if (!a_ingredient.obj || a_ingredient.count <= 0) return RE::BSContainer::ForEachResult::kContinue;
            materials[a_ingredient.obj] += (std::max)(1, a_ingredient.count / 2);
            return RE::BSContainer::ForEachResult::kContinue;
        });
        return materials;
    }

    [[nodiscard]] bool IsTemperingBench(const RE::BGSKeyword* a_keyword)
    {
        if (!a_keyword) return false;
        const auto matches = [a_keyword](std::string_view a_editorID) {
            return a_keyword == RE::TESForm::LookupByEditorID<RE::BGSKeyword>(a_editorID);
        };
        return matches("CraftingSmithingSharpeningWheel") || matches("CraftingSmithingArmorTable");
    }

    [[nodiscard]] const RE::BGSConstructibleObject* FindRepairRecipe(RE::TESBoundObject* a_item)
    {
        auto* dataHandler = RE::TESDataHandler::GetSingleton();
        if (!dataHandler || !a_item) return nullptr;
        const RE::BGSConstructibleObject* bestRecipe = nullptr;
        std::uint32_t bestScore = 0;
        for (const auto* recipe : dataHandler->GetFormArray<RE::BGSConstructibleObject>()) {
            if (!recipe || recipe->createdItem != a_item || recipe->requiredItems.numContainerObjects == 0) continue;
            const auto score = (IsTemperingBench(recipe->benchKeyword) ? 1000U : 0U) + recipe->requiredItems.numContainerObjects;
            if (!bestRecipe || score > bestScore) {
                bestRecipe = recipe;
                bestScore = score;
            }
        }
        return bestRecipe;
    }

    [[nodiscard]] std::map<RE::TESBoundObject*, std::int32_t> GetRepairMaterials(
        RE::TESBoundObject* a_item,
        const DurabilitySnapshot& a_durability)
    {
        std::map<RE::TESBoundObject*, std::int32_t> materials;
        const auto* recipe = FindRepairRecipe(a_item);
        if (a_durability.maximum <= 0.0F || a_durability.current >= a_durability.maximum) return materials;

        const auto missingRatio = std::clamp((a_durability.maximum - a_durability.current) / a_durability.maximum, 0.0F, 1.0F);
        const auto costRatio = missingRatio <= 0.25F ? 0.25F : missingRatio <= 0.50F ? 0.50F : missingRatio <= 0.75F ? 0.75F : 1.0F;
        if (!recipe) {
            auto* armor = a_item ? a_item->As<RE::TESObjectARMO>() : nullptr;
            if (!armor) return materials;
            const auto materialEditorID = armor->IsClothing() ? "LeatherStrips" : "IngotIron";
            if (auto* material = RE::TESForm::LookupByEditorID<RE::TESBoundObject>(materialEditorID)) {
                const auto fullRepairCount = armor->IsClothing() ? 2.0F : 4.0F;
                materials[material] = (std::max)(1, static_cast<std::int32_t>(std::ceil(fullRepairCount * costRatio)));
            }
            return materials;
        }
        recipe->requiredItems.ForEachContainerObject([&materials, costRatio](RE::ContainerObject& a_ingredient) {
            if (!a_ingredient.obj || a_ingredient.count <= 0) return RE::BSContainer::ForEachResult::kContinue;
            const auto scaledCount = static_cast<std::int32_t>(std::ceil(static_cast<float>(a_ingredient.count) * costRatio));
            materials[a_ingredient.obj] += (std::max)(1, scaledCount);
            return RE::BSContainer::ForEachResult::kContinue;
        });
        return materials;
    }

    [[nodiscard]] json RepairMaterialsJson(const std::map<RE::TESBoundObject*, std::int32_t>& a_materials)
    {
        json result = json::array();
        auto* player = RE::PlayerCharacter::GetSingleton();
        for (const auto& [material, required] : a_materials) {
            result.push_back({
                { "name", DisplayName(material) },
                { "required", required },
                { "owned", player ? (std::max)(0, player->GetItemCount(material)) : 0 }
            });
        }
        return result;
    }

    [[nodiscard]] std::optional<ItemKey> ParseItemKey(std::string_view a_value)
    {
        const auto separator = a_value.find(':');
        if (separator == std::string_view::npos || separator == 0 || separator + 1 >= a_value.size()) return std::nullopt;
        std::uint64_t baseFormID = 0;
        std::uint64_t uniqueID = 0;
        const auto baseResult = std::from_chars(a_value.data(), a_value.data() + separator, baseFormID);
        const auto uniqueResult = std::from_chars(a_value.data() + separator + 1, a_value.data() + a_value.size(), uniqueID);
        if (baseResult.ec != std::errc{} || baseResult.ptr != a_value.data() + separator ||
            uniqueResult.ec != std::errc{} || uniqueResult.ptr != a_value.data() + a_value.size() ||
            baseFormID > (std::numeric_limits<RE::FormID>::max)() || uniqueID > (std::numeric_limits<std::uint16_t>::max)()) {
            return std::nullopt;
        }
        return ItemKey{ static_cast<RE::FormID>(baseFormID), static_cast<std::uint16_t>(uniqueID) };
    }

    void RepairEquipment(const std::string_view a_equipmentID)
    {
        if (!GetForgeContext().active) {
            SendState("修复失败：请先使用附近的锻造熔炉、冶炼熔炉、砂轮或护甲工作台。");
            return;
        }
        const auto key = ParseItemKey(a_equipmentID);
        if (!key) {
            SendState("修复失败：装备实例标识无效。");
            return;
        }

        auto* player = RE::PlayerCharacter::GetSingleton();
        auto* item = RE::TESForm::LookupByID<RE::TESBoundObject>(key->baseFormID);
        if (!player || !item) {
            SendState("修复失败：找不到该装备。");
            return;
        }
        const auto inventory = player->GetInventory();
        const auto found = inventory.find(item);
        auto* entry = found != inventory.end() && found->second.second ? found->second.second.get() : nullptr;
        if (!entry || !FindExtraListByKey(entry, *key)) {
            SendState("修复失败：该装备实例已不在背包中。");
            return;
        }

        const auto durability = GetDurability(*key);
        if (durability.current >= durability.maximum) {
            SendState(DisplayName(item) + "的耐久已经全满。");
            return;
        }
        const auto materials = GetRepairMaterials(item, durability);
        if (materials.empty()) {
            SendState("修复失败：没有找到可用于该装备的锻造或强化配方。");
            return;
        }
        for (const auto& [material, required] : materials) {
            if (player->GetItemCount(material) < required) {
                SendState("修复失败：缺少" + DisplayName(material) + "，需要 " + std::to_string(required) + " 个。");
                return;
            }
        }
        for (const auto& [material, required] : materials) {
            player->RemoveItem(material, required, RE::ITEM_REMOVE_REASON::kRemove, nullptr, nullptr);
        }
        {
            std::scoped_lock lock(g_durabilityLock);
            auto& stored = g_durability[*key];
            stored.maximum = (std::max)(1.0F, durability.maximum);
            stored.current = stored.maximum;
            g_lowDurabilityWarnings.erase(*key);
            g_pendingBreaks.erase(*key);
        }
        logger::info("Repaired item {:08X}:{:04X} to full durability using {} material types.", key->baseFormID, key->uniqueID, materials.size());
        SendState(DisplayName(item) + "已修复至满耐久。");
    }

    struct ResolvedEquipmentInstance
    {
        RE::TESBoundObject* item = nullptr;
        RE::ExtraDataList* extraList = nullptr;
    };

    [[nodiscard]] std::optional<ResolvedEquipmentInstance> ResolveEquipmentInstance(const ItemKey& a_key)
    {
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto* item = RE::TESForm::LookupByID<RE::TESBoundObject>(a_key.baseFormID);
        if (!player || !item) return std::nullopt;
        const auto inventory = player->GetInventory();
        const auto found = inventory.find(item);
        auto* entry = found != inventory.end() && found->second.second ? found->second.second.get() : nullptr;
        if (a_key.uniqueID == 0 && found != inventory.end() && found->second.first > 0) {
            return ResolvedEquipmentInstance{ item, nullptr };
        }
        auto* extraList = FindExtraListByKey(entry, a_key);
        if (!extraList) return std::nullopt;
        return ResolvedEquipmentInstance{ item, extraList };
    }

    [[nodiscard]] float BasePerformanceValue(RE::TESBoundObject* a_item)
    {
        if (const auto* weapon = a_item ? a_item->As<RE::TESObjectWEAP>() : nullptr) {
            return static_cast<float>(weapon->GetAttackDamage());
        }
        if (auto* armor = a_item ? a_item->As<RE::TESObjectARMO>() : nullptr) return armor->GetArmorRating();
        return 0.0F;
    }

    [[nodiscard]] RE::EnchantmentItem* InstanceEnchantment(RE::TESBoundObject* a_item, RE::ExtraDataList* a_extraList)
    {
        if (auto* extraEnchantment = a_extraList ? a_extraList->GetByType<RE::ExtraEnchantment>() : nullptr) {
            return extraEnchantment->enchantment;
        }
        auto* enchantable = a_item ? a_item->As<RE::TESEnchantableForm>() : nullptr;
        return enchantable ? enchantable->formEnchanting : nullptr;
    }

    [[nodiscard]] std::optional<std::uint16_t> InstanceChargeCapacity(
        RE::TESBoundObject* a_item,
        RE::ExtraDataList* a_extraList)
    {
        if (const auto* extraEnchantment = a_extraList ? a_extraList->GetByType<RE::ExtraEnchantment>() : nullptr) {
            if (!extraEnchantment->enchantment || extraEnchantment->charge == 0) return std::nullopt;
            return extraEnchantment->charge;
        }
        const auto* enchantable = a_item ? a_item->As<RE::TESEnchantableForm>() : nullptr;
        if (!enchantable || !enchantable->formEnchanting || enchantable->amountofEnchantment == 0) return std::nullopt;
        return enchantable->amountofEnchantment;
    }

    bool SyncPerformanceRuntimeEffect(
        const ItemKey& a_key,
        RE::TESBoundObject* a_item,
        RE::ExtraDataList* a_extraList)
    {
        if (!a_item || !a_extraList) return false;
        const auto baseValue = BasePerformanceValue(a_item);
        if (!std::isfinite(baseValue) || baseValue <= 0.0F) return false;

        auto* extraHealth = a_extraList->GetByType<RE::ExtraHealth>();
        const auto currentHealth = extraHealth && std::isfinite(extraHealth->health) ?
                                       (std::max)(0.01F, extraHealth->health) :
                                       1.0F;
        float targetHealth = currentHealth;
        bool shouldSync = false;
        {
            std::scoped_lock lock(g_durabilityLock);
            const auto found = g_durability.find(a_key);
            if (found == g_durability.end()) return false;
            auto& durability = found->second;
            if (durability.performanceBonus == 0 && !durability.performanceBridgeInitialized) return false;

            if (!durability.performanceBridgeInitialized || !std::isfinite(durability.performanceBaselineHealth) ||
                !std::isfinite(durability.performanceAppliedHealth)) {
                durability.performanceBaselineHealth = currentHealth;
                durability.performanceBridgeInitialized = true;
            } else if (std::abs(currentHealth - durability.performanceAppliedHealth) > 0.001F) {
                // Carry an external tempering delta into the baseline. This keeps
                // our previous contribution from being baked in and added twice.
                durability.performanceBaselineHealth += currentHealth - durability.performanceAppliedHealth;
            }
            durability.performanceBaselineHealth = std::clamp(durability.performanceBaselineHealth, 0.01F, 10000.0F);
            targetHealth = std::clamp(
                durability.performanceBaselineHealth + static_cast<float>(durability.performanceBonus) / baseValue,
                0.01F,
                10000.0F);
            durability.performanceAppliedHealth = targetHealth;
            shouldSync = std::abs(currentHealth - targetHealth) > 0.001F;
        }
        if (!shouldSync) return false;
        if (extraHealth) extraHealth->health = targetHealth;
        else a_extraList->Add(new RE::ExtraHealth(targetHealth));
        logger::debug(
            "Synced performance bridge for {:08X}:{:04X}; health {:.4F} -> {:.4F}.",
            a_key.baseFormID,
            a_key.uniqueID,
            currentHealth,
            targetHealth);
        return true;
    }

    bool SyncChargeRuntimeEffect(
        const ItemKey& a_key,
        RE::TESBoundObject* a_item,
        RE::ExtraDataList* a_extraList)
    {
        if (!a_item || !a_extraList) return false;
        auto* enchantment = InstanceEnchantment(a_item, a_extraList);
        const auto currentCapacity = InstanceChargeCapacity(a_item, a_extraList);
        if (!enchantment || !currentCapacity) return false;

        std::uint16_t targetCapacity = *currentCapacity;
        bool shouldSync = false;
        {
            std::scoped_lock lock(g_durabilityLock);
            const auto found = g_durability.find(a_key);
            if (found == g_durability.end()) return false;
            auto& durability = found->second;
            if (durability.chargeBonus <= 0.0F && !durability.chargeBridgeInitialized) return false;

            if (!durability.chargeBridgeInitialized || durability.chargeBaselineCapacity == 0) {
                durability.chargeBaselineCapacity = *currentCapacity;
                durability.chargeBridgeInitialized = true;
            } else if (*currentCapacity != durability.chargeAppliedCapacity) {
                // A foreign capacity change normally includes our already-applied
                // multiplier. Remove that multiplier before accepting the baseline.
                const auto multiplier = 1.0 + static_cast<double>((std::max)(0.0F, durability.chargeBonus));
                durability.chargeBaselineCapacity = static_cast<std::uint16_t>(std::clamp<long long>(
                    std::llround(static_cast<double>(*currentCapacity) / multiplier),
                    1LL,
                    static_cast<long long>((std::numeric_limits<std::uint16_t>::max)())));
            }
            const auto scaledCapacity = std::llround(
                static_cast<double>(durability.chargeBaselineCapacity) *
                (1.0 + static_cast<double>(std::clamp(durability.chargeBonus, 0.0F, 65534.0F))));
            targetCapacity = static_cast<std::uint16_t>(std::clamp<long long>(
                scaledCapacity,
                1LL,
                static_cast<long long>((std::numeric_limits<std::uint16_t>::max)())));
            durability.chargeBonus = (std::max)(
                0.0F,
                static_cast<float>(targetCapacity) / static_cast<float>(durability.chargeBaselineCapacity) - 1.0F);
            durability.chargeAppliedCapacity = targetCapacity;
            shouldSync = *currentCapacity != targetCapacity;
        }
        if (!shouldSync) return false;

        auto* extraCharge = a_extraList->GetByType<RE::ExtraCharge>();
        const auto currentChargeRatio = extraCharge && std::isfinite(extraCharge->charge) ?
                                            std::clamp(extraCharge->charge / static_cast<float>(*currentCapacity), 0.0F, 1.0F) :
                                            1.0F;
        if (auto* extraEnchantment = a_extraList->GetByType<RE::ExtraEnchantment>()) {
            extraEnchantment->charge = targetCapacity;
        } else {
            a_extraList->Add(new RE::ExtraEnchantment(enchantment, targetCapacity));
        }
        if (extraCharge) extraCharge->charge = currentChargeRatio * static_cast<float>(targetCapacity);
        logger::debug(
            "Synced charge bridge for {:08X}:{:04X}; capacity {} -> {}.",
            a_key.baseFormID,
            a_key.uniqueID,
            *currentCapacity,
            targetCapacity);
        return true;
    }

    void SyncInstanceRuntimeEffects(
        const ItemKey& a_key,
        RE::TESBoundObject* a_item,
        RE::ExtraDataList* a_extraList)
    {
        if (!a_extraList) return;
        SyncPerformanceRuntimeEffect(a_key, a_item, a_extraList);
        SyncChargeRuntimeEffect(a_key, a_item, a_extraList);
    }

    void SyncAllRuntimeEffects()
    {
        std::vector<ItemKey> keys;
        {
            std::scoped_lock lock(g_durabilityLock);
            keys.reserve(g_durability.size());
            for (const auto& [key, durability] : g_durability) {
                if (durability.performanceBonus != 0 || durability.chargeBonus > 0.0F ||
                    durability.performanceBridgeInitialized || durability.chargeBridgeInitialized) {
                    keys.push_back(key);
                }
            }
        }
        std::size_t synced = 0;
        for (const auto& key : keys) {
            const auto instance = ResolveEquipmentInstance(key);
            if (!instance || !instance->extraList) continue;
            SyncInstanceRuntimeEffects(key, instance->item, instance->extraList);
            ++synced;
        }
        logger::info("Synchronized runtime effects for {} carried enhancement records.", synced);
    }

    [[nodiscard]] float EquippedAttackSpeedBonus(const bool a_leftHand)
    {
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto* entry = player ? player->GetEquippedEntryData(a_leftHand) : nullptr;
        auto* weapon = entry && entry->object ? entry->object->As<RE::TESObjectWEAP>() : nullptr;
        if (!weapon || weapon->IsBound()) return 0.0F;
        auto* extraList = FindWornExtraListForHand(entry, a_leftHand);
        const auto key = EnsureItemKeyForExtraList(extraList, weapon);
        return key ? std::clamp(GetDurability(*key).attackSpeedBonus, 0.0F, 1.0F) : 0.0F;
    }

    void ApplyAttackSpeedGraphForHand(
        RE::PlayerCharacter* a_player,
        const bool a_leftHand,
        const float a_desiredBonus)
    {
        const auto* strings = RE::FixedStrings::GetSingleton();
        if (!a_player || !strings) return;
        const auto& variable = a_leftHand ? strings->leftWeaponSpeedMult : strings->weaponSpeedMult;
        float currentValue = 0.0F;
        if (!a_player->GetGraphVariableFloat(variable, currentValue) || !std::isfinite(currentValue)) return;

        float targetValue = currentValue;
        float appliedBonus = 0.0F;
        {
            std::scoped_lock lock(g_playerRuntimeLock);
            auto& bridge = a_leftHand ? g_leftSpeedBridge : g_rightSpeedBridge;
            const auto baseline = bridge.initialized && std::abs(currentValue - bridge.lastTarget) <= 0.001F ?
                                      currentValue - bridge.appliedBonus :
                                      currentValue;
            appliedBonus = std::clamp(a_desiredBonus, 0.0F, 1.0F);
            targetValue = std::clamp(baseline + appliedBonus, -10.0F, 10.0F);
            bridge.appliedBonus = targetValue - baseline;
            bridge.lastTarget = targetValue;
            bridge.initialized = true;
        }
        if (std::abs(currentValue - targetValue) <= 0.001F) return;
        a_player->SetGraphVariableFloat(variable, targetValue);
        logger::debug(
            "Synced {} weapon speed graph value {:.4F} -> {:.4F} (bonus {:.4F}).",
            a_leftHand ? "left" : "right",
            currentValue,
            targetValue,
            appliedBonus);
    }

    void SyncAttackSpeedRuntimeEffects()
    {
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!player) return;
        ApplyAttackSpeedGraphForHand(player, false, EquippedAttackSpeedBonus(false));
        ApplyAttackSpeedGraphForHand(player, true, EquippedAttackSpeedBonus(true));
    }

    struct WeightReductionSummary
    {
        float total = 0.0F;
        float wornArmor = 0.0F;
    };

    [[nodiscard]] WeightReductionSummary CalculateWeightReduction()
    {
        WeightReductionSummary result;
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!player) return result;

        std::unordered_map<ItemKey, float, ItemKeyHash> reductions;
        {
            std::scoped_lock lock(g_durabilityLock);
            reductions.reserve(g_durability.size());
            for (const auto& [key, durability] : g_durability) {
                if (durability.weightReduction > 0.0F) reductions.emplace(key, durability.weightReduction);
            }
        }
        if (reductions.empty()) return result;

        for (const auto& [item, entry] : player->GetInventory()) {
            if (!item || !entry.second || !entry.second->extraLists) continue;
            if (item->GetFormType() != RE::FormType::Weapon && item->GetFormType() != RE::FormType::Armor) continue;
            const auto itemWeight = EquipmentWeight(item);
            if (!std::isfinite(itemWeight) || itemWeight <= 0.1F) continue;
            for (auto* extraList : *entry.second->extraLists) {
                const auto* uniqueID = extraList ? extraList->GetByType<RE::ExtraUniqueID>() : nullptr;
                if (!uniqueID) continue;
                const auto found = reductions.find(ItemKey{ item->GetFormID(), uniqueID->uniqueID });
                if (found == reductions.end()) continue;
                const auto count = static_cast<float>((std::max)(1, extraList->GetCount()));
                const auto reduction = (std::min)(itemWeight - 0.1F, (std::max)(0.0F, found->second)) * count;
                result.total += reduction;
                if (item->GetFormType() == RE::FormType::Armor && extraList->GetWorn()) result.wornArmor += reduction;
            }
        }
        result.total = std::isfinite(result.total) ? (std::max)(0.0F, result.total) : 0.0F;
        result.wornArmor = std::isfinite(result.wornArmor) ? (std::max)(0.0F, result.wornArmor) : 0.0F;
        return result;
    }

    void SyncWeightRuntimeEffect()
    {
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto* changes = player ? player->GetInventoryChanges() : nullptr;
        if (!changes) return;
        const auto reduction = CalculateWeightReduction();
        changes->changed = true;
        const auto rawTotalWeight = changes->GetInventoryWeight();
        const auto rawArmorWeight = changes->armorWeight;
        changes->totalWeight = (std::max)(0.0F, rawTotalWeight - reduction.total);
        changes->armorWeight = (std::max)(0.0F, rawArmorWeight - reduction.wornArmor);
        logger::debug(
            "Synced player weight cache {:.2F} -> {:.2F}; worn armor reduction {:.2F}.",
            rawTotalWeight,
            changes->totalWeight,
            reduction.wornArmor);
    }

    void SyncPlayerRuntimeEffects()
    {
        SyncAttackSpeedRuntimeEffects();
        SyncWeightRuntimeEffect();
    }

    void QueuePlayerRuntimeEffectsSync()
    {
        {
            std::scoped_lock lock(g_playerRuntimeLock);
            if (g_playerRuntimeSyncQueued) return;
            g_playerRuntimeSyncQueued = true;
        }
        const auto sync = [] {
            {
                std::scoped_lock lock(g_playerRuntimeLock);
                g_playerRuntimeSyncQueued = false;
            }
            SyncPlayerRuntimeEffects();
        };
        if (const auto* tasks = SKSE::GetTaskInterface()) tasks->AddTask(sync);
        else sync();
    }

    void PreparePlayerRuntimeEffectsForStateChange()
    {
        std::scoped_lock lock(g_playerRuntimeLock);
        // Keep the per-hand bridge values across a load. If Skyrim retains the
        // animation graph, the next sync can remove the previous save's bonus;
        // if it rebuilt the graph, the changed value is accepted as baseline.
        g_playerRuntimeSyncQueued = false;
    }

    [[nodiscard]] std::string CardTypeID(const EnhancementCardType a_type)
    {
        switch (a_type) {
        case EnhancementCardType::Performance: return "performance";
        case EnhancementCardType::Weight: return "weight";
        case EnhancementCardType::Speed: return "speed";
        case EnhancementCardType::Durability: return "durability";
        case EnhancementCardType::Wear: return "wear";
        case EnhancementCardType::Charge: return "charge";
        case EnhancementCardType::Enchantment: return "enchantment";
        }
        return "durability";
    }

    [[nodiscard]] std::string CardTierName(const EnhancementTier a_tier)
    {
        switch (a_tier) {
        case EnhancementTier::Weak: return "微弱";
        case EnhancementTier::Standard: return "标准";
        case EnhancementTier::Strong: return "强效";
        case EnhancementTier::Extreme: return "极强";
        }
        return "微弱";
    }

    [[nodiscard]] std::string CardTitle(const EnhancementCardType a_type)
    {
        switch (a_type) {
        case EnhancementCardType::Performance: return "千锤锋面";
        case EnhancementCardType::Weight: return "轻量重构";
        case EnhancementCardType::Speed: return "疾风配重";
        case EnhancementCardType::Durability: return "韧化锻造";
        case EnhancementCardType::Wear: return "耐磨覆层";
        case EnhancementCardType::Charge: return "灵能导路";
        case EnhancementCardType::Enchantment: return "奥术重铸";
        }
        return "未知强化";
    }

    [[nodiscard]] std::string CardDescription(const EnhancementCardType a_type)
    {
        switch (a_type) {
        case EnhancementCardType::Performance: return "提高武器攻击或护甲防御；服装不会抽到此卡。";
        case EnhancementCardType::Weight: return "降低装备重量，但最终重量不会低于 0.1。";
        case EnhancementCardType::Speed: return "提高武器攻击速度，累计上限为基础速度的 2 倍。";
        case EnhancementCardType::Durability: return "永久提高该装备实例的耐久上限。";
        case EnhancementCardType::Wear: return "降低每次战斗动作造成的耐久损耗。";
        case EnhancementCardType::Charge: return "提高已附魔武器可容纳的充能。";
        case EnhancementCardType::Enchantment: return "替换当前附魔；唯一物品与任务物品不会抽到此卡。";
        }
        return {};
    }

    [[nodiscard]] std::string FixedDecimal(const float a_value, const std::uint32_t a_precision)
    {
        std::ostringstream stream;
        stream << std::fixed << std::setprecision(a_precision) << a_value;
        return stream.str();
    }

    [[nodiscard]] std::string CardValue(const EnhancementCardState& a_card)
    {
        switch (a_card.type) {
        case EnhancementCardType::Performance:
            return "攻击 / 防御 +" + std::to_string(static_cast<std::int32_t>(std::lround(a_card.rolledValue)));
        case EnhancementCardType::Weight:
            return "重量 -" + FixedDecimal(a_card.rolledValue, 2);
        case EnhancementCardType::Speed:
            return "攻速 +" + FixedDecimal(a_card.rolledValue, 2) + "×";
        case EnhancementCardType::Durability:
            return "耐久上限 +" + std::to_string(static_cast<std::int32_t>(std::lround(a_card.rolledValue)));
        case EnhancementCardType::Wear:
            return "耐久损耗 -" + FixedDecimal(a_card.rolledValue * 100.0F, 0) + "%";
        case EnhancementCardType::Charge:
            return "附魔充能 +" + FixedDecimal(a_card.rolledValue * 100.0F, 0) + "%";
        case EnhancementCardType::Enchantment:
            return "随机附魔替换";
        }
        return {};
    }

    [[nodiscard]] EnhancementTier RollEnhancementTier(std::mt19937& a_random)
    {
        const auto roll = std::uniform_int_distribution<std::uint32_t>(1, 100)(a_random);
        if (roll <= 42) return EnhancementTier::Weak;
        if (roll <= 75) return EnhancementTier::Standard;
        if (roll <= 93) return EnhancementTier::Strong;
        return EnhancementTier::Extreme;
    }

    [[nodiscard]] float TierMultiplier(const EnhancementTier a_tier)
    {
        switch (a_tier) {
        case EnhancementTier::Weak: return 0.75F;
        case EnhancementTier::Standard: return 1.0F;
        case EnhancementTier::Strong: return 1.5F;
        case EnhancementTier::Extreme: return 2.25F;
        }
        return 1.0F;
    }

    [[nodiscard]] float RollCardValue(
        const EnhancementCardType a_type,
        const EnhancementTier a_tier,
        const DurabilitySnapshot& a_durability,
        RE::TESBoundObject* a_item,
        std::mt19937& a_random,
        std::string& a_blockedReason)
    {
        const auto tier = static_cast<std::size_t>(a_tier);
        const auto levelScale = 1.0F + static_cast<float>((std::min)(a_durability.enhancementLevel, 1000U)) * 0.04F;
        const auto roll = [&a_random](const float a_minimum, const float a_maximum) {
            return std::uniform_real_distribution<float>(a_minimum, a_maximum)(a_random);
        };
        switch (a_type) {
        case EnhancementCardType::Performance: {
            static constexpr std::array minimum{ 2.0F, 4.0F, 6.0F, 9.0F };
            static constexpr std::array maximum{ 3.0F, 5.0F, 8.0F, 10.0F };
            return std::round(roll(minimum[tier], maximum[tier]) * levelScale);
        }
        case EnhancementCardType::Weight: {
            static constexpr std::array minimum{ 1.0F, 1.4F, 1.8F, 2.4F };
            static constexpr std::array maximum{ 1.4F, 1.8F, 2.4F, 3.0F };
            const auto remaining = (std::max)(0.0F, EquipmentWeight(a_item) - a_durability.weightReduction - 0.1F);
            if (remaining <= 0.001F) a_blockedReason = "重量已达下限";
            return (std::min)(roll(minimum[tier], maximum[tier]), remaining);
        }
        case EnhancementCardType::Speed: {
            static constexpr std::array minimum{ 0.01F, 0.02F, 0.03F, 0.04F };
            static constexpr std::array maximum{ 0.019F, 0.029F, 0.039F, 0.05F };
            const auto remaining = (std::max)(0.0F, 1.0F - a_durability.attackSpeedBonus);
            if (remaining <= 0.0001F) a_blockedReason = "攻速已达 2× 上限";
            return (std::min)(roll(minimum[tier], maximum[tier]), remaining);
        }
        case EnhancementCardType::Durability: {
            static constexpr std::array minimum{ 1.0F, 3.0F, 6.0F, 9.0F };
            static constexpr std::array maximum{ 2.0F, 5.0F, 8.0F, 10.0F };
            return std::round(roll(minimum[tier], maximum[tier]) * levelScale);
        }
        case EnhancementCardType::Wear: {
            static constexpr std::array minimum{ 0.01F, 0.04F, 0.07F, 0.11F };
            static constexpr std::array maximum{ 0.03F, 0.06F, 0.10F, 0.15F };
            const auto remaining = (std::max)(0.0F, g_settings.maxWearReduction - a_durability.wearReduction);
            if (remaining <= 0.0001F) a_blockedReason = "耐磨已达上限";
            return (std::min)(roll(minimum[tier], maximum[tier]), remaining);
        }
        case EnhancementCardType::Charge: {
            static constexpr std::array minimum{ 0.05F, 0.11F, 0.21F, 0.36F };
            static constexpr std::array maximum{ 0.10F, 0.20F, 0.35F, 0.50F };
            if (a_durability.chargeBridgeInitialized &&
                a_durability.chargeAppliedCapacity == (std::numeric_limits<std::uint16_t>::max)()) {
                a_blockedReason = "附魔充能已达引擎上限";
                return 0.0F;
            }
            return roll(minimum[tier], maximum[tier]) * levelScale;
        }
        case EnhancementCardType::Enchantment:
            return 0.0F;
        }
        return 0.0F;
    }

    [[nodiscard]] std::map<RE::TESBoundObject*, std::int32_t> GetRecipeMaterials(RE::TESBoundObject* a_item)
    {
        std::map<RE::TESBoundObject*, std::int32_t> materials;
        const auto* recipe = FindRepairRecipe(a_item);
        if (!recipe) return materials;
        recipe->requiredItems.ForEachContainerObject([&materials](RE::ContainerObject& a_ingredient) {
            if (a_ingredient.obj && a_ingredient.count > 0) materials[a_ingredient.obj] += a_ingredient.count;
            return RE::BSContainer::ForEachResult::kContinue;
        });
        return materials;
    }

    void AddCardCatalyst(std::map<RE::TESBoundObject*, std::int32_t>& a_materials, std::string_view a_editorID, const std::int32_t a_count)
    {
        if (auto* material = RE::TESForm::LookupByEditorID<RE::TESBoundObject>(a_editorID)) a_materials[material] += a_count;
    }

    [[nodiscard]] std::vector<MaterialRequirementState> GetCardMaterials(
        RE::TESBoundObject* a_item,
        const EnhancementCardType a_type,
        const EnhancementTier a_tier,
        const std::uint32_t a_level)
    {
        auto materials = GetRecipeMaterials(a_item);
        const auto levelExponent = static_cast<float>((std::min)(a_level, 50U));
        const auto costScale = TierMultiplier(a_tier) * std::pow(1.16F, levelExponent);
        for (auto& [material, count] : materials) {
            count = (std::min)(9999, (std::max)(1, static_cast<std::int32_t>(std::ceil(static_cast<float>(count) * costScale))));
        }

        const auto catalystCount = (std::min)(9999, (std::max)(1, static_cast<std::int32_t>(std::ceil(costScale))));
        switch (a_type) {
        case EnhancementCardType::Performance: AddCardCatalyst(materials, "IngotIron", catalystCount); break;
        case EnhancementCardType::Weight: AddCardCatalyst(materials, "LeatherStrips", catalystCount); break;
        case EnhancementCardType::Speed: AddCardCatalyst(materials, "IngotQuicksilver", catalystCount); break;
        case EnhancementCardType::Durability: AddCardCatalyst(materials, "IngotCorundum", catalystCount); break;
        case EnhancementCardType::Wear: AddCardCatalyst(materials, "IngotDwarven", catalystCount); break;
        case EnhancementCardType::Charge: AddCardCatalyst(materials, "SoulGemCommonFilled", catalystCount); break;
        case EnhancementCardType::Enchantment:
            AddCardCatalyst(materials, "SoulGemGrandFilled", catalystCount);
            AddCardCatalyst(materials, "VoidSalts", catalystCount);
            break;
        }

        std::vector<MaterialRequirementState> result;
        result.reserve(materials.size());
        for (const auto& [material, count] : materials) {
            if (material && count > 0) result.push_back({ material->GetFormID(), count });
        }
        return result;
    }

    [[nodiscard]] std::vector<EnhancementCardType> EligibleCardTypes(RE::TESBoundObject* a_item, RE::ExtraDataList* a_extraList)
    {
        std::vector<EnhancementCardType> types;
        const auto* weapon = a_item ? a_item->As<RE::TESObjectWEAP>() : nullptr;
        const auto category = EquipmentCategory(a_item);
        if ((weapon && BasePerformanceValue(a_item) > 0.0F) || category == "armor") types.push_back(EnhancementCardType::Performance);
        if (EquipmentWeight(a_item) > 0.1F) types.push_back(EnhancementCardType::Weight);
        if (weapon) types.push_back(EnhancementCardType::Speed);
        types.push_back(EnhancementCardType::Durability);
        types.push_back(EnhancementCardType::Wear);
        if (weapon && InstanceChargeCapacity(a_item, a_extraList)) types.push_back(EnhancementCardType::Charge);
        const auto protectedItem = IsProtectedUniqueItem(a_item) || (a_extraList && a_extraList->HasQuestObjectAlias());
        if (!protectedItem) types.push_back(EnhancementCardType::Enchantment);
        return types;
    }

    [[nodiscard]] std::vector<EnhancementCardState> GenerateEnhancementCards(
        const ItemKey& a_key,
        RE::TESBoundObject* a_item,
        RE::ExtraDataList* a_extraList,
        const std::uint32_t a_refreshes)
    {
        std::uint64_t sequence = 0;
        {
            std::scoped_lock lock(g_forgeLock);
            sequence = ++g_cardSequence;
        }
        const auto seed = static_cast<std::uint32_t>(
            std::chrono::steady_clock::now().time_since_epoch().count() ^
            (static_cast<std::uint64_t>(a_key.baseFormID) << 16U) ^ a_key.uniqueID ^ sequence);
        std::mt19937 random(seed);
        auto eligibleTypes = EligibleCardTypes(a_item, a_extraList);
        std::shuffle(eligibleTypes.begin(), eligibleTypes.end(), random);
        if (eligibleTypes.size() > 3) eligibleTypes.resize(3);
        const auto distinctTypeCount = eligibleTypes.size();
        while (!eligibleTypes.empty() && eligibleTypes.size() < 3) {
            eligibleTypes.push_back(eligibleTypes[eligibleTypes.size() % distinctTypeCount]);
        }

        const auto durability = GetDurability(a_key);
        std::vector<EnhancementCardState> cards;
        cards.reserve(eligibleTypes.size());
        for (std::size_t index = 0; index < eligibleTypes.size(); ++index) {
            EnhancementCardState card;
            card.id = std::to_string(a_key.baseFormID) + "-" + std::to_string(a_key.uniqueID) + "-" +
                      std::to_string(sequence) + "-" + std::to_string(index);
            card.type = eligibleTypes[index];
            card.tier = RollEnhancementTier(random);
            card.rolledValue = RollCardValue(card.type, card.tier, durability, a_item, random, card.blockedReason);
            static constexpr std::array<std::uint32_t, 4> baseSuccess{ 96, 88, 75, 60 };
            const auto levelPenalty = (std::min)(45U, durability.enhancementLevel > 22U ? 45U : durability.enhancementLevel * 2U);
            card.successChance = (std::max)(10U, baseSuccess[static_cast<std::size_t>(card.tier)] - levelPenalty);
            card.requiredMaterials = GetCardMaterials(a_item, card.type, card.tier, durability.enhancementLevel);
            if (card.requiredMaterials.empty() && card.blockedReason.empty()) card.blockedReason = "没有可用的强化材料";
            if (a_key.uniqueID == 0 && card.blockedReason.empty()) card.blockedReason = "请先装备一次以建立独立实例";
            if (durability.current <= 0.0F && card.blockedReason.empty()) card.blockedReason = "请先修复装备";
            if (card.type == EnhancementCardType::Enchantment && card.blockedReason.empty()) card.blockedReason = "附魔替换尚未启用";
            cards.push_back(std::move(card));
        }
        logger::info("Generated {} enhancement cards for {:08X}:{:04X} after {} paid refreshes.", cards.size(), a_key.baseFormID, a_key.uniqueID, a_refreshes);
        return cards;
    }

    [[nodiscard]] json EnhancementCardsJson()
    {
        std::vector<EnhancementCardState> cards;
        {
            std::scoped_lock lock(g_forgeLock);
            cards = g_enhancementCards;
        }
        auto* player = RE::PlayerCharacter::GetSingleton();
        json result = json::array();
        for (const auto& card : cards) {
            json materials = json::array();
            std::string blockedReason = card.blockedReason;
            for (const auto& requirement : card.requiredMaterials) {
                auto* material = RE::TESForm::LookupByID<RE::TESBoundObject>(requirement.formID);
                if (!material) continue;
                const auto owned = player ? (std::max)(0, player->GetItemCount(material)) : 0;
                materials.push_back({ { "name", DisplayName(material) }, { "required", requirement.count }, { "owned", owned } });
                if (blockedReason.empty() && owned < requirement.count) blockedReason = "缺少：" + DisplayName(material);
            }
            auto item = json{
                { "id", card.id },
                { "type", CardTypeID(card.type) },
                { "tier", CardTierName(card.tier) },
                { "title", CardTitle(card.type) },
                { "description", CardDescription(card.type) },
                { "value", CardValue(card) },
                { "successChance", card.successChance },
                { "materials", std::move(materials) }
            };
            if (!blockedReason.empty()) item["blockedReason"] = blockedReason;
            result.push_back(std::move(item));
        }
        return result;
    }

    [[nodiscard]] std::uint32_t CardRefreshCost(const std::uint32_t a_refreshes)
    {
        return kBaseCardRefreshCost * ((std::min)(a_refreshes, 999U) + 1U);
    }

    void SelectEquipmentForForge(const std::string_view a_equipmentID)
    {
        if (!GetForgeContext().active) return;
        const auto key = ParseItemKey(a_equipmentID);
        if (!key) {
            SendState("无法为无效的装备实例生成强化卡片。");
            return;
        }
        const auto instance = ResolveEquipmentInstance(*key);
        if (!instance) {
            SendState("所选装备已不在背包中。");
            return;
        }
        {
            std::scoped_lock lock(g_forgeLock);
            if (g_forgeSelectedItem == key && !g_enhancementCards.empty()) return;
        }
        auto cards = GenerateEnhancementCards(*key, instance->item, instance->extraList, 0);
        {
            std::scoped_lock lock(g_forgeLock);
            g_forgeSelectedItem = *key;
            g_forgeRefreshes = 0;
            g_enhancementCards = std::move(cards);
        }
        SendState("已为" + InstanceDisplayName(instance->item, instance->extraList) + "生成三张强化卡片。");
    }

    void RefreshEnhancementCards(const std::string_view a_equipmentID)
    {
        if (!GetForgeContext().active) {
            SendState("刷新失败：请先使用附近的锻造设施。");
            return;
        }
        const auto key = ParseItemKey(a_equipmentID);
        if (!key) {
            SendState("刷新失败：装备实例标识无效。");
            return;
        }
        const auto instance = ResolveEquipmentInstance(*key);
        if (!instance) {
            SendState("刷新失败：所选装备已不在背包中。");
            return;
        }

        std::uint32_t refreshes = 0;
        bool selectionMatches = false;
        {
            std::scoped_lock lock(g_forgeLock);
            if (g_forgeSelectedItem != key) {
                g_forgeSelectedItem.reset();
                g_enhancementCards.clear();
            } else {
                selectionMatches = true;
                refreshes = g_forgeRefreshes;
            }
        }
        if (!selectionMatches) {
            SelectEquipmentForForge(a_equipmentID);
            return;
        }

        auto* player = RE::PlayerCharacter::GetSingleton();
        auto* gold = RE::TESForm::LookupByID<RE::TESBoundObject>(0x0000000FU);
        const auto cost = CardRefreshCost(refreshes);
        if (!player || !gold || player->GetGoldAmount() < static_cast<std::int32_t>(cost)) {
            SendState("刷新失败：需要 " + std::to_string(cost) + " 金币。");
            return;
        }
        player->RemoveItem(gold, static_cast<std::int32_t>(cost), RE::ITEM_REMOVE_REASON::kRemove, nullptr, nullptr);
        auto cards = GenerateEnhancementCards(*key, instance->item, instance->extraList, refreshes + 1U);
        {
            std::scoped_lock lock(g_forgeLock);
            if (g_forgeSelectedItem != key) return;
            ++g_forgeRefreshes;
            g_enhancementCards = std::move(cards);
        }
        SendState("已支付 " + std::to_string(cost) + " 金币并刷新强化卡片。");
    }

    [[nodiscard]] std::string SalvageDescription(const std::map<RE::TESBoundObject*, std::int32_t>& a_materials)
    {
        std::string description = "已损毁并分解：";
        bool first = true;
        for (const auto& [material, count] : a_materials) {
            if (!first) description += "，";
            description += DisplayName(material) + " ×" + std::to_string(count);
            first = false;
        }
        return description;
    }

    void SetNextEnhancementDraft(
        const ItemKey& a_key,
        RE::TESBoundObject* a_item,
        RE::ExtraDataList* a_extraList)
    {
        auto cards = GenerateEnhancementCards(a_key, a_item, a_extraList, 0);
        std::scoped_lock lock(g_forgeLock);
        g_forgeSelectedItem = a_key;
        g_forgeRefreshes = 0;
        g_enhancementCards = std::move(cards);
    }

    void ClearEnhancementDraft()
    {
        std::scoped_lock lock(g_forgeLock);
        g_forgeSelectedItem.reset();
        g_forgeRefreshes = 0;
        g_enhancementCards.clear();
    }

    void ApplySuccessfulCard(
        const ItemKey& a_key,
        RE::TESBoundObject* a_item,
        const EnhancementCardState& a_card)
    {
        std::scoped_lock lock(g_durabilityLock);
        auto& durability = g_durability[a_key];
        durability.maximum = (std::max)(1.0F, durability.maximum);
        durability.current = std::clamp(durability.current, 0.0F, durability.maximum);
        switch (a_card.type) {
        case EnhancementCardType::Performance: {
            const auto increased = static_cast<std::int64_t>(durability.performanceBonus) +
                                   static_cast<std::int64_t>(std::lround(a_card.rolledValue));
            durability.performanceBonus = static_cast<std::int32_t>((std::min)(
                increased,
                static_cast<std::int64_t>((std::numeric_limits<std::int32_t>::max)())));
            break;
        }
        case EnhancementCardType::Weight:
            durability.weightReduction = (std::min)(
                (std::max)(0.0F, EquipmentWeight(a_item) - 0.1F),
                durability.weightReduction + (std::max)(0.0F, a_card.rolledValue));
            break;
        case EnhancementCardType::Speed:
            durability.attackSpeedBonus = (std::min)(1.0F, durability.attackSpeedBonus + (std::max)(0.0F, a_card.rolledValue));
            break;
        case EnhancementCardType::Durability: {
            const auto missingDurability = durability.maximum - durability.current;
            durability.maximum += (std::max)(0.0F, a_card.rolledValue);
            durability.current = (std::max)(0.0F, durability.maximum - missingDurability);
            break;
        }
        case EnhancementCardType::Wear:
            durability.wearReduction = (std::min)(g_settings.maxWearReduction, durability.wearReduction + (std::max)(0.0F, a_card.rolledValue));
            break;
        case EnhancementCardType::Charge:
            durability.chargeBonus = (std::min)(
                65534.0F,
                durability.chargeBonus + (std::max)(0.0F, a_card.rolledValue));
            break;
        case EnhancementCardType::Enchantment:
            break;
        }
        if (durability.enhancementLevel < (std::numeric_limits<std::uint32_t>::max)()) ++durability.enhancementLevel;
        g_lowDurabilityWarnings.erase(a_key);
    }

    void DowngradeProtectedEquipment(const ItemKey& a_key)
    {
        std::scoped_lock lock(g_durabilityLock);
        auto& durability = g_durability[a_key];
        const auto oldLevel = durability.enhancementLevel;
        const auto newLevel = oldLevel > 0 ? oldLevel - 1U : 0U;
        const auto ratio = oldLevel > 0 ? static_cast<float>(newLevel) / static_cast<float>(oldLevel) : 0.0F;
        durability.performanceBonus = static_cast<std::int32_t>(std::lround(static_cast<float>(durability.performanceBonus) * ratio));
        durability.weightReduction *= ratio;
        durability.attackSpeedBonus *= ratio;
        durability.wearReduction *= ratio;
        durability.chargeBonus *= ratio;
        durability.maximum = 100.0F + (std::max)(0.0F, durability.maximum - 100.0F) * ratio;
        durability.current = std::clamp(durability.current, 0.0F, durability.maximum);
        durability.enhancementLevel = newLevel;
        g_lowDurabilityWarnings.erase(a_key);
    }

    void ApplyEnhancementCard(const std::string_view a_equipmentID, const std::string_view a_cardID)
    {
        if (!GetForgeContext().active) {
            SendState("强化失败：请先使用附近的锻造设施。");
            return;
        }
        const auto key = ParseItemKey(a_equipmentID);
        if (!key || key->uniqueID == 0) {
            SendState("强化失败：请先装备该物品一次，以建立可独立追踪的装备实例。");
            return;
        }

        EnhancementCardState card;
        bool foundCard = false;
        bool selectionMatches = false;
        {
            std::scoped_lock lock(g_forgeLock);
            selectionMatches = g_forgeSelectedItem == key;
            if (selectionMatches) {
                const auto found = std::find_if(g_enhancementCards.begin(), g_enhancementCards.end(), [a_cardID](const auto& a_candidate) {
                    return a_candidate.id == a_cardID;
                });
                if (found != g_enhancementCards.end()) {
                    card = *found;
                    foundCard = true;
                }
            }
        }
        if (!selectionMatches) {
            SendState("强化失败：所选装备与当前卡片不匹配。");
            return;
        }
        if (!foundCard) {
            SendState("强化失败：该卡片已经失效，请重新选择。");
            return;
        }
        if (!card.blockedReason.empty()) {
            SendState("强化失败：" + card.blockedReason + "。");
            return;
        }
        if (card.type == EnhancementCardType::Enchantment) {
            SendState("附魔替换将在建立兼容附魔池后启用，本次没有消耗材料。");
            return;
        }

        const auto instance = ResolveEquipmentInstance(*key);
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!instance || !player) {
            SendState("强化失败：所选装备已不在背包中。");
            return;
        }
        const auto durability = GetDurability(*key);
        if (durability.current <= 0.0F) {
            SendState("强化失败：请先修复已经损坏的装备。");
            return;
        }

        std::vector<std::pair<RE::TESBoundObject*, std::int32_t>> materials;
        materials.reserve(card.requiredMaterials.size());
        for (const auto& requirement : card.requiredMaterials) {
            auto* material = RE::TESForm::LookupByID<RE::TESBoundObject>(requirement.formID);
            if (!material || requirement.count <= 0) {
                SendState("强化失败：卡片材料已经失效，请刷新卡片。");
                return;
            }
            if (player->GetItemCount(material) < requirement.count) {
                SendState("强化失败：缺少" + DisplayName(material) + "，需要 " + std::to_string(requirement.count) + " 个。");
                return;
            }
            materials.emplace_back(material, requirement.count);
        }
        for (const auto& [material, count] : materials) {
            player->RemoveItem(material, count, RE::ITEM_REMOVE_REASON::kRemove, nullptr, nullptr);
        }

        const auto seed = static_cast<std::uint32_t>(
            std::chrono::steady_clock::now().time_since_epoch().count() ^
            (static_cast<std::uint64_t>(key->baseFormID) << 16U) ^ key->uniqueID ^ std::hash<std::string_view>{}(a_cardID));
        std::mt19937 random(seed);
        const auto roll = std::uniform_int_distribution<std::uint32_t>(1, 100)(random);
        const auto itemName = InstanceDisplayName(instance->item, instance->extraList);
        if (roll <= card.successChance) {
            ApplySuccessfulCard(*key, instance->item, card);
            SyncInstanceRuntimeEffects(*key, instance->item, instance->extraList);
            QueuePlayerRuntimeEffectsSync();
            const auto result = GetDurability(*key);
            SetNextEnhancementDraft(*key, instance->item, instance->extraList);
            logger::info(
                "Enhancement succeeded for {:08X}:{:04X}; card={}, roll={}, chance={}, newLevel={}.",
                key->baseFormID,
                key->uniqueID,
                CardTypeID(card.type),
                roll,
                card.successChance,
                result.enhancementLevel);
            SendState(itemName + "强化成功，当前等级 +" + std::to_string(result.enhancementLevel) + "。");
            return;
        }

        const auto protectedItem = instance->extraList->HasQuestObjectAlias() || IsProtectedUniqueItem(instance->item);
        if (protectedItem) {
            DowngradeProtectedEquipment(*key);
            SyncInstanceRuntimeEffects(*key, instance->item, instance->extraList);
            QueuePlayerRuntimeEffectsSync();
            const auto result = GetDurability(*key);
            SetNextEnhancementDraft(*key, instance->item, instance->extraList);
            logger::info(
                "Protected enhancement failed for {:08X}:{:04X}; roll={}, chance={}, downgradedTo={}.",
                key->baseFormID,
                key->uniqueID,
                roll,
                card.successChance,
                result.enhancementLevel);
            SendState(itemName + "强化失败，但受保护未被分解；强化等级降至 +" + std::to_string(result.enhancementLevel) + "。");
            return;
        }

        const auto salvage = GetSalvageMaterials(instance->item);
        player->RemoveItem(instance->item, 1, RE::ITEM_REMOVE_REASON::kRemove, instance->extraList, nullptr);
        if (IsUniqueIDInPlayerInventory(key->baseFormID, key->uniqueID)) {
            const auto retainedInstance = ResolveEquipmentInstance(*key);
            if (retainedInstance) SetNextEnhancementDraft(*key, retainedInstance->item, retainedInstance->extraList);
            else ClearEnhancementDraft();
            logger::error("Could not remove failed enhancement item {:08X}:{:04X}.", key->baseFormID, key->uniqueID);
            QueuePlayerRuntimeEffectsSync();
            SendState(itemName + "强化失败，但装备移除失败；装备已保留，尝试材料仍然消耗。");
            return;
        }
        for (const auto& [material, count] : salvage) player->AddObjectToContainer(material, nullptr, count, nullptr);
        {
            std::scoped_lock lock(g_durabilityLock);
            g_durability.erase(*key);
            g_lowDurabilityWarnings.erase(*key);
            g_pendingBreaks.erase(*key);
            g_weaponNotificationTimes.erase(*key);
        }
        ClearEnhancementDraft();
        QueuePlayerRuntimeEffectsSync();
        logger::info(
            "Enhancement failed and dismantled {:08X}:{:04X}; roll={}, chance={}, salvageTypes={}.",
            key->baseFormID,
            key->uniqueID,
            roll,
            card.successChance,
            salvage.size());
        SendState(itemName + "强化失败，装备已分解。" + (salvage.empty() ? "" : SalvageDescription(salvage)));
    }

    void ResolveZeroDurability(const ItemKey a_key, const std::uint64_t a_epoch)
    {
        {
            std::scoped_lock lock(g_durabilityLock);
            const auto durability = g_durability.find(a_key);
            if (a_epoch != g_stateEpoch || !g_pendingBreaks.contains(a_key) ||
                (durability != g_durability.end() && durability->second.current > 0.0F)) {
                g_pendingBreaks.erase(a_key);
                return;
            }
        }
        const auto finish = [&a_key] {
            std::scoped_lock lock(g_durabilityLock);
            g_pendingBreaks.erase(a_key);
        };
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto* item = RE::TESForm::LookupByID<RE::TESBoundObject>(a_key.baseFormID);
        if (!player || !item) {
            finish();
            return;
        }

        const auto inventory = player->GetInventory();
        const auto found = inventory.find(item);
        auto* entry = found != inventory.end() && found->second.second ? found->second.second.get() : nullptr;
        auto* extraList = FindExtraListByKey(entry, a_key);
        if (!entry || !extraList) {
            std::scoped_lock lock(g_durabilityLock);
            g_durability.erase(a_key);
            g_lowDurabilityWarnings.erase(a_key);
            g_pendingBreaks.erase(a_key);
            return;
        }

        const auto questItem = extraList->HasQuestObjectAlias();
        const auto uniqueItem = IsProtectedUniqueItem(item);
        const auto preserveEnchanted = IsInstanceEnchanted(item, extraList) && !g_settings.allowEnchantedItemsToBreak;
        auto materials = GetSalvageMaterials(item);
        const auto preserve = questItem || uniqueItem || preserveEnchanted || materials.empty();
        if (preserve) {
            if (auto* equipManager = RE::ActorEquipManager::GetSingleton()) equipManager->UnequipObject(player, item, extraList);
            const auto reason = questItem || uniqueItem ? "受保护物品已损坏，需要在装备工坊修复。" : preserveEnchanted ? "附魔物品已损坏，需要在装备工坊修复。" : "未找到可用的锻造配方，物品已保留为损坏状态。";
            ShowHUD("warning", DisplayName(item), reason, g_settings.weaponDisplaySeconds, 0, static_cast<std::uint32_t>(std::lround(GetDurability(a_key).maximum)));
            logger::info("Preserved broken item {:08X}:{:04X} (quest={}, unique={}, enchanted-protected={}, recipe-missing={}).", a_key.baseFormID, a_key.uniqueID, questItem, uniqueItem, preserveEnchanted, materials.empty());
        } else {
            player->RemoveItem(item, 1, RE::ITEM_REMOVE_REASON::kRemove, extraList, nullptr);
            if (IsUniqueIDInPlayerInventory(a_key.baseFormID, a_key.uniqueID)) {
                const auto refreshedInventory = player->GetInventory();
                const auto refreshed = refreshedInventory.find(item);
                auto* refreshedEntry = refreshed != refreshedInventory.end() && refreshed->second.second ? refreshed->second.second.get() : nullptr;
                auto* refreshedExtraList = FindExtraListByKey(refreshedEntry, a_key);
                if (auto* equipManager = RE::ActorEquipManager::GetSingleton(); equipManager && refreshedExtraList) equipManager->UnequipObject(player, item, refreshedExtraList);
                ShowHUD("warning", DisplayName(item), "物品移除失败，已保留为损坏状态。", g_settings.weaponDisplaySeconds, 0, static_cast<std::uint32_t>(std::lround(GetDurability(a_key).maximum)));
                logger::error("Could not remove destroyed item {:08X}:{:04X}; preserved it as broken.", a_key.baseFormID, a_key.uniqueID);
            } else {
                for (const auto& [material, count] : materials) player->AddObjectToContainer(material, nullptr, count, nullptr);
                {
                    std::scoped_lock lock(g_durabilityLock);
                    g_durability.erase(a_key);
                    g_lowDurabilityWarnings.erase(a_key);
                }
                ShowHUD("warning", DisplayName(item), SalvageDescription(materials), g_settings.weaponDisplaySeconds);
                logger::info("Destroyed and salvaged item {:08X}:{:04X} into {} material types.", a_key.baseFormID, a_key.uniqueID, materials.size());
            }
        }
        finish();
        QueuePlayerRuntimeEffectsSync();
        if (g_panelVisible) SendState();
    }

    void QueueZeroDurabilityResolution(const ItemKey& a_key)
    {
        std::uint64_t epoch = 0;
        {
            std::scoped_lock lock(g_durabilityLock);
            if (!g_pendingBreaks.insert(a_key).second) return;
            epoch = g_stateEpoch;
        }
        if (const auto* tasks = SKSE::GetTaskInterface()) tasks->AddTask([a_key, epoch] { ResolveZeroDurability(a_key, epoch); });
        else ResolveZeroDurability(a_key, epoch);
    }

    void QueueStoredZeroDurabilityResolutions()
    {
        std::vector<ItemKey> brokenItems;
        {
            std::scoped_lock lock(g_durabilityLock);
            for (const auto& [key, durability] : g_durability) {
                if (durability.current <= 0.0F) brokenItems.push_back(key);
            }
        }
        for (const auto& key : brokenItems) QueueZeroDurabilityResolution(key);
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

    [[nodiscard]] std::optional<float> BaseWeaponWear(const RE::TESObjectWEAP* a_weapon)
    {
        if (!a_weapon || a_weapon->IsBound()) return std::nullopt;
        switch (a_weapon->GetWeaponType()) {
        case RE::WEAPON_TYPE::kOneHandDagger:
            return g_settings.daggerHitWear;
        case RE::WEAPON_TYPE::kOneHandSword:
            return g_settings.swordHitWear;
        case RE::WEAPON_TYPE::kOneHandAxe:
            return g_settings.warAxeHitWear;
        case RE::WEAPON_TYPE::kOneHandMace:
            return g_settings.maceHitWear;
        case RE::WEAPON_TYPE::kTwoHandSword:
            return g_settings.greatswordHitWear;
        case RE::WEAPON_TYPE::kTwoHandAxe:
            return a_weapon->HasKeywordString("WeapTypeWarhammer") ? g_settings.warhammerHitWear : g_settings.battleaxeHitWear;
        case RE::WEAPON_TYPE::kBow:
            return g_settings.bowShotWear;
        case RE::WEAPON_TYPE::kCrossbow:
            return g_settings.crossbowShotWear;
        default:
            return std::nullopt;
        }
    }

    [[nodiscard]] float BaseArmorWear(const RE::TESObjectARMO* a_armor)
    {
        if (!a_armor) return 0.0F;
        if (a_armor->IsShield()) return g_settings.shieldBlockWear;
        return a_armor->IsClothing() ? g_settings.clothingHitWear : g_settings.armorHitWear;
    }

    void ApplyEquipmentWear(
        const RE::TESBoundObject* a_item,
        const ItemKey& a_key,
        const float a_baseWear,
        const float a_actionMultiplier,
        const std::string_view a_action)
    {
        if (!a_item || a_baseWear <= 0.0F) return;
        DurabilitySnapshot durability;
        float appliedWear = 0.0F;
        {
            std::scoped_lock lock(g_durabilityLock);
            auto& stored = g_durability[a_key];
            stored.maximum = (std::max)(1.0F, stored.maximum);
            stored.current = std::clamp(stored.current, 0.0F, stored.maximum);
            if (stored.current <= 0.0F) return;
            const auto reduction = std::clamp(stored.wearReduction, 0.0F, g_settings.maxWearReduction);
            appliedWear = (std::max)(0.1F, a_baseWear * a_actionMultiplier * (1.0F - reduction));
            stored.current = (std::max)(0.0F, stored.current - appliedWear);
            durability = stored;
        }
        logger::debug(
            "{} wore {:08X}:{:04X} by {:.2F}; now {:.2F}/{:.2F}.",
            a_action,
            a_key.baseFormID,
            a_key.uniqueID,
            appliedWear,
            durability.current,
            durability.maximum);
        UpdateLowDurabilityWarning(a_item, a_key, durability);
        if (durability.current <= 0.0F) QueueZeroDurabilityResolution(a_key);
        if (g_panelVisible) SendState();
    }

    void ApplyWeaponWear(
        RE::InventoryEntryData* a_entry,
        const RE::TESObjectWEAP* a_weapon,
        const float a_baseWear,
        const float a_actionMultiplier,
        const std::string_view a_action)
    {
        if (!a_weapon || a_weapon->IsBound()) return;
        const auto key = EnsureItemKey(a_entry, a_weapon);
        if (!key) return;
        ApplyEquipmentWear(a_weapon, *key, a_baseWear, a_actionMultiplier, a_action);
    }

    struct WornArmorInstance
    {
        RE::TESObjectARMO* armor = nullptr;
        RE::ExtraDataList* extraList = nullptr;
        ItemKey key{};
        float selectionWeight = 0.0F;
    };

    [[nodiscard]] float ArmorSelectionWeight(const RE::TESObjectARMO* a_armor)
    {
        if (!a_armor || a_armor->IsShield()) return 0.0F;
        using Slot = RE::BIPED_MODEL::BipedObjectSlot;
        const auto slots = std::to_underlying(a_armor->GetSlotMask());
        const auto has = [slots](const Slot a_slot) { return (slots & std::to_underlying(a_slot)) != 0; };
        if (has(Slot::kBody)) return 5.0F;
        if (has(Slot::kHead) || has(Slot::kCirclet)) return 2.0F;
        if (has(Slot::kHands) || has(Slot::kForearms)) return 1.5F;
        if (has(Slot::kFeet) || has(Slot::kCalves)) return 1.5F;
        if (has(Slot::kRing) || has(Slot::kAmulet)) return 0.0F;
        return slots != 0 ? 0.75F : 0.0F;
    }

    [[nodiscard]] std::vector<WornArmorInstance> CollectWornArmorInstances()
    {
        std::vector<WornArmorInstance> result;
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!player) return result;
        const auto inventory = player->GetInventory();
        for (const auto& [item, entry] : inventory) {
            auto* armor = item ? item->As<RE::TESObjectARMO>() : nullptr;
            if (!armor || !entry.second || !entry.second->extraLists) continue;
            for (auto* extraList : *entry.second->extraLists) {
                if (!extraList || !extraList->GetWorn()) continue;
                const auto key = EnsureItemKeyForExtraList(extraList, armor);
                if (!key) continue;
                if (GetDurability(*key).current <= 0.0F) {
                    QueueZeroDurabilityResolution(*key);
                    continue;
                }
                result.push_back({ armor, extraList, *key, ArmorSelectionWeight(armor) });
            }
        }
        return result;
    }

    void ApplyIncomingArmorWear(const RE::TESHitEvent& a_event)
    {
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!player || a_event.target.get() != player || a_event.cause.get() == player) return;

        const auto* source = a_event.source != 0 ? RE::TESForm::LookupByID(a_event.source) : nullptr;
        const auto* sourceWeapon = source ? source->As<RE::TESObjectWEAP>() : nullptr;
        if (a_event.source != 0 && (!sourceWeapon || sourceWeapon->IsStaff())) return;

        auto wornArmor = CollectWornArmorInstances();
        if (wornArmor.empty()) return;
        WornArmorInstance* selected = nullptr;
        const auto blocked = a_event.flags.any(RE::TESHitEvent::Flag::kHitBlocked);
        if (blocked) {
            const auto shield = std::find_if(wornArmor.begin(), wornArmor.end(), [](const auto& a_candidate) {
                return a_candidate.armor && a_candidate.armor->IsShield();
            });
            if (shield == wornArmor.end()) return;
            selected = std::addressof(*shield);
        } else {
            std::vector<double> weights;
            weights.reserve(wornArmor.size());
            for (const auto& candidate : wornArmor) weights.push_back(static_cast<double>(candidate.selectionWeight));
            if (std::none_of(weights.begin(), weights.end(), [](const double a_weight) { return a_weight > 0.0; })) return;
            const auto seed = static_cast<std::uint32_t>(
                std::chrono::steady_clock::now().time_since_epoch().count() ^
                (++g_armorHitSequence << 16U) ^ a_event.source ^ a_event.projectile);
            std::mt19937 random(seed);
            std::discrete_distribution<std::size_t> distribution(weights.begin(), weights.end());
            selected = std::addressof(wornArmor[distribution(random)]);
        }
        if (!selected || !selected->armor) return;
        const auto multiplier = a_event.flags.any(RE::TESHitEvent::Flag::kPowerAttack) ?
                                    g_settings.incomingPowerAttackWearMultiplier :
                                    1.0F;
        ApplyEquipmentWear(
            selected->armor,
            selected->key,
            BaseArmorWear(selected->armor),
            multiplier,
            blocked ? "Blocked physical hit" : "Incoming physical hit");
    }

    class EquipmentEventSink final : public RE::BSTEventSink<RE::TESEquipEvent>, public RE::BSTEventSink<RE::BSAnimationGraphEvent>, public RE::BSTEventSink<RE::TESHitEvent>, public RE::BSTEventSink<RE::TESPlayerBowShotEvent>, public RE::BSTEventSink<RE::TESActivateEvent>, public RE::BSTEventSink<RE::TESContainerChangedEvent>
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
            if (auto* source = RE::ScriptEventSourceHolder::GetSingleton()) source->AddEventSink<RE::TESHitEvent>(this);
            if (auto* source = RE::ScriptEventSourceHolder::GetSingleton()) source->AddEventSink<RE::TESPlayerBowShotEvent>(this);
            if (auto* source = RE::ScriptEventSourceHolder::GetSingleton()) source->AddEventSink<RE::TESActivateEvent>(this);
            if (auto* source = RE::ScriptEventSourceHolder::GetSingleton()) source->AddEventSink<RE::TESContainerChangedEvent>(this);
            if (const auto* player = RE::PlayerCharacter::GetSingleton()) player->AddAnimationGraphEventSink(this);
            registered_ = true;
        }

        RE::BSEventNotifyControl ProcessEvent(const RE::TESActivateEvent* a_event, RE::BSTEventSource<RE::TESActivateEvent>*) override
        {
            auto* player = RE::PlayerCharacter::GetSingleton();
            auto* station = a_event ? a_event->objectActivated.get() : nullptr;
            if (!a_event || !player || a_event->actionRef.get() != player || !station) return RE::BSEventNotifyControl::kContinue;
            auto stationName = ForgeStationName(station->GetBaseObject());
            if (!stationName.empty()) ActivateForgeContext(station, std::move(stationName));
            return RE::BSEventNotifyControl::kContinue;
        }

        RE::BSEventNotifyControl ProcessEvent(const RE::TESEquipEvent* a_event, RE::BSTEventSource<RE::TESEquipEvent>*) override
        {
            auto* player = RE::PlayerCharacter::GetSingleton();
            if (!a_event || !player || a_event->actor.get() != player) return RE::BSEventNotifyControl::kContinue;
            QueuePlayerRuntimeEffectsSync();
            if (!a_event->equipped) return RE::BSEventNotifyControl::kContinue;
            const auto* weapon = RE::TESForm::LookupByID<RE::TESObjectWEAP>(a_event->baseObject);
            if (weapon) {
                auto* entry = FindEquippedWeaponEntry(weapon);
                const auto key = EnsureItemKey(entry, weapon);
                if (key) {
                    if (const auto instance = ResolveEquipmentInstance(*key); instance && instance->extraList) {
                        SyncInstanceRuntimeEffects(*key, instance->item, instance->extraList);
                    }
                }
                if (key && GetDurability(*key).current <= 0.0F) {
                    QueueZeroDurabilityResolution(*key);
                    return RE::BSEventNotifyControl::kContinue;
                }
                ShowWeaponDurability(weapon, entry);
                return RE::BSEventNotifyControl::kContinue;
            }

            auto* armor = RE::TESForm::LookupByID<RE::TESObjectARMO>(a_event->baseObject);
            if (!armor) return RE::BSEventNotifyControl::kContinue;
            std::optional<ItemKey> key;
            RE::ExtraDataList* extraList = nullptr;
            if (a_event->uniqueID != 0) {
                key = ItemKey{ a_event->baseObject, a_event->uniqueID };
                if (const auto instance = ResolveEquipmentInstance(*key)) extraList = instance->extraList;
            }
            if (!extraList) {
                const auto inventory = player->GetInventory();
                const auto found = inventory.find(armor);
                auto* entry = found != inventory.end() && found->second.second ? found->second.second.get() : nullptr;
                extraList = FindWornExtraList(entry);
                key = EnsureItemKeyForExtraList(extraList, armor);
            }
            if (!key || !extraList) return RE::BSEventNotifyControl::kContinue;
            SyncInstanceRuntimeEffects(*key, armor, extraList);
            if (GetDurability(*key).current <= 0.0F) QueueZeroDurabilityResolution(*key);
            return RE::BSEventNotifyControl::kContinue;
        }

        RE::BSEventNotifyControl ProcessEvent(
            const RE::TESContainerChangedEvent* a_event,
            RE::BSTEventSource<RE::TESContainerChangedEvent>*) override
        {
            const auto* player = RE::PlayerCharacter::GetSingleton();
            if (!a_event || !player) return RE::BSEventNotifyControl::kContinue;
            const auto playerID = player->GetFormID();
            if (a_event->oldContainer == playerID || a_event->newContainer == playerID) QueuePlayerRuntimeEffectsSync();
            return RE::BSEventNotifyControl::kContinue;
        }

        RE::BSEventNotifyControl ProcessEvent(const RE::TESPlayerBowShotEvent* a_event, RE::BSTEventSource<RE::TESPlayerBowShotEvent>*) override
        {
            if (!a_event) return RE::BSEventNotifyControl::kContinue;
            auto* player = RE::PlayerCharacter::GetSingleton();
            auto* entry = player ? player->GetEquippedEntryData(false) : nullptr;
            const auto* weapon = entry && entry->object ? entry->object->As<RE::TESObjectWEAP>() : nullptr;
            if (!weapon || weapon->GetFormID() != a_event->weapon) return RE::BSEventNotifyControl::kContinue;
            if (weapon->IsBow()) ApplyWeaponWear(entry, weapon, g_settings.bowShotWear, 1.0F, "Ranged shot");
            else if (weapon->IsCrossbow()) ApplyWeaponWear(entry, weapon, g_settings.crossbowShotWear, 1.0F, "Ranged shot");
            return RE::BSEventNotifyControl::kContinue;
        }

        RE::BSEventNotifyControl ProcessEvent(const RE::TESHitEvent* a_event, RE::BSTEventSource<RE::TESHitEvent>*) override
        {
            const auto* player = RE::PlayerCharacter::GetSingleton();
            if (!a_event || !player) return RE::BSEventNotifyControl::kContinue;
            if (a_event->target.get() == player) ApplyIncomingArmorWear(*a_event);
            if (a_event->cause.get() != player || a_event->source == 0 || a_event->flags.any(RE::TESHitEvent::Flag::kBashAttack)) return RE::BSEventNotifyControl::kContinue;
            const auto* weapon = RE::TESForm::LookupByID<RE::TESObjectWEAP>(a_event->source);
            const auto baseWear = BaseWeaponWear(weapon);
            if (!weapon || !weapon->IsMelee() || weapon->IsHandToHandMelee() || !baseWear) return RE::BSEventNotifyControl::kContinue;
            auto* entry = FindEquippedWeaponEntry(weapon);
            if (!entry) return RE::BSEventNotifyControl::kContinue;
            const auto multiplier = a_event->flags.any(RE::TESHitEvent::Flag::kPowerAttack) ? g_settings.powerAttackWearMultiplier : 1.0F;
            ApplyWeaponWear(entry, weapon, *baseWear, multiplier, a_event->flags.any(RE::TESHitEvent::Flag::kPowerAttack) ? "Melee power hit" : "Melee hit");
            return RE::BSEventNotifyControl::kContinue;
        }

        RE::BSEventNotifyControl ProcessEvent(const RE::BSAnimationGraphEvent* a_event, RE::BSTEventSource<RE::BSAnimationGraphEvent>*) override
        {
            const auto* player = RE::PlayerCharacter::GetSingleton();
            if (!a_event || !player || a_event->holder != player || Normalize(a_event->tag.c_str()) != "WEAPONDRAW") return RE::BSEventNotifyControl::kContinue;
            QueuePlayerRuntimeEffectsSync();
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

    [[nodiscard]] json BuildEquipmentItem(
        RE::TESBoundObject* a_item,
        RE::ExtraDataList* a_extraList,
        const ItemKey& a_key,
        const DurabilitySnapshot& a_durability,
        const std::int32_t a_quantity = 1)
    {
        const auto* weapon = a_item ? a_item->As<RE::TESObjectWEAP>() : nullptr;
        const auto* armor = a_item ? a_item->As<RE::TESObjectARMO>() : nullptr;
        const auto enchantment = EnchantmentName(a_item, a_extraList);
        const auto chargeCapacity = InstanceChargeCapacity(a_item, a_extraList);
        const auto isRangedWeapon = weapon && (weapon->IsBow() || weapon->IsCrossbow()) && !weapon->IsBound();
        const auto isMeleeWeapon = weapon && weapon->IsMelee() && !weapon->IsHandToHandMelee() && !weapon->IsBound();
        const auto baseWeaponWear = BaseWeaponWear(weapon);
        const auto baseArmorWear = BaseArmorWear(armor);
        const auto effectiveWearReduction = std::clamp(a_durability.wearReduction, 0.0F, g_settings.maxWearReduction);
        const auto effectiveWeaponWear = baseWeaponWear ? (std::max)(0.1F, *baseWeaponWear * (1.0F - effectiveWearReduction)) : 0.0F;
        const auto effectiveArmorWear = armor ? (std::max)(0.1F, baseArmorWear * (1.0F - effectiveWearReduction)) : 0.0F;
        const auto questItem = a_extraList && a_extraList->HasQuestObjectAlias();
        const auto uniqueItem = IsProtectedUniqueItem(a_item);
        const auto broken = a_durability.current <= 0.0F;
        const auto repairMaterials = GetRepairMaterials(a_item, a_durability);
        const auto repairable = a_durability.current < a_durability.maximum && !repairMaterials.empty();
        auto equipmentItem = json{
            { "id", std::to_string(a_key.baseFormID) + ":" + std::to_string(a_key.uniqueID) },
            { "name", InstanceDisplayName(a_item, a_extraList) },
            { "slot", EquipmentType(a_item) },
            { "category", EquipmentCategory(a_item) },
            { "equipped", a_extraList && a_extraList->GetWorn() },
            { "quantity", (std::max)(1, a_quantity) },
            { "current", std::round(a_durability.current * 100.0F) / 100.0F },
            { "maximum", std::round(a_durability.maximum * 100.0F) / 100.0F },
            { "enhancementLevel", a_durability.enhancementLevel },
            { "damage", weapon ? static_cast<std::int32_t>(weapon->GetAttackDamage()) + a_durability.performanceBonus : 0 },
            { "armor", armor ? static_cast<std::int32_t>(const_cast<RE::TESObjectARMO*>(armor)->GetArmorRating()) + a_durability.performanceBonus : 0 },
            { "weight", (std::max)(0.1F, EquipmentWeight(a_item) - a_durability.weightReduction) },
            { "attackSpeed", weapon ? (std::min)(weapon->GetSpeed() * 2.0F, weapon->GetSpeed() * (1.0F + a_durability.attackSpeedBonus)) : 0.0F },
            { "wearRateLabel", isRangedWeapon ? "每次成功射击" : isMeleeWeapon ? "每次普通命中" : armor && armor->IsShield() ? "每次盾牌格挡" : armor ? "每次被物理命中并抽中部位" : "尚未启用" },
            { "wearReduction", effectiveWearReduction },
            { "enchantment", enchantment },
            { "enchanted", IsInstanceEnchanted(a_item, a_extraList) },
            { "enchantmentReplaceable", !questItem && !uniqueItem },
            { "quest", questItem },
            { "unique", uniqueItem },
            { "broken", broken },
            { "repairable", repairable },
            { "repairMaterials", RepairMaterialsJson(repairMaterials) }
        };
        if (isRangedWeapon || isMeleeWeapon) equipmentItem["wearRate"] = effectiveWeaponWear;
        else if (armor) equipmentItem["wearRate"] = effectiveArmorWear;
        if (chargeCapacity) {
            const auto* extraCharge = a_extraList ? a_extraList->GetByType<RE::ExtraCharge>() : nullptr;
            const auto currentCharge = extraCharge && std::isfinite(extraCharge->charge) ?
                                           std::clamp(extraCharge->charge, 0.0F, static_cast<float>(*chargeCapacity)) :
                                           static_cast<float>(*chargeCapacity);
            equipmentItem["chargeCurrent"] = std::round(currentCharge * 100.0F) / 100.0F;
            equipmentItem["chargeCapacity"] = *chargeCapacity;
            equipmentItem["chargeBonus"] = (std::max)(0.0F, a_durability.chargeBonus);
        }
        return equipmentItem;
    }

    [[nodiscard]] json CollectInventoryEquipment()
    {
        json equipment = json::array();
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!player) return equipment;
        const auto inventory = player->GetInventory();
        for (const auto& [item, entry] : inventory) {
            if (!item || entry.first <= 0 || !entry.second) continue;
            if (item->GetFormType() != RE::FormType::Weapon && item->GetFormType() != RE::FormType::Armor) continue;
            std::int32_t representedCount = 0;
            if (entry.second->extraLists) for (auto* extraList : *entry.second->extraLists) {
                if (!extraList) continue;
                representedCount += (std::max)(1, extraList->GetCount());
                const auto key = EnsureItemKeyForExtraList(extraList, item);
                if (!key) continue;
                SyncInstanceRuntimeEffects(*key, item, extraList);
                const auto durability = GetDurability(*key);
                equipment.push_back(BuildEquipmentItem(item, extraList, *key, durability, extraList->GetCount()));
            }
            const auto genericCount = (std::max)(0, entry.first - representedCount);
            if (genericCount > 0) {
                const ItemKey genericKey{ item->GetFormID(), 0 };
                equipment.push_back(BuildEquipmentItem(item, nullptr, genericKey, {}, genericCount));
            }
        }
        return equipment;
    }

    [[nodiscard]] json CollectRepairQueue()
    {
        // Retained broken instances are now part of the complete inventory list.
        // Keep this legacy field empty so older frontends can still consume the contract.
        return json::array();
    }

    [[nodiscard]] json CollectState(std::string_view a_message = {})
    {
        const auto forge = GetForgeContext();
        std::uint32_t refreshes = 0;
        {
            std::scoped_lock lock(g_forgeLock);
            refreshes = g_forgeRefreshes;
        }
        auto* player = RE::PlayerCharacter::GetSingleton();
        return {
            { "version", kPluginVersion },
            { "equipped", CollectInventoryEquipment() },
            { "repairQueue", CollectRepairQueue() },
            { "forge", {
                { "active", forge.active },
                { "station", forge.station },
                { "gold", player ? (std::max)(0, player->GetGoldAmount()) : 0 },
                { "refreshCost", forge.active ? CardRefreshCost(refreshes) : 0 },
                { "refreshes", refreshes },
                { "cards", forge.active ? EnhancementCardsJson() : json::array() }
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
        g_prisma->Invoke(g_view, "window.DurabilityManager && window.DurabilityManager.setPanelVisible(false);");
        g_prisma->Unfocus(g_view);
        UpdateViewVisibility();
        logger::info("Durability Manager panel closed.");
    }

    // Save transitions can run while Prisma is updating its render surface.
    // Reset only our own state here; calling Show/Hide/Focus/Invoke from a load
    // notification can leave Prisma's render and focus states out of sync.
    void ResetViewForLoad()
    {
        g_panelVisible = false;
        g_hudVisible = false;
        g_capturingHotkey = false;
        ClearForgeContext();
        std::scoped_lock lock(g_durabilityLock);
        ++g_stateEpoch;
        g_pendingBreaks.clear();
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
        // A death reload can leave Prisma's focus flag alive after our local
        // panel state was reset. Normalize it here, safely outside load events.
        if (g_prisma->HasFocus(g_view)) g_prisma->Unfocus(g_view);
        g_panelVisible = true;
        g_prisma->Show(g_view);
        g_prisma->Invoke(g_view, "window.DurabilityManager && window.DurabilityManager.setPanelVisible(true);");
        g_prisma->Focus(g_view, true);
        SendState();
        logger::info("Durability Manager panel opened through the restored direct Prisma lifecycle.");
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
                logger::info("Durability Manager web bridge {} is ready.", request.value("version", "<unknown>"));
                return;
            }
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
                RepairEquipment(request.value("id", ""));
            } else if (type == "selectEquipment") {
                SelectEquipmentForForge(request.value("id", ""));
            } else if (type == "refreshEnhancements") {
                RefreshEnhancementCards(request.value("id", ""));
            } else if (type == "applyEnhancement") {
                ApplyEnhancementCard(request.value("equipmentId", ""), request.value("cardId", ""));
            } else if (type == "hudHidden") {
                if (request.value("id", 0U) == g_hudSequence) {
                    g_hudVisible = false;
                    UpdateViewVisibility();
                }
            } else if (type == "clientError") {
                logger::error(
                    "Durability Manager web UI error: {} | component: {}",
                    request.value("message", "Unknown frontend error"),
                    request.value("componentStack", "<not available>"));
            } else SendState();
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
            const auto performanceBridgeInitialized = static_cast<std::uint8_t>(durability.performanceBridgeInitialized);
            const auto chargeBridgeInitialized = static_cast<std::uint8_t>(durability.chargeBridgeInitialized);
            if (!a_serialization->WriteRecordData(key.baseFormID) ||
                !a_serialization->WriteRecordData(key.uniqueID) ||
                !a_serialization->WriteRecordData(durability.current) ||
                !a_serialization->WriteRecordData(durability.maximum) ||
                !a_serialization->WriteRecordData(durability.enhancementLevel) ||
                !a_serialization->WriteRecordData(durability.performanceBonus) ||
                !a_serialization->WriteRecordData(durability.weightReduction) ||
                !a_serialization->WriteRecordData(durability.attackSpeedBonus) ||
                !a_serialization->WriteRecordData(durability.wearReduction) ||
                !a_serialization->WriteRecordData(durability.chargeBonus) ||
                !a_serialization->WriteRecordData(durability.performanceBaselineHealth) ||
                !a_serialization->WriteRecordData(durability.performanceAppliedHealth) ||
                !a_serialization->WriteRecordData(durability.chargeBaselineCapacity) ||
                !a_serialization->WriteRecordData(durability.chargeAppliedCapacity) ||
                !a_serialization->WriteRecordData(performanceBridgeInitialized) ||
                !a_serialization->WriteRecordData(chargeBridgeInitialized)) {
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
            if (type != kDurabilityRecordType || (version != 1 && version != kDurabilityRecordVersion)) {
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
                if (version >= 2) {
                    std::uint8_t performanceBridgeInitialized = 0;
                    std::uint8_t chargeBridgeInitialized = 0;
                    if (a_serialization->ReadRecordData(durability.performanceBaselineHealth) != sizeof(durability.performanceBaselineHealth) ||
                        a_serialization->ReadRecordData(durability.performanceAppliedHealth) != sizeof(durability.performanceAppliedHealth) ||
                        a_serialization->ReadRecordData(durability.chargeBaselineCapacity) != sizeof(durability.chargeBaselineCapacity) ||
                        a_serialization->ReadRecordData(durability.chargeAppliedCapacity) != sizeof(durability.chargeAppliedCapacity) ||
                        a_serialization->ReadRecordData(performanceBridgeInitialized) != sizeof(performanceBridgeInitialized) ||
                        a_serialization->ReadRecordData(chargeBridgeInitialized) != sizeof(chargeBridgeInitialized)) {
                        logger::warn("Could not finish loading runtime bridge state.");
                        break;
                    }
                    durability.performanceBridgeInitialized = performanceBridgeInitialized != 0;
                    durability.chargeBridgeInitialized = chargeBridgeInitialized != 0;
                }
                RE::FormID resolvedBaseFormID = 0;
                if (!a_serialization->ResolveFormID(savedBaseFormID, resolvedBaseFormID)) continue;
                durability.maximum = std::isfinite(durability.maximum) ? (std::max)(1.0F, durability.maximum) : 100.0F;
                durability.current = std::isfinite(durability.current) ?
                                         std::clamp(durability.current, 0.0F, durability.maximum) :
                                         durability.maximum;
                durability.performanceBonus = (std::max)(0, durability.performanceBonus);
                durability.weightReduction = std::isfinite(durability.weightReduction) ?
                                                 (std::max)(0.0F, durability.weightReduction) :
                                                 0.0F;
                durability.attackSpeedBonus = std::isfinite(durability.attackSpeedBonus) ?
                                                  std::clamp(durability.attackSpeedBonus, 0.0F, 1.0F) :
                                                  0.0F;
                durability.wearReduction = std::isfinite(durability.wearReduction) ?
                                               std::clamp(durability.wearReduction, 0.0F, 0.95F) :
                                               0.0F;
                durability.chargeBonus = std::isfinite(durability.chargeBonus) ?
                                             std::clamp(durability.chargeBonus, 0.0F, 65534.0F) :
                                             0.0F;
                if (!std::isfinite(durability.performanceBaselineHealth) || durability.performanceBaselineHealth <= 0.0F) {
                    durability.performanceBaselineHealth = 1.0F;
                    durability.performanceBridgeInitialized = false;
                }
                if (!std::isfinite(durability.performanceAppliedHealth) || durability.performanceAppliedHealth <= 0.0F) {
                    durability.performanceAppliedHealth = durability.performanceBaselineHealth;
                    durability.performanceBridgeInitialized = false;
                }
                restored[ItemKey{ resolvedBaseFormID, uniqueID }] = durability;
            }
        }
        std::size_t restoredCount = 0;
        {
            std::scoped_lock lock(g_durabilityLock);
            g_durability = std::move(restored);
            g_lowDurabilityWarnings.clear();
            g_pendingBreaks.clear();
            g_weaponNotificationTimes.clear();
            restoredCount = g_durability.size();
        }
        logger::info("Loaded {} durability instance records.", restoredCount);
    }

    void RevertState(SKSE::SerializationInterface*)
    {
        {
            std::scoped_lock lock(g_durabilityLock);
            g_durability.clear();
            g_lowDurabilityWarnings.clear();
            g_pendingBreaks.clear();
            g_weaponNotificationTimes.clear();
            g_nextGeneratedUniqueID = 0x8000U;
            ++g_stateEpoch;
        }
        PreparePlayerRuntimeEffectsForStateChange();
    }

    void OnSKSEMessage(SKSE::MessagingInterface::Message* a_message)
    {
        if (a_message->type == SKSE::MessagingInterface::kPreLoadGame) {
            ResetViewForLoad();
            PreparePlayerRuntimeEffectsForStateChange();
            logger::info("Durability Manager reset local panel state before loading a save.");
            return;
        }
        if (a_message->type == SKSE::MessagingInterface::kPostLoadGame) {
            ResetViewForLoad();
            SyncAllRuntimeEffects();
            QueuePlayerRuntimeEffectsSync();
            QueueStoredZeroDurabilityResolutions();
            logger::info("Durability Manager reset local panel state after loading a save.");
            return;
        }
        if (a_message->type == SKSE::MessagingInterface::kNewGame) {
            ResetViewForLoad();
            PreparePlayerRuntimeEffectsForStateChange();
            QueuePlayerRuntimeEffectsSync();
            logger::info("Durability Manager reset local panel state for a new game.");
            return;
        }
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
        logger::info("Durability Manager loaded with the restored direct Prisma lifecycle.");
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

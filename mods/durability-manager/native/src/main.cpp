#include "recycling_keys.h"
#include "recycling_rules.h"
#include "../../../../shared/panel-power/panel_power.h"
#include "PrismaUI_API.h"
#include "input_handler.h"
#include "enhancement_rules.h"
#include "reinforced_name.h"
#include "enhancement_drafts.h"
#include "enchantment_ranking.h"
#include "enchantment_cache.h"
#include "forge_access.h"
#include "../../../magic-arrows/native/src/crafting_access.h"
#include "wear_rules.h"
#include "hud_rules.h"
#include "hud_bridge.h"
#include "potions.h"
#ifdef UNIFIED_WORKSHOP
#include "workshop_bridge.h"
#include "workshop_ui.h"
#endif

#include <nlohmann/json.hpp>
#include <atomic>
#include <thread>

// Windows multimedia headers define PlaySound as a macro; use Skyrim's UI sound helper.
#ifdef PlaySound
#undef PlaySound
#endif

namespace
{
    using json = nlohmann::json;

#ifdef UNIFIED_WORKSHOP
    unified_workshop::WorkshopUI* g_prisma = nullptr;
#else
    PRISMA_UI_API::IVPrismaUI1* g_prisma = nullptr;
#endif
    PrismaView g_view = 0;

    struct Settings
    {
        HotkeyConfig hotkey{};
        std::uint32_t lowDurabilityThreshold = 30;
        float weaponDisplaySeconds = 3.0F;
        float hudRightPercent = 100.0F;
        float hudBottomPercent = 2.0F;
        bool enableLowDurabilityWarning = true;
        bool enableWorkshopSounds = true;
        int uiFontScale = 100;
        int uiTransparency = 16;
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
        float staffCastWear = 1.0F;
        float armorHitWear = 1.0F;
        float clothingHitWear = 1.25F;
        float shieldBlockWear = 1.0F;
        float incomingPowerAttackWearMultiplier = 1.5F;
        float magicHitWearMultiplier = 1.0F;
        float trapHitWearMultiplier = 1.0F;
        float continuousHitIntervalSeconds = 1.0F;
        float movementBootWearPer1000Units = 0.02F;
        float movementBodyWearPer1000Units = 0.005F;
        float maxWearReduction = 0.70F;
    };

    Settings g_settings{};
    enhancement::Rules g_enhancementRules{};
    std::unordered_set<RE::FormID> g_enchantmentPool;
    std::unordered_set<RE::FormID> g_deniedEnchantments;
    std::unordered_map<RE::FormID, enhancement::EnchantmentRank> g_enchantmentRanks;
    enhancement::EnchantmentCache g_enchantmentCache;
    std::mutex g_enchantmentCacheLock;

    void ClearEnchantmentCache(const std::string_view a_reason)
    {
        std::scoped_lock lock(g_enchantmentCacheLock);
        const auto stats = g_enchantmentCache.Stats();
        if (stats.hits || stats.misses) logger::info(
            "Enchantment compatibility cache cleared ({}): hits={}, scans={}, evictions={}, entries={}, retainedIDs={}.",
            a_reason, stats.hits, stats.misses, stats.evictions, g_enchantmentCache.Size(), g_enchantmentCache.RetainedIDs());
        g_enchantmentCache.Clear();
    }
    bool g_capturingRecyclingHotkey = false;
    recycling::Capture g_recyclingCapture;
    bool g_capturingHotkey = false;
    bool g_panelVisible = false;
    bool g_hudVisible = false;
    bool g_equippedHudVisible = false;
    bool g_gameHudAllowed = false;
    bool g_hudBridgeReady = false;
    std::uint32_t g_hudProbeAttempts = 0;
    bool g_clearHudPending = true;
    std::string g_equippedHudPayload;
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
        std::string displayNameBaseline;
        std::string displayNameApplied;
        bool performanceBridgeInitialized = false;
        bool chargeBridgeInitialized = false;
        bool displayNameBridgeInitialized = false;
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
        RE::FormID enchantmentFormID = 0;
        std::uint16_t enchantmentCharge = 0;
        float enchantmentPower = 0.0F;
        std::uint32_t successChance = 100;
        std::vector<MaterialRequirementState> requiredMaterials;
        std::string blockedReason;
    };

    std::unordered_map<ItemKey, DurabilitySnapshot, ItemKeyHash> g_durability;
    std::unordered_set<ItemKey, ItemKeyHash> g_lowDurabilityWarnings;
    std::unordered_set<ItemKey, ItemKeyHash> g_pendingBreaks;
    std::mutex g_durabilityLock;
    std::uint16_t g_nextGeneratedUniqueID = 1;
    std::uint64_t g_stateEpoch = 0;
    std::uint64_t g_armorHitSequence = 0;

    std::optional<ItemKey> g_forgeSelectedItem;
    enhancement::DraftLedger<ItemKey, EnhancementCardState, ItemKeyHash> g_enhancementDrafts;
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
    constexpr std::uint32_t kDurabilityRecordVersion = 3;
    constexpr std::uint32_t kMaxDurabilityRecords = 100000;
    constexpr std::uint32_t kMaxPersistedDisplayNameBytes = 2048;
#ifdef UNIFIED_WORKSHOP
    constexpr std::string_view kPluginVersion = "2.3.8";
#else
    constexpr std::string_view kPluginVersion = "0.1.55";
#endif

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
        if (key == "DELETE") return 0xD3;
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
        if (a_key == 0xD3) return "Delete";
        if (a_key == 0x2A) return "左 Shift";
        if (a_key == 0x36) return "右 Shift";
        if (a_key == 0x1D) return "左 Ctrl";
        if (a_key == 0x9D) return "右 Ctrl";
        if (a_key == 0x38) return "左 Alt";
        if (a_key == 0xB8) return "右 Alt";
        return "Scan " + std::to_string(a_key);
    }

    [[nodiscard]] std::filesystem::path ConfigPath()
    {
        const auto modulePath = REL::Module::get().filePath();
        return std::filesystem::path(modulePath.data()).parent_path() / "Data" / "SKSE" / "Plugins" / "DurabilityManager.ini";
    }

    void LoadEnhancementRules()
    {
        ClearEnchantmentCache("rules reload");
        const auto path = ConfigPath().parent_path() / "DurabilityManager.rules.json";
        std::ifstream input(path);
        g_enhancementRules = {};
        if (!input) {
            logger::info("No enhancement rule file; using built-in defaults.");
            return;
        }
        try {
            g_enhancementRules = enhancement::ParseRules(json::parse(input));
            logger::info("Loaded enhancement rules from {}.", path.string());
        } catch (const std::exception& error) {
            logger::error("Invalid enhancement rules; using defaults: {}", error.what());
        }
    }

    // Plugin-local hexadecimal IDs survive changes to load order and support ESL.
    // Plain editor IDs remain convenient for existing material rules.
    [[nodiscard]] RE::TESForm* ResolveRuleForm(const std::string& a_reference)
    {
        const auto delimiter = a_reference.find('|');
        if (delimiter == std::string::npos) return RE::TESForm::LookupByEditorID(a_reference);
        const auto plugin = a_reference.substr(0, delimiter);
        auto localIDText = std::string_view(a_reference).substr(delimiter + 1);
        if (localIDText.starts_with("0x") || localIDText.starts_with("0X")) localIDText.remove_prefix(2);
        RE::FormID localID = 0;
        const auto parsed = std::from_chars(localIDText.data(), localIDText.data() + localIDText.size(), localID, 16);
        auto* handler = RE::TESDataHandler::GetSingleton();
        if (!handler || plugin.empty() || localID == 0 || localID > 0xFFFFFF ||
            parsed.ec != std::errc{} || parsed.ptr != localIDText.data() + localIDText.size()) return nullptr;
        return handler->LookupForm(localID, plugin);
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
                   << "\nUIFontScale=" << g_settings.uiFontScale
                   << "\nUITransparency=" << g_settings.uiTransparency
                   << "\nHUDRightPercent=" << g_settings.hudRightPercent
                   << "\nHUDBottomPercent=" << g_settings.hudBottomPercent
                   << "\nWeaponDisplaySeconds=" << g_settings.weaponDisplaySeconds
                   << "\nEnableLowDurabilityWarning=" << (g_settings.enableLowDurabilityWarning ? "true" : "false")
                   << "\nEnableWorkshopSounds=" << (g_settings.enableWorkshopSounds ? "true" : "false");
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
                   << "\nStaffCastWear=" << g_settings.staffCastWear
                   << "\nArmorHitWear=" << g_settings.armorHitWear
                   << "\nClothingHitWear=" << g_settings.clothingHitWear
                   << "\nShieldBlockWear=" << g_settings.shieldBlockWear
                   << "\nIncomingPowerAttackWearMultiplier=" << g_settings.incomingPowerAttackWearMultiplier
                   << "\nMagicHitWearMultiplier=" << g_settings.magicHitWearMultiplier
                   << "\nTrapHitWearMultiplier=" << g_settings.trapHitWearMultiplier
                   << "\nContinuousHitIntervalSeconds=" << g_settings.continuousHitIntervalSeconds
                   << "\nMovementBootWearPer1000Units=" << g_settings.movementBootWearPer1000Units
                   << "\nMovementBodyWearPer1000Units=" << g_settings.movementBodyWearPer1000Units
                   << "\nMaxWearReduction=" << g_settings.maxWearReduction << '\n';
    }

    void LoadConfig()
    {
        std::ifstream configFile(ConfigPath());
        if (!configFile) {
            logger::warn("DurabilityManager.ini was not found; using Shift+{} and a 30% warning threshold.", KeyName(g_settings.hotkey.keyCode));
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
                    else if (key == "UIFONTSCALE") g_settings.uiFontScale = std::clamp(std::stoi(value), 80, 130);
                    else if (key == "UITRANSPARENCY") g_settings.uiTransparency = std::clamp(std::stoi(value), 0, 60);
                    else if (key == "HUDRIGHTPERCENT" || key == "HUDBOTTOMPERCENT") {
                        const auto position = std::stof(value);
                        if (std::isfinite(position)) {
                            (key == "HUDRIGHTPERCENT" ? g_settings.hudRightPercent : g_settings.hudBottomPercent) = std::clamp(position, 0.0F, 100.0F);
                        }
                    }
                    else if (key == "WEAPONDISPLAYSECONDS") g_settings.weaponDisplaySeconds = std::clamp(std::stof(value), 0.5F, 10.0F);
                    else if (key == "ENABLELOWDURABILITYWARNING") g_settings.enableLowDurabilityWarning = ParseBool(value, g_settings.enableLowDurabilityWarning);
                    else if (key == "ENABLEWORKSHOPSOUNDS") g_settings.enableWorkshopSounds = ParseBool(value, g_settings.enableWorkshopSounds);
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
                    else if (key == "STAFFCASTWEAR") g_settings.staffCastWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "ARMORHITWEAR") g_settings.armorHitWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "CLOTHINGHITWEAR") g_settings.clothingHitWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "SHIELDBLOCKWEAR") g_settings.shieldBlockWear = std::clamp(std::stof(value), 0.1F, 100.0F);
                    else if (key == "INCOMINGPOWERATTACKWEARMULTIPLIER") g_settings.incomingPowerAttackWearMultiplier = std::clamp(std::stof(value), 1.0F, 10.0F);
                    else if (key == "MAXWEARREDUCTION") g_settings.maxWearReduction = std::clamp(std::stof(value), 0.0F, 0.95F);
                    else if (key == "MAGICHITWEARMULTIPLIER") g_settings.magicHitWearMultiplier = std::clamp(std::stof(value), 0.0F, 10.0F);
                    else if (key == "TRAPHITWEARMULTIPLIER") g_settings.trapHitWearMultiplier = std::clamp(std::stof(value), 0.0F, 10.0F);
                    else if (key == "CONTINUOUSHITINTERVALSECONDS") g_settings.continuousHitIntervalSeconds = std::clamp(std::stof(value), 0.1F, 10.0F);
                    else if (key == "MOVEMENTBOOTWEARPER1000UNITS") g_settings.movementBootWearPer1000Units = std::clamp(std::stof(value), 0.0F, 10.0F);
                    else if (key == "MOVEMENTBODYWEARPER1000UNITS") g_settings.movementBodyWearPer1000Units = std::clamp(std::stof(value), 0.0F, 10.0F);
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

    [[nodiscard]] std::string EnchantmentLabel(const RE::EnchantmentItem* a_enchantment)
    {
        if (!a_enchantment) return {};
        const auto* name = a_enchantment->GetFullName();
        if (name && name[0]) return name;
        // Many ENCH records rely on their magic effects for their display name.
        for (const auto* effect : a_enchantment->effects) {
            if (!effect || !effect->baseEffect ||
                effect->baseEffect->data.flags.all(RE::EffectSetting::EffectSettingData::Flag::kHideInUI)) continue;
            const auto* effectName = effect->baseEffect->GetFullName();
            if (effectName && effectName[0]) return effectName;
        }
        return "附魔";
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
        return EnchantmentLabel(enchantment);
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

    void SendState(std::string_view a_message = {}, const json& a_refreshResult = nullptr);

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
        g_forgeSelectedItem.reset();
        // Leaving the vicinity changes access, not the item-owned draft.
    }

    [[nodiscard]] ForgeContext GetForgeContext()
    {
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto* cell = player ? player->GetParentCell() : nullptr;
        auto* world = player ? player->GetWorldspace() : nullptr;
        auto* tes = RE::TES::GetSingleton();
        if (!player || !cell || !cell->IsAttached() || !tes) {
            ClearForgeContext();
            return {};
        }
        const workshop::Location playerLocation{ cell->GetFormID(), world ? world->GetFormID() : 0U, cell->IsInteriorCell() };
        const auto position = player->GetPosition();
        auto nearestDistance = workshop::kRadius * workshop::kRadius;
        ForgeContext result;
        // Scan loaded local references on demand, not the global form database.
        // Exterior grid traversal includes adjacent cells at the radius boundary.
        // No raw reference is kept after traversal; every action checks again.
        tes->ForEachReferenceInRange(player, workshop::kRadius, [&](RE::TESObjectREFR* station) {
            if (!station || station->IsDeleted() || station->IsDisabled() || !station->Is3DLoaded()) return RE::BSContainer::ForEachResult::kContinue;
            auto* stationCell = station->GetParentCell();
            if (!stationCell || !stationCell->IsAttached()) return RE::BSContainer::ForEachResult::kContinue;
            auto* stationWorld = station->GetWorldspace();
            const workshop::Location stationLocation{ stationCell->GetFormID(), stationWorld ? stationWorld->GetFormID() : 0U, stationCell->IsInteriorCell() };
            const auto distance = position.GetSquaredDistance(station->GetPosition());
            if (!workshop::IsNearby(distance, playerLocation, stationLocation, true) || distance > nearestDistance) return RE::BSContainer::ForEachResult::kContinue;
            auto* base = station->GetBaseObject();
            if (!base || base->IsDeleted() || base->IsIgnored()) return RE::BSContainer::ForEachResult::kContinue;
            auto name = ForgeStationName(base);
            if (!name.empty()) {
                nearestDistance = distance;
                result = { true, std::move(name) };
            }
            return RE::BSContainer::ForEachResult::kContinue;
        });
        return result;
    }

    [[nodiscard]] bool CanPreviewEnhancement()
    {
        const auto* player = RE::PlayerCharacter::GetSingleton();
        const auto* cell = player ? player->GetParentCell() : nullptr;
        return player && !player->IsDead() && cell && cell->IsAttached();
    }

    [[nodiscard]] bool CanEnhanceEquipment()
    {
        if (!CanPreviewEnhancement()) return false;
        const auto stations = crafting_access::Nearby(RE::PlayerCharacter::GetSingleton());
        return stations.magic || stations.normal;
    }

    void UpdateViewVisibility()
    {
        if (g_prisma && g_view && !g_panelVisible && (!g_gameHudAllowed || (!g_hudVisible && !g_equippedHudVisible))) g_prisma->Hide(g_view);
    }

    void ShowHUD(
        std::string_view a_kind,
        std::string_view a_title,
        std::string_view a_detail,
        const float a_seconds,
        const std::optional<float> a_current = std::nullopt,
        const std::optional<float> a_maximum = std::nullopt)
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
        if (g_gameHudAllowed || g_panelVisible) g_prisma->Show(g_view);
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
            const auto* weapon = a_item ? a_item->As<RE::TESObjectWEAP>() : nullptr;
            if (!armor && !(weapon && weapon->IsStaff())) return materials;
            const auto clothing = armor && armor->IsClothing();
            const auto materialEditorID = clothing ? "LeatherStrips" : "IngotIron";
            if (auto* material = RE::TESForm::LookupByEditorID<RE::TESBoundObject>(materialEditorID)) {
                const auto fullRepairCount = clothing ? 2.0F : 4.0F;
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
                { "isGold", material && material->GetFormID() == 0xFU },
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

    void PlayWorkshopSound(const char* a_editorID)
    {
        if (g_settings.enableWorkshopSounds) RE::PlaySound(a_editorID);
    }

    void PlayWorkshopClick()
    {
        static auto previous = std::chrono::steady_clock::time_point{};
        const auto now = std::chrono::steady_clock::now();
        if (now - previous < std::chrono::milliseconds(80)) return;
        previous = now;
        PlayWorkshopSound("UIMenuOK");
    }

    // Result cues are native-only: early validation exits cannot sound like success.
    struct WorkshopFeedback
    {
        const char* resultSound = "UIMenuCancel";
        WorkshopFeedback() { PlayWorkshopClick(); }
        ~WorkshopFeedback() { PlayWorkshopSound(resultSound); }
    };

    void RepairEquipment(const std::string_view a_equipmentID)
    {
        WorkshopFeedback feedback;
        if (!GetForgeContext().active) {
            SendState("修复失败：请靠近锻造熔炉、冶炼熔炉、砂轮或护甲工作台。");
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
        feedback.resultSound = item->As<RE::TESObjectWEAP>() ? "UISmithingImproveWeapon" : "UISmithingImproveArmor";
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

    [[nodiscard]] bool MatchesWornRestrictionList(
        RE::TESBoundObject* a_item,
        RE::BGSListForm* a_restrictions,
        const std::uint32_t a_depth = 0)
    {
        if (!a_item || !a_restrictions || a_depth > 4) return false;
        bool matches = false;
        a_restrictions->ForEachForm([&](RE::TESForm* a_form) {
            if (matches) return RE::BSContainer::ForEachResult::kStop;
            if (!a_form) return RE::BSContainer::ForEachResult::kContinue;
            if (a_form == a_item) {
                matches = true;
            } else if (auto* keyword = a_form->As<RE::BGSKeyword>()) {
                if (const auto* weapon = a_item->As<RE::TESObjectWEAP>()) matches = weapon->HasKeyword(keyword);
                else if (const auto* armor = a_item->As<RE::TESObjectARMO>()) matches = armor->HasKeyword(keyword);
            } else if (auto* nested = a_form->As<RE::BGSListForm>()) {
                matches = MatchesWornRestrictionList(a_item, nested, a_depth + 1U);
            }
            return matches ? RE::BSContainer::ForEachResult::kStop : RE::BSContainer::ForEachResult::kContinue;
        });
        return matches;
    }

    [[nodiscard]] bool IsCompatibleEnchantment(
        RE::TESBoundObject* a_item,
        RE::EnchantmentItem* a_enchantment)
    {
        if (!a_item || !a_enchantment || a_enchantment->IsDeleted() || a_enchantment->IsIgnored() ||
            !a_enchantment->GetFile() || a_enchantment->effects.empty()) {
            return false;
        }
        if (!g_enchantmentPool.contains(a_enchantment->GetFormID())) return false;
        std::unordered_set<RE::FormID> ancestors;
        for (auto* form = a_enchantment; form; form = form->data.baseEnchantment) {
            if (ancestors.size() >= 16 || !ancestors.insert(form->GetFormID()).second ||
                form->IsDeleted() || form->IsIgnored() || g_deniedEnchantments.contains(form->GetFormID())) return false;
            const auto* source = form->GetFile(0);
            const auto* overrideFile = form->GetFile();
            for (const auto& denied : g_enhancementRules.denyPlugins) {
                if ((source && Normalize(std::string(source->GetFilename())) == Normalize(denied)) ||
                    (overrideFile && Normalize(std::string(overrideFile->GetFilename())) == Normalize(denied))) return false;
            }
            if (form->data.wornRestrictions && !MatchesWornRestrictionList(a_item, form->data.wornRestrictions)) return false;
        }
        bool visibleEffect = false;
        for (const auto* effect : a_enchantment->effects) {
            if (!effect || !effect->baseEffect || effect->baseEffect->IsDeleted() || effect->baseEffect->IsIgnored() ||
                !std::isfinite(effect->effectItem.magnitude) || !std::isfinite(effect->baseEffect->data.baseCost)) return false;
            if (!effect->baseEffect->data.flags.all(RE::EffectSetting::EffectSettingData::Flag::kHideInUI)) visibleEffect = true;
        }
        if (!visibleEffect) return false;

        if (const auto* weapon = a_item->As<RE::TESObjectWEAP>()) {
            if (weapon->IsBound() || weapon->IsHandToHandMelee()) return false;
            if (weapon->IsStaff()) {
                return a_enchantment->GetSpellType() == RE::MagicSystem::SpellType::kStaffEnchantment &&
                       a_enchantment->GetCastingType() != RE::MagicSystem::CastingType::kConstantEffect;
            }
            return a_enchantment->GetSpellType() == RE::MagicSystem::SpellType::kEnchantment &&
                   a_enchantment->GetCastingType() == RE::MagicSystem::CastingType::kFireAndForget &&
                   a_enchantment->GetDelivery() == RE::MagicSystem::Delivery::kTouch;
        }

        if (a_item->As<RE::TESObjectARMO>()) {
            if (a_enchantment->GetSpellType() != RE::MagicSystem::SpellType::kEnchantment ||
                a_enchantment->GetCastingType() != RE::MagicSystem::CastingType::kConstantEffect ||
                a_enchantment->GetDelivery() != RE::MagicSystem::Delivery::kSelf) {
                return false;
            }
            return true;  // All restrictions in the base-enchantment chain were checked above.
        }
        return false;
    }

    void BuildEnchantmentPool()
    {
        ClearEnchantmentCache("pool rebuild");
        g_enchantmentPool.clear();
        g_deniedEnchantments.clear();
        g_enchantmentRanks.clear();
        auto* handler = RE::TESDataHandler::GetSingleton();
        if (!handler) return;
        const auto collect = [](RE::TESBoundObject* item) {
            if (!item || !item->GetPlayable() || item->IsDeleted() || item->IsIgnored() || IsProtectedUniqueItem(item)) return;
            auto* enchantable = item->As<RE::TESEnchantableForm>();
            if (enchantable && enchantable->formEnchanting) g_enchantmentPool.insert(enchantable->formEnchanting->GetFormID());
        };
        for (auto* item : handler->GetFormArray<RE::TESObjectWEAP>()) {
            if (item && !item->IsBound()) collect(item);
        }
        for (auto* item : handler->GetFormArray<RE::TESObjectARMO>()) collect(item);
        for (const auto& entry : g_enhancementRules.allowEnchantments) {
            auto* form = ResolveRuleForm(entry);
            if (form && form->As<RE::EnchantmentItem>()) g_enchantmentPool.insert(form->GetFormID());
            else logger::warn("Unresolved enchantment allow rule: {}", entry);
        }
        for (const auto& entry : g_enhancementRules.denyEnchantments) {
            auto* form = ResolveRuleForm(entry);
            if (form && form->As<RE::EnchantmentItem>()) g_deniedEnchantments.insert(form->GetFormID());
            else logger::warn("Unresolved enchantment deny rule: {}", entry);
        }
        for (const auto& [entry, rank] : g_enhancementRules.enchantmentRanks) {
            auto* form = ResolveRuleForm(entry);
            if (!form || !form->As<RE::EnchantmentItem>()) logger::warn("Unresolved enchantment ranking rule: {}", entry);
            else if (!g_enchantmentRanks.emplace(form->GetFormID(), rank).second) logger::warn("Duplicate enchantment ranking rule: {}", entry);
            else logger::info("Enchantment ranking rule {} resolved to {:08X}.", entry, form->GetFormID());
        }
        std::map<std::string, std::size_t> counts;
        for (const auto id : g_enchantmentPool) {
            auto* form = RE::TESForm::LookupByID<RE::EnchantmentItem>(id);
            if (form && form->GetFile(0)) ++counts[std::string(form->GetFile(0)->GetFilename())];
        }
        logger::info("Enchantment pool: {} source candidates, {} explicit denied records (compatibility checked per item).", g_enchantmentPool.size(), g_deniedEnchantments.size());
        for (const auto& [plugin, count] : counts) logger::info("Enchantment source {}: {} candidates.", plugin, count);
    }

    [[nodiscard]] std::optional<enhancement::EnchantmentRank> EnchantmentRankOverride(const RE::EnchantmentItem* a_enchantment)
    {
        std::unordered_set<RE::FormID> visited;
        for (auto* form = a_enchantment; form && visited.size() < 16; form = form->data.baseEnchantment) {
            if (!visited.insert(form->GetFormID()).second) break;
            if (const auto found = g_enchantmentRanks.find(form->GetFormID()); found != g_enchantmentRanks.end()) return found->second;
        }
        return std::nullopt;
    }

    [[nodiscard]] float EnchantmentPower(const RE::EnchantmentItem* a_enchantment)
    {
        if (!a_enchantment) return 0.0F;
        if (const auto rank = EnchantmentRankOverride(a_enchantment); rank && rank->power) return *rank->power;
        double total = 0.0;
        for (const auto* effect : a_enchantment->effects) {
            if (!effect || !effect->baseEffect) continue;
            const auto& flags = effect->baseEffect->data.flags;
            using Flag = RE::EffectSetting::EffectSettingData::Flag;
            total += enhancement::EffectPower(effect->effectItem.magnitude, effect->effectItem.duration,
                effect->baseEffect->data.baseCost, flags.all(Flag::kNoMagnitude), flags.all(Flag::kNoDuration),
                effect->baseEffect->GetArchetype() == RE::EffectArchetypes::ArchetypeID::kSoulTrap,
                flags.all(Flag::kHideInUI));
        }
        return static_cast<float>(std::clamp(total, 0.0, 100000000.0));
    }

    [[nodiscard]] std::string EnchantmentEffectSummary(const RE::EnchantmentItem* a_enchantment)
    {
        if (!a_enchantment) return {};
        std::string result;
        for (const auto* effect : a_enchantment->effects) {
            if (!effect || !effect->baseEffect) continue;
            const auto& flags = effect->baseEffect->data.flags;
            using Flag = RE::EffectSetting::EffectSettingData::Flag;
            if (flags.all(Flag::kHideInUI)) continue;
            if (!result.empty()) result += "；";
            const auto* effectName = effect->baseEffect->GetFullName();
            result += effectName && effectName[0] ? effectName : "效果";
            std::ostringstream stream;
            const auto soulTrap = effect->baseEffect->GetArchetype() == RE::EffectArchetypes::ArchetypeID::kSoulTrap;
            if (!soulTrap && !flags.all(Flag::kNoMagnitude)) stream << " 强度 " << std::fixed << std::setprecision(1) << effect->effectItem.magnitude;
            if (!flags.all(Flag::kNoDuration) && effect->effectItem.duration > 0) {
                stream << (soulTrap ? " 捕魂时限 " : " / ") << effect->effectItem.duration << " 秒";
            }
            result += stream.str();
        }
        return result.empty() ? "原生效果" : result;
    }

    struct EnchantmentOffer
    {
        RE::EnchantmentItem* enchantment = nullptr;
        float power = 0.0F;
        std::uint16_t charge = 0;
    };

    [[nodiscard]] enhancement::EnchantmentCache::Snapshot CachedCompatibleEnchantmentIDs(RE::TESBoundObject* a_item)
    {
        if (!a_item || !RE::TESDataHandler::GetSingleton()) return {};
        // All item-specific inputs to IsCompatibleEnchantment: exact base identity,
        // weapon class/bound flags and the current keyword list. Per-instance state
        // deliberately stays outside this cache. Foreign restriction/effect edits
        // expire within five seconds, and payment always performs a fresh check.
        enhancement::EnchantmentCache::IDs signature;
        const RE::BGSKeywordForm* keywords = nullptr;
        if (const auto* weapon = a_item->As<RE::TESObjectWEAP>()) {
            signature = { 1U, static_cast<std::uint32_t>(weapon->IsBound()), static_cast<std::uint32_t>(weapon->IsHandToHandMelee()), static_cast<std::uint32_t>(weapon->IsStaff()) };
            keywords = weapon;
        } else if (const auto* armor = a_item->As<RE::TESObjectARMO>()) {
            signature = { 2U };
            keywords = armor;
        } else return {};
        keywords->ForEachKeyword([&signature](RE::BGSKeyword* keyword) {
            signature.push_back(keyword ? keyword->GetFormID() : 0U);
            return RE::BSContainer::ForEachResult::kContinue;
        });
        std::scoped_lock lock(g_enchantmentCacheLock);
        return g_enchantmentCache.Get(a_item->GetFormID(), signature, enhancement::EnchantmentCache::Clock::now(), [a_item] {
            enhancement::EnchantmentCache::IDs ids;
            for (const auto id : g_enchantmentPool) {
                auto* enchantment = RE::TESForm::LookupByID<RE::EnchantmentItem>(id);
                if (IsCompatibleEnchantment(a_item, enchantment)) ids.push_back(id);
            }
            logger::debug("Enchantment compatibility scan for {:08X}: {} / {} candidates.", a_item->GetFormID(), ids.size(), g_enchantmentPool.size());
            return ids;
        });
    }

    [[nodiscard]] bool HasCompatibleEnchantment(RE::TESBoundObject* a_item, RE::ExtraDataList* a_extraList)
    {
        const auto ids = CachedCompatibleEnchantmentIDs(a_item);
        if (!ids) return false;
        const auto* current = InstanceEnchantment(a_item, a_extraList);
        for (const auto id : *ids) {
            const auto* enchantment = RE::TESForm::LookupByID<RE::EnchantmentItem>(id);
            if (enchantment && enchantment != current && !enchantment->IsDeleted() && !enchantment->IsIgnored()) return true;
        }
        return false;
    }

    [[nodiscard]] std::vector<RE::EnchantmentItem*> CompatibleEnchantments(
        RE::TESBoundObject* a_item,
        RE::ExtraDataList* a_extraList)
    {
        std::vector<RE::EnchantmentItem*> result;
        const auto ids = CachedCompatibleEnchantmentIDs(a_item);
        if (!ids) return result;
        const auto* current = InstanceEnchantment(a_item, a_extraList);
        for (const auto id : *ids) {
            auto* enchantment = RE::TESForm::LookupByID<RE::EnchantmentItem>(id);
            if (!enchantment || enchantment == current || enchantment->IsDeleted() || enchantment->IsIgnored()) continue;
            result.push_back(enchantment);
        }
        return result;
    }

    [[nodiscard]] std::optional<EnchantmentOffer> RollEnchantmentOffer(
        RE::TESBoundObject* a_item,
        RE::ExtraDataList* a_extraList,
        EnhancementTier& a_tier,
        const DurabilitySnapshot& a_durability,
        std::mt19937& a_random)
    {
        auto candidates = CompatibleEnchantments(a_item, a_extraList);
        logger::info("Enchantment draft for {:08X}: {} compatible alternatives.", a_item->GetFormID(), candidates.size());
        if (candidates.empty()) return std::nullopt;
        struct RankedCandidate
        {
            RE::EnchantmentItem* form;
            float power;
            std::optional<std::uint8_t> fixedTier;
        };
        std::vector<RankedCandidate> ranked;
        std::array<bool, 4> available{};
        for (auto* form : candidates) {
            const auto rank = EnchantmentRankOverride(form);
            const auto fixedTier = rank ? rank->tier : std::nullopt;
            ranked.push_back({form, EnchantmentPower(form), fixedTier});
            for (std::size_t tier = 0; tier < available.size(); ++tier) {
                available[tier] = available[tier] || enhancement::MatchesTier(fixedTier, tier);
            }
        }
        const auto chosenTier = enhancement::AvailableTier(static_cast<std::size_t>(a_tier), available, a_random);
        if (!chosenTier) return std::nullopt;
        a_tier = static_cast<EnhancementTier>(*chosenTier);
        std::erase_if(ranked, [&](const auto& entry) { return !enhancement::MatchesTier(entry.fixedTier, *chosenTier); });
        std::shuffle(ranked.begin(), ranked.end(), a_random);
        std::stable_sort(ranked.begin(), ranked.end(), [](const auto& a_left, const auto& a_right) {
            return a_left.power < a_right.power;
        });

        static constexpr std::array<float, 4> tierCenters{ 0.14F, 0.39F, 0.66F, 0.88F };
        const auto tierIndex = static_cast<std::size_t>(a_tier);
        const auto levelBias = (std::min)(0.10F, static_cast<float>((std::min)(a_durability.enhancementLevel, 50U)) * 0.002F);
        const auto jitter = std::uniform_real_distribution<float>(-0.10F, 0.10F)(a_random);
        const auto percentile = std::clamp(tierCenters[tierIndex] + levelBias + jitter, 0.0F, 1.0F);
        std::vector<double> weights;
        weights.reserve(ranked.size());
        for (std::size_t index = 0; index < ranked.size(); ++index) {
            weights.push_back(enhancement::CandidateWeight(index, ranked.size(), percentile, ranked[index].fixedTier.has_value()));
        }
        const auto candidateIndex = std::discrete_distribution<std::size_t>(weights.begin(), weights.end())(a_random);
        const auto& selected = ranked[candidateIndex];

        std::uint16_t charge = 0;
        if (a_item->As<RE::TESObjectWEAP>()) {
            static constexpr std::array<std::uint32_t, 4> baseCharge{ 1200U, 1800U, 2600U, 3600U };
            const auto chargeScale = 1.0 + static_cast<double>((std::min)(a_durability.enhancementLevel, 30U)) * 0.02;
            charge = static_cast<std::uint16_t>(std::clamp<long long>(
                std::llround(static_cast<double>(baseCharge[tierIndex]) * chargeScale),
                1LL,
                static_cast<long long>((std::numeric_limits<std::uint16_t>::max)())));
        }
        logger::info("Enchantment offer {:08X}: tier={}, power={}, fixedTier={}", selected.form->GetFormID(),
            tierIndex, selected.power, selected.fixedTier.has_value());
        return EnchantmentOffer{ selected.form, selected.power, charge };
    }

    bool ApplyReplacementEnchantment(
        const ItemKey& a_key,
        RE::TESBoundObject* a_item,
        RE::ExtraDataList* a_extraList,
        RE::EnchantmentItem* a_enchantment,
        const std::uint16_t a_charge)
    {
        if (!a_extraList || a_extraList->GetWorn() || a_extraList->HasQuestObjectAlias() || IsProtectedUniqueItem(a_item) ||
            !IsCompatibleEnchantment(a_item, a_enchantment) ||
            InstanceEnchantment(a_item, a_extraList) == a_enchantment) {
            return false;
        }
        if (auto* extraEnchantment = a_extraList->GetByType<RE::ExtraEnchantment>()) {
            extraEnchantment->enchantment = a_enchantment;
            extraEnchantment->charge = a_item->As<RE::TESObjectWEAP>() ? (std::max)(a_charge, std::uint16_t{ 1 }) : 0;
            extraEnchantment->removeOnUnequip = false;
        } else {
            a_extraList->Add(new RE::ExtraEnchantment(
                a_enchantment,
                a_item->As<RE::TESObjectWEAP>() ? (std::max)(a_charge, std::uint16_t{ 1 }) : 0));
        }
        if (a_item->As<RE::TESObjectWEAP>()) {
            if (auto* extraCharge = a_extraList->GetByType<RE::ExtraCharge>()) {
                extraCharge->charge = static_cast<float>((std::max)(a_charge, std::uint16_t{ 1 }));
            } else {
                auto* createdCharge = new RE::ExtraCharge();
                createdCharge->charge = static_cast<float>((std::max)(a_charge, std::uint16_t{ 1 }));
                a_extraList->Add(createdCharge);
            }
        }
        {
            std::scoped_lock lock(g_durabilityLock);
            auto& durability = g_durability[a_key];
            durability.chargeBridgeInitialized = false;
            durability.chargeBaselineCapacity = 0;
            durability.chargeAppliedCapacity = 0;
        }
        logger::info(
            "Replaced enchantment for {:08X}:{:04X} with {:08X}; charge={}.",
            a_key.baseFormID,
            a_key.uniqueID,
            a_enchantment->GetFormID(),
            a_charge);
        if (auto* player = RE::PlayerCharacter::GetSingleton()) player->AddChange(RE::TESObjectREFR::ChangeFlags::kInventory);
        return true;
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

    [[nodiscard]] std::string LimitPersistedDisplayName(std::string a_value)
    {
        if (a_value.size() <= kMaxPersistedDisplayNameBytes) return a_value;
        std::size_t boundary = kMaxPersistedDisplayNameBytes;
        while (boundary > 0 && (static_cast<unsigned char>(a_value[boundary]) & 0xC0U) == 0x80U) --boundary;
        a_value.resize(boundary);
        return a_value;
    }

    [[nodiscard]] std::string ReinforcedDisplayName(
        const std::string_view a_baseline,
        const std::uint32_t a_level)
    {
        return durability::name::Reinforced(a_baseline, a_level);
    }

    bool SyncDisplayNameRuntimeEffect(
        const ItemKey& a_key,
        RE::TESBoundObject* a_item,
        RE::ExtraDataList* a_extraList)
    {
        if (!a_item || !a_extraList) return false;
        const auto currentName = LimitPersistedDisplayName(InstanceDisplayName(a_item, a_extraList));
        auto* textData = a_extraList->GetByType<RE::ExtraTextDisplayData>();
        const auto playerNamed = textData && textData->IsPlayerSet();
        std::string targetName;
        bool clearBridgeAfterSync = false;
        {
            std::scoped_lock lock(g_durabilityLock);
            const auto found = g_durability.find(a_key);
            if (found == g_durability.end()) return false;
            auto& durability = found->second;
            if (durability.enhancementLevel == 0 && !durability.displayNameBridgeInitialized) return false;

            if (!durability.displayNameBridgeInitialized) {
                // Store the undecorated name: a baseline that already carries our own suffix is what
                // used to make every reload append another "+N (上等)".
                durability.displayNameBaseline = durability::name::StripDecorations(LimitPersistedDisplayName(
                    playerNamed ? currentName : DisplayName(a_item)));
                durability.displayNameApplied.clear();
                durability.displayNameBridgeInitialized = true;
            } else if (playerNamed && !durability.displayNameApplied.empty() &&
                       durability::name::StripDecorations(currentName) !=
                           durability::name::StripDecorations(durability.displayNameApplied)) {
                // A different explicit name was applied after our last sync. The engine appends its
                // quality marker at display time, so the *rendered* name of our own last write never
                // matches it byte for byte; comparing what both names mean keeps that marker and the
                // stored level out of the baseline, which is what the panel used to show.
                durability.displayNameBaseline = durability::name::CleanStoredBaseline(currentName);
            }
            if (durability.displayNameBaseline.empty()) durability.displayNameBaseline = DisplayName(a_item);
            targetName = ReinforcedDisplayName(durability.displayNameBaseline, durability.enhancementLevel);
            clearBridgeAfterSync = durability.enhancementLevel == 0;
        }

        if (textData && (textData->displayNameText || textData->ownerQuest)) {
            logger::warn(
                "Skipped native +N name for {:08X}:{:04X}; its display name is owned by a quest or message.",
                a_key.baseFormID,
                a_key.uniqueID);
            return false;
        }
        if (!durability::name::AlreadyReinforced(currentName, targetName) || !playerNamed) {
            if (textData) textData->SetName(targetName.c_str());
            else a_extraList->Add(new RE::ExtraTextDisplayData(targetName.c_str()));
        }

        {
            std::scoped_lock lock(g_durabilityLock);
            const auto found = g_durability.find(a_key);
            if (found == g_durability.end()) return false;
            auto& durability = found->second;
            if (clearBridgeAfterSync) {
                durability.displayNameBaseline.clear();
                durability.displayNameApplied.clear();
                durability.displayNameBridgeInitialized = false;
            } else {
                durability.displayNameApplied = targetName;
            }
        }
        logger::debug(
            "Synced native display name for {:08X}:{:04X} to '{}'.",
            a_key.baseFormID,
            a_key.uniqueID,
            targetName);
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
        SyncDisplayNameRuntimeEffect(a_key, a_item, a_extraList);
    }

    void SyncAllRuntimeEffects()
    {
        std::vector<ItemKey> keys;
        {
            std::scoped_lock lock(g_durabilityLock);
            keys.reserve(g_durability.size());
            for (const auto& [key, durability] : g_durability) {
                if (durability.performanceBonus != 0 || durability.chargeBonus > 0.0F ||
                    durability.enhancementLevel > 0 || durability.displayNameBridgeInitialized ||
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
        case EnhancementCardType::Enchantment: return "覆盖原附魔，不叠加；已装备物品会自动临时卸下，成功后恢复原槽位。挡位为估算强度，具体效果见预览。";
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
            return "耐久上限 +" + FixedDecimal(a_card.rolledValue, 1);
        case EnhancementCardType::Wear:
            return "耐久损耗 -" + FixedDecimal(a_card.rolledValue * 100.0F, 0) + "%";
        case EnhancementCardType::Charge:
            return "附魔充能 +" + FixedDecimal(a_card.rolledValue * 100.0F, 0) + "%";
        case EnhancementCardType::Enchantment: {
            const auto* enchantment = RE::TESForm::LookupByID<RE::EnchantmentItem>(a_card.enchantmentFormID);
            if (!enchantment) return "附魔候选已失效";
            auto result = std::string("替换为：") + EnchantmentLabel(enchantment) + " · " + EnchantmentEffectSummary(enchantment);
            if (a_card.enchantmentCharge > 0) result += " · 基础充能 " + std::to_string(a_card.enchantmentCharge);
            return result;
        }
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
            const auto& ranges = g_enhancementRules.ranges[0];
            const std::array minimum{ranges[0][0], ranges[1][0], ranges[2][0], ranges[3][0]};
            const std::array maximum{ranges[0][1], ranges[1][1], ranges[2][1], ranges[3][1]};
            return std::round(roll(minimum[tier], maximum[tier]) * levelScale);
        }
        case EnhancementCardType::Weight: {
            const auto& ranges = g_enhancementRules.ranges[1];
            const std::array minimum{ranges[0][0], ranges[1][0], ranges[2][0], ranges[3][0]};
            const std::array maximum{ranges[0][1], ranges[1][1], ranges[2][1], ranges[3][1]};
            const auto remaining = (std::max)(0.0F, EquipmentWeight(a_item) - a_durability.weightReduction - 0.1F);
            if (remaining <= 0.001F) a_blockedReason = "重量已达下限";
            return (std::min)(roll(minimum[tier], maximum[tier]), remaining);
        }
        case EnhancementCardType::Speed: {
            const auto& ranges = g_enhancementRules.ranges[2];
            const std::array minimum{ranges[0][0], ranges[1][0], ranges[2][0], ranges[3][0]};
            const std::array maximum{ranges[0][1], ranges[1][1], ranges[2][1], ranges[3][1]};
            const auto remaining = (std::max)(0.0F, 1.0F - a_durability.attackSpeedBonus);
            if (remaining <= 0.0001F) a_blockedReason = "攻速已达 2× 上限";
            return (std::min)(roll(minimum[tier], maximum[tier]), remaining);
        }
        case EnhancementCardType::Durability: {
            const auto& ranges = g_enhancementRules.ranges[3];
            const std::array minimum{ranges[0][0], ranges[1][0], ranges[2][0], ranges[3][0]};
            const std::array maximum{ranges[0][1], ranges[1][1], ranges[2][1], ranges[3][1]};
            return std::round(roll(minimum[tier], maximum[tier]) * levelScale);
        }
        case EnhancementCardType::Wear: {
            const auto& ranges = g_enhancementRules.ranges[4];
            const std::array minimum{ranges[0][0], ranges[1][0], ranges[2][0], ranges[3][0]};
            const std::array maximum{ranges[0][1], ranges[1][1], ranges[2][1], ranges[3][1]};
            const auto remaining = (std::max)(0.0F, g_settings.maxWearReduction - a_durability.wearReduction);
            if (remaining <= 0.0001F) a_blockedReason = "耐磨已达上限";
            return (std::min)(roll(minimum[tier], maximum[tier]), remaining);
        }
        case EnhancementCardType::Charge: {
            const auto& ranges = g_enhancementRules.ranges[5];
            const std::array minimum{ranges[0][0], ranges[1][0], ranges[2][0], ranges[3][0]};
            const std::array maximum{ranges[0][1], ranges[1][1], ranges[2][1], ranges[3][1]};
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

    [[nodiscard]] std::vector<MaterialRequirementState> GetCardMaterials(
        RE::TESBoundObject* a_item,
        const EnhancementCardType a_type,
        const EnhancementTier a_tier,
        const std::uint32_t a_level,
        std::string& a_blockedReason)
    {
        auto materials = GetRecipeMaterials(a_item);
        const auto costScale = enhancement::CostScale(g_enhancementRules, a_level, TierMultiplier(a_tier));
        const auto add = [&](RE::TESBoundObject* material, double count) {
            if (!material || material == a_item || material->As<RE::TESObjectWEAP>() || material->As<RE::TESObjectARMO>()) {
                a_blockedReason = "规则所需材料未加载，请检查材料配置";
                return;
            }
            const auto required = enhancement::RequiredCount(count + static_cast<double>(materials[material]));
            if (!required) a_blockedReason = "材料需求超过引擎数量上限";
            else materials[material] = *required;
        };
        for (auto& [material, count] : materials) {
            if (material == a_item || material->As<RE::TESObjectWEAP>() || material->As<RE::TESObjectARMO>()) {
                a_blockedReason = "强化材料不能包含武器或护甲";
            }
            const auto required = enhancement::RequiredCount(static_cast<double>(count) * costScale);
            if (!required) a_blockedReason = "材料需求超过引擎数量上限";
            else count = *required;
        }
        for (const auto& reference : g_enhancementRules.catalysts[static_cast<std::size_t>(a_type)]) {
            auto* form = ResolveRuleForm(reference);
            add(form ? form->As<RE::TESBoundObject>() : nullptr, std::ceil(costScale));
        }
        // Merge into the existing material ledger, including any recipe gold.
        // Payment and refunds still use the single validated material loop.
        add(RE::TESForm::LookupByID<RE::TESBoundObject>(0xFU), enhancement::GoldFee(g_enhancementRules, a_level, TierMultiplier(a_tier)));
        if (a_level > 50) {
            static constexpr std::array<std::uint32_t, 3> unlocks{51, 75, 100};
            for (std::size_t index = 0; index < unlocks.size(); ++index) {
                if (a_level < unlocks[index]) continue;
                auto* form = ResolveRuleForm(g_enhancementRules.lateMaterials[index]);
                add(form ? form->As<RE::TESBoundObject>() : nullptr,
                    std::ceil((1.0 + static_cast<double>(a_level - unlocks[index]) / 10.0) * TierMultiplier(a_tier)));
            }
        }

        std::vector<MaterialRequirementState> result;
        result.reserve(materials.size());
        for (const auto& [material, count] : materials) {
            if (material && count > 0) result.push_back({ material->GetFormID(), count });
        }
        return result;
    }

    [[nodiscard]] std::vector<EnhancementCardType> EligibleCardTypes(
        RE::TESBoundObject* a_item, RE::ExtraDataList* a_extraList, const DurabilitySnapshot& a_durability)
    {
        std::vector<EnhancementCardType> types;
        const auto* weapon = a_item ? a_item->As<RE::TESObjectWEAP>() : nullptr;
        const auto category = EquipmentCategory(a_item);
        if (((weapon && BasePerformanceValue(a_item) > 0.0F) || category == "armor") &&
            a_durability.performanceBonus < (std::numeric_limits<std::int32_t>::max)() &&
            (!a_durability.performanceBridgeInitialized || a_durability.performanceAppliedHealth < 10000.0F)) {
            types.push_back(EnhancementCardType::Performance);
        }
        if (enhancement::HasRoom(a_durability.weightReduction, EquipmentWeight(a_item) - 0.1F, 0.001F)) types.push_back(EnhancementCardType::Weight);
        if (weapon && enhancement::HasRoom(a_durability.attackSpeedBonus, 1.0F, 0.0001F)) types.push_back(EnhancementCardType::Speed);
        types.push_back(EnhancementCardType::Durability);
        if (enhancement::HasRoom(a_durability.wearReduction, g_settings.maxWearReduction, 0.0001F)) types.push_back(EnhancementCardType::Wear);
        const auto capacity = InstanceChargeCapacity(a_item, a_extraList);
        if (weapon && capacity && *capacity < (std::numeric_limits<std::uint16_t>::max)() && a_durability.chargeBonus < 65534.0F) {
            types.push_back(EnhancementCardType::Charge);
        }
        const auto protectedItem = IsProtectedUniqueItem(a_item) || (a_extraList && a_extraList->HasQuestObjectAlias());
        if (!protectedItem && HasCompatibleEnchantment(a_item, a_extraList)) {
            types.push_back(EnhancementCardType::Enchantment);
        }
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
        const auto durability = GetDurability(a_key);
        auto eligibleTypes = EligibleCardTypes(a_item, a_extraList, durability);
        std::shuffle(eligibleTypes.begin(), eligibleTypes.end(), random);
        if (eligibleTypes.size() > 3) eligibleTypes.resize(3);
        const auto distinctTypeCount = eligibleTypes.size();
        while (!eligibleTypes.empty() && eligibleTypes.size() < 3) {
            eligibleTypes.push_back(eligibleTypes[eligibleTypes.size() % distinctTypeCount]);
        }

        std::vector<EnhancementCardState> cards;
        cards.reserve(eligibleTypes.size());
        for (std::size_t index = 0; index < eligibleTypes.size(); ++index) {
            EnhancementCardState card;
            card.id = std::to_string(a_key.baseFormID) + "-" + std::to_string(a_key.uniqueID) + "-" +
                      std::to_string(sequence) + "-" + std::to_string(index);
            card.type = eligibleTypes[index];
            card.tier = RollEnhancementTier(random);
            card.rolledValue = RollCardValue(card.type, card.tier, durability, a_item, random, card.blockedReason);
            if (card.type == EnhancementCardType::Enchantment) {
                const auto offer = RollEnchantmentOffer(a_item, a_extraList, card.tier, durability, random);
                if (!offer) {
                    card.blockedReason = "没有找到适用于该装备的其他附魔";
                } else {
                    card.enchantmentFormID = offer->enchantment->GetFormID();
                    card.enchantmentCharge = offer->charge;
                    card.enchantmentPower = offer->power;
                }
            }
            static constexpr std::array<std::uint32_t, 4> baseSuccess{ 96, 88, 75, 60 };
            const auto levelPenalty = (std::min)(45U, durability.enhancementLevel > 22U ? 45U : durability.enhancementLevel * 2U);
            card.successChance = (std::max)(10U, baseSuccess[static_cast<std::size_t>(card.tier)] - levelPenalty);
            card.requiredMaterials = GetCardMaterials(a_item, card.type, card.tier, durability.enhancementLevel, card.blockedReason);
            if (card.requiredMaterials.empty() && card.blockedReason.empty()) card.blockedReason = "没有可用的强化材料";
            if (a_key.uniqueID == 0 && card.blockedReason.empty()) card.blockedReason = "请先装备一次以建立独立实例";
            // Repair/unequip/owned materials are live conditions, never frozen
            // into an item draft that may be revisited after those conditions change.
            cards.push_back(std::move(card));
        }
        logger::info("Generated {} enhancement cards for {:08X}:{:04X} after {} paid refreshes.", cards.size(), a_key.baseFormID, a_key.uniqueID, a_refreshes);
        return cards;
    }

    [[nodiscard]] json EnhancementPreview(RE::TESBoundObject* a_item, RE::ExtraDataList* a_extraList,
        const DurabilitySnapshot& a_before, const EnhancementCardState& a_card);

    [[nodiscard]] json EnhancementCardsJson()
    {
        std::vector<EnhancementCardState> cards;
        std::optional<ItemKey> selected;
        {
            std::scoped_lock lock(g_forgeLock);
            selected = g_forgeSelectedItem;
            if (selected) {
                if (const auto* draft = g_enhancementDrafts.Find(*selected)) cards = draft->cards;
            }
        }
        auto* player = RE::PlayerCharacter::GetSingleton();
        const auto instance = selected ? ResolveEquipmentInstance(*selected) : std::nullopt;
        const auto durability = selected ? GetDurability(*selected) : DurabilitySnapshot{};
        const auto eligible = instance ? EligibleCardTypes(instance->item, instance->extraList, durability) : std::vector<EnhancementCardType>{};
        json result = json::array();
        for (const auto& card : cards) {
            json materials = json::array();
            std::string blockedReason = card.blockedReason;
            if (blockedReason.empty() && (!instance || durability.current <= 0.0F)) blockedReason = instance ? "请先修复装备" : "装备已不在背包中";
            if (blockedReason.empty() && std::find(eligible.begin(), eligible.end(), card.type) == eligible.end()) blockedReason = "属性已达上限或不再适用";
            for (const auto& requirement : card.requiredMaterials) {
                auto* material = RE::TESForm::LookupByID<RE::TESBoundObject>(requirement.formID);
                if (!material) {
                    blockedReason = "卡片材料已失效";
                    continue;
                }
                const auto owned = player ? (std::max)(0, player->GetItemCount(material)) : 0;
                materials.push_back({ { "name", DisplayName(material) }, { "isGold", requirement.formID == 0xFU }, { "required", requirement.count }, { "owned", owned } });
                if (blockedReason.empty() && owned < requirement.count) blockedReason = "缺少：" + DisplayName(material);
            }
            auto item = json{
                { "id", card.id },
                { "equipmentId", selected ? std::to_string(selected->baseFormID) + ":" + std::to_string(selected->uniqueID) : "" },
                { "type", CardTypeID(card.type) },
                { "tier", CardTierName(card.tier) },
                { "title", CardTitle(card.type) },
                { "description", CardDescription(card.type) },
                { "value", CardValue(card) },
                { "successChance", card.successChance },
                { "materials", std::move(materials) }
            };
            item["preview"] = instance ? EnhancementPreview(instance->item, instance->extraList, durability, card) : json::array();
            if (card.type == EnhancementCardType::Enchantment) {
                const auto* enchantment = RE::TESForm::LookupByID<RE::EnchantmentItem>(card.enchantmentFormID);
                if (enchantment && enchantment->GetFile(0)) {
                    item["description"] = CardDescription(card.type) + " 来源：" + std::string(enchantment->GetFile(0)->GetFilename());
                }
            }
            if (!blockedReason.empty()) item["blockedReason"] = blockedReason;
            result.push_back(std::move(item));
        }
        return result;
    }

    [[nodiscard]] RE::TESObjectMISC* GoldRecord()
    {
        return RE::TESForm::LookupByID<RE::TESObjectMISC>(0x0000000FU);
    }

    [[nodiscard]] std::int32_t PlayerGoldCount(RE::PlayerCharacter* a_player)
    {
        if (!a_player) return 0;
        // Avoid Actor::GetGoldAmount: this bundled CommonLib's DefaultObjectID
        // lookup misinterprets the inline default-object array as a pointer.
        // Gold001 is a fixed master record; count the same record we remove.
        auto* gold = GoldRecord();
        return gold ? (std::max)(0, a_player->GetItemCount(gold)) : 0;
    }

    [[nodiscard]] std::uint32_t CardRefreshCost(const std::uint32_t a_refreshes)
    {
        return enhancement::RefreshCost(a_refreshes);
    }

    void SelectEquipmentForForge(const std::string_view a_equipmentID)
    {
        if (!CanPreviewEnhancement()) return;
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
        bool reused = false;
        {
            std::scoped_lock lock(g_forgeLock);
            if (g_forgeSelectedItem == key && g_enhancementDrafts.Find(*key)) return;
            reused = g_enhancementDrafts.Find(*key) != nullptr;
            g_forgeSelectedItem = *key;
        }
        if (!reused) {
            auto cards = GenerateEnhancementCards(*key, instance->item, instance->extraList, 0);
            std::scoped_lock lock(g_forgeLock);
            g_enhancementDrafts.Store(*key, std::move(cards), 0);
        }
        SendState(reused ? "已恢复该装备的卡片和刷新费用。" : "已为" + InstanceDisplayName(instance->item, instance->extraList) + "生成三张强化卡片。");
    }

    void SendRefreshResult(std::string_view a_equipmentID, std::string_view a_requestID, bool a_success, std::uint32_t a_goldSpent, std::string_view a_message)
    {
        SendState(a_message, { { "requestId", a_requestID }, { "equipmentId", a_equipmentID },
            { "success", a_success }, { "goldSpent", a_goldSpent }, { "message", a_message } });
    }

    void RefreshEnhancementCards(const std::string_view a_equipmentID, const std::string_view a_requestID)
    {
        WorkshopFeedback feedback;
        if (!CanEnhanceEquipment()) {
            SendRefreshResult(a_equipmentID, a_requestID, false, 0, "刷新失败：需要靠近附魔台或锻造设备，并确保角色可操作。");
            return;
        }
        const auto key = ParseItemKey(a_equipmentID);
        if (!key) {
            SendRefreshResult(a_equipmentID, a_requestID, false, 0, "刷新失败：装备实例标识无效。");
            return;
        }
        const auto instance = ResolveEquipmentInstance(*key);
        if (!instance) {
            SendRefreshResult(a_equipmentID, a_requestID, false, 0, "刷新失败：所选装备已不在背包中。");
            return;
        }

        std::uint32_t refreshes = 0;
        bool selectionMatches = false;
        {
            std::scoped_lock lock(g_forgeLock);
            if (g_forgeSelectedItem == key) {
                if (const auto* draft = g_enhancementDrafts.Find(*key)) {
                    selectionMatches = true;
                    refreshes = draft->refreshes;
                }
            }
        }
        if (!selectionMatches) {
            SendRefreshResult(a_equipmentID, a_requestID, false, 0, "刷新失败：所选装备已变化，请返回装备详情后重试。本次未扣费。");
            return;
        }

        auto* player = RE::PlayerCharacter::GetSingleton();
        auto* gold = GoldRecord();
        const auto cost = CardRefreshCost(refreshes);
        if (!player || !gold || PlayerGoldCount(player) < static_cast<std::int32_t>(cost)) {
            SendRefreshResult(a_equipmentID, a_requestID, false, 0, "刷新失败：需要 " + std::to_string(cost) + " 金币。");
            return;
        }
        const auto nextRefreshes = (std::min)(refreshes, (std::numeric_limits<std::uint32_t>::max)() - 1U) + 1U;
        auto cards = GenerateEnhancementCards(*key, instance->item, instance->extraList, nextRefreshes);
        player->RemoveItem(gold, static_cast<std::int32_t>(cost), RE::ITEM_REMOVE_REASON::kRemove, nullptr, nullptr);
        {
            std::scoped_lock lock(g_forgeLock);
            // Record the paid result for the item even if UI selection changes.
            g_enhancementDrafts.Store(*key, std::move(cards), nextRefreshes);
        }
        feedback.resultSound = "UIEnchantRecharge";
        SendRefreshResult(a_equipmentID, a_requestID, true, cost, "已支付 " + std::to_string(cost) + " 金币并刷新强化卡片。");
    }

    [[nodiscard]] std::string SalvageDescription(const std::map<RE::TESBoundObject*, std::int32_t>& a_materials)
    {
        std::string description = "已回收：";
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
        g_enhancementDrafts.Store(a_key, std::move(cards), 0);
    }

    void ClearEnhancementDraft(const ItemKey& a_key)
    {
        std::scoped_lock lock(g_forgeLock);
        g_enhancementDrafts.Erase(a_key);
        if (g_forgeSelectedItem == a_key) g_forgeSelectedItem.reset();
    }

    [[nodiscard]] DurabilitySnapshot SuccessfulCardSnapshot(
        DurabilitySnapshot durability,
        RE::TESBoundObject* a_item,
        const EnhancementCardState& a_card)
    {
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
        return durability;
    }

    void ApplySuccessfulCard(const ItemKey& a_key, RE::TESBoundObject* a_item, const EnhancementCardState& a_card)
    {
        std::scoped_lock lock(g_durabilityLock);
        g_durability[a_key] = SuccessfulCardSnapshot(g_durability[a_key], a_item, a_card);
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

    // Holds only an instance key and slot ID across engine equip calls, never ExtraDataList pointers.
    // Every engine call is immediate, non-forced and followed by a fresh inventory lookup.
    class WorkshopEquipmentRestore
    {
    public:
        explicit WorkshopEquipmentRestore(ItemKey a_key) : key_(a_key) {}
        ~WorkshopEquipmentRestore() { if (!finished_) Restore(); }

        bool Prepare()
        {
            const auto instance = ResolveEquipmentInstance(key_);
            if (!instance || !instance->extraList) return false;
            wasEquipped_ = instance->extraList->GetWorn();
            if (!wasEquipped_) return true;
            // A shared worn stack cannot safely represent the one item being enhanced.
            if (instance->extraList->GetCount() > 1) return false;
            if (auto* weapon = instance->item->As<RE::TESObjectWEAP>()) {
                const auto left = instance->extraList->HasType<RE::ExtraWornLeft>();
                const auto right = instance->extraList->HasType<RE::ExtraWorn>();
                if (left && right) return false;
                const auto* baseSlot = weapon->GetEquipSlot();
                // Master EQUP records: RightHand 13F42, LeftHand 13F43, BothHands 13F45.
                slotID_ = baseSlot && baseSlot->GetFormID() == 0x13F45 ? 0x13F45 : left ? 0x13F43 : 0x13F42;
            }
            auto* player = RE::PlayerCharacter::GetSingleton();
            auto* manager = RE::ActorEquipManager::GetSingleton();
            auto* slot = slotID_ ? RE::TESForm::LookupByID<RE::BGSEquipSlot>(slotID_) : nullptr;
            if (!player || !manager || (slotID_ && !slot)) return false;
            manager->UnequipObject(player, instance->item, instance->extraList, 1, slot, false, false, false, true);
            const auto refreshed = ResolveEquipmentInstance(key_);
            return refreshed && refreshed->extraList && !refreshed->extraList->GetWorn();
        }

        bool Restore()
        {
            finished_ = true;
            if (!wasEquipped_) return true;
            const auto instance = ResolveEquipmentInstance(key_);
            auto* player = RE::PlayerCharacter::GetSingleton();
            auto* manager = RE::ActorEquipManager::GetSingleton();
            if (!instance || !instance->extraList || !player || !manager || GetDurability(key_).current <= 0) return false;
            if (instance->extraList->GetWorn()) return MatchesSlot(instance->extraList);
            // Do not displace something another mod equipped in the meantime.
            if ((slotID_ == 0x13F42 || slotID_ == 0x13F45) && player->GetEquippedObject(false)) return false;
            if ((slotID_ == 0x13F43 || slotID_ == 0x13F45) && player->GetEquippedObject(true)) return false;
            if (const auto* armor = instance->item->As<RE::TESObjectARMO>()) {
                if (armor->IsShield() && player->GetEquippedObject(true)) return false;
                const auto mask = static_cast<std::uint32_t>(armor->GetSlotMask());
                const auto inventory = player->GetInventory();
                for (const auto& [other, entry] : inventory) {
                    const auto* otherArmor = other ? other->As<RE::TESObjectARMO>() : nullptr;
                    if (!otherArmor || entry.first <= 0 || !entry.second || !entry.second->extraLists ||
                        !(mask & static_cast<std::uint32_t>(otherArmor->GetSlotMask()))) continue;
                    for (const auto* extra : *entry.second->extraLists) if (extra && extra->GetWorn()) return false;
                }
            }
            auto* slot = slotID_ ? RE::TESForm::LookupByID<RE::BGSEquipSlot>(slotID_) : nullptr;
            if (slotID_ && !slot) return false;
            manager->EquipObject(player, instance->item, instance->extraList, 1, slot, false, false, false, true);
            const auto refreshed = ResolveEquipmentInstance(key_);
            return refreshed && refreshed->extraList && MatchesSlot(refreshed->extraList);
        }

        void LeaveUnequipped() { finished_ = true; }

    private:
        bool MatchesSlot(RE::ExtraDataList* a_extra) const
        {
            if (slotID_ == 0x13F43) return a_extra->HasType<RE::ExtraWornLeft>();
            if (slotID_ == 0x13F42 || slotID_ == 0x13F45) return a_extra->HasType<RE::ExtraWorn>();
            return a_extra->GetWorn();
        }
        ItemKey key_;
        RE::FormID slotID_ = 0;
        bool wasEquipped_ = false;
        bool finished_ = false;
    };

    void ApplyEnhancementCard(const std::string_view a_equipmentID, const std::string_view a_cardID)
    {
        WorkshopFeedback feedback;
        if (!CanEnhanceEquipment()) {
            SendState("强化失败：需要靠近附魔台或锻造设备，并确保角色可操作。");
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
                if (const auto* draft = g_enhancementDrafts.Find(*key)) {
                    const auto found = std::find_if(draft->cards.begin(), draft->cards.end(), [a_cardID](const auto& a_candidate) {
                        return a_candidate.id == a_cardID;
                    });
                    if (found != draft->cards.end()) {
                        card = *found;
                        foundCard = true;
                    }
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
        auto instance = ResolveEquipmentInstance(*key);
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

        RE::EnchantmentItem* replacementEnchantment = nullptr;
        const auto eligible = EligibleCardTypes(instance->item, instance->extraList, durability);
        if (std::find(eligible.begin(), eligible.end(), card.type) == eligible.end()) {
            SendState("强化失败：该属性已达上限或卡片不再适用于此装备。本次未消耗材料。");
            return;
        }
        if (card.type == EnhancementCardType::Enchantment) {
            if (instance->extraList->HasQuestObjectAlias() || IsProtectedUniqueItem(instance->item)) {
                SendState("附魔替换失败：唯一物品与任务物品不能替换附魔。");
                return;
            }
            replacementEnchantment = RE::TESForm::LookupByID<RE::EnchantmentItem>(card.enchantmentFormID);
            if (!replacementEnchantment ||
                !IsCompatibleEnchantment(instance->item, replacementEnchantment) ||
                InstanceEnchantment(instance->item, instance->extraList) == replacementEnchantment) {
                SendState("附魔替换失败：卡片中的附魔已失效或不再适用于该装备，请刷新卡片。");
                return;
            }
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
        WorkshopEquipmentRestore equipment(*key);
        if (!equipment.Prepare()) {
            const auto restored = equipment.Restore();
            SendState(restored ? "无法安全卸下目标装备，本次未扣费。若为同名堆叠装备，请先手动卸下并拆分。" :
                "无法安全处理装备，本次未扣费；请检查背包和装备槽后重试。");
            return;
        }
        instance = ResolveEquipmentInstance(*key);
        const auto canPay = std::all_of(materials.begin(), materials.end(), [player](const auto& cost) {
            return player->GetItemCount(cost.first) >= cost.second;
        });
        if (!instance || !instance->extraList || instance->extraList->GetWorn() || !CanEnhanceEquipment() || !canPay) {
            equipment.Restore();
            SendState("装备或材料状态已变化，强化已取消，本次未扣费；请检查装备状态。");
            return;
        }
        for (const auto& [material, count] : materials) {
            player->RemoveItem(material, count, RE::ITEM_REMOVE_REASON::kRemove, nullptr, nullptr);
        }

        instance = ResolveEquipmentInstance(*key);
        if (!instance || !instance->extraList || instance->extraList->GetWorn()) {
            for (const auto& [material, count] : materials) player->AddObjectToContainer(material, nullptr, count, nullptr);
            equipment.Restore();
            SendState("装备状态意外变化，已退还本次金币和材料；请检查装备状态。");
            return;
        }

        const auto seed = static_cast<std::uint32_t>(
            std::chrono::steady_clock::now().time_since_epoch().count() ^
            (static_cast<std::uint64_t>(key->baseFormID) << 16U) ^ key->uniqueID ^ std::hash<std::string_view>{}(a_cardID));
        std::mt19937 random(seed);
        const auto roll = std::uniform_int_distribution<std::uint32_t>(1, 100)(random);
        const auto itemName = InstanceDisplayName(instance->item, instance->extraList);
        if (roll <= card.successChance) {
            if (card.type == EnhancementCardType::Enchantment &&
                !ApplyReplacementEnchantment(
                    *key,
                    instance->item,
                    instance->extraList,
                    replacementEnchantment,
                    card.enchantmentCharge)) {
                for (const auto& [material, count] : materials) {
                    player->AddObjectToContainer(material, nullptr, count, nullptr);
                }
                equipment.Restore();
                SendState("附魔替换失败：无法写入装备实例，金币和材料已退还；请检查装备状态。");
                return;
            }
            ApplySuccessfulCard(*key, instance->item, card);
            SyncInstanceRuntimeEffects(*key, instance->item, instance->extraList);
            const auto restored = equipment.Restore();
            QueuePlayerRuntimeEffectsSync();
            const auto result = GetDurability(*key);
            if (const auto refreshed = ResolveEquipmentInstance(*key)) SetNextEnhancementDraft(*key, refreshed->item, refreshed->extraList);
            else ClearEnhancementDraft(*key);
            logger::info(
                "Enhancement succeeded for {:08X}:{:04X}; card={}, roll={}, chance={}, newLevel={}.",
                key->baseFormID,
                key->uniqueID,
                CardTypeID(card.type),
                roll,
                card.successChance,
                result.enhancementLevel);
            const auto enchantmentResult = card.type == EnhancementCardType::Enchantment && replacementEnchantment ?
                                               "，附魔已替换为“" + EnchantmentLabel(replacementEnchantment) + "”" :
                                               std::string{};
            feedback.resultSound = "UIEnchantingItemCreate";
            SendState(itemName + "强化成功" + enchantmentResult + "，当前等级 +" + std::to_string(result.enhancementLevel) +
                (restored ? "。" : "。未能恢复原装备槽位，请在背包中手动装备。"));
            return;
        }

        equipment.LeaveUnequipped();
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
            SendState(itemName + "强化失败，已卸下并保留；强化等级降至 +" + std::to_string(result.enhancementLevel) + "。");
            return;
        }

        const auto salvage = GetSalvageMaterials(instance->item);
        player->RemoveItem(instance->item, 1, RE::ITEM_REMOVE_REASON::kRemove, instance->extraList, nullptr);
        if (IsUniqueIDInPlayerInventory(key->baseFormID, key->uniqueID)) {
            const auto retainedInstance = ResolveEquipmentInstance(*key);
            if (retainedInstance) SetNextEnhancementDraft(*key, retainedInstance->item, retainedInstance->extraList);
            else ClearEnhancementDraft(*key);
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
        }
        ClearEnhancementDraft(*key);
        QueuePlayerRuntimeEffectsSync();
        logger::info(
            "Enhancement failed and dismantled {:08X}:{:04X}; roll={}, chance={}, salvageTypes={}.",
            key->baseFormID,
            key->uniqueID,
            roll,
            card.successChance,
            salvage.size());
        feedback.resultSound = "UIEnchantingItemDestroy";
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

        const auto brokenItemName = InstanceDisplayName(item, extraList);
        const auto questItem = extraList->HasQuestObjectAlias();
        const auto uniqueItem = IsProtectedUniqueItem(item);
        const auto preserveEnchanted = IsInstanceEnchanted(item, extraList) && !g_settings.allowEnchantedItemsToBreak;
        auto materials = GetSalvageMaterials(item);
        const auto preserve = questItem || uniqueItem || preserveEnchanted || materials.empty();
        if (preserve) {
            if (auto* equipManager = RE::ActorEquipManager::GetSingleton()) equipManager->UnequipObject(player, item, extraList);
            const auto reason = questItem || uniqueItem ? "受保护物品已损坏，需要在装备工坊修复。" : preserveEnchanted ? "附魔物品已损坏，需要在装备工坊修复。" : "未找到可用的锻造配方，物品已保留为损坏状态。";
            ShowHUD("warning", DisplayName(item), reason, g_settings.weaponDisplaySeconds, 0.0F, GetDurability(a_key).maximum);
            logger::info("Preserved broken item {:08X}:{:04X} (quest={}, unique={}, enchanted-protected={}, recipe-missing={}).", a_key.baseFormID, a_key.uniqueID, questItem, uniqueItem, preserveEnchanted, materials.empty());
        } else {
            player->RemoveItem(item, 1, RE::ITEM_REMOVE_REASON::kRemove, extraList, nullptr);
            if (IsUniqueIDInPlayerInventory(a_key.baseFormID, a_key.uniqueID)) {
                const auto refreshedInventory = player->GetInventory();
                const auto refreshed = refreshedInventory.find(item);
                auto* refreshedEntry = refreshed != refreshedInventory.end() && refreshed->second.second ? refreshed->second.second.get() : nullptr;
                auto* refreshedExtraList = FindExtraListByKey(refreshedEntry, a_key);
                if (auto* equipManager = RE::ActorEquipManager::GetSingleton(); equipManager && refreshedExtraList) equipManager->UnequipObject(player, item, refreshedExtraList);
                ShowHUD("warning", DisplayName(item), "物品移除失败，已保留为损坏状态。", g_settings.weaponDisplaySeconds, 0.0F, GetDurability(a_key).maximum);
                logger::error("Could not remove destroyed item {:08X}:{:04X}; preserved it as broken.", a_key.baseFormID, a_key.uniqueID);
            } else {
                for (const auto& [material, count] : materials) player->AddObjectToContainer(material, nullptr, count, nullptr);
                {
                    std::scoped_lock lock(g_durabilityLock);
                    g_durability.erase(a_key);
                    g_lowDurabilityWarnings.erase(a_key);
                }
                ClearEnhancementDraft(a_key);
                const auto salvageMessage = SalvageDescription(materials);
                const auto brokenMessage = "「" + brokenItemName + "」耐久耗尽，已损坏并分解。";
                ShowHUD("warning", brokenMessage, salvageMessage, (std::max)(5.0F, g_settings.weaponDisplaySeconds));
                if (item->As<RE::TESObjectWEAP>()) {
                    const auto notification = brokenMessage + salvageMessage;
                    RE::DebugNotification(notification.c_str());
                }
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
        case RE::WEAPON_TYPE::kStaff:
            return g_settings.staffCastWear;
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
        const std::string_view a_action,
        const float a_minimumWear = 0.1F)
    {
        if (!a_item || !std::isfinite(a_baseWear) || !std::isfinite(a_actionMultiplier) || a_baseWear <= 0.0F || a_actionMultiplier <= 0.0F) return;
        DurabilitySnapshot durability;
        float appliedWear = 0.0F;
        {
            std::scoped_lock lock(g_durabilityLock);
            auto& stored = g_durability[a_key];
            stored.maximum = (std::max)(1.0F, stored.maximum);
            stored.current = std::clamp(stored.current, 0.0F, stored.maximum);
            if (stored.current <= 0.0F) return;
            const auto reduction = std::clamp(stored.wearReduction, 0.0F, g_settings.maxWearReduction);
            appliedWear = wear_rules::Amount(a_baseWear,a_actionMultiplier,reduction,a_minimumWear);
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

    wear_rules::Travel g_movementTravel;
    wear_rules::ImpactThrottle g_impactThrottle;
    bool g_environmentWearReady = false;

    // Snapshot on the game thread: never retain engine inventory pointers between ticks.
    void RefreshEquippedHUD()
    {
        if (!g_prisma || !g_view) return;
        if (!g_hudBridgeReady) {
            // The initial page-side ready notification may precede native bridge injection.
            // Do not wait forever for a one-shot notification that has already been lost.
            if (++g_hudProbeAttempts == 1 || g_hudProbeAttempts == 20) {
                logger::info("Equipped HUD waiting for page bridge; readiness probe {}.", g_hudProbeAttempts);
            }
            g_prisma->Invoke(g_view, durability_hud::kReadyProbe);
            return;
        }
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto* ui = RE::UI::GetSingleton();
        // Another mod's Meridian panel (the companion manager, for example) must hide the HUD too:
        // g_panelVisible only tracks this mod's own view.
        const bool otherPanelFocused = g_prisma->HasAnyActiveFocus() && !g_prisma->HasFocus(g_view);
        const bool allowed = g_environmentWearReady && player && player->GetParentCell() &&
            player->Is3DLoaded() && !player->IsDead() && ui && ui->IsShowingMenus() &&
            !ui->GameIsPaused() && !g_panelVisible && !otherPanelFocused && !ui->IsMenuOpen("Main Menu") &&
            !ui->IsMenuOpen("Loading Menu") && !ui->IsMenuOpen("InventoryMenu") &&
            !ui->IsMenuOpen("MagicMenu") && !ui->IsMenuOpen("ContainerMenu") &&
            !ui->IsMenuOpen("BarterMenu") && !ui->IsMenuOpen("Dialogue Menu");
        if (g_clearHudPending || (!allowed && g_gameHudAllowed)) {
            g_clearHudPending = false;
            g_hudVisible = false;
            g_equippedHudVisible = false;
            ++g_hudSequence;
            g_equippedHudPayload.clear();
            g_prisma->Invoke(g_view, "window.DurabilityManager?.clearHud();");
        }
        if (g_gameHudAllowed != allowed) {
            logger::info("Equipped HUD gameplay visibility: {} (loaded={}, player3D={}, paused={}, panel={}).",
                allowed, g_environmentWearReady, player && player->Is3DLoaded(), ui && ui->GameIsPaused(), g_panelVisible);
        }
        g_gameHudAllowed = allowed;
        if (!allowed) { UpdateViewVisibility(); return; }

        json items = json::array();
        std::unordered_set<ItemKey, ItemKeyHash> seen;
        const auto append = [&](RE::TESBoundObject* item, RE::ExtraDataList* extra, bool weapon, const char* slot) {
            if (!item || !extra || !extra->GetWorn()) return;
            const auto key = EnsureItemKeyForExtraList(extra, item);
            if (!key || !seen.insert(*key).second) return;
            const auto durability = GetDurability(*key);
            if (!durability_hud::ShouldDisplay(extra->GetWorn(), weapon, durability.current, durability.maximum, g_settings.lowDurabilityThreshold)) return;
            const bool low = durability.current * 100.0F / durability.maximum < g_settings.lowDurabilityThreshold;
            items.push_back({ {"id", std::to_string(key->baseFormID) + ":" + std::to_string(key->uniqueID)},
                {"kind", low ? "warning" : "weapon"}, {"title", DisplayName(item)}, {"detail", slot},
                {"current", durability.current}, {"maximum", durability.maximum} });
        };
        // Hand-specific extra lists preserve two separate instances of the same weapon.
        for (const bool left : { false, true }) {
            auto* entry = player->GetEquippedEntryData(left);
            auto* weapon = entry && entry->object ? entry->object->As<RE::TESObjectWEAP>() : nullptr;
            if (!weapon || !BaseWeaponWear(weapon)) continue;
            append(weapon, FindWornExtraListForHand(entry, left), true, left ? "左手" : "右手");
        }
        const auto inventory = player->GetInventory();
        for (const auto& [item, entry] : inventory) {
            auto* armor = item ? item->As<RE::TESObjectARMO>() : nullptr;
            if (!armor || entry.first <= 0 || !entry.second || !entry.second->extraLists) continue;
            for (auto* extra : *entry.second->extraLists) append(armor, extra, false, "低耐久");
        }
        const auto itemsPayload = items.dump();
        const auto positionPayload = json{{"hudRightPercent", g_settings.hudRightPercent}, {"hudBottomPercent", g_settings.hudBottomPercent}}.dump();
        // Read on the game thread. Values are actor-sheet values, not damage mitigation.
        const auto finiteValue = [](float value) -> json {
            return std::isfinite(value) ? json(std::round(value * 10.0F) / 10.0F) : json(nullptr);
        };
        const auto actorValue = [&](RE::ActorValue value) { return finiteValue(player->AsActorValueOwner()->GetActorValue(value)); };
        const auto* skills = player->GetPlayerRuntimeData().skills;
        const auto* calendar = RE::Calendar::GetSingleton();
        json playerState = {
            {"level", player->GetLevel()},
            {"experience", skills && skills->data ? finiteValue(skills->data->xp) : json(nullptr)},
            {"experienceNext", skills && skills->data ? finiteValue(skills->data->levelThreshold) : json(nullptr)},
            {"fire", actorValue(RE::ActorValue::kResistFire)}, {"frost", actorValue(RE::ActorValue::kResistFrost)},
            {"shock", actorValue(RE::ActorValue::kResistShock)}, {"magic", actorValue(RE::ActorValue::kResistMagic)},
            {"poison", actorValue(RE::ActorValue::kPoisonResist)}, {"disease", actorValue(RE::ActorValue::kResistDisease)},
            {"armor", actorValue(RE::ActorValue::kDamageResist)}, {"speed", actorValue(RE::ActorValue::kSpeedMult)},
            {"gold", PlayerGoldCount(player)}, {"weight", finiteValue(player->GetWeightInContainer())},
            {"carryWeight", finiteValue(player->GetTotalCarryWeight())}, {"gameMinutes", nullptr}
        };
        if (calendar && calendar->gameHour && std::isfinite(calendar->gameHour->value)) {
            const auto hour = std::fmod((std::max)(0.0F, calendar->gameHour->value), 24.0F);
            playerState["gameMinutes"] = static_cast<int>(hour * 60.0F);
        }
        const auto playerPayload = playerState.dump();
#ifdef UNIFIED_WORKSHOP
        // Queued crafting progress rides the same snapshot, so it clears with the rest.
        const auto craftPayload = unified_workshop::CraftOrderJson();
#else
        const auto craftPayload = std::string(R"({"entries":[],"paused":false,"reason":""})");
#endif
        const auto payload = itemsPayload + positionPayload + playerPayload + craftPayload;
        if (payload != g_equippedHudPayload) {
            if (g_equippedHudPayload.empty())
                logger::info("Equipped HUD snapshot: {} item(s).", items.size());
            g_equippedHudPayload = payload;
            g_equippedHudVisible = true; // Player stats remain visible even with empty hands.
            const auto script = "window.DurabilityManager?.updateHudPosition?.(" + positionPayload + ");window.DurabilityManager?.updateEquippedHud(" + itemsPayload + ");window.DurabilityManager?.updatePlayerHud?.(" + playerPayload + ");window.DurabilityManager?.updateCraftOrders?.(" + craftPayload + ");";
            g_prisma->Invoke(g_view, script.c_str());
            if (g_equippedHudVisible) g_prisma->Show(g_view);
        }
        UpdateViewVisibility();
    }

    void StartEquippedHUDUpdates()
    {
        // At most one pending task; the worker only schedules, all engine access is on the game thread.
        static std::atomic_bool pending = false;
        static std::jthread worker([](std::stop_token stop) {
            while (!stop.stop_requested()) {
                std::this_thread::sleep_for(std::chrono::milliseconds(500));
                if (stop.stop_requested()) break;
                if (auto* tasks = SKSE::GetTaskInterface(); tasks && !pending.exchange(true)) {
                    tasks->AddTask([] {
                        try { RefreshEquippedHUD(); }
                        catch (const std::exception& error) { logger::warn("Equipped HUD refresh failed: {}", error.what()); }
                        pending = false;
                    });
                }
            }
        });
    }

    double WearClockSeconds() {
        return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
    }

    void ResetEnvironmentWear() {
        g_movementTravel.Reset();
        g_impactThrottle.Reset();
    }

    void ApplyMovementWear() {
        auto* player = RE::PlayerCharacter::GetSingleton();
        auto* cell = player ? player->GetParentCell() : nullptr;
        auto* ui = RE::UI::GetSingleton();
        const bool walking = g_environmentWearReady && player && cell && !player->IsDead() && ui && !ui->GameIsPaused() &&
            !player->IsOnMount() && !player->AsActorState()->IsSwimming() && !player->IsInMidair() && !player->AsActorState()->IsFlying() && !player->AsActorState()->IsSitting();
        if (!walking) { g_movementTravel.Reset(); return; }
        const auto position = player->GetPosition();
        const auto units = g_movementTravel.Sample({position.x,position.y,position.z},cell->GetFormID(),WearClockSeconds(),true);
        if (units <= 0) return;
        using Slot = RE::BIPED_MODEL::BipedObjectSlot;
        for (const auto& worn : CollectWornArmorInstances()) {
            if (!worn.armor || worn.armor->IsShield()) continue;
            const auto slots = std::to_underlying(worn.armor->GetSlotMask());
            const bool boots = (slots & (std::to_underlying(Slot::kFeet)|std::to_underlying(Slot::kCalves))) != 0;
            const bool body = (slots & std::to_underlying(Slot::kBody)) != 0;
            if (boots || body) ApplyEquipmentWear(worn.armor,worn.key,
                boots ? g_settings.movementBootWearPer1000Units : g_settings.movementBodyWearPer1000Units,
                units,"Movement distance",0.0F);
        }
    }

    void ApplyIncomingArmorWear(const RE::TESHitEvent& a_event)
    {
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!g_environmentWearReady || !player || player->IsDead() || a_event.target.get() != player || a_event.cause.get() == player) return;

        const auto* source = a_event.source != 0 ? RE::TESForm::LookupByID(a_event.source) : nullptr;
        const auto* sourceWeapon = source ? source->As<RE::TESObjectWEAP>() : nullptr;
        const RE::MagicItem* magic = nullptr;
        if (source) {
            if (auto* spell = source->As<RE::SpellItem>()) magic = spell;
            else if (auto* scroll = source->As<RE::ScrollItem>()) magic = scroll;
            else if (auto* enchantment = source->As<RE::EnchantmentItem>()) magic = enchantment;
            else if (sourceWeapon && sourceWeapon->IsStaff()) magic = sourceWeapon->formEnchanting;
        }
        const bool harmful = magic && (magic->IsHostile() || std::any_of(magic->effects.begin(),magic->effects.end(),[](const auto* effect){
            return effect && effect->baseEffect && effect->baseEffect->IsDetrimental();
        }));
        const auto* cause = a_event.cause.get();
        const bool trap = (!cause && a_event.source==0) || (cause && !cause->As<RE::Actor>()) || (source &&
            (source->GetFormType()==RE::FormType::Explosion || source->GetFormType()==RE::FormType::Hazard || source->GetFormType()==RE::FormType::Projectile || source->GetFormType()==RE::FormType::Activator));
        const auto impact = wear_rules::Classify(false,magic!=nullptr,harmful,sourceWeapon && !sourceWeapon->IsStaff(),trap,a_event.source==0);
        if (impact == wear_rules::Impact::ignore) return;
        const auto environmentalMultiplier = impact==wear_rules::Impact::magic ? g_settings.magicHitWearMultiplier :
            impact==wear_rules::Impact::trap ? g_settings.trapHitWearMultiplier : 1.0F;
        if (environmentalMultiplier<=0) return;
        if (impact!=wear_rules::Impact::physical) {
            const auto key = (static_cast<std::uint64_t>(cause ? cause->GetFormID() : 0)<<32U)|a_event.source;
            if (!g_impactThrottle.Accept(key,WearClockSeconds(),g_settings.continuousHitIntervalSeconds)) return;
        }

        auto wornArmor = CollectWornArmorInstances();
        if (wornArmor.empty()) return;
        WornArmorInstance* selected = nullptr;
        const auto blocked = !magic && a_event.flags.any(RE::TESHitEvent::Flag::kHitBlocked);
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
            multiplier * environmentalMultiplier,
            impact==wear_rules::Impact::magic ? "Incoming magic hit" : impact==wear_rules::Impact::trap ? "Incoming trap hit" :
            blocked ? "Blocked physical hit" : "Incoming physical hit");
    }

    class EquipmentEventSink final : public RE::BSTEventSink<RE::TESEquipEvent>, public RE::BSTEventSink<RE::BSAnimationGraphEvent>, public RE::BSTEventSink<RE::TESHitEvent>, public RE::BSTEventSink<RE::TESPlayerBowShotEvent>, public RE::BSTEventSink<RE::TESContainerChangedEvent>, public RE::BSTEventSink<SKSE::ActionEvent>, public RE::BSTEventSink<RE::BGSFootstepEvent>
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
            if (auto* source = RE::ScriptEventSourceHolder::GetSingleton()) source->AddEventSink<RE::TESContainerChangedEvent>(this);
            if (auto* source = SKSE::GetActionEventSource()) source->AddEventSink(this);
            if (auto* source = RE::BGSFootstepManager::GetSingleton()) source->AddEventSink(this);
            if (const auto* player = RE::PlayerCharacter::GetSingleton()) player->AddAnimationGraphEventSink(this);
            registered_ = true;
        }

        RE::BSEventNotifyControl ProcessEvent(const RE::TESEquipEvent* a_event, RE::BSTEventSource<RE::TESEquipEvent>*) override
        {
            auto* player = RE::PlayerCharacter::GetSingleton();
            if (!a_event || !player || a_event->actor.get() != player) return RE::BSEventNotifyControl::kContinue;
            if (RE::TESForm::LookupByID<RE::TESObjectARMO>(a_event->baseObject)) g_movementTravel.Reset();
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

        RE::BSEventNotifyControl ProcessEvent(const SKSE::ActionEvent* a_event, RE::BSTEventSource<SKSE::ActionEvent>*) override
        {
            auto* player = RE::PlayerCharacter::GetSingleton();
            if (!a_event || !player || a_event->actor != player || a_event->type != SKSE::ActionEvent::Type::kSpellFire) return RE::BSEventNotifyControl::kContinue;
            if (a_event->slot != SKSE::ActionEvent::Slot::kLeft && a_event->slot != SKSE::ActionEvent::Slot::kRight) return RE::BSEventNotifyControl::kContinue;
            const auto* weapon = a_event->sourceForm ? a_event->sourceForm->As<RE::TESObjectWEAP>() : nullptr;
            if (!weapon || !weapon->IsStaff() || weapon->IsBound()) return RE::BSEventNotifyControl::kContinue;
            // SKSE supplies the equipped object and firing hand. Do not resolve by base
            // form: two copies of the same staff can be equipped in different hands.
            const auto leftHand = a_event->slot == SKSE::ActionEvent::Slot::kLeft;
            auto* entry = player->GetEquippedEntryData(leftHand);
            if (!entry || entry->object != weapon) return RE::BSEventNotifyControl::kContinue;
            auto* extraList = FindWornExtraListForHand(entry, leftHand);
            const auto* charge = extraList ? extraList->GetByType<RE::ExtraCharge>() : nullptr;
            if (charge && (!std::isfinite(charge->charge) || charge->charge <= 0.0F)) return RE::BSEventNotifyControl::kContinue;
            const auto key = EnsureItemKeyForExtraList(extraList, weapon);
            if (!key) return RE::BSEventNotifyControl::kContinue;
            // Listen only to release, never charge-start or hit events. Concentration
            // casts pay per release rather than per damage tick or target.
            ApplyEquipmentWear(weapon, *key, g_settings.staffCastWear, 1.0F, "Staff release");
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
            return RE::BSEventNotifyControl::kContinue;
        }

        RE::BSEventNotifyControl ProcessEvent(const RE::BGSFootstepEvent* event, RE::BSTEventSource<RE::BGSFootstepEvent>*) override {
            auto* player = RE::PlayerCharacter::GetSingleton();
            if (!event || !player || event->actor.get().get()!=player) return RE::BSEventNotifyControl::kContinue;
            std::uint64_t epoch;
            { std::scoped_lock lock(g_durabilityLock); epoch=g_stateEpoch; }
            if (auto* tasks=SKSE::GetTaskInterface()) tasks->AddTask([epoch]{
                { std::scoped_lock lock(g_durabilityLock); if (epoch!=g_stateEpoch) return; }
                ApplyMovementWear();
            });
            return RE::BSEventNotifyControl::kContinue;
        }

    private:
        bool registered_ = false;
    };

    [[nodiscard]] json EnhancementPreview(RE::TESBoundObject* a_item, RE::ExtraDataList* a_extraList,
        const DurabilitySnapshot& a_before, const EnhancementCardState& a_card)
    {
        // Pure projection: share the success arithmetic without mutating the item or co-save.
        const auto after = SuccessfulCardSnapshot(a_before, a_item, a_card);
        json rows = json::array();
        const auto add = [&rows](std::string label, std::string before, std::string next) {
            rows.push_back({ { "label", std::move(label) }, { "before", std::move(before) }, { "after", std::move(next) } });
        };
        add("强化等级", "+" + std::to_string(a_before.enhancementLevel), "+" + std::to_string(after.enhancementLevel));
        auto* weapon = a_item->As<RE::TESObjectWEAP>();
        auto* armor = a_item->As<RE::TESObjectARMO>();
        const auto capacity = InstanceChargeCapacity(a_item, a_extraList);
        switch (a_card.type) {
        case EnhancementCardType::Performance: {
            const auto base = static_cast<std::int64_t>(BasePerformanceValue(a_item));
            add(weapon ? "攻击（基础+本模组）" : "防御（基础+本模组）",
                std::to_string(base + a_before.performanceBonus), std::to_string(base + after.performanceBonus));
            // This extra row exposes the runtime cap separately from the ledger's additive bonus.
            const auto* extraHealth = a_extraList ? a_extraList->GetByType<RE::ExtraHealth>() : nullptr;
            const auto currentHealth = extraHealth && std::isfinite(extraHealth->health) ? (std::max)(0.01F, extraHealth->health) : 1.0F;
            auto baseline = currentHealth;
            if (a_before.performanceBridgeInitialized && std::isfinite(a_before.performanceBaselineHealth) && std::isfinite(a_before.performanceAppliedHealth)) {
                baseline = a_before.performanceBaselineHealth;
                if (std::abs(currentHealth - a_before.performanceAppliedHealth) > 0.001F) baseline += currentHealth - a_before.performanceAppliedHealth;
            }
            if (base > 0) add("锻造倍率（上限 10000）", FixedDecimal(currentHealth, 3) + "×",
                FixedDecimal(std::clamp(std::clamp(baseline, 0.01F, 10000.0F) + static_cast<float>(after.performanceBonus) / BasePerformanceValue(a_item), 0.01F, 10000.0F), 3) + "×");
            break;
        }
        case EnhancementCardType::Weight:
            add("重量", FixedDecimal((std::max)(0.1F, EquipmentWeight(a_item) - a_before.weightReduction), 2),
                FixedDecimal((std::max)(0.1F, EquipmentWeight(a_item) - after.weightReduction), 2));
            break;
        case EnhancementCardType::Speed:
            if (weapon) add("攻速", FixedDecimal(weapon->GetSpeed() * (1.0F + a_before.attackSpeedBonus), 2) + "×",
                FixedDecimal(weapon->GetSpeed() * (1.0F + after.attackSpeedBonus), 2) + "×");
            break;
        case EnhancementCardType::Durability:
            add("耐久 / 上限", FixedDecimal(a_before.current, 1) + " / " + FixedDecimal(a_before.maximum, 1),
                FixedDecimal(after.current, 1) + " / " + FixedDecimal(after.maximum, 1));
            break;
        case EnhancementCardType::Wear: {
            add("耐磨减免", FixedDecimal(a_before.wearReduction * 100.0F, 1) + "%", FixedDecimal(after.wearReduction * 100.0F, 1) + "%");
            const auto base = weapon ? BaseWeaponWear(weapon) : armor ? std::optional<float>(BaseArmorWear(armor)) : std::nullopt;
            if (base) add("每次耐久损耗", FixedDecimal((std::max)(0.1F, *base * (1.0F - a_before.wearReduction)), 2),
                FixedDecimal((std::max)(0.1F, *base * (1.0F - after.wearReduction)), 2));
            break;
        }
        case EnhancementCardType::Enchantment: {
            const auto* enchantment = RE::TESForm::LookupByID<RE::EnchantmentItem>(a_card.enchantmentFormID);
            const auto* current = InstanceEnchantment(a_item, a_extraList);
            add("附魔（整体替换）", current ? EnchantmentLabel(current) + " · " + EnchantmentEffectSummary(current) : "无",
                enchantment ? EnchantmentLabel(enchantment) + " · " + EnchantmentEffectSummary(enchantment) : "候选已失效");
            break;
        }
        case EnhancementCardType::Charge:
            break;
        }
        if (weapon && (a_card.type == EnhancementCardType::Charge || a_card.type == EnhancementCardType::Enchantment)) {
            auto baseline = a_card.type == EnhancementCardType::Enchantment ? a_card.enchantmentCharge : capacity.value_or(1);
            if (a_card.type == EnhancementCardType::Charge && a_before.chargeBridgeInitialized && a_before.chargeBaselineCapacity > 0) {
                baseline = a_before.chargeBaselineCapacity;
                if (capacity && *capacity != a_before.chargeAppliedCapacity) baseline = static_cast<std::uint16_t>(std::clamp<long long>(
                    std::llround(*capacity / (1.0 + static_cast<double>(after.chargeBonus))), 1LL, 65535LL));
            }
            const auto target = std::clamp<long long>(std::llround(baseline * (1.0 + static_cast<double>(after.chargeBonus))), 1LL, 65535LL);
            add("充能容量", capacity ? std::to_string(*capacity) : "无", std::to_string(target));
        }
        return rows;
    }

    bool NavigateEquipmentShortcut(std::uint32_t key, bool shift, bool ctrl, bool alt) {
        if (workshop_potions::active && g_panelVisible && g_prisma && g_view && g_prisma->HasFocus(g_view) && !shift && !ctrl && !alt) {
            const char* name = key == 0xC8 ? "ArrowUp" : key == 0xD0 ? "ArrowDown" : key == 0xCB ? "ArrowLeft" : key == 0xCD ? "ArrowRight" : key == 0x1C ? "Enter" : key == 0x39 ? " " : nullptr;
            if (name) { const auto script = "window.WorkshopPotions?.key(" + json(name).dump() + ");"; g_prisma->Invoke(g_view,script.c_str()); return true; }
        }

        if (g_panelVisible && g_prisma && g_view && g_prisma->HasFocus(g_view) && !shift && !ctrl && !alt && (key == 0xC8 || key == 0xD0)) {
            g_prisma->Invoke(g_view, key == 0xC8 ? "window.DurabilityManager?.navigateEquipment(-1);" : "window.DurabilityManager?.navigateEquipment(1);");
            return true;
        }
        return false;
    }

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
        const auto isStaff = weapon && weapon->IsStaff() && !weapon->IsBound();
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
        const auto panelDisplayName = a_durability.displayNameBridgeInitialized && !a_durability.displayNameBaseline.empty() ?
                                          a_durability.displayNameBaseline :
                                          InstanceDisplayName(a_item, a_extraList);
        auto equipmentItem = json{
            { "id", std::to_string(a_key.baseFormID) + ":" + std::to_string(a_key.uniqueID) },
            { "name", panelDisplayName },
            { "slot", EquipmentType(a_item) },
            { "category", EquipmentCategory(a_item) },
            { "equipped", a_extraList && a_extraList->GetWorn() },
            { "quantity", (std::max)(1, a_quantity) },
            { "current", a_durability.current },
            { "maximum", a_durability.maximum },
            { "enhancementLevel", a_durability.enhancementLevel },
            { "damage", weapon ? static_cast<std::int64_t>(weapon->GetAttackDamage()) + a_durability.performanceBonus : 0 },
            { "armor", armor ? static_cast<std::int64_t>(const_cast<RE::TESObjectARMO*>(armor)->GetArmorRating()) + a_durability.performanceBonus : 0 },
            { "weight", (std::max)(0.1F, EquipmentWeight(a_item) - a_durability.weightReduction) },
            { "attackSpeed", weapon ? (std::min)(weapon->GetSpeed() * 2.0F, weapon->GetSpeed() * (1.0F + a_durability.attackSpeedBonus)) : 0.0F },
            { "wearRateLabel", isStaff ? "每次法杖释放" : isRangedWeapon ? "每次成功射击" : isMeleeWeapon ? "每次普通命中" : armor && armor->IsShield() ? "每次盾牌格挡" : armor ? "每次基础受击并抽中部位" : "尚未启用" },
            { "wearReduction", effectiveWearReduction },
            { "enchantment", enchantment },
            { "enchanted", IsInstanceEnchanted(a_item, a_extraList) },
            { "enchantmentReplaceable", !questItem && !uniqueItem && HasCompatibleEnchantment(a_item, a_extraList) },
            { "quest", questItem },
            { "unique", uniqueItem },
            { "broken", broken },
            { "repairable", repairable },
            { "repairMaterials", RepairMaterialsJson(repairMaterials) }
        };
        if (isStaff || isRangedWeapon || isMeleeWeapon) equipmentItem["wearRate"] = effectiveWeaponWear;
        else if (armor) equipmentItem["wearRate"] = effectiveArmorWear;
        if (armor && !armor->IsShield()) {
            using Slot=RE::BIPED_MODEL::BipedObjectSlot;
            const auto slots=std::to_underlying(armor->GetSlotMask());
            const bool boots=(slots&(std::to_underlying(Slot::kFeet)|std::to_underlying(Slot::kCalves)))!=0;
            const bool body=(slots&std::to_underlying(Slot::kBody))!=0;
            if (boots||body) equipmentItem["movementWearRate"]=(boots?g_settings.movementBootWearPer1000Units:g_settings.movementBodyWearPer1000Units)*(1.0F-effectiveWearReduction);
        }
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

    #include "inventory_recycling.inl"

    void SaveRecyclingHotkey(std::uint32_t key, std::uint32_t safety)
    {
        if (!g_panelVisible || !g_prisma || !g_view || !g_prisma->HasFocus(g_view) || !g_capturingRecyclingHotkey) return;
        if (!recycling::Allowed(key) || (safety != key && !recycling::Modifier(safety))) {
            SendState("请选择字母、F1–F12、Delete、Space 或左右修饰键，最多搭配一个修饰键。"); return;
        }
        if (RecyclingKeyConflicts(key)) {
            g_capturingRecyclingHotkey = false;
            SendState("该主键与 SkyUI 的装备、丢弃或充能操作冲突，请换一个按键。"); return;
        }
        auto settings = g_recyclingSettings; settings.key = key; settings.safety = safety;
        if (!WriteRecyclingSettings(settings)) { SendState("回收配置保存失败，原快捷键保持不变。"); return; }
        g_recyclingSettings = settings;
        g_capturingRecyclingHotkey = false; g_recyclingCapture.Reset(); ResetRecyclingInput();
        SendState("工坊回收快捷键已保存并立即生效，无需 MCM 或保存游戏。");
    }

    bool CaptureRecyclingKey(std::uint32_t key, bool down)
    {
        if (!g_capturingRecyclingHotkey || !g_panelVisible || !g_prisma || !g_view || !g_prisma->HasFocus(g_view)) return false;
        if (key == 0x01 && down) { g_capturingRecyclingHotkey = false; g_recyclingCapture.Reset(); SendState("已取消回收按键录入。"); return true; }
        const auto result = g_recyclingCapture.Feed(key, down);
        if (result.invalid) SendState("不支持该组合，请使用一个按键，或搭配一个 Shift / Ctrl / Alt。");
        else if (result.key) SaveRecyclingHotkey(result.key, result.safety);
        return true;
    }

    [[nodiscard]] json CollectState(std::string_view a_message = {})
    {
        const auto forge = GetForgeContext();
        std::uint32_t refreshes = 0;
        {
            std::scoped_lock lock(g_forgeLock);
            if (g_forgeSelectedItem) {
                if (const auto* draft = g_enhancementDrafts.Find(*g_forgeSelectedItem)) refreshes = draft->refreshes;
            }
        }
        auto* player = RE::PlayerCharacter::GetSingleton();
        return {
            { "version", kPluginVersion },
#ifdef UNIFIED_WORKSHOP
            { "unified", true },
#endif
            { "equipped", CollectInventoryEquipment() },
            { "repairQueue", CollectRepairQueue() },
            { "forge", {
                { "active", forge.active },
                { "enhancementAvailable", CanEnhanceEquipment() },
                { "station", forge.station },
                { "gold", PlayerGoldCount(player) },
                { "refreshCost", CanPreviewEnhancement() ? CardRefreshCost(refreshes) : 0 },
                { "refreshes", refreshes },
                { "cards", CanPreviewEnhancement() ? EnhancementCardsJson() : json::array() }
            } },
            { "settings", {
                { "recyclingHotkey", RecyclingHotkeyState() },
                { "hotkey", { { "key", KeyName(g_settings.hotkey.keyCode) }, { "keyCode", g_settings.hotkey.keyCode }, { "shift", g_settings.hotkey.requireShift }, { "ctrl", g_settings.hotkey.requireCtrl }, { "alt", g_settings.hotkey.requireAlt } } },
                { "lowDurabilityThreshold", g_settings.lowDurabilityThreshold },
                { "uiFontScale", g_settings.uiFontScale },
                { "uiTransparency", g_settings.uiTransparency },
                { "weaponDisplaySeconds", g_settings.weaponDisplaySeconds },
                { "hudRightPercent", g_settings.hudRightPercent },
                { "hudBottomPercent", g_settings.hudBottomPercent },
                { "enableLowDurabilityWarning", g_settings.enableLowDurabilityWarning },
                { "enableWorkshopSounds", g_settings.enableWorkshopSounds },
                { "allowEnchantedItemsToBreak", g_settings.allowEnchantedItemsToBreak }
            } },
#ifdef UNIFIED_WORKSHOP
            { "pageKeyboard", g_prisma && g_prisma->views != nullptr },
#endif
            { "capturingRecyclingHotkey", g_capturingRecyclingHotkey },
            { "capturingHotkey", g_capturingHotkey },
            { "message", a_message }
        };
    }

    void SendState(std::string_view a_message, const json& a_refreshResult)
    {
        if (!g_prisma || !g_view) return;
        auto state = CollectState(a_message);
        if (!a_refreshResult.is_null()) state["refreshResult"] = a_refreshResult;
        const auto script = "window.DurabilityManager && window.DurabilityManager.receiveState(" + state.dump() + ");";
        g_prisma->Invoke(g_view, script.c_str());
    }

    void ClosePanel()
    {
        workshop_potions::Reset();
        g_capturingRecyclingHotkey = false; g_recyclingCapture.Reset();
        if (!g_prisma || !g_view) return;
        g_capturingHotkey = false;
        g_panelVisible = false;
#ifdef UNIFIED_WORKSHOP
        unified_workshop::SetArrowsVisible(false);
#endif
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
        workshop_potions::Reset();
        g_capturingRecyclingHotkey = false; ResetRecyclingInput();
        g_recyclingCapture.Reset();
#ifdef UNIFIED_WORKSHOP
        if (g_prisma && g_prisma->views && g_view) {
            g_prisma->Invoke(g_view, "window.DurabilityManager?.setPanelVisible(false);");
            g_prisma->Unfocus(g_view);
            g_prisma->Hide(g_view);
        }
#endif
        g_capturingHotkey = false;
        ClearEnchantmentCache("load/new-game transition");
        g_panelVisible = false;
        g_hudVisible = false;
        g_equippedHudVisible = false;
        g_gameHudAllowed = false;
        g_clearHudPending = true;
        g_equippedHudPayload.clear();
        ++g_hudSequence;
        g_capturingHotkey = false;
        ClearForgeContext();
        {
            std::scoped_lock lock(g_forgeLock);
            g_enhancementDrafts.Clear();  // A different save may reuse the same instance IDs.
        }
        std::scoped_lock lock(g_durabilityLock);
        ++g_stateEpoch;
        g_pendingBreaks.clear();
    }

    [[nodiscard]] bool CloseFocusedPanel()
    {
        if (!g_prisma || !g_view || !g_prisma->HasFocus(g_view)) return false;
        g_prisma->Invoke(g_view, "window.DurabilityManager?.escape();");
        return true;
    }

    void TogglePanel()
    {
        ResetRecyclingInput();
        if (!g_prisma || !g_view) return;
        if (g_panelVisible) {
            ClosePanel();
            return;
        }
        // A death reload can leave Prisma's focus flag alive after our local
        if (g_prisma->HasAnyActiveFocus() && !g_prisma->HasFocus(g_view)) return;
        // panel state was reset. Normalize it here, safely outside load events.
        if (g_prisma->HasFocus(g_view)) g_prisma->Unfocus(g_view);
        g_panelVisible = true;
        g_prisma->Show(g_view);
        g_prisma->Invoke(g_view, "window.DurabilityManager && window.DurabilityManager.setPanelVisible(true);");
        if (!g_prisma->Focus(g_view, true)) {
            g_panelVisible = false;
            g_prisma->Invoke(g_view, "window.DurabilityManager?.setPanelVisible(false);");
            UpdateViewVisibility();
            logger::warn("Equipment workshop focus request rejected.");
            return;
        }
#ifdef UNIFIED_WORKSHOP
        unified_workshop::SetArrowsVisible(true);
#endif
        SendState();
        logger::info("Durability Manager panel opened through the restored direct Prisma lifecycle.");
    }

    [[nodiscard]] bool CaptureHotkey(const std::uint32_t a_key, const bool a_shift, const bool a_ctrl, const bool a_alt)
    {
        if (!g_capturingHotkey || !g_prisma || !g_view || !g_prisma->HasFocus(g_view)) return false;
        if (a_key == 0x01) {
            g_capturingHotkey = false;
            SendState("已取消快捷键修改。"); return true;
        }
        const auto name = KeyName(a_key);
        if (name.starts_with("Scan ")) {
            SendState("请选择字母、F1–F12 或 Delete，可搭配 Shift / Ctrl / Alt。"); return true;
        }
        const HotkeyConfig binding{a_key, a_shift, a_ctrl, a_alt};
        g_settings.hotkey = binding;
        InputHandler::GetSingleton()->SetHotkey(binding);
        g_capturingHotkey = false;
        WriteConfig(); SendState("快捷键已更新并保存。"); return true;
    }

    void HandleUIActionOnGameThread(const char* a_data)
    {
        try {
            const auto request = json::parse(a_data ? a_data : "{}");
            const auto type = request.value("type", "");
            if (type == "ready") {
                logger::info("Durability Manager web bridge {} is ready.", request.value("version", "<unknown>"));
                g_hudBridgeReady = true;
                g_hudProbeAttempts = 0;
                g_clearHudPending = true;
                g_equippedHudPayload.clear();
                return;
            }
#ifdef UNIFIED_WORKSHOP
            if (type == "captureHotkeyFromPage") {
                if (!g_prisma || !g_prisma->views || !g_panelVisible || !g_prisma->HasFocus(g_view)) return;
                const auto key = ParseKeyCode(request.value("key", ""));
                if (!key) return;
                const bool shift = request.value("shift", false), ctrl = request.value("ctrl", false), alt = request.value("alt", false);
                (void)CaptureHotkey(*key, shift, ctrl, alt);
                return;
            }
#endif
            if (type == "beginRecyclingHotkeyCapture" && g_panelVisible) {
                g_capturingHotkey = false; g_capturingRecyclingHotkey = true; g_recyclingCapture.Reset();
                SendState("请按下回收按键；单独使用 Alt / Ctrl / Shift 时松开即录入，Esc 取消。");
            }
            else if ((type == "setRecyclingEnabled" || type == "setRecyclingStackEnabled") && g_panelVisible) {
                auto settings = g_recyclingSettings;
                if (type == "setRecyclingEnabled") settings.enabled = request.value("enabled", true);
                else settings.stack = request.value("enabled", true);
                if (WriteRecyclingSettings(settings)) { g_recyclingSettings = settings; ResetRecyclingInput(); SendState("回收设置已保存。"); }
                else SendState("回收配置保存失败，原设置保持不变。");
            }
            else if (type == "saveRecyclingHotkey") SaveRecyclingHotkey(request.value("keyCode", 0U), request.value("safetyCode", 0U));
            else if (type == "potionPage" || type == "potionRefresh" || type == "potionUse") {
                if (!g_panelVisible || !g_prisma || !g_view || !g_prisma->HasFocus(g_view)) return;
                if (type == "potionPage") { workshop_potions::active = request.value("active",false); workshop_potions::foodMode = request.value("food",false); ++workshop_potions::token; }
                if (!workshop_potions::active) return;
                std::string message; bool ok = false;
                if (type == "potionUse") {
                    auto result = workshop_potions::Drink(request.at("id").get<RE::FormID>(),request.at("token").get<std::uint64_t>());
                    ok = result.first; message = result.second;
                }
                auto payload = workshop_potions::Snapshot(message,request.value("requestID",std::uint64_t{}),ok);
                const auto script = "window.WorkshopPotions?.receive(" + payload.dump(-1,' ',false,json::error_handler_t::replace) + ");";
                g_prisma->Invoke(g_view,script.c_str());
            }
            else if (type == "close") ClosePanel();
#ifdef UNIFIED_WORKSHOP
            else if (type == "arrows" && g_panelVisible && request.contains("action") && request["action"].is_object()) {
                const auto action = request["action"].dump();
                unified_workshop::ArrowAction(action.c_str());
            }
#endif
            else if (type == "beginHotkeyCapture" && g_panelVisible) {
                g_capturingRecyclingHotkey = false; g_recyclingCapture.Reset();
                g_capturingHotkey = true;
                SendState("请按下新的快捷键组合。");
            } else if (type == "cancelHotkeyCapture") {
                g_capturingRecyclingHotkey = false; g_recyclingCapture.Reset();
                g_capturingHotkey = false;
                SendState("已取消快捷键修改。");
            } else if (type == "saveGeneralSettings") {
                g_settings.uiFontScale = std::clamp(request.value("uiFontScale", g_settings.uiFontScale), 80, 130);
                g_settings.uiTransparency = std::clamp(request.value("uiTransparency", g_settings.uiTransparency), 0, 60);
                g_settings.enableWorkshopSounds = request.value("enableWorkshopSounds", g_settings.enableWorkshopSounds);
                WriteConfig();
                SendState("通用设置已保存。");
            } else if (type == "saveSettings") {
                const auto right = request.value("hudRightPercent", g_settings.hudRightPercent);
                const auto bottom = request.value("hudBottomPercent", g_settings.hudBottomPercent);
                if (!std::isfinite(right) || !std::isfinite(bottom)) throw std::runtime_error("浮窗位置无效");
                g_settings.hudRightPercent = std::clamp(right, 0.0F, 100.0F);
                g_settings.hudBottomPercent = std::clamp(bottom, 0.0F, 100.0F);
                g_settings.lowDurabilityThreshold = std::clamp(request.value("lowDurabilityThreshold", g_settings.lowDurabilityThreshold), 1U, 99U);
                g_settings.weaponDisplaySeconds = std::clamp(request.value("weaponDisplaySeconds", g_settings.weaponDisplaySeconds), 0.5F, 10.0F);
                g_settings.enableLowDurabilityWarning = request.value("enableLowDurabilityWarning", g_settings.enableLowDurabilityWarning);
                g_settings.enableWorkshopSounds = request.value("enableWorkshopSounds", g_settings.enableWorkshopSounds);
                g_settings.allowEnchantedItemsToBreak = request.value("allowEnchantedItemsToBreak", g_settings.allowEnchantedItemsToBreak);
                WriteConfig();
                SendState("配置已保存至 DurabilityManager.ini。");
            } else if (type == "playWorkshopClick") {
                if (g_panelVisible) PlayWorkshopClick();
            } else if (type == "repair") {
                RepairEquipment(request.value("id", ""));
            } else if (type == "selectEquipment") {
                SelectEquipmentForForge(request.value("id", ""));
            } else if (type == "refreshEnhancements") {
                RefreshEnhancementCards(request.value("id", ""), request.value("requestId", ""));
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

    void HandleUIAction(const char* data)
    {
        const std::string copy = data ? data : "{}";
        if (copy.size() > 65536) return;
        std::uint64_t epoch;
        { std::scoped_lock lock(g_durabilityLock); epoch = g_stateEpoch; }
        if (auto* tasks = SKSE::GetTaskInterface()) tasks->AddTask([copy, epoch] {
            { std::scoped_lock lock(g_durabilityLock); if (epoch != g_stateEpoch) return; }
            HandleUIActionOnGameThread(copy.c_str());
        });
    }

    [[nodiscard]] bool WritePersistedString(
        SKSE::SerializationInterface* a_serialization,
        const std::string& a_value)
    {
        if (!a_serialization) return false;
        const auto value = LimitPersistedDisplayName(a_value);
        const auto length = static_cast<std::uint32_t>(value.size());
        return a_serialization->WriteRecordData(length) &&
               (length == 0 || a_serialization->WriteRecordData(value.data(), length));
    }

    [[nodiscard]] bool ReadPersistedString(
        SKSE::SerializationInterface* a_serialization,
        std::string& a_value)
    {
        if (!a_serialization) return false;
        std::uint32_t length = 0;
        if (a_serialization->ReadRecordData(length) != sizeof(length) || length > kMaxPersistedDisplayNameBytes) {
            return false;
        }
        a_value.resize(length);
        return length == 0 || a_serialization->ReadRecordData(a_value.data(), length) == length;
    }

    void SaveState(SKSE::SerializationInterface* a_serialization)
    {
        if (!a_serialization) return;
#ifdef UNIFIED_WORKSHOP
        unified_workshop::SaveArrows(a_serialization);
#endif
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
            const auto displayNameBridgeInitialized = static_cast<std::uint8_t>(durability.displayNameBridgeInitialized);
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
                !a_serialization->WriteRecordData(chargeBridgeInitialized) ||
                !a_serialization->WriteRecordData(displayNameBridgeInitialized) ||
                !WritePersistedString(a_serialization, durability.displayNameBaseline) ||
                !WritePersistedString(a_serialization, durability.displayNameApplied)) {
                logger::warn("Could not finish saving durability state.");
                return;
            }
        }
    }

    void LoadState(SKSE::SerializationInterface* a_serialization)
    {
        if (!a_serialization) return;
#ifdef UNIFIED_WORKSHOP
        unified_workshop::BeginLoadArrows(a_serialization);
#endif
        std::unordered_map<ItemKey, DurabilitySnapshot, ItemKeyHash> restored;
        std::uint32_t type = 0;
        std::uint32_t version = 0;
        std::uint32_t length = 0;
        while (a_serialization->GetNextRecordInfo(type, version, length)) {
#ifdef UNIFIED_WORKSHOP
            if (unified_workshop::LoadArrowRecord(a_serialization, type, version, length)) continue;
#endif
            if (type != kDurabilityRecordType ||
                (version != 1 && version != 2 && version != kDurabilityRecordVersion)) {
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
                if (version >= 3) {
                    std::uint8_t displayNameBridgeInitialized = 0;
                    if (a_serialization->ReadRecordData(displayNameBridgeInitialized) != sizeof(displayNameBridgeInitialized) ||
                        !ReadPersistedString(a_serialization, durability.displayNameBaseline) ||
                        !ReadPersistedString(a_serialization, durability.displayNameApplied)) {
                        logger::warn("Could not finish loading native display-name bridge state.");
                        break;
                    }
                    durability.displayNameBridgeInitialized = displayNameBridgeInitialized != 0;
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
                // Records written before the level-aware comparison keep the engine's quality marker
                // and a stale "+N" inside the baseline; the sync then froze that name at the level it
                // had been captured with. Repair both strings on load, so an existing save recovers
                // without the player doing anything.
                durability.displayNameBaseline = durability::name::CleanStoredBaseline(
                    LimitPersistedDisplayName(std::move(durability.displayNameBaseline)));
                durability.displayNameApplied = durability::name::CleanStoredBaseline(
                    LimitPersistedDisplayName(std::move(durability.displayNameApplied)));
                if (!durability.displayNameBridgeInitialized) {
                    durability.displayNameBaseline.clear();
                    durability.displayNameApplied.clear();
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
            restoredCount = g_durability.size();
        }
        logger::info("Loaded {} durability instance records.", restoredCount);
    }

    void RevertState(SKSE::SerializationInterface*)
    {
        g_environmentWearReady = false;
        g_clearHudPending = true;
#ifdef UNIFIED_WORKSHOP
        unified_workshop::RevertArrows(nullptr);
#endif
        ClearEnchantmentCache("serialization revert");
        {
            std::scoped_lock lock(g_forgeLock);
            g_enhancementDrafts.Clear();
            g_forgeSelectedItem.reset();
        }
        {
            std::scoped_lock lock(g_durabilityLock);
            g_durability.clear();
            g_lowDurabilityWarnings.clear();
            g_pendingBreaks.clear();
            g_nextGeneratedUniqueID = 0x8000U;
            ++g_stateEpoch;
        }
        PreparePlayerRuntimeEffectsForStateChange();
    }

    panel_power::Power g_panelPower("DurabilityManager.esp", [] {
        if (g_prisma && g_view && !g_prisma->HasAnyActiveFocus()) TogglePanel();
    });

    void OnSKSEMessage(SKSE::MessagingInterface::Message* a_message)
    {
#ifdef UNIFIED_WORKSHOP
        unified_workshop::ArrowMessage(a_message);
#endif
        g_panelPower.OnMessage(a_message);
        if (a_message->type == SKSE::MessagingInterface::kPreLoadGame) {
            g_environmentWearReady = false;
            ResetEnvironmentWear();
            ResetViewForLoad();
            PreparePlayerRuntimeEffectsForStateChange();
            logger::info("Durability Manager reset local panel state before loading a save.");
            return;
        }
        if (a_message->type == SKSE::MessagingInterface::kPostLoadGame) {
            ResetEnvironmentWear();
            g_environmentWearReady = a_message->data != nullptr;
            ResetViewForLoad();
            SyncAllRuntimeEffects();
            QueuePlayerRuntimeEffectsSync();
            QueueStoredZeroDurabilityResolutions();
            logger::info("Durability Manager reset local panel state after loading a save.");
            return;
        }
        if (a_message->type == SKSE::MessagingInterface::kNewGame) {
            ResetEnvironmentWear();
            g_environmentWearReady = true;
            ResetViewForLoad();
            PreparePlayerRuntimeEffectsForStateChange();
            QueuePlayerRuntimeEffectsSync();
            logger::info("Durability Manager reset local panel state for a new game.");
            return;
        }
        if (a_message->type != SKSE::MessagingInterface::kDataLoaded) return;
#ifdef UNIFIED_WORKSHOP
        g_prisma = unified_workshop::GetWorkshopUI();
#else
        g_prisma = PRISMA_UI_API::RequestPluginAPI();
#endif
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
#ifdef UNIFIED_WORKSHOP
        unified_workshop::AttachArrows(g_view);
#endif
        g_prisma->Hide(g_view);
        LoadConfig();
        LoadRecyclingSettings();
        if (auto* ui = RE::UI::GetSingleton()) ui->AddEventSink(&g_recyclingMenuSink);
        LoadEnhancementRules();
        BuildEnchantmentPool();
        const auto input = InputHandler::GetSingleton();
        input->SetHotkey(g_settings.hotkey);
#ifdef UNIFIED_WORKSHOP
        input->SetPageInputCallback([] { return g_prisma && g_prisma->views && g_prisma->HasFocus(g_view); });
#endif
        input->SetToggleCallback(TogglePanel);
        input->SetEscapeCallback(CloseFocusedPanel);
        input->SetCaptureCallback(CaptureHotkey);
        input->SetActionCallback(NavigateEquipmentShortcut);
        input->SetRecyclingCaptureCallback(CaptureRecyclingKey);
        input->SetInventoryRecyclingCallback(HandleInventoryRecyclingKey);
        input->RegisterSink();
        StartEquippedHUDUpdates();
        EquipmentEventSink::GetSingleton()->Register();
        logger::info("Durability Manager loaded with the restored direct Prisma lifecycle.");
    }
}

#ifdef UNIFIED_WORKSHOP
void unified_workshop::OpenArrowSection() {
    if (!g_prisma || !g_view) return;
    if (!g_panelVisible) TogglePanel();
    if (g_panelVisible && g_prisma->HasFocus(g_view)) g_prisma->Invoke(g_view, "window.DurabilityManager?.openArrows();");
}
void unified_workshop::CloseEquipment() { ClosePanel(); }
unified_workshop::ArrowCraftFeedback::ArrowCraftFeedback() { PlayWorkshopClick(); }
unified_workshop::ArrowCraftFeedback::~ArrowCraftFeedback() {
    PlayWorkshopSound(success ? "UIEnchantingItemCreate" : "UIMenuCancel");
}
#endif

extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Load(const SKSE::LoadInterface* a_skse)
{
    REL::Module::reset();
    const auto messaging = reinterpret_cast<SKSE::MessagingInterface*>(a_skse->QueryInterface(SKSE::LoadInterface::kMessaging));
    if (!messaging) return false;
    SKSE::Init(a_skse);
#ifdef UNIFIED_WORKSHOP
    const auto pluginDirectory = std::filesystem::path(REL::Module::get().filePath().data()).parent_path() / "Data/SKSE/Plugins";
    if (std::filesystem::exists(pluginDirectory / "DurabilityManager.dll") || std::filesystem::exists(pluginDirectory / "MagicArrows.dll")) {
        logger::critical("EquipmentWorkshop cannot load alongside the standalone DurabilityManager/MagicArrows DLLs. Disable the old MO2 mods.");
        return false;
    }
#endif
    if (const auto serialization = SKSE::GetSerializationInterface()) {
        serialization->SetUniqueID(kSerializationID);
        serialization->SetSaveCallback(SaveState);
        serialization->SetLoadCallback(LoadState);
        serialization->SetRevertCallback(RevertState);
    }
    messaging->RegisterListener("SKSE", OnSKSEMessage);
#ifdef UNIFIED_WORKSHOP
    return unified_workshop::InstallArrows();
#else
    return true;
#endif
}

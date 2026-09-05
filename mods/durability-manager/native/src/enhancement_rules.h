#pragma once

#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <map>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>
#include <nlohmann/json.hpp>

namespace enhancement
{
    inline constexpr std::array<const char*, 7> types{
        "performance", "weight", "speed", "durability", "wear", "charge", "enchantment"
    };
    struct EnchantmentRank
    {
        std::optional<float> power;
        std::optional<std::uint8_t> tier;
    };
    struct Rules
    {
        std::array<std::array<std::array<float, 2>, 4>, 6> ranges{{
            {{{2,3}, {4,5}, {6,8}, {9,10}}},
            {{{1,1.4F}, {1.4F,1.8F}, {1.8F,2.4F}, {2.4F,3}}},
            {{{.01F,.019F}, {.02F,.029F}, {.03F,.039F}, {.04F,.05F}}},
            {{{1,2}, {3,5}, {6,8}, {9,10}}},
            {{{.01F,.03F}, {.04F,.06F}, {.07F,.10F}, {.11F,.15F}}},
            {{{.05F,.10F}, {.11F,.20F}, {.21F,.35F}, {.36F,.50F}}}
        }};
        std::array<std::vector<std::string>, 7> catalysts{{
            {"IngotIron"}, {"LeatherStrips"}, {"IngotQuicksilver"}, {"IngotCorundum"},
            {"IngotDwarven"}, {"SoulGemCommonFilled"}, {"SoulGemGrandFilled", "VoidSalts"}
        }};
        double growth = 1.16;
        double baseGold = 100.0;
        double lateGold = 200.0;
        std::vector<std::string> lateMaterials{"IngotEbony", "DaedraHeart", "DragonBone"};
        std::vector<std::string> allowEnchantments;
        std::vector<std::string> denyEnchantments;
        std::vector<std::string> denyPlugins;
        std::map<std::string, EnchantmentRank> enchantmentRanks;
    };

    // Reject the entire override on malformed input; callers retain defaults.
    inline Rules ParseRules(const nlohmann::json& value)
    {
        if (!value.is_object() || value.at("schemaVersion") != 1) throw std::runtime_error("Expected schemaVersion 1");
        Rules result;
        if (value.contains("ranges")) {
            const auto& ranges = value.at("ranges");
            if (!ranges.is_object()) throw std::runtime_error("ranges must be an object");
            for (std::size_t i = 0; i < result.ranges.size(); ++i) {
                if (!ranges.contains(types[i])) continue;
                const auto& tiers = ranges.at(types[i]);
                if (!tiers.is_array() || tiers.size() != 4) throw std::runtime_error("Expected four tiers");
                for (const auto& pair : tiers) {
                    if (!pair.is_array() || pair.size() != 2) throw std::runtime_error("Expected min/max pair");
                }
                result.ranges[i] = ranges.at(types[i]).get<decltype(result.ranges)::value_type>();
                float previous = 0;
                for (const auto& range : result.ranges[i]) {
                    if (!std::isfinite(range[0]) || !std::isfinite(range[1]) || range[0] <= 0 ||
                        range[0] < previous || range[1] < range[0] || range[1] > 10000) {
                        throw std::runtime_error("Invalid or unordered tier range");
                    }
                    previous = range[1];
                }
            }
        }
        const auto strings = [](const nlohmann::json& input) {
            auto entries = input.get<std::vector<std::string>>();
            if (entries.size() > 4096) throw std::runtime_error("Too many rule entries");
            for (const auto& entry : entries) {
                if (entry.empty() || entry.size() > 256) throw std::runtime_error("Invalid empty/long rule identifier");
            }
            return entries;
        };
        if (value.contains("catalysts")) {
            const auto& catalysts = value.at("catalysts");
            if (!catalysts.is_object()) throw std::runtime_error("catalysts must be an object");
            for (std::size_t i = 0; i < types.size(); ++i) {
                if (!catalysts.contains(types[i])) continue;
                result.catalysts[i] = strings(catalysts.at(types[i]));
                if (result.catalysts[i].empty()) throw std::runtime_error("Each card needs a catalyst");
            }
        }
        if (value.contains("cost")) {
            const auto& cost = value.at("cost");
            if (!cost.is_object()) throw std::runtime_error("cost must be an object");
            result.growth = cost.value("growth", result.growth);
            result.baseGold = cost.value("baseGold", result.baseGold);
            result.lateGold = cost.value("lateGold", result.lateGold);
            if (!std::isfinite(result.growth) || result.growth < 1.01 || result.growth > 1.5 ||
                !std::isfinite(result.baseGold) || result.baseGold < 1 || result.baseGold > 100000 ||
                !std::isfinite(result.lateGold) || result.lateGold < 1 || result.lateGold > 100000) {
                throw std::runtime_error("Invalid cost curve");
            }
            if (cost.contains("lateMaterials")) {
                result.lateMaterials = strings(cost.at("lateMaterials"));
                if (result.lateMaterials.size() != 3) throw std::runtime_error("Expected three late materials");
            }
        }
        if (value.contains("enchantments")) {
            const auto& pool = value.at("enchantments");
            if (!pool.is_object()) throw std::runtime_error("enchantments must be an object");
            if (pool.contains("allow")) result.allowEnchantments = strings(pool.at("allow"));
            if (pool.contains("deny")) result.denyEnchantments = strings(pool.at("deny"));
            if (pool.contains("denyPlugins")) result.denyPlugins = strings(pool.at("denyPlugins"));
            if (pool.contains("ranking")) {
                const auto& ranking = pool.at("ranking");
                if (!ranking.is_object() || ranking.size() > 4096) throw std::runtime_error("Invalid enchantment ranking object");
                for (const auto& [reference, entry] : ranking.items()) {
                    if (reference.empty() || reference.size() > 256 || !entry.is_object() || entry.empty()) {
                        throw std::runtime_error("Invalid enchantment ranking entry");
                    }
                    EnchantmentRank rank;
                    for (const auto& [field, ignored] : entry.items()) {
                        if (field != "power" && field != "tier") throw std::runtime_error("Unknown ranking field");
                    }
                    if (entry.contains("power")) {
                        rank.power = entry.at("power").get<float>();
                        if (!std::isfinite(*rank.power) || *rank.power < 0 || *rank.power > 100000000) throw std::runtime_error("Invalid ranking power");
                    }
                    if (entry.contains("tier")) {
                        const auto tier = entry.at("tier").get<std::string>();
                        static constexpr std::array names{"weak", "standard", "strong", "extreme"};
                        for (std::uint8_t i = 0; i < names.size(); ++i) {
                            if (tier == names[i]) rank.tier = i;
                        }
                        if (!rank.tier) throw std::runtime_error("Unknown ranking tier");
                    }
                    result.enchantmentRanks.emplace(reference, rank);
                }
            }
        }
        return result;
    }

    inline double CostScale(const Rules& rules, std::uint32_t level, double tier)
    {
        // Keep the existing early curve; continue with a quadratic tail rather
        // than freezing costs at +50 or overflowing an unbounded exponential.
        const double extra = level > 50 ? static_cast<double>(level - 50) : 0.0;
        return tier * std::pow(rules.growth, level < 50 ? level : 50) * std::pow(1.0 + extra / 25.0, 2.0);
    }
    inline double GoldFee(const Rules& rules, std::uint32_t level, double tier)
    {
        const double extra = level > 50 ? static_cast<double>(level - 50) : 0.0;
        return rules.baseGold * CostScale(rules, level, tier) + rules.lateGold * extra * extra * tier;
    }
    inline std::optional<std::int32_t> RequiredCount(double value)
    {
        if (!std::isfinite(value) || value <= 0 ||
            std::ceil(value) > static_cast<double>((std::numeric_limits<std::int32_t>::max)())) return std::nullopt;
        return static_cast<std::int32_t>(std::ceil(value));
    }
}

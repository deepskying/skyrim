#include "enhancement_rules.h"
#include "enhancement_drafts.h"
#include "enchantment_ranking.h"
#include "enchantment_cache_tests.h"
#include <fstream>
#include <iostream>

int main(int argc, char** argv)
{
    const auto require = [](bool condition) { if (!condition) throw std::runtime_error("Rule test failed"); };
    try {
        TestEnchantmentCache();
        enhancement::Rules rules;
        // No-magnitude/no-duration flags prevent irrelevant record fields from
        // inflating utility effects; hidden helpers contribute no score.
        require(enhancement::EffectPower(999, 999, 4, true, true, false, false) == 2.0);
        require(enhancement::EffectPower(10, 30, 4, false, false, false, false) == 40.0);
        require(enhancement::EffectPower(999, 999, 999, false, false, true, true) == 0.0);
        require(enhancement::EffectPower(0, 10, 0, true, false, true, false) == 35.0);
        require(enhancement::EffectPower(999, 10, 999, false, false, true, false) == 35.0);
        require(enhancement::EffectPower(0, 60, 0, true, false, true, false) ==
            enhancement::EffectPower(0, 6000, 0, true, false, true, false));
        require(enhancement::MatchesTier(std::nullopt, 0));
        require(enhancement::MatchesTier(std::uint8_t{1}, 1));
        require(!enhancement::MatchesTier(std::uint8_t{1}, 3));
        require(enhancement::CandidateWeight(0, 100, .9, true) == .25);
        require(enhancement::CandidateWeight(0, 100, .9, false) == .02);
        require(enhancement::CandidateWeight(9, 11, .9, false) > enhancement::CandidateWeight(1, 11, .9, false));
        require(enhancement::CandidateWeight(0, 1, .9, true) == 1.0);
        std::mt19937 random(42);
        require(!enhancement::AvailableTier(0, {false,false,false,false}, random));
        for (std::size_t requested = 0; requested < 4; ++requested) {
            require(enhancement::AvailableTier(requested, {false,true,false,false}, random) == 1);
            require(enhancement::AvailableTier(requested, {true,true,true,true}, random) == requested);
        }
        const auto rankRules = enhancement::ParseRules(nlohmann::json::parse(
            R"({"schemaVersion":1,"enchantments":{"ranking":{"Example.esp|123":{"power":0,"tier":"weak"},"Example.esp|456":{"tier":"strong"}}}})"));
        require(rankRules.enchantmentRanks.at("Example.esp|123").power == 0);
        require(rankRules.enchantmentRanks.at("Example.esp|123").tier == 0);
        require(rankRules.enchantmentRanks.at("Example.esp|456").tier == 2);
        require(enhancement::HasRoom(0.0F, 1.0F, .0001F));
        require(!enhancement::HasRoom(1.0F, 1.0F, .0001F));
        require(!enhancement::HasRoom(1.1F, 1.0F, .0001F));
        require(!enhancement::HasRoom(.70F, .70F, .0001F));
        require(enhancement::HasRoom(.69F, .70F, .0001F));
        require(!enhancement::HasRoom(9.9F, 10.0F - .1F, .001F));
        require(enhancement::HasRoom(9.8F, 10.0F - .1F, .001F));
        require(!enhancement::HasRoom(0.0F, 0.0F, .0001F));
        require(!enhancement::HasRoom(std::numeric_limits<float>::quiet_NaN(), 1.0F, .0001F));
        // Two copies of the same base item retain independent offers and fees.
        enhancement::DraftLedger<std::uint64_t, std::string> drafts;
        const std::uint64_t first = (0x1234ULL << 16) | 1;
        const std::uint64_t second = (0x1234ULL << 16) | 2;
        drafts.Store(first, {"a", "b", "c"}, 2);
        drafts.Store(second, {"d", "e", "f"}, 0);
        for (int revisit = 0; revisit < 20; ++revisit) {
            require(drafts.Find(second)->cards[0] == "d");
            require(drafts.Find(first)->cards == std::vector<std::string>{"a", "b", "c"});
            require(enhancement::RefreshCost(drafts.Find(first)->refreshes) == 240);
        }
        drafts.Store(first, {"g", "h", "i"}, 3);  // One paid refresh.
        require(enhancement::RefreshCost(drafts.Find(first)->refreshes) == 320);
        require(drafts.Find(second)->refreshes == 0);
        drafts.Store(first, {"j", "k", "l"}, 0);  // A resolved enhancement starts a new round.
        require(enhancement::RefreshCost(drafts.Find(first)->refreshes) == 80);
        drafts.Erase(first);
        require(!drafts.Find(first) && drafts.Find(second));
        drafts.Clear();  // Load/new-game reset cannot leak state to reused IDs.
        require(!drafts.Find(second));
        require(enhancement::RefreshCost(UINT32_MAX) == 80000);
        for (const auto tier : {.75, 1.0, 1.5, 2.25}) {
            double previous = 0;
            for (std::uint32_t level = 0; level <= 10000; ++level) {
                const auto current = enhancement::CostScale(rules, level, tier);
                require(std::isfinite(current) && current > previous);
                previous = current;
            }
            require(std::abs(enhancement::CostScale(rules, 50, tier) - tier * std::pow(1.16, 50)) < 1e-6);
        }
        require(enhancement::RequiredCount(0.75) == 1);
        require(enhancement::RequiredCount(10000) == 10000);
        require(enhancement::RequiredCount(2147483647.0) == 2147483647);
        require(!enhancement::RequiredCount(2147483647.1));
        require(!enhancement::RequiredCount(-1));
        require(!enhancement::RequiredCount(std::numeric_limits<double>::quiet_NaN()));
        require(!enhancement::RequiredCount(enhancement::CostScale(rules, UINT32_MAX, 2.25)));
        require(enhancement::ParseRules({{"schemaVersion", 1}}).catalysts[6].size() == 2);
        const auto custom = enhancement::ParseRules(nlohmann::json::parse(
            R"({"schemaVersion":1,"cost":{"growth":1.1},"catalysts":{"weight":["Example.esp|123"]},"enchantments":{"deny":["Example.esp|456"]}})"));
        require(custom.growth == 1.1 && custom.catalysts[1][0] == "Example.esp|123" && custom.denyEnchantments[0] == "Example.esp|456");
        const std::vector<std::string> invalid{
            R"({"schemaVersion":1,"enchantments":{"ranking":{"x":{"power":-1}}}})",
            R"({"schemaVersion":1,"enchantments":{"ranking":{"x":{"tier":"legendary"}}}})",
            R"({"schemaVersion":1,"enchantments":{"ranking":{"x":{}}}})",
            R"({"schemaVersion":1,"enchantments":{"ranking":{"x":{"teir":"weak"}}}})",
            R"({"schemaVersion":2})",
            R"({"schemaVersion":1,"ranges":{"weight":[[1,2]]}})",
            R"({"schemaVersion":1,"ranges":{"speed":[[2,1],[3,4],[5,6],[7,8]]}})",
            R"({"schemaVersion":1,"cost":{"growth":0.9}})",
            R"({"schemaVersion":1,"cost":{"lateMaterials":[]}})",
            R"({"schemaVersion":1,"enchantments":{"deny":[null]}})",
            R"({"schemaVersion":1,"catalysts":{"enchantment":[]}})"
        };
        for (const auto& input : invalid) {
            bool rejected = false;
            try { (void)enhancement::ParseRules(nlohmann::json::parse(input)); }
            catch (const std::exception&) { rejected = true; }
            require(rejected);
        }
        if (argc != 2) throw std::runtime_error("Pass packaged rule JSON path");
        std::ifstream file(argv[1]);
        const auto packaged = enhancement::ParseRules(nlohmann::json::parse(file));
        require(packaged.ranges == rules.ranges && packaged.catalysts == rules.catalysts);
        require(packaged.growth == rules.growth && packaged.lateMaterials == rules.lateMaterials);
        std::cout << "Rules tests passed: bounded compatibility cache (5000 queries / 20 scans), utility ranking/tiers, cap boundaries, drafts/fees, cost/configuration validation.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

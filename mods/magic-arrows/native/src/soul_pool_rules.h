#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <random>
#include <vector>
namespace soul_pool_rules {
inline constexpr std::uint32_t record=0x50554F53; // 'SOUP' co-save record under the retained uid
inline constexpr int baseCapacity=20,capacityStep=10,maxPoints=100000;
inline constexpr int minUpgrade=1,maxUpgrade=100,maxTier=100000;
inline constexpr std::size_t maxMaterials=10;
inline constexpr int maxMaterialCount=10;
// Two independent plans per tier, so a roll that lands on a hard-to-find material is
// never a dead end: the player can always take the other plan instead.
inline constexpr std::size_t upgradeOptions=2;
inline constexpr std::array<std::uint32_t,5> filledGems{0x2E4E3,0x2E4E5,0x2E4F3,0x2E4FB,0x2E4FF};
inline constexpr std::uint32_t filledBlackGem=0x2E504;
inline constexpr std::array<std::uint32_t,6> emptyGems{0x2E4E2,0x2E4E4,0x2E4E6,0x2E4F4,0x2E4FC,0x2E500};
// A captured soul is worth its engine soul level; humanoid souls arrive as grand.
inline int SoulValue(int level){return level>=1&&level<=5?level:0;}
// Only used to migrate saves from the fixed +10 system.
inline int LegacyCapacity(int tier){return baseCapacity+capacityStep*std::max(0,tier);}
inline bool Accepts(int points,int capacity,int value){return value>0&&points>=0&&capacity>0&&points+value<=capacity;}
struct Cost{int points=0;int gold=0;};
inline Cost GemCost(int level){
    static const std::array<int,5> gold{60,120,250,500,900};
    if(level<1||level>5)return {};
    return {level,gold[static_cast<std::size_t>(level-1)]};
}
inline Cost BlackGemCost(){return {5,1500};}
inline int Convertible(int points,int gold,Cost cost){
    if(cost.points<=0||cost.gold<=0)return 0;
    return std::max(0,std::min(points/cost.points,gold/cost.gold));
}
// Gold retains the tier formula; every ten gain points add a material kind.
inline int UpgradeGold(int tier){return 500+500*std::max(0,tier);}
inline int UpgradeKinds(int gain){return (std::clamp(gain,minUpgrade,maxUpgrade)+9)/10;}
template<class Random>
inline std::vector<int> RollUpgradeCounts(int kinds,Random& rng){
    std::vector<int> counts;
    for(int i=0;i<std::clamp(kinds,0,static_cast<int>(maxMaterials));++i)
        counts.push_back(std::uniform_int_distribution<int>(1,maxMaterialCount)(rng));
    return counts;
}
inline bool ValidPool(int points,int tier,int absorbed,int gold,int capacity){
    return tier>=0&&tier<=maxTier&&capacity>=baseCapacity+tier&&capacity<=baseCapacity+maxUpgrade*tier&&
        points>=0&&points<=capacity&&absorbed>=0&&gold>=0;
}
}

#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
namespace soul_pool_rules {
inline constexpr std::uint32_t record=0x50554F53; // 'SOUP' co-save record under the retained uid
inline constexpr int baseCapacity=20,capacityStep=10,maxPoints=100000;
inline constexpr std::size_t maxMaterials=5;
// Two independent plans per tier, so a roll that lands on a hard-to-find material is
// never a dead end: the player can always take the other plan instead.
inline constexpr std::size_t upgradeOptions=2;
inline constexpr std::array<std::uint32_t,5> filledGems{0x2E4E3,0x2E4E5,0x2E4F3,0x2E4FB,0x2E4FF};
inline constexpr std::uint32_t filledBlackGem=0x2E504;
inline constexpr std::array<std::uint32_t,6> emptyGems{0x2E4E2,0x2E4E4,0x2E4E6,0x2E4F4,0x2E4FC,0x2E500};
// A captured soul is worth its engine soul level; humanoid souls arrive as grand.
inline int SoulValue(int level){return level>=1&&level<=5?level:0;}
inline int Capacity(int tier){return baseCapacity+capacityStep*std::max(0,tier);}
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
// Costs grow with the tier; the roll only picks which materials and how many.
inline int UpgradeGold(int tier){return 500+500*std::max(0,tier);}
inline int UpgradeKinds(int tier){return 1+std::min(std::max(tier,0),static_cast<int>(maxMaterials)-1);}
inline int UpgradeCount(int tier,int roll){return 2+std::max(0,tier)+static_cast<int>(roll&3);}
inline bool ValidPool(int points,int tier,int absorbed,int gold,std::size_t materials){
    return points>=0&&points<=Capacity(tier)&&tier>=0&&tier<=100&&absorbed>=0&&gold>=0&&materials<=upgradeOptions*maxMaterials;
}
}

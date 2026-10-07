#pragma once
#include <algorithm>
#include <cstdint>
#include <limits>
namespace divine_blood_rules {
inline int Cost(int base,std::uint32_t absorbed){
    const auto numerator=static_cast<std::uint64_t>(std::max(1,base))*(10ULL+absorbed/10);
    return static_cast<int>(std::min<std::uint64_t>((numerator+9)/10,std::numeric_limits<int>::max()));
}
inline int Output(std::int64_t alchemy,int capacity,int souls,int alchemyCost,int soulCost){
    if(alchemy<0||alchemy>capacity||souls<0||alchemyCost<1||soulCost<1)return 0;
    return static_cast<int>(std::min(alchemy/alchemyCost,static_cast<std::int64_t>(souls/soulCost)));
}
}

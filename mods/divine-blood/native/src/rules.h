#pragma once
#include <algorithm>
#include <cstdint>
#include <cmath>
#include <limits>
namespace divine_blood_rules {
// Ingredient effects contribute their own magnitude; duration increases potency
// gradually, at most twofold. Only the strongest applicable effect is counted.
inline int IngredientPoints(float magnitude,std::uint32_t duration,int scale=1,bool noMagnitude=false){
    if(!std::isfinite(magnitude)||(!noMagnitude&&magnitude<=0)||scale<1)return 0;
    const double strength=(noMagnitude?1.0:static_cast<double>(magnitude))*std::sqrt(std::clamp(duration/30.0,1.0,4.0));
    return static_cast<int>(std::ceil(std::min(strength*scale,1000000.0)));
}
inline int Cost(int base,std::uint32_t absorbed){
    const auto numerator=static_cast<std::uint64_t>(std::max(1,base))*(10ULL+absorbed/10);
    return static_cast<int>(std::min<std::uint64_t>((numerator+9)/10,std::numeric_limits<int>::max()));
}
inline int Output(std::int64_t alchemy,int capacity,int souls,int alchemyCost,int soulCost){
    if(alchemy<0||alchemy>capacity||souls<0||alchemyCost<1||soulCost<1)return 0;
    return static_cast<int>(std::min(alchemy/alchemyCost,static_cast<std::int64_t>(souls/soulCost)));
}
}

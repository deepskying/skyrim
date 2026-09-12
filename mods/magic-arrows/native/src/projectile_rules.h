#pragma once
#include <cstdint>
#include <span>
namespace projectile_rules {
inline bool Sustained(std::uint32_t type){return type==4||type==8||type==16;}
struct Candidate{std::uint32_t type=0;bool aimedConcentration=false,conditional=false;};
inline int Choose(std::span<const Candidate> effects){
    int fallback=-1;
    for(std::size_t i=0;i<effects.size();++i){auto e=effects[i];if(!e.aimedConcentration||!Sustained(e.type))continue;if(!e.conditional)return static_cast<int>(i);if(fallback<0)fallback=static_cast<int>(i);}
    return fallback;
}
}

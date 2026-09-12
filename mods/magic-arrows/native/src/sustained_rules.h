#pragma once
#include <cmath>
#include <cstddef>
namespace sustained_rules {
inline constexpr float seconds=3.f;
inline constexpr std::size_t capacity=16;
// Only simulation time advances a cast. Invalid context terminates even while paused.
inline bool Advance(float& remaining,float delta,bool paused,bool valid){
    if(!valid||!std::isfinite(remaining)||remaining<=0)return false;
    if(!paused&&std::isfinite(delta)&&delta>0)remaining-=delta;
    return remaining>0;
}
inline bool NeedsEviction(std::size_t count){return count>=capacity;}
}

#pragma once
#include <algorithm>
#include <cstdint>
namespace follower_rules {
inline std::uint32_t Shots(std::uint32_t requested,std::uint8_t engineCount){
    // SE UseAmmo interprets every negative signed argument as its cached shot count.
    return requested&0x80000000u?engineCount:requested;
}
inline int Missing(int before,int after,std::uint32_t shots){
    before=std::max(0,before);after=std::max(0,after);
    auto required=std::min<std::uint32_t>(shots,static_cast<std::uint32_t>(before));
    auto already=std::max(0,before-after);
    return std::min(after,std::max(0,static_cast<int>(required)-already));
}
}

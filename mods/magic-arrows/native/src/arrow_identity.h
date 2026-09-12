#pragma once
#include <cstdint>
#include <span>
#include <limits>
namespace arrow_identity {
inline constexpr float physicalDamage=8.f;
inline bool Fits(int stored,int added){return stored>=0&&added>0&&stored<=std::numeric_limits<int>::max()-added;}
struct Entry {std::uint32_t ammo=0,spell=0;bool active=false,canonical=false;};
// A saved designation wins over equipment and inventory order. The preferred
// equipped form is considered only during the first migration of a legacy spell.
inline int Find(std::span<const Entry> entries,std::uint32_t spell,std::uint32_t preferred=0){
    if(!spell)return -1;
    int first=-1,equipped=-1;
    for(std::size_t i=0;i<entries.size();++i){const auto& e=entries[i];if(!e.active||!e.ammo||e.spell!=spell)continue;
        if(e.canonical)return static_cast<int>(i);
        if(first<0)first=static_cast<int>(i);
        if(e.ammo==preferred)equipped=static_cast<int>(i);
    }
    return equipped>=0?equipped:first;
}
}

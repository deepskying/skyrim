#pragma once
namespace crafting {
// familyIndex is the arrow family these fixed recipes belong to (fire／ice／shock), which
// also selects the accepted charging effects.
struct Adapter {RE::FormID spell,ammo;const char *family,*arrow,*spellName;int familyIndex,damage,radius,gold,mana,charge;};
inline constexpr std::array<Adapter,3> adapters{{
    {0x1C789,0x900,"fire","火焰箭","火球术",0,40,320,5,12,10},
    {0x2B96C,0xB00,"ice","霜晶箭","冰锥术",1,25,96,4,8,8},
    {0x2DD29,0xB10,"shock","雷棱箭","闪电术",2,25,96,4,8,8},
}};
}

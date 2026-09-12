#pragma once
namespace crafting {
struct Adapter {RE::FormID spell,ammo;const char *family,*arrow,*spellName,*material;RE::ActorValue resist;int damage,radius,gold,mana,charge;};
inline constexpr std::array<Adapter,3> adapters{{
    {0x1C789,0x900,"fire","火焰箭","火球术","抗火／弱火",RE::ActorValue::kResistFire,40,320,5,12,10},
    {0x2B96C,0xB00,"ice","霜晶箭","冰锥术","抗冰／弱冰",RE::ActorValue::kResistFrost,25,96,4,8,8},
    {0x2DD29,0xB10,"shock","雷棱箭","闪电术","抗电／弱电",RE::ActorValue::kResistShock,25,96,4,8,8},
}};
}

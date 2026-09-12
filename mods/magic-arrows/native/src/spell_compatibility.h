#pragma once
#include <cstdint>
#include <span>
namespace spell_compatibility {
// Numeric values follow MagicSystem::Delivery/CastingType and EffectArchetype.
enum class Route { none, aimed, actor, location, area };
enum class Denial { none, casting, delivery, specialEffect, noProjectile, nonCombatTarget, selfOnly, malformed };
struct Effect {int archetype=0,delivery=2;std::uint32_t projectile=0;bool hostile=false;std::uint32_t area=0;};
struct Decision {Route route=Route::none;Denial denial=Denial::none;};
inline bool Special(int a){switch(a){case 17:case 18:case 19:case 20:case 22:case 35:case 36:case 37:case 39:case 45:case 46:return true;default:return false;}}
inline bool MagicProjectile(std::uint32_t type){return type==1||type==2||type==4||type==8||type==16||type==32;}
inline Decision Decide(int casting,int delivery,std::span<const Effect> effects){
    if(casting!=1&&casting!=2)return {Route::none,Denial::casting};
    if(effects.empty()||effects.size()>128)return {Route::none,Denial::malformed};
    bool hostile=false,area=false,projectile=false;
    for(auto e:effects){
        if(e.delivery<0||e.delivery>4||e.archetype<0||e.archetype>46)return {Route::none,Denial::malformed};
        if(Special(e.archetype))return {Route::none,Denial::specialEffect};
        hostile|=e.hostile;area|=e.hostile&&e.area>0;projectile|=MagicProjectile(e.projectile);
    }
    switch(delivery){
    case 2:return projectile?Decision{Route::aimed}:Decision{Route::none,Denial::noProjectile};
    case 1:case 3:return hostile?Decision{Route::actor}:Decision{Route::none,Denial::nonCombatTarget};
    case 4:return hostile||projectile?Decision{Route::location}:Decision{Route::none,Denial::nonCombatTarget};
    case 0:return casting==1&&area?Decision{Route::area}:Decision{Route::none,Denial::selfOnly};
    default:return {Route::none,Denial::delivery};
    }
}
}

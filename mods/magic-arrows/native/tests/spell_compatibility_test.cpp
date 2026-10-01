#include "spell_compatibility.h"
#include <array>
#include <iostream>
#include <stdexcept>
using namespace spell_compatibility;
void check(bool ok){if(!ok)throw std::runtime_error("spell compatibility regression");}
int main(){
    const Effect missile{0,2,1,true,0},script{1,2,0,false,0},jet{5,2,8,true,0};
    check(Decide(1,2,std::array{missile,script}).route==Route::aimed);
    check(Decide(2,2,std::array{jet,script,missile}).route==Route::aimed); // Frostbite / scripted slow
    check(Decide(1,2,std::array{missile,Effect{0,2,4,true,0}}).route==Route::aimed); // independent projectiles
    for(auto type:{1u,2u,4u,8u,16u,32u})check(Decide(1,2,std::array{Effect{0,2,type,true,0}}).route==Route::aimed);
    check(Decide(1,2,std::array{Effect{38,2,1,false,0}}).route==Route::aimed); // Rally is no longer blanket-blocked
    check(Decide(1,3,std::array{Effect{21,3,0,true,0}}).route==Route::actor);
    check(Decide(2,3,std::array{Effect{4,3,0,true,0}}).route==Route::actor);
    check(Decide(1,1,std::array{Effect{0,1,0,true,0}}).route==Route::actor);
    check(Decide(2,3,std::array{Effect{0,3,0,false,0}}).denial==Denial::nonCombatTarget); // Healing Hands
    check(Decide(2,0,std::array{Effect{0,0,0,false,0}}).denial==Denial::selfOnly); // Healing
    check(Decide(1,4,std::array{Effect{40,4,32,true,0}}).route==Route::location);
    check(Decide(1,0,std::array{Effect{0,0,0,true,60}}).route==Route::area);
    check(Decide(1,0,std::array{Effect{1,0,0,false,0}}).denial==Denial::selfOnly);
    check(Decide(2,0,std::array{Effect{0,0,0,true,60}}).denial==Denial::selfOnly);
    for(int a:{17,18,19,20,22,35,36,37,39,45,46})check(Decide(1,2,std::array{missile,Effect{a,2,0,false,0}}).denial==Denial::specialEffect);
    check(Decide(1,2,std::array{script}).denial==Denial::noProjectile);
    check(Decide(1,2,std::array{Effect{0,2,64,true,0}}).denial==Denial::noProjectile);
    check(Decide(0,2,std::array{missile}).denial==Denial::casting);
    check(Decide(1,5,std::array{missile}).denial==Denial::delivery);
    check(Decide(1,2,{}).denial==Denial::malformed);
    check(Decide(1,2,std::array<Effect,129>{}).denial==Denial::malformed);
    check(Decide(1,2,std::array{Effect{99,2,1,true,0}}).denial==Denial::malformed);
    for(int delivery:{0,2,4})check(!CasterAttribution(delivery)); // self, aimed and location keep the marker attributes
    check(CasterAttribution(1)&&CasterAttribution(3));            // touch and target actor credit the shooter
    std::cout<<"PASS: full spell/projectile routes, scripted concentration, hostile targets, area casts, helper caster attribution, healing/summon/cloak exclusions and malformed inputs\n";
}

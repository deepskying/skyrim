#include "material_charge.h"
#include <array>
#include <iostream>
#include <limits>
using namespace crafting;
void require(bool value,int line){if(!value){std::cerr<<"material charge assertion failed at line "<<line<<"\n";throw std::runtime_error("material charge assertion failed");}}
#define check(expression) require((expression),__LINE__)
// 25 magnitude over 60 seconds is 25 * sqrt(2) -> 36 charge at full weight.
constexpr EffectSample effect(bool known,int archetype,int av,float magnitude=25,std::uint32_t duration=60,int secondary=-1){return EffectSample{known,archetype,av,secondary,magnitude,duration};}
int main(){
    // Completed alchemy effects are known; ingredients still require discovery.
    const std::array stamina{effect(false,archetypeValueModifier,26)};
    check(MaterialUnits(MaterialKind::ingredient,stamina,6)==0);
    check(MaterialUnits(MaterialKind::potion,stamina,6)==36);
    check(MaterialUnits(MaterialKind::poison,stamina,6)==36);
    check(MaterialUnits(MaterialKind::food,stamina,6)==0);
    check(MaterialUnits(MaterialKind::unsupported,stamina,6)==0);
    // Damage stamina feeds the three stamina arrows, never the elemental ones.
    for(int family:{6,7,8})check(MaterialUnits(MaterialKind::poison,stamina,family)==36);
    check(MaterialUnits(MaterialKind::poison,stamina,0)==18); // 50% generic fallback
    check(MaterialUnits(MaterialKind::poison,stamina,0,0)==0); // fallback disabled
    check(MaterialUnits(MaterialKind::poison,stamina,0,100)==36); // fallback at full weight
    // Magicka, health and the resistances keep their own families.
    const std::array magicka{effect(true,archetypeValueModifier,25)};
    check(MaterialUnits(MaterialKind::potion,magicka,9)==36&&MaterialUnits(MaterialKind::potion,magicka,11)==36);
    check(MaterialUnits(MaterialKind::potion,magicka,0)==18);
    const std::array resistFire{effect(true,archetypePeakValueModifier,41)};
    check(MaterialUnits(MaterialKind::potion,resistFire,0)==36&&MaterialUnits(MaterialKind::potion,resistFire,1)==18);
    // The destruction power modifier (CACO "intelligence") feeds all three elemental arrows.
    const std::array destruction{effect(true,archetypeValueModifier,149)};
    for(int family:{0,1,2})check(MaterialUnits(MaterialKind::potion,destruction,family)==36);
    check(MaterialUnits(MaterialKind::potion,destruction,11)==18);
    // Recovery rate, speed, carry weight, armour, resist magic and the schools are matched too.
    const std::array magickaRate{effect(true,archetypePeakValueModifier,156)};
    check(MaterialUnits(MaterialKind::poison,magickaRate,11)==36);
    const std::array speed{effect(true,archetypePeakValueModifier,30)};
    check(MaterialUnits(MaterialKind::poison,speed,6)==36&&MaterialUnits(MaterialKind::poison,speed,7)==18);
    const std::array carry{effect(true,archetypePeakValueModifier,32)};
    check(MaterialUnits(MaterialKind::poison,carry,8)==36);
    const std::array resistMagic{effect(true,archetypePeakValueModifier,44)};
    check(MaterialUnits(MaterialKind::potion,resistMagic,11)==36);
    const std::array illusion{effect(true,archetypePeakValueModifier,150)};
    check(MaterialUnits(MaterialKind::potion,illusion,9)==36);
    // Dual effects read the second actor value, so CACO slow-regen still charges stamina.
    const std::array dualRate{effect(true,archetypeDualValueModifier,89,25,60,157)};
    check(MaterialUnits(MaterialKind::poison,dualRate,6)==36);
    check(MaterialUnits(MaterialKind::poison,dualRate,0)==18);
    // Every remaining numeric effect charges through the fallback, utility ones never do.
    const std::array skill{effect(true,archetypePeakValueModifier,16)};
    check(MaterialUnits(MaterialKind::potion,skill,0)==18);
    check(MaterialUnits(MaterialKind::potion,skill,0,100)==36);
    const std::array waterBreathing{effect(true,archetypePeakValueModifier,57)};
    const std::array nightEye{effect(true,archetypePeakValueModifier,55)};
    const std::array cureDisease{effect(true,3,-1)};
    const std::array scripted{effect(true,1,26)};
    const std::array invisibility{effect(true,11,54)};
    for(int family=0;family<12;++family){
        check(MaterialUnits(MaterialKind::potion,waterBreathing,family,100)==0);
        check(MaterialUnits(MaterialKind::potion,nightEye,family,100)==0);
        check(MaterialUnits(MaterialKind::potion,cureDisease,family,100)==0);
        check(MaterialUnits(MaterialKind::potion,scripted,family,100)==0);
        check(MaterialUnits(MaterialKind::potion,invisibility,family,100)==0);
    }
    // The strongest single effect charges the bottle; effects are never summed.
    const std::array strongest{effect(true,archetypeValueModifier,26,10,30),effect(true,archetypeValueModifier,26,50,60),effect(true,archetypeValueModifier,16,100,120)};
    check(MaterialUnits(MaterialKind::potion,strongest,6,0)==71); // strongest matching effect, never the sum
    check(MaterialUnits(MaterialKind::potion,strongest,0,0)==0);  // no family match with the fallback off
    check(MaterialUnits(MaterialKind::potion,strongest,0)==100);  // half of the 200-charge skill effect
    const std::array negative{effect(true,archetypeValueModifier,26,-25,30)};
    check(MaterialUnits(MaterialKind::poison,negative,6)==25);
    const std::array invalid{effect(true,archetypeValueModifier,26,0,30),effect(true,archetypeValueModifier,26,std::numeric_limits<float>::infinity(),30)};
    check(MaterialUnits(MaterialKind::potion,invalid,6)==0);
    const std::array cap{effect(true,archetypeValueModifier,26,500,500)};
    check(MaterialUnits(MaterialKind::potion,cap,6)==1000); // 500 x sqrt(4), no 100 ceiling
    const std::array ceiling{effect(true,archetypeValueModifier,26,6000,500)};
    check(MaterialUnits(MaterialKind::potion,ceiling,6)==materialUnitCap); // 12000 clamped to 10000
    const std::array huge{effect(true,archetypeValueModifier,26,std::numeric_limits<float>::max(),30)};
    check(MaterialUnits(MaterialKind::potion,huge,6)==materialUnitCap); // finite extreme value cannot overflow
    const std::array trivial{effect(true,archetypePeakValueModifier,16,1,1)};
    check(MaterialUnits(MaterialKind::potion,trivial,11,1)==1); // a 1% fallback still rounds up to 1
    const auto mixed=MakeChargedPlan({{1,10,0}},{{1,10,0}},{{203,1,50},{202,2,10}},1000,1000);
    check(mixed.total==7&&mixed.suppliedCharge==70&&mixed.ingredients.size()==2);
    check(mixed.ingredients[0].count==1&&mixed.ingredients[1].count==2);
    const auto scaled=MakeChargedPlan({{1,999,0}},{{1,999,0}},{{203,1,500}},1000000,1000000,{5,12,1});
    check(scaled.total==500&&scaled.requestedTotal==999&&scaled.suppliedCharge==500&&scaled.charge==500);
    // Above the batch ceiling the plan is computed with the ceiling and reports the clamp.
    const auto clamped=MakeChargedPlan({{1,999,0}},{{1,999,0}},{{203,999,10000}},1000000,1000000,{5,12,1});
    check(clamped.total==999&&clamped.suppliedCharge==crafting::batchChargeCap&&clamped.chargeClamped);
    const auto capped=MakeChargedPlan({{1,999,0}},{{1,999,0}},{{203,999,10000}},1000000,1000000,{5,12,250});
    check(capped.total==400&&capped.suppliedCharge==crafting::batchChargeCap&&capped.chargeClamped); // 250 per arrow
    std::cout<<"Family matching, generic fallback, dual actor values, utility exclusions, discovery, caps and mixed charge passed.\n";
}

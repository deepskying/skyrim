#include "material_charge.h"
#include <array>
#include <iostream>
#include <limits>
using namespace crafting;
void check(bool value){if(!value)throw std::runtime_error("material charge assertion failed");}
int main(){
    // Completed alchemy effects are known; ingredients still require discovery.
    const std::array hidden{ChargeEffect{false,true,25,60}};
    check(MaterialUnits(MaterialKind::ingredient,hidden)==0);
    check(MaterialUnits(MaterialKind::potion,hidden)==36);
    check(MaterialUnits(MaterialKind::poison,hidden)==36);
    check(MaterialUnits(MaterialKind::food,hidden)==0);
    check(MaterialUnits(MaterialKind::unsupported,hidden)==0);
    const std::array effects{ChargeEffect{true,true,10,30},ChargeEffect{true,true,50,60},ChargeEffect{true,false,100,120}};
    check(MaterialUnits(MaterialKind::potion,effects)==71); // strongest matching, never sum/unrelated
    check(MaterialUnits(MaterialKind::ingredient,effects)==71);
    const std::array weak{ChargeEffect{true,true,10,30}};
    check(MaterialUnits(MaterialKind::potion,effects)>MaterialUnits(MaterialKind::potion,weak));
    const std::array negative{ChargeEffect{true,true,-25,30}};
    check(MaterialUnits(MaterialKind::poison,negative)==25);
    const std::array invalid{ChargeEffect{true,true,0,30},ChargeEffect{true,true,std::numeric_limits<float>::infinity(),30}};
    check(MaterialUnits(MaterialKind::potion,invalid)==0);
    const std::array cap{ChargeEffect{true,true,500,500}};
    check(MaterialUnits(MaterialKind::potion,cap)==1000); // 500 x sqrt(4), no 100 ceiling
    const std::array ceiling{ChargeEffect{true,true,6000,500}};
    check(MaterialUnits(MaterialKind::potion,ceiling)==materialUnitCap); // 12000 clamped to 10000
    const std::array huge{ChargeEffect{true,true,std::numeric_limits<float>::max(),30}};
    check(MaterialUnits(MaterialKind::potion,huge)==materialUnitCap); // finite extreme value cannot overflow
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
    std::cout<<"Potion and ingredient discovery, matching, potency, protection caps, exclusions and mixed charge passed.\n";
}

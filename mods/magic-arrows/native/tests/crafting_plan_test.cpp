#include "crafting_plan.h"
#include <iostream>
#include <limits>
using namespace crafting;
void check(bool b){if(!b)throw std::runtime_error("assertion failed");}
template<class F>void reject(F f){bool rejected=false;try{f();}catch(const std::runtime_error&){rejected=true;}check(rejected);}
int main(){
    check(EffectCharge(3,30)==3&&EffectCharge(3,60)==5&&EffectCharge(-3,60)==5);
    check(EffectCharge(100,300)==200&&EffectCharge(0,0)==0&&EffectCharge(std::numeric_limits<float>::infinity(),30)==0);
    check(EffectCharge(5000,120)==materialUnitCap&&EffectCharge(std::numeric_limits<float>::max(),30)==materialUnitCap);
    auto elemental=MakePlan({{1,3,0}},{{1,10,0}},{{8,2,16}},12,24,{4,8,8});
    check(elemental.total==3&&elemental.gold==12&&elemental.magicka==24&&elemental.charge==24&&elemental.ingredients[0].count==2);
    reject([&]{MakePlan({{1,1,0}},{{1,10,0}},{{8,1,8}},3,8,{4,8,8});});
    reject([&]{MakePlan({{1,1,0}},{{1,10,0}},{{8,1,8}},4,7,{4,8,8});});
    reject([&]{MakePlan({{1,1,0}},{{1,10,0}},{{8,1,7}},4,8,{4,8,8});});
    reject([&]{MakePlan({{1,1,0}},{{1,10,0}},{{8,1,8}},4,8,{0,8,8});});
    std::vector<Stack> stock{{1,30,0},{2,20,0}};
    auto p=MakePlan({{1,3,0},{2,2,0}},stock,{{8,2,20},{9,9,6}},25,60);
    check(p.total==5&&p.gold==25&&p.magicka==60&&p.charge==50);
    check(p.ingredients.size()==2&&p.ingredients[0].id==8&&p.ingredients[0].count==2&&p.ingredients[1].count==2);
    check(p.bases.size()==2); // distinct bases remain distinct outputs
    reject([&]{MakePlan({{1,31,0}},stock,{{8,100,100}},1000,1000);});
    reject([&]{MakePlan({{1,1,0},{1,1,0}},stock,{{8,100,100}},1000,1000);});
    reject([&]{MakePlan({{1,0,0}},stock,{{8,100,100}},1000,1000);});
    reject([&]{MakePlan({{1,-1,0}},stock,{{8,100,100}},1000,1000);});
    reject([&]{MakePlan({{3,1,0}},stock,{{8,100,100}},1000,1000);});
    reject([&]{MakePlan({{1,1,0}},stock,{{8,100,100}},4,1000);});
    reject([&]{MakePlan({{1,1,0}},stock,{{8,100,100}},1000,11);});
    reject([&]{MakePlan({{1,1,0}},stock,{{8,100,100}},1000,std::numeric_limits<float>::quiet_NaN());});
    reject([&]{MakePlan({{1,1,0}},stock,{{8,1,9}},1000,1000);});
    reject([&]{MakePlan({{1,1,0}},stock,{{8,100,100},{8,100,100}},1000,1000);});
    reject([&]{MakePlan({{1,1000,0}},{{1,1000,0}},{{8,100,100}},100000,100000);}); // one box is capped at 999
    auto large=MakePlan({{1,999,0},{2,999,0}},{{1,999,0},{2,999,0}},{{8,200,100}},100000,100000,{5,12,10},false);
    check(large.total==1998&&large.charge==19980); // batches have no 100 arrow ceiling
    auto unlocked=MakeChargedPlan({{1,600,0}},{{1,600,0}},{{8,600,10}},3000,0,{5,12,10},false);
    check(unlocked.total==600); // queued crafting plans without magicka on hand
    reject([&]{MakeChargedPlan({{1,600,0}},{{1,600,0}},{{8,600,10}},3000,0,{5,12,10});});
    auto exact=MakePlan({{1,1,0}},stock,{{8,1,10}},5,12);check(exact.ingredients[0].count==1);
    // 10 selected bases, explicit basket only funds 7; all four costs use 7.
    auto partial=MakeChargedPlan({{1,10,0}},stock,{{8,7,10}},35,84);
    check(partial.total==7&&partial.requestedTotal==10&&partial.suppliedCharge==70&&partial.charge==70);
    check(partial.bases[0].count==7&&partial.ingredients[0].count==7&&partial.gold==35&&partial.magicka==84);
    auto mixed=MakeChargedPlan({{2,4,0},{1,6,0}},stock,{{9,1,5},{8,2,35}},35,84);
    check(mixed.total==7&&mixed.bases[0].id==2&&mixed.bases[0].count==4&&mixed.bases[1].count==3);
    check(mixed.ingredients[0].id==9&&mixed.ingredients[0].count==1&&mixed.ingredients[1].count==2&&mixed.suppliedCharge==75);
    // Reducing base count does not silently change the explicitly added basket.
    auto excess=MakeChargedPlan({{1,2,0}},stock,{{8,7,10}},10,24);
    check(excess.total==2&&excess.ingredients[0].count==7&&excess.suppliedCharge-excess.charge==50);
    reject([&]{MakeChargedPlan({{1,10,0}},stock,{{8,1,9}},1000,1000);});
    reject([&]{MakeChargedPlan({{1,10,0}},stock,{{8,7,10}},34,84);});
    reject([&]{MakeChargedPlan({{1,10,0}},stock,{{8,7,10}},35,83);});
    reject([&]{MakeChargedPlan({{1,10,0}},stock,{{8,1,10},{8,1,10}},1000,1000);});
    reject([&]{MakeChargedPlan({{1,10,0}},stock,{{8,10001,10}},1000,1000);});
    reject([&]{MakeChargedPlan({{1,10,0},{2,21,0}},stock,{{8,1,10}},1000,1000);});
    std::cout<<"Explicit charge basket: partial 7/10, four resource costs, mixed bases in selection order, excess, insufficient single arrow and stale stock passed.\n";
    std::cout<<"Craft planner: mixed potency, costs, distinct bases, limits, stale stock and malformed requests passed.\n";
}

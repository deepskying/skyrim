#include "runtime_rules.h"
#include <iostream>
#include <limits>
#include <stdexcept>
void check(bool ok){if(!ok)throw std::runtime_error("alchemy cost regression");}
int main(){
    crafting::Costs base{5,12,20};
    for(auto [level,charge]:{std::pair{0.f,20},std::pair{20.f,18},std::pair{50.f,15},std::pair{100.f,10},std::pair{150.f,10},std::pair{-10.f,20}}){auto c=crafting::WithAlchemy(base,level);check(c.charge==charge&&c.mana==12&&c.gold==5);}
    check(crafting::WithAlchemy({5,12,1},100).charge==1);
    check(crafting::WithAlchemy({5,12,11},100).charge==6);
    check(crafting::WithAlchemy(base,std::numeric_limits<float>::quiet_NaN()).charge==20);
    check(runtime_rules::Costs(80,true,100).charge==30);
    const auto c=crafting::WithAlchemy(base,100);
    auto plan=crafting::MakeChargedPlan({{1,10,0}},{{1,10,0}},{{2,5,20}},1000,1000,c);
    check(plan.total==10&&plan.gold==50&&plan.magicka==120&&plan.charge==100&&plan.ingredients[0].count==5);
    auto unskilled=crafting::MakeChargedPlan({{1,10,0}},{{1,10,0}},{{2,5,20}},1000,1000,base);
    check(unskilled.total==5); // same basket, twice the output at Alchemy 100
    for(auto [level,mana]:{std::pair{0.f,40},std::pair{25.f,35},std::pair{50.f,30},std::pair{75.f,25},std::pair{100.f,20},std::pair{150.f,20},std::pair{-10.f,40}}){
        auto discounted=runtime_rules::Costs(80,false,0,level);
        check(discounted.mana==mana&&discounted.charge==20&&discounted.gold==4);
    }
    check(crafting::WithEnchanting({5,11,20},100).mana==6);
    check(crafting::WithEnchanting({5,1,20},100).mana==1);
    check(crafting::WithEnchanting(base,std::numeric_limits<float>::quiet_NaN()).mana==12);
    check(crafting::WithEnchanting(base,std::numeric_limits<float>::infinity()).mana==12);
    auto both=runtime_rules::Costs(80,true,100,100);
    check(both.mana==60&&both.charge==30&&both.gold==12);
    auto discounted=crafting::WithEnchanting(c,100);
    auto affordable=crafting::MakeChargedPlan({{1,10,0}},{{1,10,0}},{{2,5,20}},50,60,discounted);
    check(affordable.total==10&&affordable.magicka==60&&affordable.gold==50&&affordable.charge==100);
    bool rejected=false;
    try{crafting::MakeChargedPlan({{1,10,0}},{{1,10,0}},{{2,5,20}},50,59,discounted);}catch(const std::runtime_error&){rejected=true;}
    check(rejected);
    std::cout<<"PASS: alchemy levels, rounding, caps, invalid skill, sustained cost and actual material plan\n";
}

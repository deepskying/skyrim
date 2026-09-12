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
    std::cout<<"PASS: alchemy levels, rounding, caps, invalid skill, sustained cost and actual material plan\n";
}

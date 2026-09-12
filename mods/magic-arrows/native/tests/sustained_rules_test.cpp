#include "sustained_rules.h"
#include "runtime_rules.h"
#include <iostream>
#include <limits>
void check(bool ok){if(!ok)throw std::runtime_error("sustained lifecycle assertion failed");}
int main(){
    using namespace sustained_rules;
    float t=seconds;
    check(Advance(t,1,false,true)&&t==2);
    check(Advance(t,100,true,true)&&t==2); // UI time is not combat time
    check(Advance(t,0,false,true)&&t==2);
    check(Advance(t,-1,false,true)&&t==2);
    check(Advance(t,std::numeric_limits<float>::quiet_NaN(),false,true)&&t==2);
    check(Advance(t,1.5f,false,true)&&t==.5f);
    check(!Advance(t,.5f,false,true)); // exact expiry, no extra damage interval
    t=seconds;check(!Advance(t,4,false,true)); // long frame expires immediately
    t=seconds;check(!Advance(t,0,true,false)); // load/unload/shooter loss beats pause
    t=std::numeric_limits<float>::infinity();check(!Advance(t,0,true,true));
    check(!NeedsEviction(15)&&NeedsEviction(16)&&NeedsEviction(17));
    auto c=runtime_rules::Costs(10,true);check(c.gold==2&&c.mana==15&&c.charge==8);
    c=runtime_rules::Costs(80,true);check(c.gold==12&&c.mana==120&&c.charge==60);
    c=runtime_rules::Costs(std::numeric_limits<float>::max(),true);check(c.gold==100&&c.mana==500&&c.charge==250);
    auto plan=crafting::MakePlan({{7,2,0}},{{7,2,0}},{{9,6,20}},24,240,runtime_rules::Costs(80,true));
    check(plan.gold==24&&plan.magicka==240&&plan.charge==120&&plan.ingredients[0].count==6);
    std::cout<<"Sustained: simulation/pause timing, exact and long-frame expiry, invalid context, capacity, bounded 3-second costs and transaction totals passed.\n";
}

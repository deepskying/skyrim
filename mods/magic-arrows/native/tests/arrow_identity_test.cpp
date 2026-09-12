#include "arrow_identity.h"
#include "arrow_transfer.h"
#include "crafting_plan.h"
#include <array>
#include <stdexcept>
#include <iostream>
using namespace arrow_identity;
void check(bool b){if(!b)throw std::runtime_error("arrow identity regression");}
int main(){
    std::array<Entry,5> slots{{{0xC00,10,true,false},{0xC01,20,true,false},{0xC02,20,true,false},{0xC03,30,false,true},{0xC04,0,false,false}}};
    check(Find(slots,0)==-1&&Find(slots,40)==-1&&Find(slots,30)==-1);
    // First upgrade: an equipped legacy frost arrow wins over the earlier slot.
    check(Find(slots,20,0xC02)==2);
    slots[2].canonical=true;
    check(Find(slots,20)==2&&Find(slots,20,0xC01)==2);
    auto restored=slots; // saved canonical marker restored into a new session
    check(Find(restored,20)==2);
    restored[2].active=false;check(Find(restored,20)==1); // unavailable source cannot be used
    check(Find(slots,10,0xC02)==0); // another spell never merges just because equipped
    // Multiple selected arrow materials produce a single quantity, even with
    // partial energy. A later batch adds to that same spell identity.
    auto plan=crafting::MakeChargedPlan({{101,5,0},{102,5,0}},{{101,5,0},{102,5,0}},{{201,7,10}},100,100,{1,1,10});
    check(plan.total==7&&plan.bases.size()==2&&plan.bases[0].count==5&&plan.bases[1].count==2);
    check(Fits(7,plan.total)&&7+plan.total==14&&Find(slots,20)==2);
    check(!Fits(std::numeric_limits<int>::max()-10,11));
    check(Fits(std::numeric_limits<int>::max()-10,10));
    check(!Fits(-1,1)&&!Fits(1,0)&&physicalDamage==8.f);
    for(int removalLimit:{0,3,7})for(int deliveryLimit:{0,4,7}){
        int source=7,target=7;
        auto move=[&]{return Transfer([&]{return source;},[&]{return target;},[&](int n){source-=std::min(n,removalLimit);},[&](int n){target+=std::min(n,deliveryLimit);},[&](int n){source+=n;});};
        int moved=move();check(source+target==14&&target==7+moved);
        if(removalLimit<7)check(moved==0&&source==7);
        if(removalLimit==7&&deliveryLimit==7)check(source==0&&target==14&&move()==0);
    }
    int source=7,target=7;
    try{Transfer([&]{return source;},[&]{return target;},[&](int n){source-=n;},[&](int){target+=2;throw std::runtime_error("intercepted add");},[&](int n){source+=n;});check(false);}
    catch(const std::runtime_error&){check(source==5&&target==9);}
    std::cout<<"Inventory transfer: 7 + 7, partial removal/delivery, idempotence and thrown-add recovery preserve quantities.\n";
    std::cout<<"Arrow identity: repeated/mixed-base batches, saved canonical priority, equipped legacy migration, partial output and aggregate overflow passed.\n";
}

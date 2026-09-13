#include "wear_rules.h"
#include <iostream>
#include <stdexcept>
using namespace wear_rules;
void check(bool v){if(!v)throw std::runtime_error("environment wear assertion failed");}
int main(){
    check(Classify(false,true,true,false,false,false)==Impact::magic);
    check(Classify(false,true,false,false,false,false)==Impact::ignore);
    check(Classify(true,true,true,false,false,false)==Impact::ignore);
    check(Classify(false,false,false,true,false,false)==Impact::physical);
    check(Classify(false,false,false,false,false,true)==Impact::physical);
    check(Classify(false,false,false,true,true,false)==Impact::trap);
    check(Classify(false,true,true,false,true,false)==Impact::trap);
    check(Classify(false,true,false,false,true,false)==Impact::ignore);
    check(Classify(false,false,false,false,false,false)==Impact::ignore);
    ImpactThrottle hits;
    check(hits.Accept(1,10,1));check(!hits.Accept(1,10.9,1));check(hits.Accept(2,10.9,1));check(hits.Accept(1,11,1));
    hits.Reset();check(hits.Accept(1,11.1,1));
    Travel travel;
    check(travel.Sample({0,0,0},1,0,true)==0);
    for(int i=1;i<10;++i)check(travel.Sample({float(i*100),0,0},1,i*.3,true)==0);
    check(travel.Sample({1000,0,0},1,3,true)==1);
    check(travel.Sample({1000,0,0},1,3.3,true)==0); // stationary
    check(travel.Sample({9000,0,0},1,3.6,true)==0); // teleport
    check(travel.Sample({9100,0,0},2,3.9,true)==0); // cell transition
    check(travel.Sample({9200,0,0},2,4.2,false)==0); // riding, swimming or paused
    check(travel.Sample({9300,0,0},2,4.5,true)==0); // rebaseline
    check(travel.Sample({9400,0,0},2,8,true)==0); // long interruption
    travel.Reset();check(travel.Sample({0,0,0},2,9,true)==0); // load/equip reset
    check(std::abs(Amount(.02F,1,.5F,0)-.01F)<.00001F);
    check(std::abs(Amount(.005F,1,0,0)-.005F)<.00001F);
    check(Amount(1,0,0)==0);check(Amount(0,1,0)==0);
    check(Amount(.02F,1,0)==.1F); // retain existing combat minimum
    std::cout<<"Hostile/trap classification, continuous-hit limits, travel exclusions and fractional wear passed.\n";
}

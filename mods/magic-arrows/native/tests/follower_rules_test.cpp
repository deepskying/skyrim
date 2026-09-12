#include "follower_rules.h"
#include <stdexcept>
#include <iostream>
#include <limits>
void check(bool ok){if(!ok)throw std::runtime_error("follower ammo assertion failed");}
int main(){
    using namespace follower_rules;
    check(Shots(1,3)==1&&Shots(0,3)==0);
    check(Shots(0xffffffff,3)==3&&Shots(0x80000000,2)==2);
    check(Missing(10,10,1)==1); // infinite-ammo engine path
    check(Missing(10,9,1)==0); // native or other mod already charged
    check(Missing(10,8,1)==0); // never refund another mod's extra consumption
    check(Missing(10,9,3)==2); // only supplement remainder of a burst
    check(Missing(1,1,3)==1&&Missing(1,0,3)==0);
    check(Missing(0,0,1)==0&&Missing(0,1,1)==0);
    check(Missing(10,10,0)==0&&Missing(-1,-1,1)==0);
    check(Missing(10,12,1)==1); // ammo arriving during callback remains valid inventory
    check(Missing(std::numeric_limits<int>::max(),std::numeric_limits<int>::max(),0x7fffffff)==std::numeric_limits<int>::max());
    std::cout<<"Follower ammo: native debit, infinite mode, partial burst, last arrow, zero/sentinel count and overflow passed.\n";
}

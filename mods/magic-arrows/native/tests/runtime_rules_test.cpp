#include "runtime_rules.h"
#include <iostream>
#include <limits>
using namespace runtime_rules;
void check(bool b){if(!b)throw std::runtime_error("assertion failed");}
template<class F>void reject(F f){bool rejected=false;try{f();}catch(const std::runtime_error&){rejected=true;}check(rejected);}
int main(){
    check(Keyword("MagicDamageFire")==0&&Keyword("MagicDamageFrost")==1&&Keyword("MagicDamageShock")==2);
    check(Keyword("MyBloodDamage")==4&&Keyword("ModWindEffect")==6&&Keyword("UnknownEffect")==-1);
    std::array<int,12> scores{};check(Dominant(scores)==11);scores[0]=3;check(Dominant(scores)==0);scores[1]=3;check(Dominant(scores)==11);scores[1]=8;check(Dominant(scores)==1);
    auto c=Costs(80);check(c.gold==4&&c.mana==40&&c.charge==20);
    c=Costs(0);check(c.gold==1&&c.mana==1&&c.charge==1);
    c=Costs(100000);check(c.gold==100&&c.mana==500&&c.charge==250);
    reject([]{Costs(-1);});reject([]{Costs(std::numeric_limits<float>::quiet_NaN());});
    check(Resolvable({true,true,1,1,0}));
    check(!Resolvable({false,false,0,0,0})); // no identity assigned yet
    check(!Resolvable({true,true,0,1,0})); // source spell missing: keep occupied
    check(Resolvable({true,true,1,0,0})); // spell-only identity; legacy base may also be missing
    check(!Resolvable({true,true,1,2,0})); // ambiguous legacy records
    check(!Resolvable({true,false,1,1,0})); // corrupt marker
    check(!Resolvable({true,true,2,1,0})); // ambiguous spell identity
    check(!Resolvable({true,true,1,1,1})); // unrelated record in identity list
    auto plan=crafting::MakePlan({{0xFE001123,3,0}},{{0xFE001123,5,0}},{{91,2,30}},12,120,Costs(80));
    check(plan.total==3&&plan.gold==12&&plan.magicka==120&&plan.charge==60&&plan.ingredients[0].count==2);
    std::cout<<"Runtime rules: fallback/ties, keyword matching, bounded costs, missing/ambiguous save references and third-party base transaction passed.\n";
}

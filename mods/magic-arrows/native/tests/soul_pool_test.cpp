#include "soul_pool_rules.h"
#include <iostream>
#include <stdexcept>
using namespace soul_pool_rules;
void check(bool ok){if(!ok)throw std::runtime_error("soul pool regression");}
int main(){
    check(SoulValue(0)==0&&SoulValue(1)==1&&SoulValue(5)==5&&SoulValue(6)==0);
    check(Capacity(0)==20&&Capacity(3)==50&&Capacity(-1)==20);
    check(Accepts(15,20,5)&&!Accepts(16,20,5)&&!Accepts(20,20,1)&&!Accepts(0,20,0));
    check(GemCost(1).points==1&&GemCost(5).points==5&&GemCost(5).gold==900&&GemCost(0).points==0&&GemCost(6).points==0);
    check(BlackGemCost().points==5&&BlackGemCost().gold==1500);
    check(Convertible(12,50,GemCost(1))==0);     // gold gates the petty gems
    check(Convertible(12,1000,GemCost(1))==12);  // points gate it when gold is plentiful
    check(Convertible(12,600,GemCost(1))==10);   // points allow 12, gold allows 10
    check(Convertible(4,10000,GemCost(5))==0);   // four points never buy a grand gem
    check(Convertible(15,10000,BlackGemCost())==3);
    check(UpgradeGold(0)==500&&UpgradeGold(2)==1500);
    check(maxMaterials==5&&upgradeOptions==2);
    check(UpgradeKinds(0)==1&&UpgradeKinds(1)==2&&UpgradeKinds(2)==3&&UpgradeKinds(3)==4);
    check(UpgradeKinds(4)==5&&UpgradeKinds(9)==5);  // the kind count stops at the pool ceiling
    for(int tier=0;tier<5;++tier)for(int roll=0;roll<8;++roll){const int count=UpgradeCount(tier,roll);check(count>=2&&count<=9);}
    for(int tier=0;tier<8;++tier)check(UpgradeKinds(tier+1)>=UpgradeKinds(tier)&&UpgradeGold(tier+1)>UpgradeGold(tier));
    for(int tier=0;tier<8;++tier)for(int roll=0;roll<4;++roll)check(UpgradeCount(tier+1,roll)>UpgradeCount(tier,roll));
    check(ValidPool(20,0,20,500,1)&&!ValidPool(21,0,21,500,1)&&!ValidPool(0,0,0,500,11));
    check(ValidPool(20,0,20,500,upgradeOptions*maxMaterials));
    check(filledGems.size()==5&&emptyGems.size()==6&&filledGems[0]<filledGems[1]);
    std::cout<<"PASS: soul pool values, capacity, acceptance gate, gem costs, conversion math, upgrade roll ranges and save validation\n";
}

#include "soul_pool_record.h"
#include <iostream>
#include <stdexcept>
using namespace soul_pool_rules;
void check(bool ok){if(!ok)throw std::runtime_error("soul pool regression");}
int main(){
    check(SoulValue(0)==0&&SoulValue(1)==1&&SoulValue(5)==5&&SoulValue(6)==0);
    check(LegacyCapacity(0)==20&&LegacyCapacity(3)==50&&LegacyCapacity(-1)==20);
    check(Accepts(15,20,5)&&!Accepts(16,20,5)&&!Accepts(20,20,1)&&!Accepts(0,20,0));
    check(GemCost(1).points==1&&GemCost(5).points==5&&GemCost(5).gold==900&&GemCost(0).points==0&&GemCost(6).points==0);
    check(BlackGemCost().points==5&&BlackGemCost().gold==1500);
    check(Convertible(12,50,GemCost(1))==0);     // gold gates the petty gems
    check(Convertible(12,1000,GemCost(1))==12);  // points gate it when gold is plentiful
    check(Convertible(12,600,GemCost(1))==10);   // points allow 12, gold allows 10
    check(Convertible(4,10000,GemCost(5))==0);   // four points never buy a grand gem
    check(Convertible(15,10000,BlackGemCost())==3);
    check(UpgradeGold(0)==500&&UpgradeGold(2)==1500);
    check(maxMaterials==10&&maxMaterialCount==10&&upgradeOptions==2);
    for(int gain=1;gain<=100;++gain)check(UpgradeKinds(gain)==(gain+9)/10);
    check(UpgradeKinds(1)==1&&UpgradeKinds(10)==1&&UpgradeKinds(11)==2&&UpgradeKinds(20)==2);
    check(UpgradeKinds(21)==3&&UpgradeKinds(90)==9&&UpgradeKinds(91)==10&&UpgradeKinds(100)==10);
    std::mt19937 rng{12345};
    std::array<bool,11> seen{};
    for(int trial=0;trial<100;++trial)for(int kinds=1;kinds<=10;++kinds){
        const auto counts=RollUpgradeCounts(kinds,rng);
        check(counts.size()==static_cast<std::size_t>(kinds));
        for(int count:counts){check(count>=1&&count<=10);seen[count]=true;}
    }
    for(int count=1;count<=10;++count)check(seen[count]);
    check(RollUpgradeCounts(0,rng).empty());
    check(ValidPool(20,0,20,500,20)&&!ValidPool(21,0,21,500,20));
    check(ValidPool(350,4,500,2500,350)&&!ValidPool(350,4,500,2500,50));
    check(!ValidPool(0,-1,0,0,20)&&!ValidPool(0,maxTier+1,0,0,20));
    check(!ValidPool(0,1,0,0,20)&&!ValidPool(0,1,0,0,121));
    auto resolve=[](std::uint32_t form,std::uint32_t& id){id=form+100;return true;};
    Pool saved;saved.points=150;saved.tier=3;saved.absorbed=500;saved.gold=2000;
    saved.capacity=173;saved.upgradeGain=100;saved.rolled=true;
    for(auto& plan:saved.options)for(int i=0;i<10;++i)plan.materials.push_back({static_cast<std::uint32_t>(i+1),i+1});
    const auto words=EncodePool(saved);
    Pool loaded;
    check(DecodePool(recordVersion,words,loaded,resolve));
    check(loaded.rolled&&loaded.capacity==173&&loaded.upgradeGain==100&&loaded.points==150&&loaded.tier==3&&loaded.absorbed==500);
    for(const auto& plan:loaded.options){check(plan.materials.size()==10);for(int i=0;i<10;++i)check(plan.materials[i].form==static_cast<std::uint32_t>(i+101)&&plan.materials[i].count==saved.options[0].materials[i].count);}
    // Repeated save/load keeps accumulated capacity and the quoted gain, including a failed material resolution.
    check(DecodePool(4,EncodePool(loaded),loaded,resolve)&&loaded.capacity==173&&loaded.upgradeGain==100);
    check(DecodePool(4,words,loaded,[](std::uint32_t,std::uint32_t&){return false;}));
    check(!loaded.rolled&&loaded.capacity==173&&loaded.upgradeGain==100&&loaded.options[0].materials.empty());
    // 2.3.33 keeps its already quoted gain and capacity, replacing materials once.
    Pool old=saved;old.upgradeGain=81;
    for(auto& plan:old.options){plan.materials.resize(5);for(auto& material:plan.materials)material.count=41;}
    const auto previous=EncodePool(old);
    check(previous.size()==29);
    check(DecodePool(3,previous,loaded,resolve));
    check(loaded.capacity==173&&loaded.upgradeGain==81&&loaded.points==150&&loaded.tier==3&&!loaded.rolled&&loaded.options[0].materials.empty());
    // Both previous record layouts retain the old +10 capacity and replace their plans.
    check(DecodePool(1,std::vector<std::uint32_t>{1,45,3,90,2000,1,4},loaded,resolve));
    check(loaded.points==45&&loaded.capacity==50&&loaded.tier==3&&!loaded.rolled&&loaded.upgradeGain==0);
    check(DecodePool(2,std::vector<std::uint32_t>{2,45,3,90,2000,1,1,5,1,2,5},loaded,resolve));
    check(loaded.capacity==50&&loaded.absorbed==90&&!loaded.rolled);
    check(DecodePool(4,EncodePool(Pool{}),loaded,resolve)&&loaded.capacity==20&&!loaded.rolled);
    auto bad=words;bad[5]=149;check(!DecodePool(4,bad,loaded,resolve));
    bad=words;bad[6]=101;check(!DecodePool(4,bad,loaded,resolve));
    bad=words;bad.pop_back();check(DecodePool(4,bad,loaded,resolve)&&!loaded.rolled&&loaded.capacity==173);
    bad=words;bad[9]=0;check(DecodePool(4,bad,loaded,resolve)&&!loaded.rolled);
    bad=words;bad[9]=11;check(DecodePool(4,bad,loaded,resolve)&&!loaded.rolled&&loaded.upgradeGain==100);
    check(!DecodePool(5,words,loaded,resolve)&&!DecodePool(4,std::vector<std::uint32_t>{2,0},loaded,resolve));
    check(filledGems.size()==5&&emptyGems.size()==6&&filledGems[0]<filledGems[1]);
    std::cout<<"PASS: soul pool values, capacity, acceptance gate, gem costs, conversion math, random upgrade costs, v4 save roundtrip and legacy migration\n";
}

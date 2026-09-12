#pragma once
#ifdef min
#undef min
#endif
#ifdef max
#undef max
#endif
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <stdexcept>
#include <unordered_set>
#include <vector>
namespace crafting {
inline int EffectCharge(float magnitude,std::uint32_t duration){
    magnitude=std::abs(magnitude);if(!std::isfinite(magnitude)||magnitude<=0)return 0;
    float value=std::min(magnitude,100.f)*std::sqrt(std::clamp(duration/30.f,1.f,4.f));
    return static_cast<int>(std::ceil(std::min(value,100.f)));
}
struct Stack {std::uint32_t id;int count;int units;};
struct Plan {int total=0,gold=0,charge=0,requestedTotal=0,suppliedCharge=0;float magicka=0;std::vector<Stack> bases,ingredients;};
struct Costs {int gold=5,mana=12,charge=10;};
inline Costs WithAlchemy(Costs costs,float level){
    if(!std::isfinite(level))level=0.f;
    const double multiplier=1.0-std::clamp(static_cast<double>(level),0.0,100.0)*.005;
    costs.charge=std::max(1,static_cast<int>(std::ceil(costs.charge*multiplier)));
    return costs;
}
inline Plan MakePlan(const std::vector<Stack>& requested,const std::vector<Stack>& stock,std::vector<Stack> ingredients,int gold,float magicka,Costs costs={}){
    if(costs.gold<1||costs.gold>1000||costs.mana<1||costs.mana>1000||costs.charge<1||costs.charge>1000)throw std::runtime_error("配方费用无效");
    Plan p;std::unordered_set<std::uint32_t> seen;
    for(auto b:requested){
        if(b.count<=0||b.count>100||!seen.insert(b.id).second)throw std::runtime_error("基材数量无效或重复");
        auto it=std::find_if(stock.begin(),stock.end(),[&](auto s){return s.id==b.id;});
        if(it==stock.end()||it->count<b.count)throw std::runtime_error("基材库存不足或不支持此箭种");
        p.total+=b.count;if(p.total>100)throw std::runtime_error("每次最多制作 100 支");p.bases.push_back(b);
    }
    if(!p.total)throw std::runtime_error("请选择基材和数量");
    p.gold=p.total*costs.gold;p.magicka=static_cast<float>(p.total*costs.mana);p.charge=p.total*costs.charge;
    if(gold<p.gold)throw std::runtime_error("金币不足");
    if(!std::isfinite(magicka)||magicka<p.magicka)throw std::runtime_error("当前魔法值不足");
    std::sort(ingredients.begin(),ingredients.end(),[](auto a,auto b){return a.units==b.units?a.id<b.id:a.units>b.units;});
    seen.clear();int remaining=p.charge;
    for(auto s:ingredients){
        if(!seen.insert(s.id).second||s.count<=0||s.units<=0||s.units>100)throw std::runtime_error("材料数据无效");
        if(remaining>0){int take=std::min(s.count,(remaining+s.units-1)/s.units);p.ingredients.push_back({s.id,take,s.units});remaining-=take*s.units;}
    }
    if(remaining>0)throw std::runtime_error("勾选材料的充能量不足；需已发现对应元素功效的材料");
    return p;
}
// Explicit material quantities are a pending basket, not permission to use all stock.
// Charge caps output; bases are allocated in the order selected by the player.
inline Plan MakeChargedPlan(const std::vector<Stack>& requested,const std::vector<Stack>& stock,const std::vector<Stack>& materials,int gold,float magicka,Costs costs={}){
    if(costs.charge<1||costs.charge>1000||requested.size()>32||materials.size()>128)throw std::runtime_error("充能清单无效");
    int target=0,energy=0;std::unordered_set<std::uint32_t> seen;
    for(auto b:requested){
        if(b.count<1||b.count>100||!seen.insert(b.id).second)throw std::runtime_error("基材数量无效或重复");
        auto it=std::find_if(stock.begin(),stock.end(),[&](auto x){return x.id==b.id;});
        if(it==stock.end()||it->count<b.count)throw std::runtime_error("基材库存变化，请重新选择");
        target+=b.count;if(target>100)throw std::runtime_error("每次最多制作 100 支");
    }
    seen.clear();
    for(auto m:materials){
        if(m.count<1||m.count>10000||m.units<1||m.units>100||!seen.insert(m.id).second)throw std::runtime_error("待消耗材料无效");
        energy+=m.count*m.units;
    }
    if(!target)throw std::runtime_error("请选择基材和数量");
    int total=std::min(target,energy/costs.charge);
    if(!total)throw std::runtime_error("充能不足以制作 1 支箭，请添加材料");
    std::vector<Stack> bases;int remaining=total;
    for(auto b:requested){int take=std::min(remaining,b.count);if(take)bases.push_back({b.id,take,0});remaining-=take;}
    auto p=MakePlan(bases,stock,materials,gold,magicka,costs);
    p.ingredients=materials;p.requestedTotal=target;p.suppliedCharge=energy;return p;
}
}

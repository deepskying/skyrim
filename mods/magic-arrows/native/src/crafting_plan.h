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
// Material potency is linear in effect strength. The caps guard against extreme mod
// values and integer overflow; they are not balance levers.
inline constexpr int materialUnitCap=10000;   // per bottle or ingredient
inline constexpr int batchChargeCap=100000;   // accepted charge of one batch
inline constexpr int inputCountMax=999;       // one quantity box
inline constexpr int baseKindLimit=32,materialKindLimit=128;
inline int EffectCharge(float magnitude,std::uint32_t duration){
    magnitude=std::abs(magnitude);if(!std::isfinite(magnitude)||magnitude<=0)return 0;
    // Clamp in floating point first: casting an out-of-range float to int is undefined.
    const double value=static_cast<double>(magnitude)*std::sqrt(std::clamp(duration/30.0,1.0,4.0));
    if(!std::isfinite(value)||value<=0)return 0;
    return static_cast<int>(std::ceil(std::min(value,static_cast<double>(materialUnitCap))));
}
struct Stack {std::uint32_t id;int count;int units;};
// chargeClamped reports that the basket exceeded the batch ceiling: the surplus is
// neither counted nor consumed, the caller only has to tell the player.
struct Plan {int total=0,gold=0,charge=0,requestedTotal=0;std::int64_t suppliedCharge=0;bool chargeClamped=false;float magicka=0;std::vector<Stack> bases,ingredients;};
struct Costs {int gold=5,mana=12,charge=10;};
inline Costs WithEnchanting(Costs costs,float level){
    if(!std::isfinite(level))level=0.f;
    const double multiplier=1.0-std::clamp(static_cast<double>(level),0.0,100.0)*.005;
    costs.mana=std::max(1,static_cast<int>(std::ceil(costs.mana*multiplier)));
    return costs;
}
inline Costs WithAlchemy(Costs costs,float level){
    if(!std::isfinite(level))level=0.f;
    const double multiplier=1.0-std::clamp(static_cast<double>(level),0.0,100.0)*.005;
    costs.charge=std::max(1,static_cast<int>(std::ceil(costs.charge*multiplier)));
    return costs;
}
// The queued crafting path locks gold, bases and charge up front and spends magicka one
// arrow at a time, so it plans without the magicka check. Manual crafting keeps it.
inline Plan MakePlan(const std::vector<Stack>& requested,const std::vector<Stack>& stock,std::vector<Stack> ingredients,int gold,float magicka,Costs costs={},bool requireMagicka=true){
    if(costs.gold<1||costs.gold>1000||costs.mana<1||costs.mana>1000||costs.charge<1||costs.charge>1000)throw std::runtime_error("配方费用无效");
    Plan p;std::unordered_set<std::uint32_t> seen;
    for(auto b:requested){
        if(b.count<=0||b.count>inputCountMax||!seen.insert(b.id).second)throw std::runtime_error("基材数量必须为 1–999 的整数");
        auto it=std::find_if(stock.begin(),stock.end(),[&](auto s){return s.id==b.id;});
        if(it==stock.end()||it->count<b.count)throw std::runtime_error("基材库存不足或不支持此箭种");
        p.total+=b.count;p.bases.push_back(b);
    }
    if(!p.total)throw std::runtime_error("请选择基材和数量");
    p.gold=p.total*costs.gold;p.magicka=static_cast<float>(p.total*costs.mana);p.charge=p.total*costs.charge;
    if(gold<p.gold)throw std::runtime_error("金币不足");
    if(requireMagicka&&(!std::isfinite(magicka)||magicka<p.magicka))throw std::runtime_error("当前魔法值不足");
    std::sort(ingredients.begin(),ingredients.end(),[](auto a,auto b){return a.units==b.units?a.id<b.id:a.units>b.units;});
    seen.clear();int remaining=p.charge;
    for(auto s:ingredients){
        if(!seen.insert(s.id).second||s.count<=0||s.count>inputCountMax||s.units<=0||s.units>materialUnitCap)throw std::runtime_error("材料数据无效");
        if(remaining>0){int take=std::min(s.count,(remaining+s.units-1)/s.units);p.ingredients.push_back({s.id,take,s.units});remaining-=take*s.units;}
    }
    if(remaining>0)throw std::runtime_error("勾选材料的充能量不足；需已发现对应元素功效的材料");
    return p;
}
// Explicit material quantities are a pending basket, not permission to use all stock.
// Charge caps output; bases are allocated in the order selected by the player.
inline Plan MakeChargedPlan(const std::vector<Stack>& requested,const std::vector<Stack>& stock,const std::vector<Stack>& materials,int gold,float magicka,Costs costs={},bool requireMagicka=true){
    if(costs.charge<1||costs.charge>1000||requested.size()>baseKindLimit||materials.size()>materialKindLimit)throw std::runtime_error("充能清单无效");
    int target=0;std::int64_t energy=0;std::unordered_set<std::uint32_t> seen;
    for(auto b:requested){
        if(b.count<1||b.count>inputCountMax||!seen.insert(b.id).second)throw std::runtime_error("基材数量必须为 1–999 的整数");
        auto it=std::find_if(stock.begin(),stock.end(),[&](auto x){return x.id==b.id;});
        if(it==stock.end()||it->count<b.count)throw std::runtime_error("基材库存变化，请重新选择");
        target+=b.count;
    }
    seen.clear();
    for(auto m:materials){
        if(m.count<1||m.count>inputCountMax||m.units<1||m.units>materialUnitCap||!seen.insert(m.id).second)throw std::runtime_error("待消耗材料无效");
        energy+=m.count*m.units;
    }
    if(!target)throw std::runtime_error("请选择基材和数量");
    // Above the batch ceiling the plan is computed with the ceiling; extra material stays
    // in the inventory instead of being spent or rejected.
    const std::int64_t accepted=std::min<std::int64_t>(energy,batchChargeCap);
    const int total=static_cast<int>(std::min<std::int64_t>(target,accepted/costs.charge));
    if(!total)throw std::runtime_error("充能不足以制作 1 支箭，请添加材料");
    std::vector<Stack> bases;int remaining=total;
    for(auto b:requested){int take=std::min(remaining,b.count);if(take)bases.push_back({b.id,take,0});remaining-=take;}
    auto p=MakePlan(bases,stock,materials,gold,magicka,costs,requireMagicka);
    // The selected basket is still spent as a whole, matching manual crafting; only the
    // computed charge is capped and reported so the caller can warn the player.
    p.ingredients=materials;p.requestedTotal=target;p.suppliedCharge=accepted;p.chargeClamped=energy>batchChargeCap;return p;
}
}

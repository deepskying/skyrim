#pragma once
#include "crafting_plan.h"
#include <map>
#include <limits>
namespace normal_crafting {
using crafting::Stack;
struct Plan {int batches=0,total=0;std::vector<Stack> ingredients;};
inline Plan MakePlan(int batches,int yield,const std::vector<Stack>& recipe,const std::vector<Stack>& stock){
    if(batches<1||batches>100||yield<1||yield>1000||recipe.empty()||recipe.size()>128)throw std::runtime_error("配方或批次数量无效");
    Plan p{batches,batches*yield,{}};
    if(p.total>1000)throw std::runtime_error("每次最多制作 1000 支普通箭");
    std::map<std::uint32_t,std::int64_t> totals;
    for(auto s:recipe){if(!s.id||s.count<=0)throw std::runtime_error("配方材料无效");totals[s.id]+=std::int64_t(s.count)*batches;}
    for(auto [id,count]:totals){
        if(count>std::numeric_limits<int>::max())throw std::runtime_error("材料数量超出范围");
        auto it=std::find_if(stock.begin(),stock.end(),[&](auto s){return s.id==id;});
        if(it==stock.end()||it->count<count)throw std::runtime_error("普通箭配方材料不足");
        p.ingredients.push_back({id,static_cast<int>(count),0});
    }
    return p;
}
}

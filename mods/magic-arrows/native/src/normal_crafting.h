#pragma once
#include "normal_plan.h"
namespace normal_crafting {
using json=nlohmann::json;
inline std::vector<RE::BGSConstructibleObject*> catalog;
inline std::unordered_map<RE::FormID,std::string> audit;
inline json quote=nullptr;
inline std::uint64_t serial=0;
struct Request {RE::FormID recipe=0;int batches=0;};
inline std::optional<Request> pending;
inline void Reset(){pending.reset();quote=nullptr;++serial;}
inline bool Normal(RE::TESAmmo* a){
    if(!a||a->IsBolt()||!a->GetPlayable())return false;
    auto* p=a->GetRuntimeData().data.projectile;
    return p&&!p->data.explosionType;
}
inline void Init(){
    catalog.clear();Reset();auto* d=RE::TESDataHandler::GetSingleton();if(!d)return;
    for(auto* r:d->GetFormArray<RE::BGSConstructibleObject>())
        if(r&&!r->IsDeleted()&&!r->IsIgnored()&&r->createdItem&&Normal(r->createdItem->As<RE::TESAmmo>())&&r->benchKeyword&&std::string_view(r->benchKeyword->GetFormEditorID())=="CraftingSmithingForge")catalog.push_back(r);
    logger::info("Normal arrow forge recipes indexed: {}",catalog.size());
}
inline std::string Unsupported(RE::BGSConstructibleObject* r){
    if(!r||r->IsDeleted()||r->IsIgnored()||!r->createdItem||!Normal(r->createdItem->As<RE::TESAmmo>()))return "不是可用的普通箭配方";
    if(!r->data.numConstructed||r->data.numConstructed>1000||!r->requiredItems.numContainerObjects||r->requiredItems.numContainerObjects>128)return "不支持空材料或异常产出的配方";
    std::unordered_set<RE::TESConditionItem*> visited;
    for(auto* c=r->conditions.head;c;c=c->next){
        if(visited.size()>=128||!visited.insert(c).second)return "配方条件链无效";
        auto& d=c->data;
        if(d.object!=RE::CONDITIONITEMOBJECT::kSelf||d.flags.usesAliases||d.flags.usePackData||d.flags.swapTarget)return "配方依赖工作台、目标或任务别名，须在原工作台制作";
        using F=RE::FUNCTION_DATA::FunctionID;
        switch(d.functionData.function.get()){
        case F::kHasPerk:case F::kGetItemCount:case F::kGetActorValue:case F::kGetBaseActorValue:
        case F::kGetGlobalValue:case F::kGetIsRace:case F::kGetIsID:case F::kGetLevel:
        case F::kGetQuestCompleted:case F::kGetStage:case F::kGetStageDone:break;
        default:return "包含尚未适配的条件，须在原工作台制作";
        }
    }
    for(std::uint32_t i=0;i<r->requiredItems.numContainerObjects;++i){
        auto* x=r->requiredItems.containerObjects[i];
        if(!x||!x->obj||x->count<=0||x->obj==r->createdItem)return "配方材料无效或循环使用成品";
        if(!x->obj->As<RE::TESObjectMISC>()&&!x->obj->As<RE::IngredientItem>()&&!Normal(x->obj->As<RE::TESAmmo>()))return "特殊物品材料须在原工作台使用";
    }
    return {};
}
inline RE::BGSConstructibleObject* Find(RE::FormID id){for(auto* r:catalog)if(r->GetFormID()==id)return r;return nullptr;}
inline auto Stock(RE::PlayerCharacter* p){return p->GetInventory();}
inline int Available(const RE::TESObjectREFR::InventoryItemMap& inv,RE::TESBoundObject* item){
    auto it=inv.find(item);if(it==inv.end()||!it->second.second||it->second.second->IsQuestObject()||it->second.second->IsEnchanted())return 0;
    return std::max(0,it->second.first);
}
inline std::vector<Stack> Ingredients(RE::BGSConstructibleObject* r){
    std::vector<Stack> result;
    for(std::uint32_t i=0;i<r->requiredItems.numContainerObjects;++i){auto* x=r->requiredItems.containerObjects[i];result.push_back({x->obj->GetFormID(),x->count,0});}
    return result;
}
inline bool ConditionsMet(RE::BGSConstructibleObject* r,RE::PlayerCharacter* p){
    return p&&r&&(!r->conditions.head||r->conditions.IsTrue(p,p));
}
inline json Conditions(RE::BGSConstructibleObject* r,RE::PlayerCharacter* p){
    json rows=json::array();using F=RE::FUNCTION_DATA::FunctionID;
    for(auto* c=r->conditions.head;c;c=c->next){
        auto& d=c->data;auto f=d.functionData.function.get();std::string name;
        switch(f){
        case F::kHasPerk:name="天赋："+crafting::Name(static_cast<RE::TESForm*>(d.functionData.params[0]));break;
        case F::kGetItemCount:name="物品条件："+crafting::Name(static_cast<RE::TESForm*>(d.functionData.params[0]));break;
        case F::kGetGlobalValue:name="全局条件";break;
        case F::kGetActorValue:case F::kGetBaseActorValue:name="技能／属性条件";break;
        case F::kGetLevel:name="等级条件";break;
        case F::kGetQuestCompleted:case F::kGetStage:case F::kGetStageDone:name="任务："+crafting::Name(static_cast<RE::TESForm*>(d.functionData.params[0]));break;
        default:name="种族／角色条件";break;
        }
        RE::ConditionCheckParams params(p,p);
        rows.push_back({{"name",name},{"met",c->IsTrue(params)},{"orNext",bool(d.flags.isOR)},{"function",static_cast<int>(f)}});
    }
    return rows;
}
inline Plan Evaluate(RE::PlayerCharacter* p,RE::BGSConstructibleObject* r,int batches){
    auto reason=Unsupported(r);if(!reason.empty())throw std::runtime_error(reason);
    if(!ConditionsMet(r,p))throw std::runtime_error("尚未满足该配方条件，请查看具体条件列表");
    auto inv=Stock(p);std::vector<Stack> stock;
    for(auto& [obj,v]:inv)if(obj)stock.push_back({obj->GetFormID(),Available(inv,obj),0});
    auto plan=MakePlan(batches,r->data.numConstructed,Ingredients(r),stock);
    if(crafting::Count(p,r->createdItem->As<RE::TESAmmo>())>std::numeric_limits<int>::max()-plan.total)throw std::runtime_error("成品库存数量超出范围");
    return plan;
}
inline json Rows(RE::PlayerCharacter* p){
    json rows=json::array();auto inv=Stock(p);
    for(auto* r:catalog){
        auto reason=Unsupported(r);json items=json::array(),conditions=json::array();int maxBatches=0;
        if(reason.empty()){
            std::map<RE::FormID,std::int64_t> totals;
            for(auto s:Ingredients(r))totals[s.id]+=s.count;
            maxBatches=std::min(100,1000/static_cast<int>(r->data.numConstructed));
            for(auto [id,need]:totals){auto* item=RE::TESForm::LookupByID<RE::TESBoundObject>(id);int have=Available(inv,item);
                items.push_back({{"id",id},{"name",crafting::Name(item)},{"need",need},{"have",have}});
                maxBatches=std::min(maxBatches,static_cast<int>(have/need));
            }
            conditions=Conditions(r,p);
            if(!ConditionsMet(r,p))reason="尚未满足配方条件，请查看下方条件列表";
            else if(!maxBatches)reason="材料不足（任务物品不计入可用库存）";
        }
        auto* file=r->GetFile(0);
        rows.push_back({{"id",r->GetFormID()},{"name",crafting::Name(r->createdItem)},{"yield",r->data.numConstructed},{"ingredients",items},{"conditions",conditions},{"maxBatches",reason.empty()?maxBatches:0},{"craftable",reason.empty()},{"reason",reason},{"source",file?std::string(file->GetFilename()):"运行时配方"}});
        auto snapshot=rows.back().dump();if(audit[r->GetFormID()]!=snapshot){audit[r->GetFormID()]=snapshot;logger::info("Normal recipe: {}",snapshot);}
    }
    return rows;
}
inline void Quote(RE::PlayerCharacter* p,const json& q){
    Reset();if(!q.at("batches").is_number_integer()||q.at("batches")<1||q.at("batches")>100)throw std::runtime_error("批次数量必须为整数");
    Request request{q.at("recipe").get<RE::FormID>(),q.at("batches").get<int>()};auto* r=Find(request.recipe);
    auto plan=Evaluate(p,r,request.batches);json items=json::array();
    for(auto s:plan.ingredients)items.push_back({{"id",s.id},{"name",crafting::Name(RE::TESForm::LookupByID(s.id))},{"count",s.count}});
    quote={{"token",serial},{"recipe",request.recipe},{"batches",request.batches},{"output",r->createdItem->GetFormID()},{"name",crafting::Name(r->createdItem)},{"total",plan.total},{"ingredients",items}};pending=request;
}
inline void Commit(RE::PlayerCharacter* p,std::uint64_t token){
    if(!pending||quote.is_null()||token!=serial)throw std::runtime_error("报价已失效，请重新计算");
    auto request=*pending;auto old=quote;Reset();auto* r=Find(request.recipe);auto plan=Evaluate(p,r,request.batches);
    if(plan.total!=old["total"]||r->createdItem->GetFormID()!=old["output"]||plan.ingredients.size()!=old["ingredients"].size())throw std::runtime_error("配方变化，请重新计算");
    for(std::size_t i=0;i<plan.ingredients.size();++i)if(plan.ingredients[i].id!=old["ingredients"][i]["id"]||plan.ingredients[i].count!=old["ingredients"][i]["count"])throw std::runtime_error("材料变化，请重新计算");
    std::vector<Stack> removed;int added=0;auto* output=r->createdItem->As<RE::TESAmmo>();
    try{
        for(auto s:plan.ingredients){auto* item=RE::TESForm::LookupByID<RE::TESBoundObject>(s.id);auto inv=Stock(p);
            if(Available(inv,item)<s.count)throw std::runtime_error("库存变化，交易取消");
            int before=crafting::Count(p,item);p->RemoveItem(item,s.count,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
            int delta=before-crafting::Count(p,item);if(delta>0)removed.push_back({s.id,delta,0});
            if(delta!=s.count)throw std::runtime_error("资源扣除异常，已尝试恢复");
        }
        int before=crafting::Count(p,output);p->AddObjectToContainer(output,nullptr,plan.total,nullptr);added=std::max(0,crafting::Count(p,output)-before);
        if(added!=plan.total)throw std::runtime_error("成品添加异常，已尝试恢复");
    }catch(...){
        if(added)p->RemoveItem(output,added,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
        for(auto s:removed)p->AddObjectToContainer(RE::TESForm::LookupByID<RE::TESBoundObject>(s.id),nullptr,s.count,nullptr);
        throw;
    }
    logger::info("Crafted normal arrows recipe={:08X} batches={} output={:08X} count={}",request.recipe,request.batches,output->GetFormID(),plan.total);
}
}

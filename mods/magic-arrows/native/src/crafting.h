#pragma once
#include "crafting_plan.h"
#include "material_charge.h"
#include "spell_adapters.h"
#include "arrow_identity.h"
#include <unordered_map>
namespace crafting {
using json=nlohmann::json;
constexpr std::array<RE::FormID,8> baseIDs{0x1397d,0x1397f,0x139bb,0x139bc,0x139bd,0x139be,0x139bf,0x139c0};
inline RE::SpellItem* Spell(const Adapter& a){auto* d=RE::TESDataHandler::GetSingleton();return d?d->LookupForm<RE::SpellItem>(a.spell,"Skyrim.esm"):nullptr;}
inline RE::SpellItem* Fireball(){return Spell(adapters[0]);}
inline const Adapter* ForSpell(RE::SpellItem* spell){if(spell)for(const auto& a:adapters)if(Spell(a)==spell)return &a;return nullptr;}
inline RE::TESAmmo* Output(int i,const Adapter& a=adapters[0]){if(i<0||i>=8)return nullptr;auto* d=RE::TESDataHandler::GetSingleton();return d?d->LookupForm<RE::TESAmmo>(a.ammo+i,"MagicArrows.esp"):nullptr;}
inline int Index(RE::FormID id){for(int i=0;i<8;++i)if(baseIDs[i]==id)return i;return -1;}
inline std::unordered_map<RE::TESAmmo*,const Adapter*> ammoAdapters;
inline const Adapter* ForAmmo(RE::TESAmmo* ammo){auto it=ammoAdapters.find(ammo);return it==ammoAdapters.end()?nullptr:it->second;}
inline bool IsOutput(RE::TESAmmo* a){return ForAmmo(a)!=nullptr;}
inline float Alchemy(RE::PlayerCharacter* p){return p?p->AsActorValueOwner()->GetBaseActorValue(RE::ActorValue::kAlchemy):0.f;}
inline float Enchanting(RE::PlayerCharacter* p){return p?p->AsActorValueOwner()->GetBaseActorValue(RE::ActorValue::kEnchanting):0.f;}
inline Costs RecipeCosts(const Adapter& a,RE::PlayerCharacter* p){return WithEnchanting(WithAlchemy({a.gold,a.mana,a.charge},Alchemy(p)),Enchanting(p));}
inline json Info(const Adapter& a,RE::PlayerCharacter* p=nullptr){auto costs=RecipeCosts(a,p);return {{"family",a.family},{"material",a.material},{"damage",a.damage},{"radius",a.radius},{"gold",a.gold},{"mana",costs.mana},{"charge",costs.charge},{"baseCharge",a.charge}};}
inline std::string Name(RE::TESForm* f){return f&&f->GetName()?f->GetName():"未命名";}
inline MaterialKind Kind(RE::TESBoundObject* item){
    if(!item)return MaterialKind::unsupported;
    if(item->As<RE::IngredientItem>())return MaterialKind::ingredient;
    if(auto* potion=item->As<RE::AlchemyItem>())return potion->IsFood()?MaterialKind::food:potion->IsPoison()?MaterialKind::poison:MaterialKind::potion;
    return MaterialKind::unsupported;
}
inline const char* KindName(RE::TESBoundObject* item){
    switch(Kind(item)){case MaterialKind::ingredient:return "ingredient";case MaterialKind::potion:return "potion";case MaterialKind::poison:return "poison";default:return "unsupported";}
}
inline int Units(RE::TESBoundObject* item,RE::ActorValue resist=RE::ActorValue::kResistFire){
    const auto kind=Kind(item);
    if(kind!=MaterialKind::ingredient&&kind!=MaterialKind::potion&&kind!=MaterialKind::poison)return 0;
    auto* ingredient=item->As<RE::IngredientItem>();
    auto* magic=ingredient?static_cast<RE::MagicItem*>(ingredient):static_cast<RE::MagicItem*>(item->As<RE::AlchemyItem>());
    std::vector<ChargeEffect> effects;
    for(std::uint32_t i=0;i<magic->effects.size()&&(!ingredient||i<4);++i){
        auto* e=magic->effects[i];if(!e||!e->baseEffect)continue;
        auto* effect=e->baseEffect;auto a=effect->GetArchetype();
        const bool matching=effect->data.primaryAV==resist&&(a==RE::EffectArchetype::kValueModifier||a==RE::EffectArchetype::kPeakValueModifier);
        effects.push_back({!ingredient||bool(ingredient->gamedata.knownEffectFlags&(1u<<i)),matching,e->effectItem.magnitude,e->effectItem.duration});
    }
    return MaterialUnits(kind,effects);
}
inline int Count(RE::PlayerCharacter* p,RE::TESBoundObject* item){auto inv=p->GetInventory();auto it=inv.find(item);return it==inv.end()?0:std::max(0,it->second.first);}
inline void Sync(){
    ammoAdapters.clear();
    for(const auto& a:adapters)for(int i=0;i<8;++i){auto* base=RE::TESForm::LookupByID<RE::TESAmmo>(baseIDs[i]);auto* out=Output(i,a);if(!base||!out)continue;
        ammoAdapters.emplace(out,&a);
        out->GetRuntimeData().data.damage=arrow_identity::physicalDamage;
        out->fullName=(std::string(a.arrow)+"·"+a.spellName).c_str();
    }
}
struct Request {RE::FormID spell=0;std::vector<Stack> bases;std::vector<Stack> materials;};
inline std::vector<Stack> ReadMaterials(const json& rows){
    if(!rows.is_array()||rows.size()>materialKindLimit)throw std::runtime_error("材料清单无效");
    std::vector<Stack> result;
    for(auto& row:rows){if(!row.at("count").is_number_integer()||row.at("count")<1||row.at("count")>inputCountMax)throw std::runtime_error("材料数量必须为 1–999 的整数");result.push_back({row.at("id").get<RE::FormID>(),row.at("count").get<int>(),0});}
    return result;
}
inline Plan Evaluate(RE::PlayerCharacter* p,const Request& request){
    auto* a=ForSpell(RE::TESForm::LookupByID<RE::SpellItem>(request.spell));
    if(!p||!a||!p->HasSpell(Spell(*a)))throw std::runtime_error("需要先掌握已适配的法术");
    std::vector<Stack> stock,ingredients;
    for(int i=0;i<8;++i){auto* b=RE::TESForm::LookupByID<RE::TESAmmo>(baseIDs[i]);if(b&&Output(i,*a))stock.push_back({b->GetFormID(),Count(p,b),0});}
    auto inventory=p->GetInventory();
    std::unordered_set<RE::FormID> seen;
    for(auto selected:request.materials){auto id=selected.id;
        if(!seen.insert(id).second)throw std::runtime_error("材料选择重复");
        auto* ingredient=RE::TESForm::LookupByID<RE::TESBoundObject>(id);int units=Units(ingredient,a->resist);
        auto found=inventory.find(ingredient);
        if(units<=0||selected.count<1||found==inventory.end()||!found->second.second||found->second.second->IsQuestObject()||found->second.first<selected.count)throw std::runtime_error("充能材料不足、受任务保护或没有适用功效");
        ingredients.push_back({id,selected.count,units});
    }
    // Planning never requires magicka on hand: queued orders pay it one arrow at a time,
    // and manual commit re-checks the current value before spending anything.
    auto plan=MakeChargedPlan(request.bases,stock,ingredients,Count(p,RE::TESForm::LookupByID<RE::TESBoundObject>(0xf)),p->AsActorValueOwner()->GetActorValue(RE::ActorValue::kMagicka),RecipeCosts(*a,p),false);
    if(!arrow_identity::Fits(Count(p,Output(0,*a)),plan.total))throw std::runtime_error("成品库存数量超限");return plan;
}
inline std::optional<Request> pending;inline json quote=nullptr;inline std::uint64_t serial=0;
inline void Reset(){pending.reset();quote=nullptr;++serial;}
inline void Quote(RE::PlayerCharacter* p,const json& q){
    Reset();Request request;request.spell=q.at("spell").get<RE::FormID>();
    auto* a=ForSpell(RE::TESForm::LookupByID<RE::SpellItem>(request.spell));if(!a)throw std::runtime_error("该法术尚未适配");
    if(q.at("bases").size()>8||q.at("materials").size()>materialKindLimit)throw std::runtime_error("选择数量过多");
    for(auto& b:q.at("bases")){if(!b.at("count").is_number_integer()||b.at("count")<1||b.at("count")>inputCountMax)throw std::runtime_error("数量必须为 1–999 的整数");request.bases.push_back({b.at("id").get<RE::FormID>(),b.at("count").get<int>(),0});}
    request.materials=ReadMaterials(q.at("materials"));auto p1=Evaluate(p,request);
    json items=json::array(),outputs=json::array(),bases=json::array();
    for(auto x:p1.bases)bases.push_back({{"id",x.id},{"count",x.count}});
    for(auto x:p1.ingredients)items.push_back({{"id",x.id},{"name",Name(RE::TESForm::LookupByID(x.id))},{"count",x.count},{"units",x.units}});
    outputs.push_back({{"id",Output(0,*a)->GetFormID()},{"name",Name(Output(0,*a))},{"count",p1.total}});
    quote={{"selection",{{"spell",q.at("spell")},{"bases",q.at("bases")},{"materials",q.at("materials")}}},{"requestedTotal",p1.requestedTotal},{"suppliedCharge",p1.suppliedCharge},{"token",serial},{"gold",p1.gold},{"magicka",p1.magicka},{"charge",p1.charge},{"ingredients",items},{"outputs",outputs},{"bases",bases},{"total",p1.total}};pending=std::move(request);
}
inline void Commit(RE::PlayerCharacter* p,std::uint64_t token){
    if(!pending||quote.is_null()||token!=serial)throw std::runtime_error("报价已失效，请重新计算");
    auto request=*pending;auto old=quote;Reset(); // consume before any mutation; duplicate clicks cannot charge again
    auto plan=Evaluate(p,request);
    auto* a=ForSpell(RE::TESForm::LookupByID<RE::SpellItem>(request.spell));
    if(plan.total!=old["total"]||plan.gold!=old["gold"]||plan.magicka!=old["magicka"]||plan.charge!=old["charge"]||plan.ingredients.size()!=old["ingredients"].size())throw std::runtime_error("材料变化，请重新计算");
    for(std::size_t i=0;i<plan.ingredients.size();++i){auto s=plan.ingredients[i];auto q=old["ingredients"][i];if(s.id!=q["id"]||s.count!=q["count"]||s.units!=q["units"])throw std::runtime_error("材料变化，请重新计算");}
    std::vector<Stack> required=plan.bases;required.insert(required.end(),plan.ingredients.begin(),plan.ingredients.end());required.push_back({0xf,plan.gold,0});
    std::vector<Stack> removed,added;float manaRemoved=0;
    try{
        for(auto s:required){auto* item=RE::TESForm::LookupByID<RE::TESBoundObject>(s.id);int before=Count(p,item);
            if(before<s.count)throw std::runtime_error("库存变化，交易取消");
            p->RemoveItem(item,s.count,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
            int delta=before-Count(p,item);if(delta>0)removed.push_back({s.id,delta,0});
            if(delta!=s.count)throw std::runtime_error("资源扣除异常，已尝试恢复");
        }
        auto* av=p->AsActorValueOwner();float before=av->GetActorValue(RE::ActorValue::kMagicka);
        if(before<plan.magicka)throw std::runtime_error("魔法值变化，交易取消");
        av->RestoreActorValue(RE::ACTOR_VALUE_MODIFIER::kDamage,RE::ActorValue::kMagicka,-plan.magicka);
        manaRemoved=std::max(0.f,before-av->GetActorValue(RE::ActorValue::kMagicka));
        if(std::abs(manaRemoved-plan.magicka)>.1f)throw std::runtime_error("魔法值扣除异常，已尝试恢复");
        auto* out=Output(0,*a);int beforeCount=Count(p,out);p->AddObjectToContainer(out,nullptr,plan.total,nullptr);
        int delta=Count(p,out)-beforeCount;if(delta>0)added.push_back({out->GetFormID(),delta,0});
        if(delta!=plan.total)throw std::runtime_error("成品添加异常，已尝试恢复");
    }catch(...){
        for(auto s:added)p->RemoveItem(RE::TESForm::LookupByID<RE::TESBoundObject>(s.id),s.count,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
        for(auto s:removed)p->AddObjectToContainer(RE::TESForm::LookupByID<RE::TESBoundObject>(s.id),nullptr,s.count,nullptr);
        if(manaRemoved>0)p->AsActorValueOwner()->RestoreActorValue(RE::ACTOR_VALUE_MODIFIER::kDamage,RE::ActorValue::kMagicka,manaRemoved);
        throw;
    }
    logger::info("Crafted {} arrows spell={:08X}; gold {}, magicka {}, material kinds {}",plan.total,request.spell,plan.gold,plan.magicka,plan.ingredients.size());
}
}

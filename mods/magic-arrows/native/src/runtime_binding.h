#pragma once
#include "runtime_rules.h"
#include "spell_compatibility.h"
#include "prototype_catalog.h"
#include "arrow_identity.h"
#include "arrow_transfer.h"
#ifdef AddForm
#undef AddForm
#endif
namespace runtime_binding {
using json=nlohmann::json;using crafting::Stack;using crafting::Plan;
constexpr int capacity=256;
struct Binding {RE::TESAmmo* ammo=nullptr;RE::BGSListForm* refs=nullptr;RE::SpellItem* spell=nullptr;RE::TESAmmo* base=nullptr;int family=11;bool occupied=false,active=false,canonical=false;};
inline std::array<Binding,capacity> slots{};
inline std::unordered_map<RE::FormID,int> slotIDs;
inline RE::TESObjectSTAT* canonicalMarker=nullptr;
inline bool initialized=false,ready=false,hookReady=false,sustainedReady=false;
inline std::atomic<std::uint64_t> generation{0};
inline const std::array<const char*,12> names{"火焰箭","霜晶箭","雷棱箭","蛇牙箭","嗜血箭","圣辉箭","旋翼箭","碧波箭","岩锥箭","影镰箭","星魂箭","奥术箭"};
// Family material names and the accepted actor values live in crafting::material_charge so
// the standalone panel, the unified workshop and the queue all share one rule set.
inline int Index(RE::TESAmmo* a){if(!a)return -1;auto it=slotIDs.find(a->GetFormID());return it==slotIDs.end()?-1:it->second;}
inline const Binding* Bound(RE::TESAmmo* a){int i=Index(a);return ready&&i>=0&&slots[i].active?&slots[i]:nullptr;}
inline bool Base(RE::TESAmmo* a){if(!a||!a->GetPlayable()||a->IsBolt()||a->IsDeleted()||Index(a)>=0||!a->GetFile(0))return false;auto* p=a->GetRuntimeData().data.projectile;return p&&!p->data.explosionType;}
inline bool Sustained(RE::SpellItem* s){return s&&s->GetCastingType()==RE::MagicSystem::CastingType::kConcentration;}
inline RE::BGSProjectile* PrimaryProjectile(RE::SpellItem* s){
    // Only used for the impact offset. The native caster releases the whole spell.
    RE::BGSProjectile* fallback=nullptr;if(!s)return nullptr;
    for(auto* effect:s->effects){auto* e=effect?effect->baseEffect:nullptr;auto* p=e?e->data.projectileBase:nullptr;
        if(!p||!spell_compatibility::MagicProjectile(static_cast<std::uint32_t>(p->data.types.get())))continue;
        if(!effect->conditions.head&&!e->conditions.head)return p;if(!fallback)fallback=p;
    }
    return fallback;
}
inline spell_compatibility::Decision Compatibility(RE::SpellItem* s){
    using namespace spell_compatibility;
    if(!s||s->effects.empty()||s->effects.size()>128)return {Route::none,Denial::malformed};
    std::array<spell_compatibility::Effect,128> effects{};std::size_t i=0;
    for(auto* effect:s->effects){
        auto* e=effect?effect->baseEffect:nullptr;
        if(!e||e->IsDeleted()||!std::isfinite(effect->effectItem.magnitude))return {Route::none,Denial::malformed};
        effects[i++]={static_cast<int>(e->GetArchetype()),static_cast<int>(e->data.delivery),e->data.projectileBase?static_cast<std::uint32_t>(e->data.projectileBase->data.types.get()):0,e->data.flags.any(RE::EffectSetting::EffectSettingData::Flag::kHostile),e->data.flags.any(RE::EffectSetting::EffectSettingData::Flag::kNoArea)?0u:effect->effectItem.area};
    }
    return Decide(static_cast<int>(s->GetCastingType()),static_cast<int>(s->GetDelivery()),std::span(effects.data(),i));
}
inline const char* RouteName(RE::SpellItem* s){using R=spell_compatibility::Route;switch(Compatibility(s).route){case R::aimed:return "aimed";case R::actor:return "actor";case R::location:return "location";case R::area:return "area";default:return "none";}}
inline std::string Unsupported(RE::SpellItem* s){
    if(!s||s->IsDeleted()||!s->GetFile(0)||s->GetSpellType()!=RE::MagicSystem::SpellType::kSpell)return "不是可保存来源的普通法术";
    if(!sustainedReady)return "命中点施放组件未就绪，请检查模组版本";
    using D=spell_compatibility::Denial;
    switch(Compatibility(s).denial){
    case D::none:return {};
    case D::casting:return "仅支持瞬发或持续释放的普通法术";
    case D::specialEffect:return "包含斗篷、召唤、变身、念动或装备类效果，尚无对应箭矢玩法";
    case D::noProjectile:return "瞄准法术没有可由命中点释放的魔法投射物";
    case D::nonCombatTarget:return "治疗或非敌对目标辅助法术暂不制作攻击箭矢";
    case D::selfOnly:return "自身增益或持续自身效果不能转为落点攻击；仅支持敌对的瞬发范围效果";
    case D::malformed:return "存在缺失、异常或过多的法术效果";
    default:return "未知施放目标类型";
    }
}
inline int Classify(RE::SpellItem* s){
    std::array<int,12> score{};if(!s)return 11;
    for(auto* effect:s->effects){if(!effect||!effect->baseEffect)continue;auto* e=effect->baseEffect;
        using A=RE::ActorValue;
        switch(e->data.resistVariable){case A::kResistFire:score[0]+=3;break;case A::kResistFrost:score[1]+=3;break;case A::kResistShock:score[2]+=3;break;case A::kPoisonResist:score[3]+=3;break;default:break;}
        if(e->GetArchetype()==RE::EffectArchetype::kAbsorb&&e->data.primaryAV==A::kHealth)score[4]+=2;
        if(e->GetArchetype()==RE::EffectArchetype::kSoulTrap)score[10]+=3;
        for(std::uint32_t i=0;i<e->numKeywords;++i)if(e->keywords&&e->keywords[i]){int f=runtime_rules::Keyword(e->keywords[i]->GetFormEditorID());if(f>=0)score[f]+=5;}
    }
    return runtime_rules::Dominant(score);
}
inline json Info(RE::SpellItem* s,RE::PlayerCharacter* p){int f=Classify(s);auto c=runtime_rules::Costs(s->CalculateMagickaCost(p),Sustained(s),crafting::Alchemy(p),crafting::Enchanting(p));return {{"runtime",true},{"castRoute",RouteName(s)},{"releaseMode",Sustained(s)?"sustained":"instant"},{"seconds",Sustained(s)?sustained_rules::seconds:0.f},{"family",runtime_rules::families[f]},{"material",crafting::FamilyMaterialName(f)},{"gold",c.gold},{"mana",c.mana},{"charge",c.charge}};}
inline std::string OutputName(RE::SpellItem* s,RE::TESAmmo*){return std::string(names[Classify(s)])+"·"+crafting::Name(s);}
inline void Neutral(Binding& b){
    b.spell=nullptr;b.base=nullptr;b.active=false;b.canonical=false;b.family=11;
    if(b.ammo){b.ammo->fullName="封存箭〔绑定待恢复〕";b.ammo->SetModel("magicarrows\\arcane.nif");auto& d=b.ammo->GetRuntimeData().data;d.damage=0;d.flags.set(RE::AMMO_DATA::Flag::kNonPlayable);}
}
inline void Refresh(Binding& b){
    Neutral(b);b.occupied=false;if(!b.ammo||!b.refs)return;
    b.occupied=!b.refs->forms.empty()||(b.refs->scriptAddedTempForms&&!b.refs->scriptAddedTempForms->empty());
    if(!b.occupied)return;
    b.ammo->fullName="封存箭〔来源缺失或不兼容〕";
    runtime_rules::SavedRefs state{true,b.refs->HasForm(b.ammo),0,0,0};
    b.refs->ForEachForm([&](RE::TESForm* f){if(f==b.ammo)return RE::BSContainer::ForEachResult::kContinue;
        if(f==canonicalMarker){b.canonical=true;return RE::BSContainer::ForEachResult::kContinue;}
        if(auto* s=f->As<RE::SpellItem>()){b.spell=s;++state.spellCount;}else if(auto* a=f->As<RE::TESAmmo>()){b.base=a;++state.baseCount;}else ++state.otherCount;
        return RE::BSContainer::ForEachResult::kContinue;});
    if(!runtime_rules::Resolvable(state)||!Unsupported(b.spell).empty())return;
    b.family=Classify(b.spell);auto* d=RE::TESDataHandler::GetSingleton();RE::TESAmmo* proto=nullptr;
    for(auto e:prototypes::entries)if(std::string_view(e.family)==runtime_rules::families[b.family])proto=d->LookupForm<RE::TESAmmo>(e.id,"MagicArrows.esp");
    if(!proto)return;
    b.ammo->SetModel(proto->GetModel());b.ammo->fullName=OutputName(b.spell,b.base).c_str();
    auto& data=b.ammo->GetRuntimeData().data;data.projectile=proto->GetRuntimeData().data.projectile;data.damage=arrow_identity::physicalDamage;data.flags=RE::AMMO_DATA::Flag::kNonBolt;b.active=true;
    logger::info("Binding ready ammo={:08X} spell={:08X} legacyBase={:08X} canonical={} damage={} family={}",b.ammo->GetFormID(),b.spell->GetFormID(),b.base?b.base->GetFormID():0,b.canonical,data.damage,runtime_rules::families[b.family]);
}
inline void Init(){
    auto* d=RE::TESDataHandler::GetSingleton();slotIDs.clear();initialized=d!=nullptr;
    canonicalMarker=d?d->LookupForm<RE::TESObjectSTAT>(0xE00,"MagicArrows.esp"):nullptr;if(!canonicalMarker)initialized=false;
    logger::info("Spell compatibility: full native casting; aimed, hostile actor/location and instant hostile area routes");
    for(int i=0;i<capacity;++i){auto& b=slots[i];b.ammo=d?d->LookupForm<RE::TESAmmo>(0xC00+i,"MagicArrows.esp"):nullptr;b.refs=d?d->LookupForm<RE::BGSListForm>(0xD00+i,"MagicArrows.esp"):nullptr;
        if(b.ammo)slotIDs.emplace(b.ammo->GetFormID(),i);if(!b.ammo||!b.refs)initialized=false;Neutral(b);}
}
inline void Suspend(){ready=false;++generation;for(auto& b:slots)Neutral(b);}
inline void Restore(){if(!initialized)return;++generation;for(auto& b:slots)Refresh(b);ready=hookReady;logger::info("Runtime bindings restored: {} occupied; ready={}",std::count_if(slots.begin(),slots.end(),[](auto& b){return b.occupied;}),ready);}
inline Binding* Existing(RE::SpellItem* s,RE::FormID preferred=0){
    std::array<arrow_identity::Entry,capacity> entries{};
    for(int i=0;i<capacity;++i){auto& b=slots[i];entries[i]={b.ammo?b.ammo->GetFormID():0,b.spell?b.spell->GetFormID():0,b.active,b.canonical};}
    int i=arrow_identity::Find(entries,s?s->GetFormID():0,preferred);return i>=0?&slots[i]:nullptr;
}
inline void Designate(Binding& b){
    // The existing helper base Form is an explicit persistent canonical marker.
    // Legacy source references and all old AMMO identities remain intact.
    if(!b.canonical){b.refs->AddForm(canonicalMarker);b.refs->AddChange(RE::BGSListForm::ChangeFlags::kAddedForm);b.canonical=b.refs->HasForm(canonicalMarker);}
    if(!b.canonical)throw std::runtime_error("箭矢合并身份保存失败");
}
inline bool PlainEntry(const RE::InventoryEntryData& entry){
    if(entry.IsQuestObject()||entry.IsEnchanted()||entry.IsWorn())return false;
    if(entry.extraLists)for(auto* list:*entry.extraLists)if(list)for(auto& extra:*list)if(extra.GetType()!=RE::ExtraDataType::kCount)return false;
    return true;
}
inline void MergeInventory(RE::PlayerCharacter* p){
    if(!ready||!p)return;
    auto inventory=p->GetInventory();auto* worn=p->GetCurrentAmmo();
    for(auto& b:slots)if(b.active){auto* canonical=Existing(b.spell,worn?worn->GetFormID():0);if(canonical)Designate(*canonical);}
    for(auto& [object,value]:inventory){auto* source=object?object->As<RE::TESAmmo>():nullptr;auto* binding=Bound(source);
        if(!binding||value.first<=0||!value.second)continue;
        auto* target=Existing(binding->spell);if(!target||target->ammo==source)continue;
        // Never replace equipment or strip meaningful per-item data while merging.
        if(source==worn||!PlainEntry(*value.second))continue;
        const int moved=arrow_identity::Transfer([&]{return crafting::Count(p,source);},[&]{return crafting::Count(p,target->ammo);},
            [&](int n){p->RemoveItem(source,n,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);},
            [&](int n){p->AddObjectToContainer(target->ammo,nullptr,n,nullptr);},
            [&](int n){p->AddObjectToContainer(source,nullptr,n,nullptr);});
        logger::info("Arrow merge spell={:08X} source={:08X} target={:08X} moved={}",binding->spell->GetFormID(),source->GetFormID(),target->ammo->GetFormID(),moved);
    }
}
inline int Free(){return static_cast<int>(std::count_if(slots.begin(),slots.end(),[](auto& b){return !b.occupied;}));}
inline RE::TESAmmo* Allocate(RE::SpellItem* s){
    if(auto* b=Existing(s)){Designate(*b);return b->ammo;}
    for(auto& b:slots)if(!b.occupied){
        b.occupied=true; // partial allocation stays reserved, never repurposed
        b.refs->AddForm(b.ammo);b.refs->AddForm(s);b.refs->AddForm(canonicalMarker);b.refs->AddChange(RE::BGSListForm::ChangeFlags::kAddedForm);
        Refresh(b);if(!b.active)throw std::runtime_error("封存记录写入失败，交易已撤销");return b.ammo;
    }
    throw std::runtime_error("本存档的 256 组封存身份已用满");
}
struct Request {RE::FormID spell;std::vector<Stack> bases;std::vector<Stack> materials;};
inline std::optional<Request> pending;inline json quote=nullptr;inline std::uint64_t serial=0;
inline void Reset(){pending.reset();quote=nullptr;++serial;}
inline Plan Evaluate(RE::PlayerCharacter* p,const Request& q){
    if(!ready)throw std::runtime_error("运行时封存尚未准备好，请重新读取存档");
    auto* s=RE::TESForm::LookupByID<RE::SpellItem>(q.spell);auto reason=Unsupported(s);if(!reason.empty())throw std::runtime_error(reason);
    if(!p||!p->HasSpell(s))throw std::runtime_error("尚未掌握该法术");
    auto inv=p->GetInventory();std::vector<Stack> stock,ingredients;
    for(auto& [obj,v]:inv)if(obj&&v.second&&!v.second->IsQuestObject()&&!v.second->IsEnchanted())if(auto* a=obj->As<RE::TESAmmo>();Base(a))stock.push_back({a->GetFormID(),v.first,0});
    int f=Classify(s);std::unordered_set<RE::FormID> seen;
    for(auto selected:q.materials){auto id=selected.id;if(!seen.insert(id).second)throw std::runtime_error("材料选择重复");auto* i=RE::TESForm::LookupByID<RE::TESBoundObject>(id);auto it=inv.find(i);
        int units=crafting::Units(i,f);if(units<=0||it==inv.end()||!it->second.second||it->second.second->IsQuestObject()||selected.count<1||it->second.first<selected.count)throw std::runtime_error("充能材料不足、受任务保护或没有适用功效");ingredients.push_back({id,selected.count,units});}
    auto costs=runtime_rules::Costs(s->CalculateMagickaCost(p),Sustained(s),crafting::Alchemy(p),crafting::Enchanting(p));auto result=crafting::MakeChargedPlan(q.bases,stock,ingredients,crafting::Count(p,RE::TESForm::LookupByID<RE::TESBoundObject>(0xF)),p->AsActorValueOwner()->GetActorValue(RE::ActorValue::kMagicka),costs,false);
    auto* existing=Existing(s);int needed=existing?0:1;
    if(existing&&!arrow_identity::Fits(crafting::Count(p,existing->ammo),result.total))throw std::runtime_error("成品库存数量超限");
    if(needed>Free())throw std::runtime_error("剩余封存身份不足（每存档最多 256 组）");return result;
}
inline void Quote(RE::PlayerCharacter* p,const json& q){
    Reset();Request req{q.at("spell").get<RE::FormID>(),{}, {}};
    if(!q.at("bases").is_array()||!q.at("materials").is_array()||q.at("bases").size()>32||q.at("materials").size()>128)throw std::runtime_error("材料选择无效");
    for(auto& b:q.at("bases")){if(!b.at("count").is_number_integer()||b.at("count")<1||b.at("count")>crafting::inputCountMax)throw std::runtime_error("数量必须是 1–999 的整数");req.bases.push_back({b.at("id").get<RE::FormID>(),b.at("count").get<int>(),0});}
    req.materials=crafting::ReadMaterials(q.at("materials"));auto plan=Evaluate(p,req);auto* s=RE::TESForm::LookupByID<RE::SpellItem>(req.spell);
    json items=json::array(),outputs=json::array(),bases=json::array();for(auto x:plan.ingredients)items.push_back({{"id",x.id},{"name",crafting::Name(RE::TESForm::LookupByID(x.id))},{"count",x.count},{"units",x.units}});
    for(auto x:plan.bases)bases.push_back({{"id",x.id},{"count",x.count}});
    outputs.push_back({{"id",s->GetFormID()},{"name",OutputName(s,nullptr)},{"count",plan.total}});
    quote={{"runtime",true},{"sustained",Sustained(s)},{"family",Classify(s)},{"selection",{{"spell",req.spell},{"bases",q.at("bases")},{"materials",q.at("materials")}}},{"requestedTotal",plan.requestedTotal},{"suppliedCharge",plan.suppliedCharge},{"token",serial},{"gold",plan.gold},{"magicka",plan.magicka},{"charge",plan.charge},{"total",plan.total},{"ingredients",items},{"outputs",outputs},{"bases",bases}};pending=req;
}
inline void Commit(RE::PlayerCharacter* p,std::uint64_t token){
    if(!pending||quote.is_null()||token!=serial)throw std::runtime_error("报价已失效，请重新计算");auto req=*pending;auto old=quote;Reset();
    auto plan=Evaluate(p,req);auto* spell=RE::TESForm::LookupByID<RE::SpellItem>(req.spell);
    if(old["sustained"]!=Sustained(spell)||old["family"]!=Classify(spell)||old["total"]!=plan.total||old["gold"]!=plan.gold||old["magicka"]!=plan.magicka||old["charge"]!=plan.charge||old["ingredients"].size()!=plan.ingredients.size())throw std::runtime_error("法术或费用变化，请重新报价");
    for(std::size_t i=0;i<plan.ingredients.size();++i){auto x=plan.ingredients[i];auto y=old["ingredients"][i];if(x.id!=y["id"]||x.count!=y["count"]||x.units!=y["units"])throw std::runtime_error("材料变化，请重新报价");}
    std::vector<Stack> required=plan.bases;required.insert(required.end(),plan.ingredients.begin(),plan.ingredients.end());required.push_back({0xF,plan.gold,0});
    std::vector<Stack> removed,added;float mana=0;
    try{
        for(auto x:required){auto* obj=RE::TESForm::LookupByID<RE::TESBoundObject>(x.id);int before=crafting::Count(p,obj);if(before<x.count)throw std::runtime_error("库存变化，交易取消");p->RemoveItem(obj,x.count,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);int delta=before-crafting::Count(p,obj);if(delta>0)removed.push_back({x.id,delta,0});if(delta!=x.count)throw std::runtime_error("扣除异常，已尝试恢复");}
        auto* av=p->AsActorValueOwner();float before=av->GetActorValue(RE::ActorValue::kMagicka);if(!std::isfinite(before)||before<plan.magicka)throw std::runtime_error("魔法值不足");av->RestoreActorValue(RE::ACTOR_VALUE_MODIFIER::kDamage,RE::ActorValue::kMagicka,-plan.magicka);mana=std::max(0.f,before-av->GetActorValue(RE::ActorValue::kMagicka));if(std::abs(mana-plan.magicka)>.1f)throw std::runtime_error("魔法值扣除异常");
        auto* out=Allocate(spell);int beforeCount=crafting::Count(p,out);p->AddObjectToContainer(out,nullptr,plan.total,nullptr);int delta=crafting::Count(p,out)-beforeCount;if(delta>0)added.push_back({out->GetFormID(),delta,0});if(delta!=plan.total)throw std::runtime_error("成品添加异常");
        logger::info("Runtime output spell={:08X} ammo={:08X} count={} stock={}",spell->GetFormID(),out->GetFormID(),plan.total,crafting::Count(p,out));
    }catch(...){for(auto x:added)p->RemoveItem(RE::TESForm::LookupByID<RE::TESBoundObject>(x.id),x.count,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);for(auto x:removed)p->AddObjectToContainer(RE::TESForm::LookupByID<RE::TESBoundObject>(x.id),nullptr,x.count,nullptr);if(mana>0)p->AsActorValueOwner()->RestoreActorValue(RE::ACTOR_VALUE_MODIFIER::kDamage,RE::ActorValue::kMagicka,mana);throw;}
    logger::info("Runtime crafted spell={:08X} count={} free slots={}",req.spell,plan.total,Free());
}
}

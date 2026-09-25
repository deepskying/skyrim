#pragma once
// Queued magic arrow crafting. Gold, charged materials and base arrows are locked when the
// order starts; magicka is spent one arrow at a time while the player keeps playing.
#include "crafting.h"
#include "runtime_binding.h"
#include "craft_order_rules.h"
#include "crafting_access.h"
namespace craft_order {
using json=nlohmann::json;
inline std::vector<craft_order_rules::Entry> queue;
inline bool pauseInCombat=true,available=false;
// Same co-save unique ID as the ammo queue, its own record type inside that stream.
constexpr std::uint32_t record=0x4f524452; // "ORDR"
inline craft_order_rules::Pause paused=craft_order_rules::Pause::none;

inline RE::PlayerCharacter* Player(){return RE::PlayerCharacter::GetSingleton();}
inline void Notify(const std::string& text){if(!text.empty())RE::DebugNotification(text.c_str());}
inline float Magicka(RE::Actor* a){return a?a->AsActorValueOwner()->GetActorValue(RE::ActorValue::kMagicka):0.f;}
inline const char* Reason(){return craft_order_rules::Reason(paused);}
inline RE::TESBoundObject* Form(RE::FormID id){return RE::TESForm::LookupByID<RE::TESBoundObject>(id);}
inline int Gold(){auto* p=Player();return p?crafting::Count(p,RE::TESForm::LookupByID<RE::TESBoundObject>(0xF)):0;}

// Locked resources are removed as one transaction; any failure restores what was taken.
struct Payment {
    std::vector<crafting::Stack> removed;
    bool Take(RE::PlayerCharacter* p,const crafting::Stack& stack) {
        auto* item=Form(stack.id);if(!p||!item||stack.count<=0)return false;
        const int before=crafting::Count(p,item);
        if(before<stack.count)return false;
        p->RemoveItem(item,stack.count,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
        const int delta=before-crafting::Count(p,item);
        if(delta>0)removed.push_back({stack.id,delta,0});
        return delta==stack.count;
    }
    void Restore(RE::PlayerCharacter* p) {
        if(!p)return;
        for(auto s:removed)if(auto* item=Form(s.id))p->AddObjectToContainer(item,nullptr,s.count,nullptr);
        removed.clear();
    }
};

inline void Output(RE::SpellItem* spell,const crafting::Adapter* adapter,RE::TESAmmo*& arrow,int& family) {
    if(adapter){family=runtime_rules::Family(adapter->family);arrow=crafting::Output(0,*adapter);return;}
    family=runtime_binding::Classify(spell);arrow=runtime_binding::Allocate(spell);
}
// Refunds everything still owed for an entry that can no longer run, then drops it.
inline void Abort(craft_order_rules::Entry& entry,const std::string& why) {
    auto* p=Player();
    if(p){
        for(auto s:craft_order_rules::RefundBases(entry))if(auto* item=Form(s.id))p->AddObjectToContainer(item,nullptr,s.count,nullptr);
        for(auto s:craft_order_rules::RefundMaterials(entry))if(auto* item=Form(s.id))p->AddObjectToContainer(item,nullptr,s.count,nullptr);
        const int gold=craft_order_rules::RefundGold(entry);
        if(gold>0)if(auto* coin=RE::TESForm::LookupByID<RE::TESBoundObject>(0xF))p->AddObjectToContainer(coin,nullptr,gold,nullptr);
    }
    logger::warn("Craft order aborted spell={:08X} remaining={} reason={}",entry.spell,entry.remaining,why);
    Notify("制作中止，已退还剩余材料与金币");
}
inline void Lock(RE::PlayerCharacter* p,const crafting::Plan& plan,Payment& payment) {
    std::vector<crafting::Stack> required=plan.bases;
    required.insert(required.end(),plan.ingredients.begin(),plan.ingredients.end());
    required.push_back({0xF,plan.gold,0});
    for(auto s:required)if(!payment.Take(p,s))throw std::runtime_error("资源扣除失败，交易已取消");
}
inline json Start(const json& q) {
    auto* p=Player();
    if(!p||p->IsDead())throw std::runtime_error("当前无法开始制作");
    // Without the co-save an order would run but vanish on the next load.
    if(!available)throw std::runtime_error("队列保存组件不可用，无法开始制作");
    // Standing at an enchanter is required to start; the queue then runs anywhere.
    if(!crafting_access::Nearby(p).magic)throw std::runtime_error("请靠近附魔台后开始制作");
    auto* spell=RE::TESForm::LookupByID<RE::SpellItem>(q.at("spell").get<RE::FormID>());
    if(!spell)throw std::runtime_error("法术无效");
    const bool runtime=q.value("runtime",false);
    auto* adapter=runtime?nullptr:crafting::ForSpell(spell);
    if(!runtime&&!adapter)throw std::runtime_error("该法术尚未适配");
    if(runtime&&!runtime_binding::ready)throw std::runtime_error("运行时封存尚未准备好，请重新读档");
    if(runtime&&!p->HasSpell(spell))throw std::runtime_error("尚未掌握该法术");
    // Costs and material matching reuse the manual crafting rules exactly.
    crafting::Costs costs;
    if(runtime)costs=runtime_rules::Costs(spell->CalculateMagickaCost(p),runtime_binding::Sustained(spell),crafting::Alchemy(p),crafting::Enchanting(p));
    else costs=crafting::RecipeCosts(*adapter,p);
    std::vector<crafting::Stack> stock;
    const int family=runtime?runtime_binding::Classify(spell):runtime_rules::Family(adapter->family);
    auto inventory=p->GetInventory();
    if(runtime){
        for(auto& [obj,v]:inventory)if(obj&&v.second&&!v.second->IsQuestObject()&&!v.second->IsEnchanted())if(auto* a=obj->As<RE::TESAmmo>();runtime_binding::Base(a))stock.push_back({a->GetFormID(),v.first,0});
    }else {
        for(int i=0;i<8;++i){auto* b=RE::TESForm::LookupByID<RE::TESAmmo>(crafting::baseIDs[i]);if(b&&crafting::Output(i,*adapter))stock.push_back({b->GetFormID(),crafting::Count(p,b),0});}
    }
    std::unordered_set<RE::FormID> seen;
    std::vector<crafting::Stack> materials;
    for(auto& row:q.at("materials")){
        if(!row.at("count").is_number_integer()||row.at("count")<1||row.at("count")>crafting::inputCountMax)throw std::runtime_error("材料数量必须为 1–999 的整数");
        const auto id=row.at("id").get<RE::FormID>();
        if(!seen.insert(id).second)throw std::runtime_error("材料选择重复");
        auto* item=Form(id);const int units=crafting::Units(item,runtime_binding::MaterialAV(family));
        auto it=inventory.find(item);
        if(units<=0||it==inventory.end()||!it->second.second||it->second.second->IsQuestObject()||it->second.first<row.at("count").get<int>())
            throw std::runtime_error("充能材料不足、受任务保护或没有适用功效");
        materials.push_back({id,row.at("count").get<int>(),units});
    }
    std::vector<crafting::Stack> bases;
    for(auto& row:q.at("bases")){
        if(!row.at("count").is_number_integer()||row.at("count")<1||row.at("count")>crafting::inputCountMax)throw std::runtime_error("基材数量必须为 1–999 的整数");
        bases.push_back({row.at("id").get<RE::FormID>(),row.at("count").get<int>(),0});
    }
    // The queue is not limited by magicka on hand: that is paid one arrow at a time.
    auto plan=crafting::MakeChargedPlan(bases,stock,materials,Gold(),Magicka(p),costs,false);
    if(!craft_order_rules::Accept(queue,spell->GetFormID(),plan.total))throw std::runtime_error("该法术的排队数量已达上限 10000 支");
    RE::TESAmmo* arrow=nullptr;int arrowFamily=family;
    Output(spell,adapter,arrow,arrowFamily);
    if(!arrow)throw std::runtime_error("成品箭矢身份不可用");
    if(!arrow_identity::Fits(crafting::Count(p,arrow),plan.total))throw std::runtime_error("成品库存数量超限");
    Payment payment;
    try{Lock(p,plan,payment);}catch(const std::exception&){payment.Restore(p);throw;}
    craft_order_rules::Entry entry;
    entry.spell=spell->GetFormID();entry.arrow=arrow->GetFormID();entry.family=arrowFamily;
    entry.total=plan.total;entry.remaining=plan.total;
    entry.manaPerArrow=static_cast<int>(std::ceil(costs.mana));entry.chargePerArrow=costs.charge;entry.goldPerArrow=costs.gold;
    entry.bases=plan.bases;entry.materials=plan.ingredients;
    craft_order_rules::Add(queue,entry);
    logger::info("Craft order queued spell={:08X} arrows={} mana={} gold={} clamped={}",entry.spell,entry.total,entry.manaPerArrow,plan.gold,plan.chargeClamped);
    return {{"total",entry.total},{"mana",entry.manaPerArrow},{"gold",plan.gold},{"charge",plan.charge},{"chargeClamped",plan.chargeClamped},{"queued",craft_order_rules::Queued(queue,entry.spell)},{"paused",false}};
}
// One arrow per call, on the game thread. Waiting for magicka is not a pause.
inline void Tick(RE::PlayerCharacter* p,const std::string& pauseReason) {
    if(queue.empty()||!p)return;
    auto* spell=RE::TESForm::LookupByID<RE::SpellItem>(queue.front().spell);
    if(!spell||!p->HasSpell(spell)){Abort(queue.front(),"法术已不可用");queue.erase(queue.begin());return;}
    if(paused!=craft_order_rules::Pause::none)return;
    auto& entry=queue.front();
    auto* arrow=RE::TESForm::LookupByID<RE::TESAmmo>(entry.arrow);
    if(!arrow){Abort(entry,"成品箭矢缺失");queue.erase(queue.begin());return;}
    auto* av=p->AsActorValueOwner();
    if(Magicka(p)<entry.manaPerArrow)return;
    av->RestoreActorValue(RE::ACTOR_VALUE_MODIFIER::kDamage,RE::ActorValue::kMagicka,-static_cast<float>(entry.manaPerArrow));
    p->AddObjectToContainer(arrow,nullptr,1,nullptr);
    Notify(crafting::Name(arrow)); // one notification per arrow, like a pick-up message
    if(!craft_order_rules::Advance(entry)){Notify("制作完成："+crafting::Name(arrow));queue.erase(queue.begin());}
    (void)pauseReason;
}
inline json State() {
    json rows=json::array();
    for(const auto& entry:queue) {
        auto* arrow=RE::TESForm::LookupByID<RE::TESAmmo>(entry.arrow);
        auto* spell=RE::TESForm::LookupByID<RE::SpellItem>(entry.spell);
        rows.push_back({{"spell",entry.spell},{"spellName",crafting::Name(spell)},{"arrow",entry.arrow},
            {"name",arrow?crafting::Name(arrow):"未知箭矢"},{"family",runtime_rules::families[entry.family]},
            {"familyIndex",entry.family},{"total",entry.total},{"remaining",entry.remaining},
            {"label",craft_order_rules::CountLabel(entry.remaining)},{"progress",craft_order_rules::Progress(entry)},
            {"manaPerArrow",entry.manaPerArrow},{"chargePerArrow",entry.chargePerArrow}});
    }
    return {{"entries",rows},{"count",queue.size()},{"paused",paused!=craft_order_rules::Pause::none},
        {"reason",Reason()},{"limit",craft_order_rules::perSpellLimit},{"pauseInCombat",pauseInCombat},{"available",available}};
}
inline void Revert(){queue.clear();paused=craft_order_rules::Pause::none;}
inline void Save(SKSE::SerializationInterface* api) {
    const auto words=craft_order_rules::Encode(queue);
    if(!api->WriteRecord(record,craft_order_rules::recordVersion,words.data(),static_cast<std::uint32_t>(words.size()*sizeof(std::uint32_t))))logger::error("Craft order save failed");
}
inline bool LoadRecord(SKSE::SerializationInterface* api,std::uint32_t type,std::uint32_t version,std::uint32_t length) {
    if(type!=record)return false;
    if(version==craft_order_rules::recordVersion&&length>=8&&length%4==0&&length<=1<<20) {
        std::vector<std::uint32_t> words(length/4);
        if(api->ReadRecordData(words.data(),length)==length) {
            auto resolve=[&](std::uint32_t id,std::uint32_t& out){RE::FormID resolved=0;if(api->ResolveFormID(id,resolved)&&resolved){out=resolved;return true;}out=0;return false;};
            std::vector<craft_order_rules::Entry> restored;
            if(craft_order_rules::Decode(words,restored,resolve))queue=std::move(restored);
        }
    }
    logger::info("Craft order loaded entries={}",queue.size());
    return true;
}
}

#pragma once
#include "runtime_binding.h"
#include "ammo_queue_rules.h"
#include "craft_order.h"
#include "soul_pool.h"
namespace ammo_queue {
using json=nlohmann::json;
inline std::vector<RE::FormID> order;
inline bool enabled=true,available=false;
inline std::uint64_t revision=0;
inline ammo_queue_rules::Tracker tracker;
inline RE::TESAmmo* Ammo(RE::FormID id){auto* a=RE::TESForm::LookupByID<RE::TESAmmo>(id);return a&&a->GetPlayable()&&!a->IsBolt()&&!a->IsDeleted()?a:nullptr;}
inline RE::FormID Canonical(RE::FormID id){auto* a=Ammo(id);if(auto* b=runtime_binding::Bound(a)){auto* c=runtime_binding::Existing(b->spell);if(c)return c->ammo->GetFormID();}return id;}
inline void Suspend(){tracker.Reset();++revision;}
inline void Revert(SKSE::SerializationInterface*){order.clear();enabled=true;Suspend();craft_order::Revert();soul_pool::Revert(nullptr);}
inline void Normalize(){
    std::vector<RE::FormID> updated;for(auto id:order){id=Canonical(id);if(!ammo_queue_rules::Contains(updated,id))updated.push_back(id);}
    if(updated!=order){order=std::move(updated);Suspend();}
}
inline int Count(RE::PlayerCharacter* p,RE::FormID id){auto* a=Ammo(id);return p&&a?crafting::Count(p,a):0;}
inline void Observe(RE::PlayerCharacter*,RE::FormID){tracker.Reset();}
inline void Prune(RE::PlayerCharacter* p){
    // Do not treat temporarily neutral forms during loading as empty inventory.
    if(!p||!runtime_binding::ready)return;
    auto inventory=p->GetInventory();
    if(ammo_queue_rules::Prune(order,[&](RE::FormID id){auto* ammo=Ammo(id);auto it=inventory.find(ammo);return ammo&&it!=inventory.end()?std::max(0,it->second.first):0;})){
        tracker.Reset();tracker.finished=order.empty();logger::info("Ammo queue removed empty entries; remaining={}",order.size());
    }
}
inline void Edit(RE::PlayerCharacter* p,const json& q){
    if(!available)throw std::runtime_error("队列保存组件不可用");
    const auto& rows=q.at("ids");if(!rows.is_array()||rows.size()>ammo_queue_rules::limit)throw std::runtime_error("队列最多 64 种箭矢");
    std::vector<RE::FormID> next;
    for(const auto& row:rows){if(!row.is_number_integer()||row<=0||row>std::numeric_limits<RE::FormID>::max())throw std::runtime_error("队列条目 ID 无效");auto id=row.get<RE::FormID>();if(ammo_queue_rules::Contains(next,id))throw std::runtime_error("队列条目重复或无效");
        if(!ammo_queue_rules::Contains(order,id)&&(!Ammo(id)||Count(p,id)<=0))throw std::runtime_error("只能加入背包中的可用弓箭");next.push_back(id);}
    order=std::move(next);enabled=true;Suspend();Prune(p);
}
inline json State(RE::PlayerCharacter* p){
    Prune(p);
    json rows=json::array();auto* worn=p?p->GetCurrentAmmo():nullptr;
    for(auto id:order){auto* a=RE::TESForm::LookupByID<RE::TESAmmo>(id);rows.push_back({{"id",id},{"name",a?crafting::Name(a):"来源缺失的箭矢"},{"count",Count(p,id)},{"usable",Ammo(id)!=nullptr},{"equipped",a&&a==worn}});}
    return {{"available",available},{"enabled",enabled},{"ids",order},{"items",rows},{"limit",ammo_queue_rules::limit},{"finished",tracker.finished}};
}
// One bounded record per save. SKSE resolves full and light-plugin FormIDs.
constexpr std::uint32_t uid=0x4D415151,record=0x51554555;
inline void Save(SKSE::SerializationInterface* api){
    std::vector<std::uint32_t> words{0u,static_cast<std::uint32_t>(order.size())};words.insert(words.end(),order.begin(),order.end());
    if(!api->WriteRecord(record,2,words.data(),static_cast<std::uint32_t>(words.size()*sizeof(std::uint32_t))))logger::error("Ammo queue save failed");
    craft_order::Save(api);
    soul_pool::Save(api);
}
inline void Load(SKSE::SerializationInterface* api){
    Revert(api);std::uint32_t type,version,length;
    while(api->GetNextRecordInfo(type,version,length)){
        if(craft_order::LoadRecord(api,type,version,length))continue;
        if(soul_pool::LoadRecord(api,type,version,length))continue;
        if(type!=record||(version!=1&&version!=2)||length<8||length>(ammo_queue_rules::limit+2)*4||length%4)continue;
        std::vector<std::uint32_t> words(length/4);if(api->ReadRecordData(words.data(),length)!=length||!ammo_queue_rules::ValidRecord(words,version))continue;
        std::vector<RE::FormID> restored;for(std::size_t i=2;i<words.size();++i){RE::FormID id=0;if(api->ResolveFormID(words[i],id)&&id&&!ammo_queue_rules::Contains(restored,id))restored.push_back(id);}
        order=std::move(restored);enabled=true; // Ignore legacy cycle/random mode values.
    }
    logger::info("Ammo queue loaded enabled={} entries={}",enabled,order.size());
}
inline void Install(){auto* api=SKSE::GetSerializationInterface();if(!api)return;api->SetUniqueID(uid);api->SetSaveCallback(Save);api->SetLoadCallback(Load);api->SetRevertCallback(Revert);available=true;soul_pool::available=true;}
}

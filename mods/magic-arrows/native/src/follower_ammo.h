#pragma once
#include "runtime_binding.h"
#include "follower_rules.h"
namespace follower_ammo {
inline bool consume=true,installed=false;
inline thread_local bool inside=false;
using UseAmmoFn=std::uint32_t(*)(RE::Actor*,std::uint32_t);
inline REL::Relocation<UseAmmoFn> original;
inline RE::InventoryEntryData* Cache(RE::Actor* actor){
    auto* p=actor->GetActorRuntimeData().currentProcess;
    return p&&p->middleHigh?p->middleHigh->bothHands:nullptr;
}
inline int Count(RE::Actor* actor,RE::TESAmmo* ammo){
    auto inv=actor->GetInventory([ammo](RE::TESBoundObject& obj){return &obj==ammo;});
    auto it=inv.find(ammo);return it==inv.end()?0:std::max(0,it->second.first);
}
inline void Empty(RE::Actor* actor,RE::TESAmmo* ammo){
    auto* tasks=SKSE::GetTaskInterface();if(!tasks)return;
    auto handle=actor->CreateRefHandle();auto id=ammo->GetFormID();auto epoch=runtime_binding::generation.load();
    tasks->AddTask([handle,id,epoch]{
        if(epoch!=runtime_binding::generation.load())return;
        auto ref=handle.get();auto* a=ref?ref->As<RE::Actor>():nullptr;auto* item=RE::TESForm::LookupByID<RE::TESAmmo>(id);
        if(!a||!item||a->GetCurrentAmmo()!=item||Count(a,item)>0)return;
        if(auto* manager=RE::ActorEquipManager::GetSingleton())manager->UnequipObject(a,item,nullptr,1,nullptr,true,false,true,false,nullptr);
    });
}
inline std::uint32_t UseAmmo(RE::Actor* actor,std::uint32_t requested){
    // Preserve the previous hook for every call, including ordinary ammo and players.
    if(inside||!consume||!runtime_binding::ready||!actor||actor==RE::PlayerCharacter::GetSingleton()||!actor->IsPlayerTeammate())return original(actor,requested);
    auto* ammo=actor->GetCurrentAmmo();auto* entry=Cache(actor);
    auto* equipped=actor->GetEquippedObject(false);auto* weapon=equipped?equipped->As<RE::TESObjectWEAP>():nullptr;
    if(!ammo||!ammo->GetPlayable()||(!runtime_binding::Bound(ammo)&&!crafting::IsOutput(ammo))||!entry||entry->object!=ammo||entry->IsQuestObject()||!weapon||weapon->GetWeaponType()!=RE::WEAPON_TYPE::kBow)return original(actor,requested);
    struct Guard{Guard(){inside=true;}~Guard(){inside=false;}} guard;
    auto* process=actor->GetActorRuntimeData().currentProcess;
    auto shots=follower_rules::Shots(requested,process->middleHigh->unk310);
    const int before=Count(actor,ammo);
    const auto result=original(actor,requested);
    // A zero result with existing stock means the original routine rejected the shot.
    // Do not debit an unsuccessful request or invent ammo when another mod removed it.
    const int after=Count(actor,ammo);
    const int missing=result||before==0?follower_rules::Missing(before,after,shots):0;
    if(missing>0)actor->RemoveItem(ammo,missing,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
    const int remaining=missing>0?Count(actor,ammo):after;
    if(missing>0||before==0){
        // SE 1.5.97 keeps a separate equipped-ammo InventoryEntryData at +0x268.
        // Re-fetch after inventory mutation; never reuse a potentially freed entry.
        if(auto* current=Cache(actor);current&&current->object==ammo)current->countDelta=remaining;
        if(!remaining)Empty(actor,ammo);
        logger::info("Follower ammo actor={:08X} ammo={:08X} shots={} before={} nativeAfter={} supplement={} remaining={}",actor->GetFormID(),ammo->GetFormID(),shots,before,after,missing,remaining);
        return static_cast<std::uint32_t>(remaining); // native contract: stock left, not shots fired
    }
    return result;
}
inline void Install(){
    if(REL::Module::get().version()!=REL::Version(1,5,97,0))return;
    REL::Relocation<std::uintptr_t> table{RE::VTABLE_Actor[0]};original=table.write_vfunc(0xD2,UseAmmo);installed=true;
    logger::info("Follower magic ammo consumption hook installed");
}
}

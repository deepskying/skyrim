#pragma once
#include "soul_capture_rules.h"
#include "runtime_binding.h"
namespace soul_capture {
// A vanilla soul trap only fills a gem the caster already carries, so a kill with a
// sealed soul arrow can silently produce nothing. Wrap the engine's own Actor::TrapSoul
// and, when the capture failed on a victim our soul arrow hit, lend one empty gem so the
// engine can run its own matching again. Every other rule (dead victim, soul size,
// humanoid souls needing a black gem, already trapped) still comes from the engine.
using TrapSoulFn=bool(*)(RE::Actor*,RE::Actor*);
inline REL::Relocation<TrapSoulFn> original;
inline std::vector<soul_capture_rules::Entry> armed;
inline bool installed=false;
inline int Count(RE::Actor* actor,RE::TESBoundObject* item){
    auto inventory=actor->GetInventory([item](RE::TESBoundObject& object){return &object==item;});
    auto it=inventory.find(item);return it==inventory.end()?0:std::max(0,it->second.first);
}
inline void Arm(RE::Actor* victim,RE::Actor* shooter){
    if(!victim||victim->IsDead())return;
    soul_capture_rules::Arm(armed,victim->GetFormID(),shooter?shooter->GetFormID():0,GetTickCount64(),runtime_binding::generation.load());
}
inline void Reset(){armed.clear();}
inline bool TrapSoul(RE::Actor* caster,RE::Actor* victim){
    if(original(caster,victim))return true;
    if(!installed||!caster||!victim||!victim->IsDead())return false;
    const auto now=GetTickCount64(),epoch=runtime_binding::generation.load();
    if(!soul_capture_rules::Armed(armed,victim->GetFormID(),now,epoch))return false;
    const int soul=static_cast<int>(victim->GetSoulSize());
    for(auto id:soul_capture_rules::Candidates(soul)){
        auto* gem=RE::TESForm::LookupByID<RE::TESSoulGem>(id);
        if(!gem)continue;
        const int before=Count(caster,gem);
        caster->AddObjectToContainer(gem,nullptr,1,nullptr);
        if(original(caster,victim)){
            logger::info("Unconditional soul capture victim={:08X} caster={:08X} soul={} gem={:08X}",victim->GetFormID(),caster->GetFormID(),soul,id);
            return true;
        }
        if(Count(caster,gem)>before)caster->RemoveItem(gem,1,RE::ITEM_REMOVE_REASON::kRemove,nullptr,nullptr);
    }
    return false;
}
inline void Install(){
    if(REL::Module::get().version()!=REL::Version(1,5,97,0))return;
    REL::Relocation<std::uintptr_t> function{REL::ID(37863)}; // Actor::TrapSoul
    original=function.write_branch<5>(TrapSoul);
    installed=true;
    logger::info("Unconditional soul capture hook installed");
}
}

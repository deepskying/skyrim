#pragma once
#include "soul_capture_rules.h"
#include "runtime_binding.h"
#include "soul_pool.h"
#include <cstring>
namespace soul_capture {
// Every soul capture in the game ends up in the engine's Actor::TrapSoul: the vanilla Soul
// Trap script, weapon enchantments, the engine's soul trap archetype and our sealed arrows.
// While the pool is enabled the player and their followers bank the soul there instead of
// filling a gem; a soul the pool cannot take falls through to the vanilla capture below,
// which needs an empty gem the caster carries.
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
    if(soul_pool::enabled&&caster&&victim&&victim->IsDead()&&(caster==RE::PlayerCharacter::GetSingleton()||caster->IsPlayerTeammate()))
        if(soul_pool::Bank(victim))return true;
    if(original(caster,victim))return true;
    if(soul_pool::enabled)return false; // Pool full or not ours: exactly the vanilla capture.
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
    // Hooking a function prologue needs our own copy of the displaced bytes: write_branch
    // only reports the target of an existing branch, it does not build a callable copy, so
    // calling its return value would jump into the middle of the prologue's data.
    auto& trampoline=SKSE::GetTrampoline();
    if(trampoline.empty()||trampoline.free_size()<64){logger::error("No trampoline space reserved; unconditional soul capture disabled");return;}
    auto* address=reinterpret_cast<std::byte*>(REL::ID(37863).address()); // Actor::TrapSoul
    // The prologue is "mov rax, rsp / push rsi / push rdi": exactly five bytes, no relative
    // operands, so the copy plus an absolute jump back is enough to chain the original.
#pragma pack(push, 1)
    struct AbsoluteJump {std::uint8_t opcode=0xFF,modrm=0x25;std::int32_t disp=0;std::uint64_t target=0;};
#pragma pack(pop)
    constexpr std::size_t displaced=5;
    auto* copy=static_cast<std::byte*>(trampoline.allocate(displaced+sizeof(AbsoluteJump)));
    if(!copy){logger::error("Soul capture trampoline allocation failed");return;}
    std::memcpy(copy,address,displaced);
    AbsoluteJump jump{};jump.target=reinterpret_cast<std::uint64_t>(address+displaced);
    std::memcpy(copy+displaced,&jump,sizeof(jump));
    original=reinterpret_cast<std::uintptr_t>(copy);
    trampoline.write_branch<5>(reinterpret_cast<std::uintptr_t>(address),reinterpret_cast<std::uintptr_t>(&TrapSoul));
    installed=true;
    const auto byte=[](std::byte value){return static_cast<unsigned>(value);};
    logger::info("Unconditional soul capture hook installed (target={:08X} prologue={:02X}{:02X}{:02X}{:02X}{:02X} copy={:p})",
        REL::ID(37863).offset(),byte(address[0]),byte(address[1]),byte(address[2]),byte(address[3]),byte(address[4]),static_cast<void*>(copy));
}
}

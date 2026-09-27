#pragma once
#include "runtime_binding.h"
#include "runtime_sustained.h"
#include "soul_capture.h"
#include <deque>
namespace runtime_impact {
using Original=void(*)(RE::ArrowProjectile*,RE::TESObjectREFR*,const RE::NiPoint3&,const RE::NiPoint3&,RE::hkpCollidable*,std::int32_t,std::uint32_t);
inline REL::Relocation<Original> original;
inline std::atomic<int> queued{0};
inline std::unordered_set<std::uint32_t> handled;
inline std::deque<std::uint32_t> order;
inline std::uint64_t lastGeneration=0;
inline bool Finite(RE::NiPoint3 p){return std::isfinite(p.x)&&std::isfinite(p.y)&&std::isfinite(p.z);}
inline void AddImpact(RE::ArrowProjectile* arrow,RE::TESObjectREFR* target,const RE::NiPoint3& position,const RE::NiPoint3& velocity,RE::hkpCollidable* collidable,std::int32_t arg6,std::uint32_t arg7){
    // Capture handles and values, never retain a physics callback's object pointers.
    auto& d=arrow->GetProjectileRuntimeData();auto* ammo=d.ammoSource;
    const bool ours=ammo&&runtime_binding::slotIDs.contains(ammo->GetFormID());
    auto shot=ours?arrow->CreateRefHandle():RE::ObjectRefHandle{};
    auto shooter=d.shooter;auto victim=ours&&target?target->CreateRefHandle():RE::ObjectRefHandle{};
    const auto ammoID=ours?ammo->GetFormID():0;auto* cell=ours?arrow->GetParentCell():nullptr;const auto cellID=cell?cell->GetFormID():0;
    const auto pos=position;auto dir=d.velocity; // AddImpact's velocity can already be negated by a collision handler.
    if(ours&&dir.x*dir.x+dir.y*dir.y+dir.z*dir.z<.000001f){float x=arrow->GetAngleX(),z=arrow->GetAngleZ();dir={std::sin(z)*std::cos(x),std::cos(z)*std::cos(x),-std::sin(x)};}
    const auto epoch=runtime_binding::generation.load();
    original(arrow,target,position,velocity,collidable,arg6,arg7);
    if(!ours||!cellID||!Finite(pos)||!Finite(dir))return;
    auto* tasks=SKSE::GetTaskInterface();if(!tasks)return;
    if(queued.fetch_add(1)>=256){--queued;return;}
    tasks->AddTask([ammoID,shot,shooter,victim,pos,dir,cellID,epoch]() mutable {
        --queued;
        if(epoch!=runtime_binding::generation.load()||!runtime_binding::ready)return;
        if(lastGeneration!=epoch){handled.clear();order.clear();lastGeneration=epoch;}
        if(!handled.insert(shot.native_handle()).second)return;
        order.push_back(shot.native_handle());if(order.size()>8192){handled.erase(order.front());order.pop_front();}
        auto source=shooter.get();auto* actor=source?source->As<RE::Actor>():nullptr;
        auto* cell=RE::TESForm::LookupByID<RE::TESObjectCELL>(cellID);auto* binding=runtime_binding::Bound(RE::TESForm::LookupByID<RE::TESAmmo>(ammoID));
        if(!actor||actor->IsDead()||!cell||!cell->IsAttached()||!binding||!runtime_binding::Unsupported(binding->spell).empty())return;
        float length=std::sqrt(dir.x*dir.x+dir.y*dir.y+dir.z*dir.z);if(!std::isfinite(length)||length<.001f)return;
        dir.x/=length;dir.y/=length;dir.z/=length;
        auto* proj=runtime_binding::PrimaryProjectile(binding->spell);
        const auto route=runtime_binding::Compatibility(binding->spell).route;
        float offset=proj?std::clamp(proj->data.collisionRadius*2+4,12.f,64.f):12.f;if(!std::isfinite(offset))return;
        if(route==spell_compatibility::Route::area)offset=0.f;
        RE::NiPoint3 origin{pos.x-dir.x*offset,pos.y-dir.y*offset,pos.z-dir.z*offset};
        RE::Projectile::ProjectileRot angles{-std::atan2(dir.z,std::hypot(dir.x,dir.y)),std::atan2(dir.x,dir.y)};
        auto hit=victim.get();auto* target=hit?hit->As<RE::Actor>():nullptr;
        if(route==spell_compatibility::Route::actor&&(!target||target->IsDead())){
            logger::info("Impact cast skipped ammo={:08X}; spell requires a living actor hit",ammoID);return;
        }
        const bool started=runtime_sustained::Start(actor,binding->spell,cell,origin,pos,{angles.x,0.f,angles.z},target);
        if(started&&target&&runtime_binding::Classify(binding->spell)==10)soul_capture::Arm(target,actor);
        logger::info("Runtime impact ammo={:08X} spell={:08X} shooter={:08X} started={} impact=({:.1f},{:.1f},{:.1f})",ammoID,binding->spell->GetFormID(),actor->GetFormID(),started,pos.x,pos.y,pos.z);
    });
}
inline void Install(){
    // This hook is validated against the local 1.5.97 ArrowProjectile vtable layout.
    if(REL::Module::get().version()!=REL::Version(1,5,97,0)){logger::error("Runtime impact disabled: only SE 1.5.97 is supported by this build");return;}
    REL::Relocation<std::uintptr_t> table{RE::VTABLE_ArrowProjectile[0]};original=table.write_vfunc(0xBD,AddImpact);
    runtime_binding::hookReady=true;logger::info("Runtime ArrowProjectile AddImpact hook installed");
}
}

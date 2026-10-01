#pragma once
#include "runtime_binding.h"
#include "sustained_rules.h"
#include <deque>
namespace runtime_sustained {
struct Cast {
    RE::ObjectRefHandle origin,target,shooter;
    RE::FormID cell=0,spell=0;
    std::uint64_t epoch=0;
    float remaining=sustained_rules::seconds;
    bool sustained=true;
    RE::ObjectRefHandle victim;
    bool requiresActor=false;
};
inline std::deque<Cast> casts;
inline RE::TESObjectSTAT* marker=nullptr;
inline RE::BGSListForm* registry=nullptr;
using UpdateFn=void(*)(RE::PlayerCharacter*,float);
inline REL::Relocation<UpdateFn> originalUpdate;
inline bool installed=false;
inline void (*afterUpdate)()=nullptr;
// A non-actor caster returns its reference but never fills the out actor, so the engine
// creates every active effect of our helper casts with an empty caster handle: scripted
// effects receive akCaster = None (the vanilla Soul Trap script then calls
// Caster.TrapSoul(victim) on nothing) and absorb or ownership logic cannot credit the
// shooter. Report the blame actor the caller passed in as the caster actor on the routes
// whose target comes from the caster's own target handle.
using CasterReferenceFn=RE::TESObjectREFR*(*)(RE::MagicCaster*,RE::Actor**);
inline REL::Relocation<CasterReferenceFn> originalCasterReference;
inline RE::TESObjectREFR* CasterReference(RE::MagicCaster* caster,RE::Actor** outActor){
    auto* reference=originalCasterReference(caster,outActor);auto* spell=caster?caster->currentSpell:nullptr;
    if(outActor&&reference&&spell&&spell_compatibility::CasterAttribution(static_cast<int>(spell->GetDelivery()))&&reference->GetBaseObject()==marker)
        if(auto* shooter=caster->GetCasterAsActor()){
            *outActor=shooter;
            logger::info("Helper caster attribution spell={:08X} delivery={} shooter={:08X} helper={:08X}",spell->GetFormID(),static_cast<int>(spell->GetDelivery()),shooter->GetFormID(),reference->GetFormID());
        }
    return reference;
}
inline bool Owned(RE::TESObjectREFR* ref){return ref&&marker&&ref->GetBaseObject()==marker;}
inline void Delete(RE::TESObjectREFR* ref){
    if(!Owned(ref))return;
    // Read existing extra data: cleanup must not create a fresh caster on the target marker.
    if(auto* extra=ref->extraList.GetByType<RE::ExtraMagicCaster>())extra->InterruptCast(false);
    ref->Disable();ref->SetDelete(true);
}
inline void Stop(Cast& c,const char* reason){
    auto origin=c.origin.get();auto target=c.target.get();
    Delete(origin.get());Delete(target.get());
    logger::info("Impact cast stop spell={:08X} sustained={} reason={}",c.spell,c.sustained,reason);
}
inline void SaveRegistry(){
    if(!registry)return;
    // This dedicated FLST has no editor entries. Keep only live helper references.
    registry->forms.clear();
    if(registry->scriptAddedTempForms)registry->scriptAddedTempForms->clear();
    registry->scriptAddedFormCount=0;
    for(auto& c:casts){auto a=c.origin.get();auto b=c.target.get();if(Owned(a.get()))registry->AddForm(a.get());if(Owned(b.get()))registry->AddForm(b.get());}
    registry->AddChange(RE::BGSListForm::ChangeFlags::kAddedForm);
}
inline void Clear(const char* reason){for(auto& c:casts)Stop(c,reason);casts.clear();SaveRegistry();}
inline void AfterLoad(){
    // Old-world handles must never be resolved after a load. Native saved references
    // clean up casts captured by an autosave, including a fresh process with no timers.
    casts.clear();
    if(registry){registry->ForEachForm([](RE::TESForm* f){Delete(f->As<RE::TESObjectREFR>());return RE::BSContainer::ForEachResult::kContinue;});SaveRegistry();}
}
inline void Tick(float delta){
    if(casts.empty())return;
    auto* ui=RE::UI::GetSingleton();bool paused=!ui||ui->GameIsPaused();bool changed=false;
    for(auto it=casts.begin();it!=casts.end();){
        auto a=it->origin.get();auto b=it->target.get();auto source=it->shooter.get();auto* actor=source?source->As<RE::Actor>():nullptr;
        auto* cell=RE::TESForm::LookupByID<RE::TESObjectCELL>(it->cell);
        auto* extra=a?a->extraList.GetByType<RE::ExtraMagicCaster>():nullptr;
        bool valid=runtime_binding::ready&&it->epoch==runtime_binding::generation.load()&&Owned(a.get())&&Owned(b.get())&&!a->IsDeleted()&&!a->IsDisabled()&&actor&&!actor->IsDead()&&!actor->IsDeleted()&&cell&&cell->IsAttached()&&extra&&(!it->sustained||(extra->currentSpell&&extra->currentSpell->GetFormID()==it->spell));
        if(it->requiresActor){auto victim=it->victim.get();auto* hit=victim?victim->As<RE::Actor>():nullptr;valid=valid&&hit&&!hit->IsDead()&&!hit->IsDeleted()&&hit->GetParentCell()==cell;}
        if(!sustained_rules::Advance(it->remaining,delta,paused,valid)){Stop(*it,valid?"expired":"context lost");it=casts.erase(it);changed=true;}else ++it;
    }
    if(changed)SaveRegistry();
}
inline void Update(RE::PlayerCharacter* player,float delta){originalUpdate(player,delta);Tick(delta);if(afterUpdate)afterUpdate();}
inline bool Start(RE::Actor* shooter,RE::SpellItem* spell,RE::TESObjectCELL* cell,const RE::NiPoint3& origin,const RE::NiPoint3& impact,const RE::NiPoint3& angles,RE::Actor* victim=nullptr){
    if(!installed||!marker||!registry||!shooter||!spell||!cell||!cell->IsAttached())return false;
    const bool sustained=runtime_binding::Sustained(spell);
    const bool requiresActor=runtime_binding::Compatibility(spell).route==spell_compatibility::Route::actor;
    if(requiresActor&&(!victim||victim->IsDead()||victim->IsDeleted()))return false;
    auto count=std::count_if(casts.begin(),casts.end(),[&](const Cast& c){return c.sustained==sustained;});
    if(count>=(sustained?16:32)){auto oldest=std::find_if(casts.begin(),casts.end(),[&](const Cast& c){return c.sustained==sustained;});Stop(*oldest,"capacity: oldest cast replaced");casts.erase(oldest);SaveRegistry();}
    auto* data=RE::TESDataHandler::GetSingleton();
    auto place=[&](const RE::NiPoint3& pos){return data->CreateReferenceAtLocation(marker,pos,angles,cell,cell->GetRuntimeData().worldSpace,nullptr,nullptr,RE::ObjectRefHandle{},false,true);};
    auto a=place(origin);auto b=place(impact);auto source=a.get();auto target=b.get();
    if(!Owned(source.get())||!Owned(target.get())){Delete(source.get());Delete(target.get());return false;}
    source->SetActivationBlocked(true);target->SetActivationBlocked(true);
    auto* caster=source->GetMagicCaster(RE::MagicSystem::CastingSource::kInstant);
    if(!caster){Delete(source.get());Delete(target.get());return false;}
    casts.push_back({a,b,shooter->CreateRefHandle(),cell->GetFormID(),spell->GetFormID(),runtime_binding::generation.load(),sustained?sustained_rules::seconds:1.f,sustained,victim?victim->CreateRefHandle():RE::ObjectRefHandle{},requiresActor});SaveRegistry();
    const auto route=runtime_binding::Compatibility(spell).route;
    RE::TESObjectREFR* castTarget=requiresActor?static_cast<RE::TESObjectREFR*>(victim):route==spell_compatibility::Route::area?source.get():target.get();
    // Release the original MagicItem through the engine, including all projectiles,
    // conditions and script effects. The blame actor remains the actual shooter.
    // A concentration cast starts once; the native caster updates it for three seconds.
    caster->CastSpellImmediate(spell,false,castTarget,1.f,false,0.f,shooter);
    if(sustained&&caster->currentSpell!=spell){Stop(casts.back(),"cast rejected");casts.pop_back();SaveRegistry();return false;}
    logger::info("Impact cast start spell={:08X} shooter={:08X} route={} origin={:08X} target={:08X} sustained={} active={}",spell->GetFormID(),shooter->GetFormID(),runtime_binding::RouteName(spell),source->GetFormID(),castTarget->GetFormID(),sustained,casts.size());return true;
}
inline void Install(){
    if(REL::Module::get().version()!=REL::Version(1,5,97,0))return;
    auto* data=RE::TESDataHandler::GetSingleton();marker=data->LookupForm<RE::TESObjectSTAT>(0xE00,"MagicArrows.esp");registry=data->LookupForm<RE::BGSListForm>(0xE01,"MagicArrows.esp");
    if(!marker||!registry){logger::error("Sustained cast helpers missing; concentration disabled");return;}
    REL::Relocation<std::uintptr_t> casterTable{RE::VTABLE_NonActorMagicCaster[1]};originalCasterReference=casterTable.write_vfunc(0xD,CasterReference);
    logger::info("Helper caster attribution hook installed (touch and target-actor routes)");
    REL::Relocation<std::uintptr_t> table{RE::VTABLE_PlayerCharacter[0]};originalUpdate=table.write_vfunc(0xAD,Update);installed=true;runtime_binding::sustainedReady=true;
}
}

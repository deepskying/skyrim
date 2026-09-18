#include "pch.h"
#include "rules.h"
namespace {
using V=RE::NiPoint3;
using H=RE::ObjectRefHandle;
using Source=RE::MagicSystem::CastingSource;
constexpr const char* plugin="ArcaneArsenal.esp";
std::array<RE::EnchantmentItem*,4> enchant{};
std::array<RE::SpellItem*,8> payload{};
std::array<RE::TESObjectSTAT*,8> visuals{};
RE::BGSListForm* registry=nullptr;
std::atomic_bool ready=false;
std::atomic_uint64_t epoch=0;
bool recordsValid=false;
std::mutex carrierMutex;
float now=0;
rules::Marks marks;
std::uint64_t shotID=0;
struct FX {H ref; float end;H follow{},owner{};V offset{};};
std::vector<FX> fx;
struct Shot {
    std::uint64_t id; int kind; H caster; RE::FormID cell; Source hand;
    V pos,dir,start,endpoint,previousGround;
    float age=0,travel=0,nextBand=0;int band=0;bool returning=false,anchor=false;
    H visual;std::set<RE::FormID> outbound,inbound;std::map<RE::FormID,float> chilled;
};
std::vector<Shot> shots;
struct Reservation {H caster;Source hand;int kind;float end;bool released=false;};
std::vector<Reservation> reservations;
struct Slow {H target,caster,rootCaster;float until=0,rootUntil=0,immuneUntil=0;};
std::map<RE::FormID,Slow> slows;
std::set<std::uint32_t> intercepted;
int Kind(RE::MagicItem* spell){for(int i=0;i<4;++i)if(spell&&spell==enchant[i])return i;return -1;}
RE::Actor* Actor(H h){auto r=h.get();return r?r->As<RE::Actor>():nullptr;}
V Unit(V v){if(v.Unitize()<.001f)return {0,1,0};return v;}
bool Paused(){auto* ui=RE::UI::GetSingleton();return !ui||ui->GameIsPaused();}
bool Friendly(RE::Actor* caster,RE::Actor* target){
    if(caster==target)return true;
    auto player=RE::PlayerCharacter::GetSingleton();
    const bool sourceTeam=caster==player||caster->IsPlayerTeammate();
    const bool targetTeam=target==player||target->IsPlayerTeammate();
    return sourceTeam&&targetTeam;
}
bool Victim(RE::Actor* c,RE::Actor* t){return t&&!t->IsDead()&&!t->IsDeleted()&&!t->IsDisabled()&&t->Is3DLoaded()&&!Friendly(c,t);}
bool Owned(RE::TESObjectREFR* r){return r&&std::ranges::find(visuals,r->GetBaseObject())!=visuals.end();}
void Delete(H h){auto r=h.get();if(Owned(r.get())){r->Disable();r->SetDelete(true);}}
void SaveRegistry(){
    if(!registry)return;registry->forms.clear();
    if(registry->scriptAddedTempForms)registry->scriptAddedTempForms->clear();registry->scriptAddedFormCount=0;
    for(auto& f:fx){auto r=f.ref.get();if(Owned(r.get()))registry->AddForm(r.get());}
    for(auto& s:shots){auto r=s.visual.get();if(Owned(r.get()))registry->AddForm(r.get());}
    registry->AddChange(RE::BGSListForm::ChangeFlags::kAddedForm);
}
H Visual(int index,RE::TESObjectCELL* cell,V pos,V angles={}){
    if(!cell||!cell->IsAttached()||!visuals[index])return {};
    auto h=RE::TESDataHandler::GetSingleton()->CreateReferenceAtLocation(visuals[index],pos,angles,cell,cell->GetRuntimeData().worldSpace,nullptr,nullptr,H{},false,true);
    if(auto r=h.get())r->SetActivationBlocked(true);return h;
}
void Flash(int index,RE::TESObjectCELL* cell,V p,float seconds,V angle={}){
    if(fx.size()>=128){Delete(fx.front().ref);fx.erase(fx.begin());}
    auto h=Visual(index,cell,p,angle);if(h)fx.push_back({h,now+seconds});SaveRegistry();
}
bool ActorLayer(RE::COL_LAYER l){return l==RE::COL_LAYER::kBiped||l==RE::COL_LAYER::kCharController||l==RE::COL_LAYER::kBipedNoCC||l==RE::COL_LAYER::kDeadBip;}
// Terrain/doors/props stop spells. Actor collision is swept separately, so a
// piercing shuttle never relies on a discrete engine impact event.
bool Ray(RE::TESObjectCELL* cell,V a,V b,V& hit){
    auto* world=cell?cell->GetbhkWorld():nullptr;if(!world){hit=a;return true;}
    V direction=Unit(b-a);
    for(int skip=0;skip<64;++skip){
        RE::bhkPickData pick{};pick.rayInput.from=RE::hkVector4(a/rules::meter);pick.rayInput.to=RE::hkVector4(b/rules::meter);
        pick.rayInput.filterInfo=static_cast<std::uint32_t>(RE::COL_LAYER::kLOS);
        pick.rayOutput.Reset();world->PickObject(pick);
        if(!pick.rayOutput.HasHit())return false;
        hit=a+(b-a)*pick.rayOutput.hitFraction;
        if(!ActorLayer(pick.rayOutput.rootCollidable->GetCollisionLayer()))return true;
        a=hit+direction*8.f;if((b-a)*direction<=0)return false;
    }
    // Fail closed if a dense actor scene exhausts the bounded ray traversal.
    hit=a;return true;
}
V Center(RE::Actor* a){V p=a->GetPosition();p.z+=std::clamp(a->GetBoundMax().z*.5f,25.f,85.f);return p;}
bool ClearLine(RE::TESObjectCELL* cell,V a,V b){V hit;return !Ray(cell,a,b,hit)||(hit-b).Length()<10.f;}
void Cast(RE::Actor* c,RE::Actor* target,int index){
    if(!Victim(c,target))return;
    float magnitude=index==7?std::max(0.f,target->AsActorValueOwner()->GetActorValue(RE::ActorValue::kSpeedMult)):0.f;
    if(auto* mc=c->GetMagicCaster(Source::kInstant))mc->CastSpellImmediate(payload[index],false,target,1.f,false,magnitude,c);
}
void Dispel(RE::Actor* t,H caster,int index){
    if(!t)return;
    // Slow/root are globally non-stacking per target. Only remove this mod's
    // exact payload, even when its original caster has already been deleted.
    std::vector<RE::ActiveEffect*> remove;
    if(auto* list=t->AsMagicTarget()->GetActiveEffectList())for(auto* e:*list)if(e&&e->spell==payload[index])remove.push_back(e);
    for(auto* e:remove)e->Dispel(true);
}
template<class F>void Actors(RE::TESObjectCELL* cell,V center,float radius,F callback){
    if(!cell)return;
    auto visit=[&](RE::Actor* a){if(!a||(a->GetPosition()-center).Length()>radius)return;
        auto* other=a->GetParentCell();
        if(other==cell||(other&&other->GetRuntimeData().worldSpace&&other->GetRuntimeData().worldSpace==cell->GetRuntimeData().worldSpace))callback(a);};
    auto* player=RE::PlayerCharacter::GetSingleton();visit(player);
    if(auto* list=RE::ProcessLists::GetSingleton())for(auto h:list->highActorHandles){auto a=h.get();if(a&&a.get()!=player)visit(a.get());}
}
void Burst(RE::Actor* c,RE::TESObjectCELL* cell,V p,float radius,int spell,int visual){
    Flash(visual,cell,p,.35f);
    Actors(cell,p,radius+100,[&](RE::Actor* a){if(Victim(c,a)&&(Center(a)-p).Length()<=radius&&ClearLine(cell,p,Center(a)))Cast(c,a,spell);});
}
void Hit(Shot& s,RE::Actor* c,RE::Actor* target,RE::TESObjectCELL* cell,V p){
    if(s.kind==0){
        Cast(c,target,0);
        // Stacks are acknowledged by the actual engine ActiveMagicEffect start.
    }else if(s.kind==1)Cast(c,target,2);
    else if(s.kind==3)Cast(c,target,4);
}
// Sort continuous segment/actor intersections, then clip them against the
// nearest world collision. An actor behind a wall can never be hit by the sweep.
std::vector<std::pair<float,RE::Actor*>> Sweep(RE::Actor* c,RE::TESObjectCELL* cell,V a,V b){
    std::vector<std::pair<float,RE::Actor*>> hits;
    Actors(cell,(a+b)*.5f,(b-a).Length()*.5f+220,[&](RE::Actor* t){
        if(!Victim(c,t))return;V p=Center(t);
        float f=rules::segmentParameter(p.x,p.y,p.z,a.x,a.y,a.z,b.x,b.y,b.z);
        float r=std::clamp(t->GetBoundMax().x-t->GetBoundMin().x,28.f,120.f)*.5f+12;
        V q=a+(b-a)*f;V d=q-p;
        const float halfHeight=std::clamp(t->GetBoundMax().z*.5f,30.f,100.f);
        if(d.x*d.x+d.y*d.y<=r*r&&std::abs(d.z)<=halfHeight)hits.emplace_back(f,t);
    });
    std::sort(hits.begin(),hits.end(),[](auto& a,auto& b){return a.first<b.first;});return hits;
}
void SlowTarget(Shot& s,RE::Actor* c,RE::Actor* t,bool final){
    auto& slow=slows[t->GetFormID()];
    if(final&&s.chilled.contains(t->GetFormID())&&s.chilled[t->GetFormID()]>now&&slow.immuneUntil<=now){
        // Race keyword excludes creatures whose locomotion should not be rooted.
        if(!t->HasKeywordString("ActorTypeDragon")&&!t->HasKeywordString("ActorTypeGiant")&&!t->HasKeywordString("ImmuneParalysis")){
            Dispel(t,slow.rootCaster,7);Cast(c,t,7);
            if(t->AsMagicTarget()->HasMagicEffect(payload[7]->effects[0]->baseEffect)){
                slow.rootCaster=c->CreateRefHandle();slow.rootUntil=now+.7f;slow.immuneUntil=now+6.f;}
        }
    }
    Dispel(t,slow.caster,6);Cast(c,t,6);slow.target=t->CreateRefHandle();slow.caster=c->CreateRefHandle();slow.until=now+2;
    if(t->AsMagicTarget()->HasMagicEffect(payload[6]->effects[0]->baseEffect))s.chilled[t->GetFormID()]=now+2;
}
bool Advance(Shot& s,float dt){
    auto* c=Actor(s.caster);auto* cell=RE::TESForm::LookupByID<RE::TESObjectCELL>(s.cell);
    if(!c||c->IsDead()||!cell||!cell->IsAttached()||c->GetParentCell()!=cell)return false;
    s.age+=dt;
    if(s.kind==2){
        while(s.band<4&&s.age>=s.nextBand){
            V p=s.start+s.dir*((2+3*s.band)*rules::meter),ground;
            if(!ClearLine(cell,s.previousGround+V{0,0,35},p+V{0,0,35})||!Ray(cell,p+V{0,0,90},p-V{0,0,140},ground)||std::abs(ground.z-s.previousGround.z)>110)return false;
            s.previousGround=ground;p=ground+V{0,0,8};
            Flash(6,cell,p,.45f,{0,0,std::atan2(s.dir.x,s.dir.y)});
            Actors(cell,p,2*rules::meter,[&](RE::Actor* t){
                if(!Victim(c,t))return;V d=t->GetPosition()-p;
                float along=d*s.dir;float across=d.x*s.dir.y-d.y*s.dir.x;
                if(std::abs(along)<=rules::meter&&std::abs(across)<=1.5f*rules::meter&&std::abs(d.z)<100&&ClearLine(cell,p+V{0,0,25},Center(t))){Cast(c,t,3);SlowTarget(s,c,t,s.band==3);}
            });
            ++s.band;s.nextBand+=.22f;
        }
        return s.band<4;
    }
    if(s.anchor){
        if(s.age>=1.2f){Burst(c,cell,s.pos,2.5f*rules::meter,5,7);return false;}
        if(s.age>=.9f)if(auto v=s.visual.get())v->SetScale(std::max(.05f,(1.2f-s.age)/.3f));return true;
    }
    if(s.age>=3)return false;
    float step=std::min(dt*2200.f,(s.kind==1&&!s.returning?18*rules::meter-s.travel:8192.f));
    if(s.returning){s.dir=Unit(s.endpoint-s.pos);step=std::min(step,(s.endpoint-s.pos).Length());}
    V from=s.pos,to=from+s.dir*std::max(0.f,step),wall;
    bool blocked=Ray(cell,from,to,wall);if(blocked)to=wall-s.dir*2;
    auto hits=Sweep(c,cell,from,to);
    for(auto& [f,t]:hits){
        auto& leg=s.returning?s.inbound:s.outbound;if(!leg.insert(t->GetFormID()).second)continue;
        V point=from+(to-from)*f;Hit(s,c,t,cell,point);
        if(s.kind==0)return false;
        if(s.kind==3){to=point;blocked=true;break;}
    }
    s.travel+=(to-from).Length();s.pos=to;
    if(auto v=s.visual.get()){
        v->SetPosition(s.pos);
        if(s.kind==1)v->SetAngle({-std::asin(std::clamp(s.dir.z,-1.f,1.f)),0,std::atan2(s.dir.x,s.dir.y)});
    }
    if(s.kind==3&&blocked){Delete(s.visual);s.visual=Visual(5,cell,s.pos);s.anchor=true;s.age=0;SaveRegistry();return true;}
    if(s.kind==1){
        if(s.returning)return !blocked&&(s.endpoint-s.pos).Length()>3;
        if(blocked||s.travel>=18*rules::meter-1){s.returning=true;s.endpoint=Center(c);s.dir=Unit(s.endpoint-s.pos);s.pos+=s.dir*4;}
        return true;
    }
    return !blocked;
}
void Tick(float delta){
    if(!ready||Paused())return;
    const float dt=std::clamp(delta,0.f,.25f);if(dt<=0)return;now+=dt;marks.expire(now);
    std::erase_if(marks.marks,[](auto& pair){auto* c=RE::TESForm::LookupByID<RE::Actor>(pair.first.first);auto* t=RE::TESForm::LookupByID<RE::Actor>(pair.first.second);
        // Keep a dead target's short-lived mark until the primary-effect
        // callback arrives, so a lethal third hit can still detonate.
        return !c||c->IsDead()||!t||!c->GetParentCell()||c->GetParentCell()->GetFormID()!=pair.second.cell||t->GetParentCell()!=c->GetParentCell();});
    std::erase_if(reservations,[](auto& r){auto c=Actor(r.caster);if(!c||c->IsDead())return true;
        if(!r.released){auto* mc=c->GetMagicCaster(r.hand);if(mc&&Kind(mc->currentSpell)==r.kind&&mc->state.any(RE::MagicCaster::State::kCharging,RE::MagicCaster::State::kReady))r.end=now+2;}
        return r.end<=now;});
    for(auto it=shots.begin();it!=shots.end();){if(!Advance(*it,dt)){Delete(it->visual);it=shots.erase(it);SaveRegistry();}else ++it;}
    for(auto it=fx.begin();it!=fx.end();){
        if(it->follow){auto* t=Actor(it->follow);auto* c=Actor(it->owner);auto r=it->ref.get();
            if(!t||t->IsDead()||!c||c->IsDead()||t->GetParentCell()!=c->GetParentCell())it->end=now;
            else if(r)r->SetPosition(Center(t)+it->offset);}
        if(it->end<=now){Delete(it->ref);it=fx.erase(it);SaveRegistry();}else ++it;}
    for(auto it=slows.begin();it!=slows.end();){auto& s=it->second;auto* t=Actor(s.target);
        if(s.rootUntil>0&&s.rootUntil<=now){Dispel(t,s.rootCaster,7);s.rootUntil=0;}
        if(s.until<=now)Dispel(t,s.caster,6);
        auto* source=Actor(s.caster);
        if(!t||!source||source->IsDead()||source->GetParentCell()!=t->GetParentCell()){
            if(s.until>0)Dispel(t,s.caster,6);if(s.rootUntil>0)Dispel(t,s.rootCaster,7);s.until=0;s.rootUntil=0;
            if(!t||s.immuneUntil<=now)it=slows.erase(it);else ++it;
        }else if(s.immuneUntil<=now&&s.until<=now)it=slows.erase(it);else ++it;
    }
}
bool Available(RE::ActorMagicCaster* mc,int kind){
    if(kind<0)return true;if(!ready||shots.size()+reservations.size()>=256)return false;
    H owner=mc->actor->CreateRefHandle();int active=0,reserved=0;
    for(auto& s:shots)if(s.caster==owner&&s.kind==kind)++active;
    for(auto& r:reservations)if(r.caster==owner&&r.kind==kind){if(r.hand==mc->castingSource&&!r.released)return true;++reserved;}
    return rules::canStart(kind,active,reserved);
}
using CheckFn=bool(*)(RE::ActorMagicCaster*,RE::MagicItem*,bool,float*,RE::MagicSystem::CannotCastReason*,bool);
REL::Relocation<CheckFn> originalCheck;
bool Check(RE::ActorMagicCaster* mc,RE::MagicItem* item,bool dual,float* strength,RE::MagicSystem::CannotCastReason* reason,bool base){
    if(mc->actor&&!Available(mc,Kind(item))){if(reason)*reason=RE::MagicSystem::CannotCastReason::kMultipleCast;return false;}return originalCheck(mc,item,dual,strength,reason,base);
}
using ChargeFn=bool(*)(RE::ActorMagicCaster*);REL::Relocation<ChargeFn> originalCharge;
bool Charge(RE::ActorMagicCaster* mc){
    int k=Kind(mc->currentSpell);if(mc->actor&&!Available(mc,k))return false;
    bool ok=originalCharge(mc);if(ok&&k>=0&&mc->actor){H h=mc->actor->CreateRefHandle();
        std::erase_if(reservations,[&](auto& r){return r.caster==h&&r.hand==mc->castingSource&&!r.released;});
        reservations.push_back({h,mc->castingSource,k,now+30,false});}
    return ok;
}
using InterruptFn=void(*)(RE::ActorMagicCaster*,bool);REL::Relocation<InterruptFn> originalInterrupt;
void Interrupt(RE::ActorMagicCaster* mc,bool deplete){if(mc->actor){H h=mc->actor->CreateRefHandle();std::erase_if(reservations,[&](auto& r){return r.caster==h&&r.hand==mc->castingSource&&!r.released;});}originalInterrupt(mc,deplete);}
using CastFn=void(*)(RE::ActorMagicCaster*,bool,std::uint32_t,RE::MagicItem*);REL::Relocation<CastFn> originalCast;
void Release(RE::ActorMagicCaster* mc,bool cast,std::uint32_t arg,RE::MagicItem* item){
    if(cast&&Kind(item?item:mc->currentSpell)>=0&&mc->actor){H h=mc->actor->CreateRefHandle();for(auto& r:reservations)if(r.caster==h&&r.hand==mc->castingSource&&!r.released){r.released=true;r.end=now+2;break;}}
    originalCast(mc,cast,arg,item);
}
using MissileFn=void(*)(RE::MissileProjectile*,float);REL::Relocation<MissileFn> originalMissile;
void Missile(RE::MissileProjectile* p,float dt){
    auto& d=p->GetProjectileRuntimeData();int kind=Kind(d.spell);
    if(kind<0){originalMissile(p,dt);return;}
    if(Paused())return;
    auto handle=p->CreateRefHandle();{
        std::scoped_lock lock(carrierMutex);if(!intercepted.insert(handle.native_handle()).second)return;
        if(intercepted.size()>8192){intercepted.clear();intercepted.insert(handle.native_handle());}}
    // Projectile updates may be dispatched by engine workers. Never mutate the
    // world, spell queues or helper references from that callback.
    auto shooter=d.shooter;auto hand=d.castingSource;auto velocity=d.velocity;auto position=p->GetPosition();
    auto generation=epoch.load();
    SKSE::GetTaskInterface()->AddTask([handle,shooter,hand,velocity,position,kind,generation]{
    if(generation!=epoch.load())return;
    auto ref=handle.get();if(!ref)return;
    auto* caster=Actor(shooter);auto* cell=ref->GetParentCell();
    if(ready&&caster&&cell&&shots.size()<256){
        V direction=Unit(velocity);
        Shot s{};s.id=++shotID;s.kind=kind;s.caster=shooter;s.cell=cell->GetFormID();s.hand=hand;s.pos=position;s.dir=direction;
        s.start=caster->GetPosition();s.previousGround=s.start;
        if(kind==2){s.dir.z=0;s.dir=Unit(s.dir);}else s.visual=Visual(kind,cell,s.pos);
        shots.push_back(std::move(s));
        auto it=std::find_if(reservations.begin(),reservations.end(),[&](auto& r){return r.caster==shooter&&r.kind==kind&&r.hand==hand;});
        if(it!=reservations.end())reservations.erase(it);SaveRegistry();
    }
    // Carrier has no gameplay effect and never enters the engine impact path.
    ref->Disable();ref->SetDelete(true);
    });
}
using UpdateFn=void(*)(RE::PlayerCharacter*,float);REL::Relocation<UpdateFn> originalUpdate;
void Update(RE::PlayerCharacter* p,float dt){originalUpdate(p,dt);Tick(dt);}
void Reset(bool loading){
    ++epoch;
    if(!loading){for(auto& s:shots)Delete(s.visual);for(auto& f:fx)Delete(f.ref);
        for(auto& [id,s]:slows){Dispel(Actor(s.target),s.caster,6);Dispel(Actor(s.target),s.rootCaster,7);}}
    shots.clear();fx.clear();marks.marks.clear();slows.clear();reservations.clear();{std::scoped_lock lock(carrierMutex);intercepted.clear();}now=0;
    if(loading&&registry)registry->ForEachForm([](RE::TESForm* f){if(auto* r=f->As<RE::TESObjectREFR>();Owned(r)){r->Disable();r->SetDelete(true);}return RE::BSContainer::ForEachResult::kContinue;});SaveRegistry();
}
void Message(SKSE::MessagingInterface::Message* m){
    if(m->type==SKSE::MessagingInterface::kPreLoadGame){Reset(false);ready=false;}
    if(m->type==SKSE::MessagingInterface::kPostLoadGame||m->type==SKSE::MessagingInterface::kNewGame){Reset(true);ready=recordsValid;}
    if(m->type!=SKSE::MessagingInterface::kDataLoaded)return;
    auto* data=RE::TESDataHandler::GetSingleton();bool valid=true;
    auto checkEffects=[](RE::MagicItem* item, std::uint32_t expected){
        if(!item||item->effects.size()!=1||!item->effects[0]||!item->effects[0]->baseEffect){
            logger::error("Invalid staff magic item {:06X}: missing loaded effect; check ESP record order",expected);return false;
        }
        auto* effect=item->GetCostliestEffectItem();
        if(!effect||effect!=item->effects[0]){
            logger::error("Invalid staff magic item {:06X}: no selectable primary effect",expected);return false;
        }
        logger::info("Staff magic item {:06X}: effect {:08X}, cost {}, school {}",expected,
            effect->baseEffect->GetFormID(),effect->cost,static_cast<int>(effect->baseEffect->GetMagickSkill()));
        return true;
    };
    for(int i=0;i<4;++i){enchant[i]=data->LookupForm<RE::EnchantmentItem>(0xB30+i,plugin);valid&=checkEffects(enchant[i],0xB30+i);}
    for(int i=0;i<8;++i){payload[i]=data->LookupForm<RE::SpellItem>(0xB48+i,plugin);visuals[i]=data->LookupForm<RE::TESObjectSTAT>(0xB50+i,plugin);valid&=checkEffects(payload[i],0xB48+i)&&visuals[i];}
    registry=data->LookupForm<RE::BGSListForm>(0xB59,plugin);valid&=registry!=nullptr;
    if(!valid){logger::error("Staff records missing; hooks not installed");return;}
    REL::Relocation<std::uintptr_t> mc{RE::VTABLE_ActorMagicCaster[0]};
    originalCheck=mc.write_vfunc(0xA,Check);originalCharge=mc.write_vfunc(4,Charge);originalInterrupt=mc.write_vfunc(8,Interrupt);originalCast=mc.write_vfunc(9,Release);
    REL::Relocation<std::uintptr_t> missile{RE::VTABLE_MissileProjectile[0]};originalMissile=missile.write_vfunc(0xAB,Missile);
    REL::Relocation<std::uintptr_t> player{RE::VTABLE_PlayerCharacter[0]};originalUpdate=player.write_vfunc(0xAD,Update);
    recordsValid=true;ready=true;logger::info("Four staff prototypes ready (SE 1.5.97); B00-B7F records");
}
void RedApplied(RE::StaticFunctionTag*,RE::Actor* caster,RE::Actor* target){
    if(!caster||!target)return;
    auto c=caster->CreateRefHandle(),t=target->CreateRefHandle();auto generation=epoch.load();
    SKSE::GetTaskInterface()->AddTask([c,t,generation]{
        if(!ready||generation!=epoch.load())return;auto* source=Actor(c);auto* victim=Actor(t);
        if(!source||source->IsDead()||!victim||Friendly(source,victim))return;
        auto* cell=victim->GetParentCell();if(!cell||!cell->IsAttached()||source->GetParentCell()!=cell)return;
        if(victim->AsActorValueOwner()->GetActorValue(RE::ActorValue::kResistFire)>=100||victim->AsActorValueOwner()->GetActorValue(RE::ActorValue::kResistMagic)>=100)return;
        V p=Center(victim);
        std::erase_if(fx,[&](auto& f){if(f.follow==t&&f.owner==c){Delete(f.ref);return true;}return false;});
        if(marks.hit(source->GetFormID(),victim->GetFormID(),now,cell->GetFormID()))Burst(source,cell,p,2*rules::meter,1,4);
        else{
            int count=marks.marks.at({source->GetFormID(),victim->GetFormID()}).stacks;
            for(int i=0;i<count;++i){
                if(fx.size()>=128){Delete(fx.front().ref);fx.erase(fx.begin());}
                V offset{float(i*14-7),0,24};auto ref=Visual(0,cell,p+offset);if(ref)fx.push_back({ref,now+4,t,c,offset});
            }SaveRegistry();
        }
    });
}
bool Register(RE::BSScript::IVirtualMachine* vm){vm->RegisterFunction("RedApplied","AAStaffRuntime",RedApplied);return true;}
}
extern "C" __declspec(dllexport) bool SKSEAPI SKSEPlugin_Load(const SKSE::LoadInterface* skse){
    REL::Module::reset();SKSE::Init(skse);
    if(auto dir=SKSE::log::log_directory()){
        auto sink=std::make_shared<spdlog::sinks::basic_file_sink_mt>((*dir/"ArcaneStaves.log").string(),true);
        spdlog::set_default_logger(std::make_shared<spdlog::logger>("ArcaneStaves",sink));spdlog::flush_on(spdlog::level::info);
    }
    if(REL::Module::get().version()!=REL::Version(1,5,97,0)){logger::error("Unsupported runtime; staff native disabled");return false;}
    return SKSE::GetPapyrusInterface()->Register(Register)&&SKSE::GetMessagingInterface()->RegisterListener("SKSE",Message);
}

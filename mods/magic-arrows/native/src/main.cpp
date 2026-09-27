#ifdef UNIFIED_WORKSHOP
#include "../../../durability-manager/native/src/PrismaUI_API.h"
#include "../../../../shared/panel-power/panel_power.h"
#else
#include "PrismaUI_API.h"
#include "panel_power.h"
#endif
#include <nlohmann/json.hpp>
#include <atomic>
#include "crafting.h"
#include "normal_crafting.h"
#include "crafting_access.h"
#include "prototype_catalog.h"
#include "runtime_impact.h"
#include "follower_ammo.h"
#include "ammo_queue.h"
#include "craft_order.h"
#include <ranges>
#ifdef UNIFIED_WORKSHOP
#include "workshop_bridge.h"
#include "workshop_ui.h"
#include "legacy_queue.h"
namespace { std::string legacySaveName; }
#endif

namespace {
using json=nlohmann::json;
#ifdef UNIFIED_WORKSHOP
unified_workshop::WorkshopUI* api=nullptr;
#else
PRISMA_UI_API::IVPrismaUI1* api=nullptr;
#endif
PrismaView view=0;
bool loaded=false,ready=false,panelVisible=false;
ULONGLONG openedAt=0;
std::string activePage="equipment",activeCraftMode="magic";
std::uint64_t generation=0;
json workshopReply=nullptr;
std::unordered_set<RE::FormID> auditedSpells;
struct Binding { std::string key="W"; std::uint32_t code=0x11; bool shift=true,ctrl=false,alt=false; } binding;
constexpr std::array<std::uint32_t,26> codes{0x1E,0x30,0x2E,0x20,0x12,0x21,0x22,0x23,0x17,0x24,0x25,0x26,0x32,0x31,0x18,0x19,0x10,0x13,0x1F,0x14,0x16,0x2F,0x11,0x2D,0x15,0x2C};
std::optional<std::uint32_t> KeyCode(const std::string& key) {
    if(key.size()==1 && key[0]>='A' && key[0]<='Z') return codes[key[0]-'A'];
    for(int i=1;i<=12;++i) if(key=="F"+std::to_string(i)) return i<=10?0x3A+i:(i==11?0x57:0x58);
    return {};
}
auto ConfigPath() { return std::filesystem::path(REL::Module::get().filePath().data()).parent_path()/"Data/SKSE/Plugins/MagicArrows.ini"; }
void LoadConfig() {
    auto path=ConfigPath();wchar_t text[32]{};
    follower_ammo::consume=GetPrivateProfileIntW(L"Followers",L"ConsumeMagicArrows",1,path.c_str())!=0;
    craft_order::pauseInCombat=GetPrivateProfileIntW(L"Crafting",L"PauseInCombat",1,path.c_str())!=0;
#ifdef UNIFIED_WORKSHOP
    soul_pool::enabled=GetPrivateProfileIntW(L"SoulPool",L"Enabled",1,path.c_str())!=0;
#else
    // The standalone panel has no soul pool page yet, so it keeps the 2.3.8 behaviour.
    soul_pool::enabled=GetPrivateProfileIntW(L"SoulPool",L"Enabled",0,path.c_str())!=0;
#endif
    crafting::GenericPercent=std::clamp(static_cast<int>(GetPrivateProfileIntW(L"Crafting",L"GenericMaterialPercent",50,path.c_str())),0,100);
    GetPrivateProfileStringW(L"Hotkey",L"Key",L"W",text,32,path.c_str());
    std::string key;for(auto* ch=text;*ch;++ch){if(*ch>127){key.clear();break;}key.push_back(static_cast<char>(*ch));}
    std::transform(key.begin(),key.end(),key.begin(),[](unsigned char c){return static_cast<char>(std::toupper(c));});
    if(auto c=KeyCode(key)){binding.key=key;binding.code=*c;}
    auto flag=[&](const wchar_t* name,bool fallback){
        wchar_t value[16]{};GetPrivateProfileStringW(L"Hotkey",name,fallback?L"true":L"false",value,16,path.c_str());
        return _wcsicmp(value,L"true")==0 || wcscmp(value,L"1")==0;
    };
    binding.shift=flag(L"Shift",true);binding.ctrl=flag(L"Ctrl",false);binding.alt=flag(L"Alt",false);
    // An unmodified movement key must not intercept walking.
    if(!binding.shift&&!binding.ctrl&&!binding.alt&&binding.key.size()==1)binding=Binding{};
}
bool SaveConfig(const Binding& b) {
    auto path=ConfigPath();std::wstring key(b.key.begin(),b.key.end());
    // Only the Hotkey section is replaced. Preserve PanelPower and future sections.
    std::wstring section=L"Key="+key;section.push_back(0);
    for(auto [name,value]:{std::pair{L"Shift",b.shift},std::pair{L"Ctrl",b.ctrl},std::pair{L"Alt",b.alt}}){section+=name;section+=value?L"=true":L"=false";section.push_back(0);}
    section.push_back(0);return WritePrivateProfileSectionW(L"Hotkey",section.c_str(),path.c_str())!=0;
}
std::string Name(RE::TESForm* form) {const char* n=form?form->GetName():nullptr;return n&&*n?n:"未命名";}
std::string Family(RE::TESAmmo* ammo) {
    if(auto* b=runtime_binding::Bound(ammo))return runtime_rules::families[b->family];
    if(runtime_binding::Index(ammo)>=0)return "arcane";
    if(auto* adapter=crafting::ForAmmo(ammo))return adapter->family;
    auto* data=RE::TESDataHandler::GetSingleton();if(!data)return "normal";
    for(auto [id,name]:prototypes::entries)
        if(ammo==data->LookupForm<RE::TESAmmo>(id,"MagicArrows.esp"))return name;
    return "normal";
}
// The displayed status and craftable flag share the same final availability decision.
json SpellEligibility(RE::SpellItem* s,bool craftable,bool dynamic,const std::string& reason) {
    const bool sustained=runtime_binding::Sustained(s);
    if(craftable){
        if(dynamic)return {{"status","candidate"},{"releaseMode",sustained?"sustained":"instant"},{"reasons",json::array({sustained?"命中点持续施放 3 秒，费用按 3 秒施法参考量计算":"从命中点释放封存法术；使用实际射手归属"})}};
        return {{"status","candidate"},{"releaseMode","instant"},{"reasons",json::array({"使用固定元素适配，不继承原法术全部附加效果"})}};
    }
    using D=spell_compatibility::Denial;
    const auto denial=runtime_binding::Compatibility(s).denial;
    const bool excluded=denial==D::selfOnly||denial==D::nonCombatTarget||denial==D::specialEffect||denial==D::casting||denial==D::delivery;
    std::string why=reason.empty()?(runtime_binding::ready?"法术费用无效，无法计算材料":"运行时封存组件未就绪，请重新读档"):reason;
    return {{"status",excluded?"excluded":"review"},{"releaseMode",sustained?"sustained":"instant"},{"reasons",json::array({why})}};
}
json MaterialCharges(RE::TESBoundObject* item){json result=json::object();for(int f=0;f<12;++f)result[runtime_rules::families[f]]=crafting::Units(item,f);return result;}
json State(std::string message={}) {
    auto* p=RE::PlayerCharacter::GetSingleton();
    json arrows=json::array(),spells=json::array(),materials=json::array(),recipes=json::array();
    if(p&&loaded){
        auto inv=p->GetInventory();
        for(auto& [item,value]:inv){
            auto& [count,entry]=value;if(!item||count<=0||!entry)continue;
            if(auto* a=item->As<RE::TESAmmo>();a&&(a->GetPlayable()||(runtime_binding::Index(a)>=0&&runtime_binding::slots[runtime_binding::Index(a)].occupied))){
                auto* bound=runtime_binding::Bound(a);
                arrows.push_back({{"id",a->GetFormID()},{"name",Name(a)},{"count",count},{"damage",a->GetRuntimeData().data.damage},{"family",Family(a)},{"spellBound",crafting::IsOutput(a)||runtime_binding::Index(a)>=0},{"usable",a->GetPlayable()},{"runtimeBase",runtime_binding::Base(a)},{"adapter",bound?json{{"runtime",true},{"family",runtime_rules::families[bound->family]},{"castRoute",runtime_binding::RouteName(bound->spell)},{"releaseMode",runtime_binding::Sustained(bound->spell)?"sustained":"instant"},{"seconds",runtime_binding::Sustained(bound->spell)?sustained_rules::seconds:0.f}}:crafting::ForAmmo(a)?crafting::Info(*crafting::ForAmmo(a)):json(nullptr)},{"equipped",entry->IsWorn()},{"bolt",a->IsBolt()},{"fireballBase",crafting::Index(a->GetFormID())>=0}});
            }else if(activePage=="craft"&&activeCraftMode=="magic"&&!entry->IsQuestObject()){
                const auto kind=crafting::Kind(item);
                if(kind==crafting::MaterialKind::ingredient||kind==crafting::MaterialKind::potion||kind==crafting::MaterialKind::poison)
                    materials.push_back({{"id",item->GetFormID()},{"name",Name(item)},{"count",count},{"kind",crafting::KindName(item)},{"charges",MaterialCharges(item)}});
            }
        }
        if(activePage=="craft"){
        if(activeCraftMode=="magic"){
        std::unordered_set<RE::FormID> seen;
        auto add=[&](RE::SpellItem* s){
            if(!s||s->GetSpellType()!=RE::MagicSystem::SpellType::kSpell||!seen.insert(s->GetFormID()).second)return;
            auto* file=s->GetFile(0);auto cost=s->CalculateMagickaCost(p);auto reason=runtime_binding::Unsupported(s);bool dynamic=runtime_binding::ready&&reason.empty()&&std::isfinite(cost)&&cost>=0;
            const bool craftable=dynamic||crafting::ForSpell(s)!=nullptr;
            auto eligibility=SpellEligibility(s,craftable,dynamic,reason);
            if(auditedSpells.insert(s->GetFormID()).second){
                auto* primary=runtime_binding::PrimaryProjectile(s);auto* av=s->GetAVEffect();
                logger::info("Spell route id={:08X} casting={} delivery={} route={} effects={}",s->GetFormID(),static_cast<int>(s->GetCastingType()),static_cast<int>(s->GetDelivery()),runtime_binding::RouteName(s),s->effects.size());
                logger::info("Spell eligibility id={:08X} name={} craftable={} cost={} reason={} primary={:08X} costEffect={:08X}",s->GetFormID(),Name(s),craftable,cost,eligibility.dump(),primary?primary->GetFormID():0,av?av->GetFormID():0);
                for(auto* effect:s->effects)if(auto* e=effect?effect->baseEffect:nullptr){auto* proj=e->data.projectileBase;logger::info("  Effect {:08X} archetype={} casting={} delivery={} projectile={:08X} type={} conditional={}",e->GetFormID(),RE::EffectArchetypeToString(e->GetArchetype()),static_cast<int>(e->data.castingType),static_cast<int>(e->data.delivery),proj?proj->GetFormID():0,proj?static_cast<int>(proj->data.types.get()):0,bool(effect->conditions.head||e->conditions.head));}
            }
            spells.push_back({{"id",s->GetFormID()},{"name",Name(s)},{"cost",cost},
                {"source",file?std::string(file->GetFilename()):"运行时法术"},{"eligibility",eligibility},{"craftable",craftable},{"adapter",dynamic?runtime_binding::Info(s,p):crafting::ForSpell(s)?crafting::Info(*crafting::ForSpell(s),p):json(nullptr)}});
        };
        if(auto* base=p->GetActorBase())if(auto* list=base->GetSpellList())for(std::uint32_t i=0;list->spells&&i<list->numSpells;++i)add(list->spells[i]);
        for(auto* s:p->GetActorRuntimeData().addedSpells)add(s);
        }else recipes=normal_crafting::Rows(p);
    }
    } // spell and recipe data are only requested by the crafting page
    auto sort=[](json& xs){std::sort(xs.begin(),xs.end(),[](const json& a,const json& b){return a["name"].get<std::string>()<b["name"].get<std::string>();});};
    sort(arrows);sort(spells);sort(materials);sort(recipes);
    const auto access = loaded ? crafting_access::Nearby(p) : crafting_access::Access{};
    return {{"craftingAccess",{{"magic",access.magic},{"normal",access.normal}}},{"page",activePage},{"mode",activeCraftMode},{"nativeEscape",true},{"ammoQueue",ammo_queue::State(p)},{"alchemy",crafting::Alchemy(p)},{"resources",{{"magicka",p&&loaded?p->AsActorValueOwner()->GetActorValue(RE::ActorValue::kMagicka):0.f},{"gold",p&&loaded?crafting::Count(p,RE::TESForm::LookupByID<RE::TESBoundObject>(0xF)):0}}},{"workshopReply",workshopReply},{"followers",{{"consumeMagicArrows",follower_ammo::consume},{"available",follower_ammo::installed}}},{"runtimeSlots",{{"ready",runtime_binding::ready},{"capacity",256},{"free",runtime_binding::Free()}}},{"normalQuote",normal_crafting::quote},{"quote",runtime_binding::quote.is_null()?crafting::quote:runtime_binding::quote},{"fireballRecipe",{{"gold",5},{"magicka",12},{"charge",10},{"damage",40}}},{"version","1.1.0"},{"arrows",arrows},{"spells",spells},{"materials",materials},{"recipes",recipes},{"message",message},
        {"orders",craft_order::State()},
        {"soulPool",soul_pool::State(p)},
        {"materialGenericPercent",crafting::GenericPercent},
        {"hotkey",{{"key",binding.key},{"shift",binding.shift},{"ctrl",binding.ctrl},{"alt",binding.alt}}},
        {"loaded",loaded},{"powerAvailable",RE::TESDataHandler::GetSingleton()&&RE::TESDataHandler::GetSingleton()->LookupForm<RE::SpellItem>(0x840,"MagicArrows.esp")!=nullptr}};
}
void Send(std::string message={}) {
    if(!api||!view||!ready||!loaded)return;
    auto started=GetTickCount64();
    auto script="window.MagicArrows?.receiveState("+State(std::move(message)).dump(-1,' ',false,json::error_handler_t::replace)+");";
    api->Invoke(view,script.c_str());
    logger::info("State sent page={} bytes={} elapsed={}ms",activePage,script.size(),GetTickCount64()-started);
}
void Close(){
#ifdef UNIFIED_WORKSHOP
    unified_workshop::CloseEquipment();
#else
    panelVisible=false;crafting::Reset();normal_crafting::Reset();runtime_binding::Reset();
    if(api&&view){api->Invoke(view,"window.MagicArrows?.closeDialog();");api->Unfocus(view);api->Hide(view);}
    logger::info("Panel closed; focus released");
#endif
}
// Only the SKSE task mutates pending state; the frame hook merely schedules it.
struct PendingEquip { RE::FormID id;std::uint64_t epoch;ULONGLONG started;unsigned frames=0;bool submitted=false;bool automatic=false;std::uint64_t queueRevision=0;};
std::optional<PendingEquip> pendingEquip;
std::atomic<bool> equipActive{false},equipTickQueued{false};
void CancelEquip(){if(pendingEquip&&pendingEquip->automatic)ammo_queue::tracker.Cancel();pendingEquip.reset();equipActive=false;}
void RequestEquip(RE::FormID id,bool automatic=false){
    pendingEquip=PendingEquip{id,generation,GetTickCount64(),0,false,automatic,ammo_queue::revision};equipActive=true;
}
void EquipTick(){
    if(!pendingEquip)return;
    auto& request=*pendingEquip;
    if(!loaded||request.epoch!=generation){CancelEquip();return;}
    auto* p=RE::PlayerCharacter::GetSingleton();auto* ui=RE::UI::GetSingleton();
    if(!p||p->IsDead()||panelVisible){CancelEquip();return;}
    const auto elapsed=GetTickCount64()-request.started;
    if(elapsed>8000){logger::warn("Equip timeout form={:08X} submitted={}",request.id,request.submitted);CancelEquip();RE::DebugNotification("箭矢装备未完成，请查看日志");return;}
    if(!ui||ui->GameIsPaused()||(api&&api->HasAnyActiveFocus()))return;
    auto* ammo=RE::TESForm::LookupByID<RE::TESAmmo>(request.id);
    if(!ammo||!ammo->GetPlayable()){CancelEquip();return;}
    if(request.automatic&&(!ammo_queue::enabled||request.queueRevision!=ammo_queue::revision)){CancelEquip();return;}
    if(request.automatic){auto* object=p->GetEquippedObject(false);auto* weapon=object?object->As<RE::TESObjectWEAP>():nullptr;if(!weapon||weapon->GetWeaponType()!=RE::WEAPON_TYPE::kBow){CancelEquip();return;}}
    if(p->GetCurrentAmmo()==ammo){logger::info("Equip confirmed form={:08X} elapsed={}ms",request.id,elapsed);const auto id=request.id;CancelEquip();ammo_queue::Observe(p,id);return;}
    if(request.automatic&&(ammo_queue::order.empty()||!ammo_queue_rules::Contains(ammo_queue::order,request.id)||ammo_queue::order.front()!=request.id||ammo_queue::Count(p,request.id)<=0)){CancelEquip();return;}
    if(request.submitted||++request.frames<2||elapsed<250)return;
    if(ui->IsMenuOpen("Loading Menu")||ui->IsMenuOpen("Main Menu")||!p->Is3DLoaded())return;
    auto inventory=p->GetInventory();auto it=inventory.find(ammo);
    if(it==inventory.end()||it->second.first<=0){CancelEquip();return;}
    auto* manager=RE::ActorEquipManager::GetSingleton();if(!manager){CancelEquip();return;}
    request.submitted=true;
    logger::info("Equip submit form={:08X} model={} frames={} elapsed={}ms",request.id,ammo->GetModel(),request.frames,elapsed);
    manager->EquipObject(p,ammo,nullptr,1,nullptr,true,false,true,false);
    logger::info("Equip request returned form={:08X}; awaiting current ammo",request.id);
}
void EquipFrame(){
    // Every frame while equipping; otherwise only four inventory checks a second.
    static std::atomic<ULONGLONG> lastQueueTick{0};const auto now=GetTickCount64();
    if(!equipActive.load()&&now-lastQueueTick.load()<250)return;
    if(equipTickQueued.exchange(true))return;lastQueueTick=now;
    if(auto* tasks=SKSE::GetTaskInterface())tasks->AddTask([]{equipTickQueued=false;
        if(pendingEquip){EquipTick();return;}
        // Queued crafting advances on the game thread; every resource is already locked.
        if(auto* player=RE::PlayerCharacter::GetSingleton())if(!craft_order::queue.empty()){
            auto* ui=RE::UI::GetSingleton();
            const bool panelOpen=panelVisible||(api&&api->HasAnyActiveFocus())||!loaded;
            const bool loading=ui&&(ui->IsMenuOpen("Loading Menu")||ui->IsMenuOpen("Main Menu"));
            craft_order::paused=craft_order_rules::Evaluate(panelOpen||(ui&&ui->GameIsPaused()),loading,player->IsDead(),player->IsInCombat(),craft_order::pauseInCombat);
            if(craft_order::paused==craft_order_rules::Pause::none)craft_order::Tick(player,"");
        }
        if(!loaded||panelVisible||ammo_queue::order.empty())return;
        auto* p=RE::PlayerCharacter::GetSingleton();auto* ui=RE::UI::GetSingleton();
        if(!p||p->IsDead()||!p->Is3DLoaded()||!ui||ui->GameIsPaused()||ui->IsMenuOpen("Loading Menu")||ui->IsMenuOpen("Main Menu")||(api&&api->HasAnyActiveFocus()))return;
        ammo_queue::Prune(p);if(!ammo_queue::enabled||ammo_queue::order.empty())return;
        auto* item=p->GetEquippedObject(false);auto* bow=item?item->As<RE::TESObjectWEAP>():nullptr;
        if(!bow||bow->GetWeaponType()!=RE::WEAPON_TYPE::kBow){ammo_queue::tracker.Reset();return;}
        const auto inventory=p->GetInventory();auto count=[&](RE::FormID id){auto* a=ammo_queue::Ammo(id);auto it=inventory.find(a);return a&&it!=inventory.end()?std::max(0,it->second.first):0;};
        auto* current=p->GetCurrentAmmo();
        auto next=ammo_queue::tracker.Tick(ammo_queue::order,current?current->GetFormID():0,count);
        if(next){logger::info("Ammo queue priority head={:08X}",next);RequestEquip(next,true);}
    });
    else equipTickQueued=false;
}
bool CanOpen(){auto* p=RE::PlayerCharacter::GetSingleton();auto* ui=RE::UI::GetSingleton();return loaded&&p&&!p->IsDead()&&ui&&!ui->GameIsPaused()&&!ui->IsMenuOpen("Main Menu")&&!ui->IsMenuOpen("Loading Menu")&&!ui->IsMenuOpen("Console");}
void Open(){
#ifdef UNIFIED_WORKSHOP
    unified_workshop::OpenArrowSection();
#else
    if(!api||!view||!CanOpen()||api->HasAnyActiveFocus())return;
    if(!ready){RE::DebugNotification("魔法箭工坊正在载入，请稍后重试");return;}
    try{runtime_binding::MergeInventory(RE::PlayerCharacter::GetSingleton());}
    catch(const std::exception& e){logger::warn("Arrow inventory merge skipped: {}",e.what());}
    ammo_queue::Normalize();
    api->Show(view);
    if(!api->Focus(view,true)){api->Hide(view);logger::warn("Panel focus request rejected");return;}
    auditedSpells.clear();normal_crafting::audit.clear();panelVisible=true;openedAt=GetTickCount64();logger::info("Panel opened");Send();
#endif
}
void Action(const char* raw){
    std::string copy=raw?raw:"{}";if(copy.size()>8192)return;
    if(auto* tasks=SKSE::GetTaskInterface())tasks->AddTask([copy=std::move(copy)]{
        try{
            workshopReply=nullptr;auto q=json::parse(copy);auto type=q.value("type",std::string{});
            if(type=="quote"||type=="craft"||type=="normalQuote"||type=="normalCraft"||type=="orderStart")workshopReply={{"type",type},{"requestID",q.value("requestID",std::uint64_t{})},{"ok",false}};
            if(type=="ready"){ready=true;if(api&&view&&api->HasFocus(view))Send();return;}
            if(type=="close"){if(q.value("reason",std::string{})!="hotkey"||GetTickCount64()-openedAt>250)Close();return;}
            if(!loaded||!api||!view||!api->HasFocus(view))return;
            logger::info("Action begin: {}",type);
            if(type=="inspect"){logger::info("Card selected form={:08X}",q.value("id",RE::FormID{}));return;}
            auto* player=RE::PlayerCharacter::GetSingleton();if(!player)return;
            if(type=="queueEdit"){ammo_queue::Edit(player,q);Send("使用队列已更新，将随角色存档保存");return;}
            if(type=="queueStart"){
                ammo_queue::Prune(player);
                auto next=ammo_queue_rules::Next(ammo_queue::order,0,[&](RE::FormID id){return ammo_queue::Count(player,id)>0;});
                if(!next){Send("队列中没有可用库存");return;}
                ammo_queue::enabled=true;ammo_queue::Suspend();Close();RequestEquip(next);return;
            }
            if(type=="cancelCraft"){crafting::Reset();normal_crafting::Reset();runtime_binding::Reset();Send();return;}
            if(type=="workshopMode"){auto mode=q.value("mode",std::string{});if(mode=="magic"||mode=="normal"){activeCraftMode=mode;crafting::Reset();normal_crafting::Reset();runtime_binding::Reset();}Send();return;}
            if(type=="page"){auto page=q.value("page",std::string{});if(page=="equipment"||page=="craft"||page=="settings"||page=="soul")activePage=page;Send();return;}
            if(type=="quote"||type=="craft"||type=="normalQuote"||type=="normalCraft"){
                const bool normal=type=="normalQuote"||type=="normalCraft";
                const auto access=crafting_access::Nearby(player);
                if(!(normal?access.normal:access.magic)){
                    crafting::Reset();normal_crafting::Reset();runtime_binding::Reset();
                    throw std::runtime_error(normal?"请靠近锻造炉、冶炼炉、磨刀石或护甲工作台后制作普通箭矢":"请靠近附魔台后制作魔法箭");
                }
            }
            if(type=="normalQuote"){runtime_binding::Reset();crafting::Reset();normal_crafting::Quote(player,q);workshopReply["ok"]=true;Send("普通箭费用已计算，请核对后确认");
            }else if(type=="normalCraft"){normal_crafting::Commit(player,q.at("token").get<std::uint64_t>());workshopReply["ok"]=true;Send("普通箭制作完成，成品已加入背包");
            }else if(type=="orderStart"){const auto started=craft_order::Start(q);workshopReply["ok"]=true;
                Send(started.value("chargeClamped",false)?"已加入制作队列；已达单批上限 100000 充能，超出部分不会增加产量":"已加入制作队列，离开附魔台后继续制作");
            }else if(type=="quote"){normal_crafting::Reset();runtime_binding::Reset();crafting::Reset();
                if(q.value("runtime",false))runtime_binding::Quote(player,q);else crafting::Quote(player,q);workshopReply["ok"]=true;Send("费用已计算，请核对后确认制作");
            }else if(type=="craft"){
#ifdef UNIFIED_WORKSHOP
                unified_workshop::ArrowCraftFeedback feedback;
#endif
                if(q.value("runtime",false))runtime_binding::Commit(player,q.at("token").get<std::uint64_t>());else crafting::Commit(player,q.at("token").get<std::uint64_t>());
#ifdef UNIFIED_WORKSHOP
                feedback.success = true;
#endif
                workshopReply["ok"]=true;Send("制作完成，魔法箭已加入背包");
            }else if(type=="equip"){
                auto id=q.value("id",RE::FormID{});auto* ammo=RE::TESForm::LookupByID<RE::TESAmmo>(id);
                if(!ammo||!ammo->GetPlayable()){Send("无法装备该箭矢");return;}
                auto inv=player->GetInventory();auto it=inv.find(ammo);
                if(it==inv.end()||it->second.first<=0){Send("背包中已没有这组箭矢");return;}
                auto* manager=RE::ActorEquipManager::GetSingleton();if(!manager){Send("装备管理器不可用");return;}
                if(!ammo->IsBolt()){
                    if(!ammo_queue::available){Send("队列保存组件不可用，无法将箭矢设为队首");return;}
                    ammo_queue::Normalize();ammo_queue::Prune(player);
                    if(!ammo_queue_rules::Promote(ammo_queue::order,id)){Send("无法将该箭矢设为队首");return;}
                    ammo_queue::enabled=true;ammo_queue::Suspend();
                }
                logger::info("Equip validated form={:08X}; waiting for resumed frames",id);
                Close();
                ammo_queue::tracker.Reset();RequestEquip(id);
            }else if(type=="followerSettings"){
                const bool consume=q.at("consumeMagicArrows").get<bool>();
                if(!follower_ammo::installed){Send("随从消耗组件未就绪");return;}
                if(!WritePrivateProfileStringW(L"Followers",L"ConsumeMagicArrows",consume?L"1":L"0",ConfigPath().c_str())){Send("配置保存失败，消耗规则未更改");return;}
                follower_ammo::consume=consume;Send(consume?"随从魔法箭按射击数量消耗":"随从箭矢消耗已恢复为游戏规则");
            }else if(type=="settings"){
                Binding b; b.key=q.at("key").get<std::string>();auto code=KeyCode(b.key);
                b.shift=q.at("shift").get<bool>();b.ctrl=q.at("ctrl").get<bool>();b.alt=q.at("alt").get<bool>();
                if(!code||(!b.shift&&!b.ctrl&&!b.alt&&b.key.size()==1)){Send("字母快捷键至少需要一个修饰键；也可以单独使用 F1–F12");return;}
                b.code=*code;if(!SaveConfig(b)){Send("配置文件保存失败，快捷键未更改");return;}binding=b;Send("快捷键已保存，立即生效");
            }else if(type=="soulUpgrade"){
                soul_pool::Upgrade(player);Send("灵魂池已扩容");
            }else if(type=="soulConvert"){
                std::vector<soul_pool::Request> requests;
                if(q.contains("items")&&q.at("items").is_array())
                    for(const auto& item:q.at("items"))requests.push_back({item.value("level",0),item.value("count",0)});
                else requests.push_back({q.value("level",0),q.value("count",1)});
                const auto result=soul_pool::Convert(player,requests);
                const int gems=result.value("gems",0);
                Send(gems>0?("已兑换 "+std::to_string(gems)+" 颗灵魂石，消耗 "+std::to_string(result.value("points",0))+" 点与 "+std::to_string(result.value("gold",0))+" 金币"):"灵魂点数或金币不足");
            }else if(type=="soulDeposit"){
                const int moved=soul_pool::Deposit(player,q.value("id",RE::FormID{}),q.value("count",1));
                Send(moved>0?"灵魂石已存入灵魂池":"灵魂池已满或没有可存入的灵魂石");
            }else if(type=="refresh")Send();
        }catch(const std::exception& e){logger::warn("Panel request rejected: {}",e.what());if(!workshopReply.is_null())workshopReply["error"]=e.what();Send(e.what());}
    });
}
class Input final:public RE::BSTEventSink<RE::InputEvent*>{
    RE::BSEventNotifyControl ProcessEvent(RE::InputEvent* const* events,RE::BSTEventSource<RE::InputEvent*>*) override {
        if(!events||!api||!view)return RE::BSEventNotifyControl::kContinue;
        // Native Escape remains active even when the embedded browser misses it.
        for(auto* e=*events;e;e=e->next){
            if(e->GetDevice()!=RE::INPUT_DEVICE::kKeyboard)continue;
            auto* b=e->AsButtonEvent();if(!b||!b->IsDown())continue;
            if(b->GetIDCode()==0x01){
                if(panelVisible&&api->HasFocus(view)){logger::info("Native Escape: dispatch one UI layer");api->Invoke(view,"window.MagicArrows?.escape();");}
                continue;
            }
            if(b->GetIDCode()!=binding.code)continue;
            auto down=[](int v){return (GetAsyncKeyState(v)&0x8000)!=0;};
            if(down(VK_SHIFT)!=binding.shift||down(VK_CONTROL)!=binding.ctrl||down(VK_MENU)!=binding.alt)continue;
            if(panelVisible&&api->HasFocus(view)){
                if(GetTickCount64()-openedAt>250)Close();
            }else if(!api->HasAnyActiveFocus()){
                if(auto* tasks=SKSE::GetTaskInterface())tasks->AddTask(Open);
            }
        }
        return RE::BSEventNotifyControl::kContinue;
    }
}input;
panel_power::Power power("MagicArrows.esp",Open);
void Message(SKSE::MessagingInterface::Message* m){
#ifdef UNIFIED_WORKSHOP
    if(m->type==SKSE::MessagingInterface::kPreLoadGame)legacySaveName=m->data?static_cast<const char*>(m->data):"";
#endif
    if(m->type==SKSE::MessagingInterface::kPreLoadGame){loaded=false;++generation;CancelEquip();ammo_queue::Suspend();
#ifdef UNIFIED_WORKSHOP
        panelVisible=false;crafting::Reset();normal_crafting::Reset();runtime_binding::Reset();
#else
        Close();
#endif
        runtime_sustained::Clear("preload");runtime_binding::Suspend();}
    if(m->type==SKSE::MessagingInterface::kNewGame||m->type==SKSE::MessagingInterface::kPostLoadGame){loaded=m->type==SKSE::MessagingInterface::kNewGame||m->data!=nullptr;++generation;CancelEquip();runtime_binding::Reset();crafting::Reset();normal_crafting::Reset();ammo_queue::Suspend();if(m->type==SKSE::MessagingInterface::kNewGame)ammo_queue::Revert(nullptr);if(loaded){runtime_sustained::AfterLoad();runtime_binding::Restore();ammo_queue::Normalize();}}
    power.OnMessage(m);
    if(m->type!=SKSE::MessagingInterface::kDataLoaded)return;
    runtime_sustained::afterUpdate=EquipFrame;crafting::Sync();runtime_binding::Init();runtime_impact::Install();runtime_sustained::Install();soul_capture::Install();follower_ammo::Install();normal_crafting::Init();
    LoadConfig();
#ifdef UNIFIED_WORKSHOP
    api=unified_workshop::GetWorkshopUI();
#else
    api=PRISMA_UI_API::RequestPluginAPI();
#endif
    if(!api){logger::error("PrismaUI v1 unavailable; MagicArrows panel disabled");return;}
#ifndef UNIFIED_WORKSHOP
    view=api->CreateView("MagicArrows/index.html",[](PrismaView v){
        logger::info("MagicArrows view ready: {}",v);
        if(auto* tasks=SKSE::GetTaskInterface())tasks->AddTask([]{ready=true;});
    });
    if(!view){logger::error("Failed to create MagicArrows view");return;}
    api->RegisterJSListener(view,"magicArrowsAction",Action);api->Hide(view);
    if(auto* device=RE::BSInputDeviceManager::GetSingleton())device->AddEventSink(&input);
#endif
    logger::info("MagicArrows 1.1.0 loaded; ability local ID 840; key {}",binding.key);
}
}
#ifdef UNIFIED_WORKSHOP
void unified_workshop::AttachArrows(std::uint64_t sharedView){view=sharedView;ready=true;}
void unified_workshop::SetArrowsVisible(bool visible){
    panelVisible=visible;
    if(visible&&loaded){openedAt=GetTickCount64();try{runtime_binding::MergeInventory(RE::PlayerCharacter::GetSingleton());}catch(const std::exception& e){logger::warn("Arrow merge: {}",e.what());}ammo_queue::Normalize();Send();}
    else{crafting::Reset();normal_crafting::Reset();runtime_binding::Reset();}
}
void unified_workshop::ArrowAction(const char* json){Action(json);}
void unified_workshop::SaveArrows(SKSE::SerializationInterface* serial){ammo_queue::Save(serial);}
void unified_workshop::RevertArrows(SKSE::SerializationInterface* serial){ammo_queue::Revert(serial);}
namespace {
void RestoreQueueWords(SKSE::SerializationInterface* serial,const std::vector<std::uint32_t>& words,std::uint32_t version=1){
    if(!ammo_queue_rules::ValidRecord(words,version))return;
    std::vector<RE::FormID> restored;
    for(std::size_t i=2;i<words.size();++i){RE::FormID id=0;if(serial->ResolveFormID(words[i],id)&&id&&!ammo_queue_rules::Contains(restored,id))restored.push_back(id);}
    ammo_queue::order=std::move(restored);ammo_queue::enabled=true; // Old mode values are intentionally ignored.
}
}
void unified_workshop::BeginLoadArrows(SKSE::SerializationInterface* serial){
    ammo_queue::Revert(serial);
    // Import the legacy UID without changing the old co-save. The next save writes
    // both modules under the retained durability UID. A current queue record wins.
    if(legacySaveName.empty())return;
    try{
        const auto logs=SKSE::log::log_directory();if(!logs)return;
        std::filesystem::path relative="Saves";
        if(auto* ini=RE::INISettingCollection::GetSingleton())if(auto* setting=ini->GetSetting("sLocalSavePath:General"))if(const auto* value=setting->GetString();value&&*value)relative=value;
        auto name=std::filesystem::path(legacySaveName).filename();name.replace_extension(".skse");
        const auto path=logs->parent_path()/relative/name;
        std::ifstream saveStream(path,std::ios::binary);
        if(const auto words=workshop_migration::ReadLegacyQueue(saveStream)){RestoreQueueWords(serial,*words);logger::info("Imported legacy arrow queue from {}",path.string());}
    }catch(const std::exception& e){logger::warn("Legacy arrow queue import failed: {}",e.what());}
}
bool unified_workshop::LoadArrowRecord(SKSE::SerializationInterface* serial,std::uint32_t type,std::uint32_t version,std::uint32_t length){
    if(craft_order::LoadRecord(serial,type,version,length))return true;
    if(soul_pool::LoadRecord(serial,type,version,length))return true;
    if(type!=ammo_queue::record)return false;
    if((version==1||version==2)&&length>=8&&length<=264&&length%4==0){std::vector<std::uint32_t> words(length/4);if(serial->ReadRecordData(words.data(),length)==length)RestoreQueueWords(serial,words,version);}
    return true;
}
bool unified_workshop::InstallArrows(){
    // Both queues need the co-save, so they share one availability probe.
    SKSE::AllocTrampoline(1<<10); // reserved for the Actor::TrapSoul branch hook
    ammo_queue::available=SKSE::GetSerializationInterface()!=nullptr;
    craft_order::available=ammo_queue::available;
    soul_pool::available=ammo_queue::available;
    return ammo_queue::available;
}
std::string unified_workshop::CraftOrderJson(){return craft_order::State().dump();}
std::string unified_workshop::SoulPoolHudJson(){return soul_pool::Hud().dump();}
void unified_workshop::ArrowMessage(SKSE::MessagingInterface::Message* message){Message(message);}
#else
extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Load(const SKSE::LoadInterface* skse){
    REL::Module::reset();SKSE::Init(skse);
    SKSE::AllocTrampoline(1<<10); // reserved for the Actor::TrapSoul branch hook
    if(auto dir=SKSE::log::log_directory()){
        auto sink=std::make_shared<spdlog::sinks::basic_file_sink_mt>((*dir/"MagicArrows.log").string(),true);
        auto log=std::make_shared<spdlog::logger>("MagicArrows",sink);spdlog::set_default_logger(log);spdlog::flush_on(spdlog::level::info);
    }
    ammo_queue::Install();craft_order::available=ammo_queue::available;
    auto* messaging=SKSE::GetMessagingInterface();return messaging&&messaging->RegisterListener("SKSE",Message);
}
#endif

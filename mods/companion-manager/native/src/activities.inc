// Included inside manager.cpp's private namespace; all calls run on the game thread under lock.
struct WardrobeItem {
    RE::TESBoundObject* item{};
    RE::ExtraDataList* extra{};
    std::string key, name;
    int count{}, value{}, category{};
    float weight{};
    bool equipped{}, quest{}, favorite{}, equipment{}, stolen{};
};
struct ActivityJob {
    RE::FormID actor{}, target{};
    std::string kind;
    double started{}, arrived{};
    int phase{};
};
std::optional<ActivityJob> activityJob;
std::unordered_map<RE::FormID,double> activityCooldown, requestCooldown;
std::unordered_map<RE::FormID,std::string> activityRequests;
std::unordered_set<RE::FormID> battleEnemies, droppedReferences;
std::deque<std::string> activityHistory;
RE::FormID wardrobeOpenRequest=0;
RE::FormID dialogueOutfitRequest=0;
double dialogueOutfitDeadline=0;
bool battleSeen=false;
bool activityCleanup=false;
double lootUntil=0, quietSince=0;
double ActivityTime() { return GetTickCount64()/1000.0; }
json Behavior(const json& r) {
    return r.contains("behavior") ? r["behavior"] : settings.value("behavior",activity::Defaults());
}
int Category(RE::TESBoundObject* item) {
    if (item->As<RE::TESObjectWEAP>()) return 1;
    if (auto* armor=item->As<RE::TESObjectARMO>()) {
        const auto mask=static_cast<std::uint32_t>(armor->GetSlotMask());
        return (mask & ((1u<<5)|(1u<<6))) ? 4 : 2;
    }
    if (item->GetFormID()==0xF || item->As<RE::TESSoulGem>()) return 8;
    if (auto* keywords=item->As<RE::BGSKeywordForm>())
        if (keywords->HasKeywordString("VendorItemGem")) return 8;
    if (item->As<RE::AlchemyItem>()) return 16;
    if (item->As<RE::IngredientItem>()) return 32;
    if (item->As<RE::TESObjectBOOK>()) return 64;
    if (item->As<RE::TESObjectMISC>() || item->As<RE::TESAmmo>()) return 128;
    return 0;
}
std::string WardrobeKey(RE::TESBoundObject* item,RE::ExtraDataList* extra) {
    auto* unique=extra?extra->GetByType<RE::ExtraUniqueID>():nullptr;
    return std::format("{:08X}:{:08X}:{:04X}",item->GetFormID(),unique?unique->baseID:0,unique?unique->uniqueID:0);
}
std::vector<WardrobeItem> Wardrobe(RE::TESObjectREFR* owner,const json& r,bool identify=false) {
    std::vector<WardrobeItem> rows;
    for (auto& [item,entry]:owner->GetInventory()) {
        if (!item||entry.first<=0||!entry.second||!Category(item)) continue;
        auto add=[&](RE::ExtraDataList* extra,int count) {
            if (count<=0||rows.size()>=512) return;
            if (extra && !extra->GetByType<RE::ExtraUniqueID>() && identify) {
                if (auto* changes=owner->GetInventoryChanges()) {
                    extra->Add(new RE::ExtraUniqueID(owner->GetFormID(),changes->GetNextUniqueID()));
                    owner->AddChange(RE::TESObjectREFR::ChangeFlags::kInventory);
                }
            }
            auto key=WardrobeKey(item,extra);
            // Unidentified decorated stacks are protected until they can be addressed safely.
            bool favorite=extra&&!extra->GetByType<RE::ExtraUniqueID>();
            if (r.contains("favorites"))
                for (const auto& f:r["favorites"]) if (f==key) favorite=true;
            RE::InventoryEntryData specific(item,count);
            if (extra) specific.AddExtraList(extra);
            const auto* name=specific.GetDisplayName();
            rows.push_back({item,extra,key,name?name:item->GetName(),count,
                (std::max)(0,specific.GetValue()),Category(item),(std::max)(0.0f,specific.GetWeight()),
                extra?(extra->HasType<RE::ExtraWorn>()||extra->HasType<RE::ExtraWornLeft>()):false,
                entry.second->IsQuestObject()||!item->GetPlayable()||
                    (r.value("casual",false)&&r.contains("battleOutfit")&&std::find(r["battleOutfit"].begin(),r["battleOutfit"].end(),key)!=r["battleOutfit"].end()),favorite,
                item->As<RE::TESObjectARMO>()||item->As<RE::TESObjectWEAP>(),
                !specific.IsOwnedBy(RE::PlayerCharacter::GetSingleton(),true)});
        };
        int remaining=entry.first;
        if (entry.second->extraLists)
            for (auto* extra:*entry.second->extraLists) if (extra&&remaining>0) {
                int n=(std::min)(remaining,(std::max)(1,extra->GetCount()));
                add(extra,n); remaining-=n;
            }
        // Materialize plain equipment as individually addressable copies before it is worn.
        // Adding a zero-delta entry only annotates existing stock; it creates no new items.
        if(identify&&remaining>0&&(item->As<RE::TESObjectARMO>()||item->As<RE::TESObjectWEAP>())) {
            if(auto* changes=owner->GetInventoryChanges()) {
                RE::InventoryEntryData* actual=nullptr;
                if(changes->entryList) for(auto* e:*changes->entryList) if(e&&e->object==item) {actual=e;break;}
                if(!actual) {actual=new RE::InventoryEntryData(item,0);changes->AddEntryData(actual);}
                while(remaining>0&&rows.size()<512) {
                    // This build targets SE 1.5.97: two null pointers + a zero-initialized RW lock.
                    // CommonLib declares but does not implement the ExtraDataList constructor.
                    if(REL::Module::get().version()!=SKSE::RUNTIME_SSE_1_5_97)
                        throw std::runtime_error("装备实例管理当前仅支持 Skyrim SE 1.5.97");
                    auto* extra=RE::calloc<RE::ExtraDataList>(1,0x18);
                    if(!extra) throw std::bad_alloc();
                    extra->Add(new RE::ExtraUniqueID(owner->GetFormID(),changes->GetNextUniqueID()));
                    actual->AddExtraList(extra);add(extra,1);--remaining;
                }
                changes->changed=true;
                owner->AddChange(RE::TESObjectREFR::ChangeFlags::kInventory);
            }
        }
        add(nullptr,remaining);
    }
    std::sort(rows.begin(),rows.end(),[](const auto& a,const auto& b){
        if(a.favorite!=b.favorite) return a.favorite>b.favorite;
        if(a.equipped!=b.equipped) return a.equipped>b.equipped;
        return a.key<b.key;
    });
    return rows;
}
float Carried(RE::Actor* actor) {
    // Count all inventory weight, including worn items; never exploit perk weight exemptions.
    float total=0;
    for(auto& [item,e]:actor->GetInventory()) if(item&&e.first>0&&e.second)
        total+=(std::max)(0.0f,e.second->GetWeight())*e.first;
    return total;
}
float Capacity(RE::Actor* actor) {
    return (std::max)(0.0f,actor->AsActorValueOwner()->GetActorValue(RE::ActorValue::kCarryWeight));
}
int Count(RE::TESObjectREFR* ref,RE::TESBoundObject* item) {
    auto inv=ref->GetInventory(); return inv.contains(item)?inv.at(item).first:0;
}
int MoveChecked(RE::TESObjectREFR* from,RE::TESObjectREFR* to,const WardrobeItem& item,int amount) {
    if(amount<=0||amount>item.count) return 0;
    const int before=Count(from,item.item), destination=Count(to,item.item);
    from->RemoveItem(item.item,amount,RE::ITEM_REMOVE_REASON::kStoreInContainer,item.extra,to);
    const int removed=before-Count(from,item.item), received=Count(to,item.item)-destination;
    if(removed!=received||removed!=amount)
        throw std::runtime_error("库存变动未完整确认，自动操作已停止，请检查双方库存");
    return received;
}
void ActivityLog(const std::string& message,bool notify=true) {
    activityHistory.push_front(message);
    while(activityHistory.size()>40) activityHistory.pop_back();
    logger::info("Activity: {}",message);
    if(notify&&settings["notifications"].get<bool>()) RE::DebugNotification(message.c_str());
    RefreshManagerView();
}
bool Nearby(RE::TESObjectREFR* a,RE::TESObjectREFR* b,float distance) {
    return a&&b&&a->GetParentCell()&&a->GetParentCell()==b->GetParentCell()&&
           (a->GetPosition()-b->GetPosition()).Length()<=distance;
}
bool ActorAvailable(RE::Actor* actor,const json& r) {
    return actor&&!actor->IsDead()&&!actor->IsDisabled()&&
        activity::CanRun(r["active"],r["waiting"],actor->IsInCombat(),actor->GetCurrentScene()!=nullptr,actor->Is3DLoaded());
}
void CancelActivity() {
    if(!activityJob) return;
    const auto old=*activityJob;
    activityJob.reset();
    if(members.contains(old.actor)) {
        if(auto* a=Actor(old.actor)) {
            Apply(a,members[old.actor]);
            const int slot=members[old.actor]["slot"];
            activityCleanup=true;
            const auto stamp=epoch;
            Call("EndActivity",[stamp](bool){std::scoped_lock guard(lock);if(stamp==epoch) activityCleanup=false;},slot);
        }
    }
}
void ResetActivities() {
    activityJob.reset(); activityRequests.clear(); activityCooldown.clear(); requestCooldown.clear();
    battleEnemies.clear(); activityHistory.clear();
    battleSeen=false; activityCleanup=false; wardrobeOpenRequest=0; lootUntil=quietSince=0;
    dialogueOutfitRequest=0; dialogueOutfitDeadline=0;
}
bool StartActivity(RE::Actor* actor,RE::TESObjectREFR* target,const std::string& kind) {
    if(activityJob||activityCleanup||!members.contains(actor->GetFormID())) return false;
    const auto id=actor->GetFormID(); const int slot=members[id]["slot"];
    activityJob=ActivityJob{id,target->GetFormID(),kind,ActivityTime(),0,0};
    const auto stamp=epoch;
    const auto started=activityJob->started;
    Call("BeginActivity",[id,stamp,started](bool ok){
        std::scoped_lock guard(lock);
        if(stamp!=epoch||!activityJob||activityJob->actor!=id||activityJob->started!=started) return;
        if(!ok) { activityCooldown[activityJob->target]=ActivityTime()+60; CancelActivity(); return; }
        if(auto* a=Actor(id)) a->AddToFaction(modeFaction,100);
        if(auto* a=Actor(id)) a->EvaluatePackage(false,false);
        activityJob->phase=1;
    },slot,target);
    return true;
}
RE::TESFaction* Merchant(RE::Actor* actor) {
    if(!actor||actor->IsDead()||actor->IsInCombat()||actor->GetCurrentScene()||!actor->Is3DLoaded()) return nullptr;
    auto* player=RE::PlayerCharacter::GetSingleton();
    if(!Nearby(actor,player,1800)||actor->IsHostileToActor(player)) return nullptr;
    auto* faction=actor->GetVendorFaction();
    if(!faction||!faction->IsVendor()||!faction->vendorData.merchantContainer) return nullptr;
    auto& v=faction->vendorData;
    const float hour=RE::Calendar::GetSingleton()->GetHour();
    const auto start=v.vendorValues.startHour,end=v.vendorValues.endHour;
    const bool open=start==end||(start<end?(hour>=start&&hour<end):(hour>=start||hour<end));
    if(!open||(v.vendorConditions&&!v.vendorConditions->IsTrue(actor,player))) return nullptr;
    return faction;
}
bool Buys(RE::TESFaction* faction,const WardrobeItem& row) {
    if(row.favorite||row.quest||row.equipped||row.item->GetFormID()==0xF) return false;
    auto& v=faction->vendorData;
    if(row.stolen&&!v.vendorValues.buysStolen) return false;
    if(!v.vendorSellBuyList) return false;
    bool match=false;
    auto* keywords=row.item->As<RE::BGSKeywordForm>();
    v.vendorSellBuyList->ForEachForm([&](RE::TESForm* f){
        if(f==row.item) match=true;
        if(auto* keyword=f?f->As<RE::BGSKeyword>():nullptr)
            if(keywords&&keywords->HasKeyword(keyword)) match=true;
        return RE::BSContainer::ForEachResult::kContinue;
    });
    return v.vendorValues.notBuySell?!match:match;
}
int SalePrice(RE::Actor* actor,const WardrobeItem& row) {
    // Companion speech determines a conservative barter rate; player-only barter perks do not apply.
    const float speech=std::clamp(actor->AsActorValueOwner()->GetActorValue(RE::ActorValue::kSpeech),0.0f,100.0f);
    return (std::max)(1,static_cast<int>(row.value/(3.3f-1.3f*speech/100.0f)));
}
bool HasSale(RE::Actor* actor,RE::TESFaction* faction,const json& r) {
    auto* gold=RE::TESForm::LookupByID<RE::TESBoundObject>(0xF);
    const int budget=Count(faction->vendorData.merchantContainer,gold);
    for(auto& item:Wardrobe(actor,r,true))
        if(Buys(faction,item)&&item.count>0&&item.value>0&&SalePrice(actor,item)<=budget) return true;
    return false;
}
void Sell(RE::Actor* actor,RE::Actor* merchant,json& r) {
    auto* faction=Merchant(merchant);
    if(!faction||!Nearby(actor,merchant,180)) return;
    auto* chest=faction->vendorData.merchantContainer;
    auto* gold=RE::TESForm::LookupByID<RE::TESBoundObject>(0xF);
    int total=0,units=0;
    for(auto& row:Wardrobe(actor,r,true)) {
        if(!Buys(faction,row)||row.value<=0) continue;
        const int price=SalePrice(actor,row);
        const int count=activity::SaleCount(row.count,price,Count(chest,gold));
        if(!count) continue;
        // Reserve real merchant gold first; refund it if the item could not be moved.
        const int payment=count*price, before=Count(actor,gold), budget=Count(chest,gold);
        chest->RemoveItem(gold,payment,RE::ITEM_REMOVE_REASON::kStoreInContainer,nullptr,actor);
        if(Count(actor,gold)!=before+payment||Count(chest,gold)!=budget-payment)
            throw std::runtime_error("商家金币交接未确认，已停止出售，请检查金币");
        const int stockBefore=Count(actor,row.item), chestBefore=Count(chest,row.item);
        try { MoveChecked(actor,chest,row,count); }
        catch(...) {
            const int moved=stockBefore-Count(actor,row.item), received=Count(chest,row.item)-chestBefore;
            if(moved==received&&moved>=0&&moved<=count) {
                const int refund=(count-moved)*price;
                if(refund) actor->RemoveItem(gold,refund,RE::ITEM_REMOVE_REASON::kStoreInContainer,nullptr,chest);
                ActivityLog(std::format("{}交易中断：已确认 {} 件、{} 金币；请检查库存",actor->GetName(),moved,moved*price));
            }
            throw;
        }
        total+=payment; units+=count;
        ActivityLog(std::format("{} → {}：{} ×{}，{} 金币",actor->GetName(),merchant->GetName(),row.name,count,payment),false);
        if(units>=100) break;
    }
    if(total) ActivityLog(std::format("{}出售了 {} 件物品，获得 {} 金币",actor->GetName(),units,total));
}
bool LootTarget(RE::TESObjectREFR* target,const json& p) {
    if(!target||target->IsDisabled()||target->IsDeleted()||target->IsCrimeToActivate()||droppedReferences.contains(target->GetFormID())) return false;
    if(auto* actor=target->As<RE::Actor>())
        return p["corpses"].get<bool>()&&actor->IsDead()&&!members.contains(actor->GetFormID())&&
            !actor->IsPlayerTeammate()&&battleEnemies.contains(actor->GetFormID());
    if(target->GetBaseObject()->As<RE::TESObjectCONT>())
        return p["containers"].get<bool>()&&!target->GetOwner()&&!target->IsLocked();
    return p["ground"].get<bool>()&&!target->GetOwner()&&Category(target->GetBaseObject())!=0;
}
bool HasLoot(RE::Actor* actor,RE::TESObjectREFR* target,const json& p) {
    if(!LootTarget(target,p)) return false;
    const float carried=Carried(actor),cap=Capacity(actor);
    if(target->As<RE::Actor>()||target->GetBaseObject()->As<RE::TESObjectCONT>()) {
        for(auto& row:Wardrobe(target,json::object()))
            if(!row.quest&&!row.stolen&&activity::Worth(row.category,row.value,row.weight,p)&&
                activity::Fits(cap,carried,row.weight,row.count)>0) return true;
    } else {
        auto* item=target->GetBaseObject();
        RE::InventoryEntryData row(item,1); row.AddExtraList(&target->extraList);
        return !row.IsQuestObject()&&item->GetPlayable()&&activity::Worth(Category(item),row.GetValue(),row.GetWeight(),p)&&
            activity::Fits(cap,carried,row.GetWeight(),(std::max)(1,target->extraList.GetCount()))>0;
    }
    return false;
}
void Loot(RE::Actor* actor,RE::TESObjectREFR* target,const json& p) {
    if(!Nearby(actor,target,180)||!LootTarget(target,p)) return;
    int total=0;
    if(target->As<RE::Actor>()||target->GetBaseObject()->As<RE::TESObjectCONT>()) {
        for(auto& row:Wardrobe(target,json::object())) {
            if(row.quest||row.stolen||!activity::Worth(row.category,row.value,row.weight,p)) continue;
            const int count=activity::Fits(Capacity(actor),Carried(actor),row.weight,row.count);
            total+=MoveChecked(target,actor,row,count);
        }
    } else {
        auto* item=target->GetBaseObject(); RE::InventoryEntryData entry(item,1); entry.AddExtraList(&target->extraList);
        if(entry.IsQuestObject()||!activity::Worth(Category(item),entry.GetValue(),entry.GetWeight(),p)) return;
        const int count=activity::Fits(Capacity(actor),Carried(actor),entry.GetWeight(),(std::max)(1,target->extraList.GetCount()));
        if(count>0) { const int before=Count(actor,item); actor->PickUpObject(target,count,false,true); total=Count(actor,item)-before; }
    }
    if(total>0) ActivityLog(std::format("{}拾取了 {} 件物品",actor->GetName(),total),false);
}
bool WearSet(RE::Actor* actor,const std::vector<WardrobeItem>& selected) {
    auto* equip=RE::ActorEquipManager::GetSingleton();
    if(!equip) return false;
    for(const auto& item:selected)
        equip->EquipObject(actor,item.item,item.extra,1,nullptr,false,true,false,true);
    const auto after=Wardrobe(actor,json::object(),true);
    return std::all_of(selected.begin(),selected.end(),[&](const auto& item){
        return std::any_of(after.begin(),after.end(),[&](const auto& row){return row.key==item.key&&row.equipped;});
    });
}
bool ChangeOutfit(RE::Actor* actor,json& r,bool restore=false,bool fallback=false) {
    auto inventory=Wardrobe(actor,r,true);
    if(restore) {
        if(!r.value("casual",false)) return false;
        std::vector<WardrobeItem> original;
        for(auto& row:inventory)
            if(r.contains("battleOutfit")&&std::find(r["battleOutfit"].begin(),r["battleOutfit"].end(),row.key)!=r["battleOutfit"].end()) original.push_back(row);
        if(WearSet(actor,original)) {r["casual"]=false;return true;}
        return false;
    }
    std::vector<outfit::Candidate> candidates;
    for(std::size_t i=0;i<inventory.size();++i) {
        auto& row=inventory[i];
        if(auto* armor=row.item->As<RE::TESObjectARMO>();armor&&!row.quest)
            candidates.push_back({i,static_cast<std::uint32_t>(armor->GetSlotMask()),row.favorite,row.equipped});
    }
    if(candidates.empty()) return false;
    static std::mt19937 rng{std::random_device{}()}; std::shuffle(candidates.begin(),candidates.end(),rng);
    std::uint32_t occupied=0;
    for(auto& row:inventory) if(row.quest&&row.equipped)
        if(auto* armor=row.item->As<RE::TESObjectARMO>()) occupied|=static_cast<std::uint32_t>(armor->GetSlotMask());
    std::vector<WardrobeItem> selected;
    for(auto index:outfit::Select(candidates,occupied,fallback)) selected.push_back(inventory[index]);
    if(selected.empty()) return false;
    if(std::all_of(selected.begin(),selected.end(),[](const auto& row){return row.equipped;})) return false;
    if(!r.value("casual",false)) {
        r["battleOutfit"]=json::array();
        for(auto& row:inventory) if(row.equipped&&row.item->As<RE::TESObjectARMO>()) r["battleOutfit"].push_back(row.key);
    }
    r["casual"]=true;
    if(!WearSet(actor,selected)) return false;
    ActivityLog(std::format("{}更换了穿搭",actor->GetName()),false);
    if(!fallback) activityRequests[actor->GetFormID()]="outfit";
    return true;
}
class ActivityAnswer final:public RE::IMessageBoxCallback {
    RE::FormID actor; std::uint64_t session;
public:
    ActivityAnswer(RE::FormID id,std::uint64_t e):RE::IMessageBoxCallback{},actor(id),session(e){}
    void Run(Message choice) override {
        if(auto* tasks=SKSE::GetTaskInterface()) tasks->AddTask([id=actor,e=session,choice]{
            std::scoped_lock guard(lock);
            if(e!=epoch||!ready||!members.contains(id)||!members[id].value("active",false)) return;
            if(static_cast<int>(choice)==0) wardrobeOpenRequest=id;
        });
    }
};
void AskPlayer(RE::Actor* actor,const std::string& kind) {
    const auto id=actor->GetFormID();
    const auto text=std::format("{}：{}",actor->GetName(),kind=="carry"?
        "我快拿不动了，你能挑一些有价值的东西取走吗？":"可以给我一些服装上的建议吗？");
    const bool queued=activity::QueuePrompt(text.c_str(),
        RE::BSTSmartPointer<RE::IMessageBoxCallback>(new ActivityAnswer(id,epoch)));
    logger::info("Activity prompt actor={:08X} kind={} queued={}",id,kind,queued);
    if(queued) activityRequests.erase(id);
    requestCooldown[id]=ActivityTime()+(queued?300:30);
}
void TickActivities() {
    auto* player=RE::PlayerCharacter::GetSingleton(); auto* ui=RE::UI::GetSingleton();
    const double now=ActivityTime();
    std::erase_if(activityCooldown,[now](const auto& entry){return entry.second<=now;});
    bool combat=player->IsInCombat();
    for(auto& [id,r]:members) if(r["active"].get<bool>())
        if(auto* a=Actor(id);a&&a->IsInCombat()) combat=true;
    if(combat) {
        if(!battleSeen) battleEnemies.clear();
        CancelActivity(); quietSince=now; lootUntil=0; battleSeen=true;
        RE::TES::GetSingleton()->ForEachReferenceInRange(player,6000,[&](RE::TESObjectREFR* ref){
            if(auto* a=ref->As<RE::Actor>();a&&!a->IsDead()&&a->IsHostileToActor(player)&&battleEnemies.size()<1024)
                battleEnemies.insert(a->GetFormID());
            return RE::BSContainer::ForEachResult::kContinue;
        });
        for(auto& [id,r]:members) if(auto* a=Actor(id);a&&a->Is3DLoaded()) ChangeOutfit(a,r,true);
        return;
    }
    if(battleSeen) { quietSince=now;lootUntil=now+180;battleSeen=false; }
    const bool menu=ui->IsMenuOpen(RE::DialogueMenu::MENU_NAME)||ui->IsMenuOpen(RE::BarterMenu::MENU_NAME)||
        ui->IsMenuOpen(RE::ContainerMenu::MENU_NAME)||ui->IsMenuOpen(RE::InventoryMenu::MENU_NAME)||
        ui->IsMenuOpen(RE::MessageBoxMenu::MENU_NAME)||ManagerViewOpen();
    if(menu) { CancelActivity(); return; }
    if(wardrobeOpenRequest) { const auto id=wardrobeOpenRequest;wardrobeOpenRequest=0;OpenPartnerWardrobe(id);return; }
    if(now-quietSince<4) return;
    if(activityJob) {
        auto job=*activityJob; auto* actor=Actor(job.actor); auto* target=RE::TESForm::LookupByID<RE::TESObjectREFR>(job.target);
        if(!members.contains(job.actor)||!ActorAvailable(actor,members[job.actor])||!target||target->IsDisabled()||
           target->IsDeleted()||!Nearby(player,target,4500)||!Nearby(player,actor,4500)||now-job.started>35) {
            activityCooldown[job.target]=now+60; CancelActivity(); return;
        }
        if(job.phase==0) return;
        if(job.phase==1&&Nearby(actor,target,150)) {
            activityJob->phase=2; activityJob->arrived=now;
            const int slot=members[job.actor]["slot"];
            const auto stamp=epoch;
            Call("FaceActivity",[stamp,job](bool ok){
                std::scoped_lock guard(lock);
                if(stamp!=epoch||!activityJob||activityJob->started!=job.started) return;
                if(!ok) { CancelActivity();return; }
                if(job.kind=="sell") if(auto* speaker=Actor(job.actor))
                    ActivityLog(std::format("{}：{}",speaker->GetName(),"老板，看看这些货物，你这里收吗？"));
                activityJob->phase=3;activityJob->arrived=ActivityTime();
            },slot,job.kind=="loot",job.kind=="sell");
            return;
        }
        if(job.phase==3&&now-job.arrived>=2) {
            if(!Nearby(actor,target,180)) { CancelActivity();return; }
            auto& r=members[job.actor]; const auto p=Behavior(r);
            try {
                if(job.kind=="loot"&&p["loot"].get<bool>()) Loot(actor,target,p);
                else if(job.kind=="sell"&&p["sell"].get<bool>())Sell(actor,target->As<RE::Actor>(),r);
                else if((job.kind=="carry"||job.kind=="outfit")&&p["requests"].get<bool>()) {
                    if(job.kind!="carry"||(Capacity(actor)-Carried(actor)<5&&Capacity(player)-Carried(player)>1)) AskPlayer(actor,job.kind);
                    else activityRequests.erase(job.actor);
                }
            } catch(const std::exception& e) { ActivityLog(e.what()); activityCooldown[job.actor]=now+300; }
            activityCooldown[job.target]=now+((job.kind=="sell")?60:30); CancelActivity();
        }
        return;
    }
    std::vector<RE::Actor*> active;
    for(auto& [id,r]:members) if(auto* a=Actor(id);ActorAvailable(a,r)&&Nearby(a,player,4200)&&!activityCooldown.contains(id)) active.push_back(a);
    std::sort(active.begin(),active.end(),[](auto* a,auto* b){return a->GetFormID()<b->GetFormID();});
    for(auto* actor:active) {
        const auto id=actor->GetFormID(); auto& r=members[id]; const auto p=Behavior(r);
        const double hours=RE::Calendar::GetSingleton()->GetHoursPassed();
        if(!r.contains("lastOutfitHours")||hours<r["lastOutfitHours"].get<double>()) r["lastOutfitHours"]=hours;
        if(p["outfits"].get<bool>()&&hours-r["lastOutfitHours"].get<double>()>=p["outfitHours"].get<int>()) {
            ChangeOutfit(actor,r); r["lastOutfitHours"]=hours; RefreshManagerView();
        }
        if(!activityRequests.contains(id)&&Capacity(actor)-Carried(actor)<5&&Capacity(player)-Carried(player)>1) activityRequests[id]="carry";
        if(p["requests"].get<bool>()&&activityRequests.contains(id)&&requestCooldown[id]<=now)
            if(StartActivity(actor,player,activityRequests[id])) return;
    }
    // One global job serializes merchants and loot claims; actors compete by distance below.
    std::vector<RE::TESObjectREFR*> targets;
    RE::TES::GetSingleton()->ForEachReferenceInRange(player,4200,[&](RE::TESObjectREFR* ref){
        if(targets.size()<256&&!ref->IsDisabled()&&!ref->IsDeleted()&&!activityCooldown.contains(ref->GetFormID())&&
            (ref->As<RE::Actor>()||ref->GetBaseObject()->As<RE::TESObjectCONT>()||Category(ref->GetBaseObject()))) targets.push_back(ref);
        return RE::BSContainer::ForEachResult::kContinue;
    });
    for(auto* target:targets) if(auto* merchant=target->As<RE::Actor>()) if(auto* vendor=Merchant(merchant))
        for(auto* actor:active) if(actor!=merchant&&(Behavior(members[actor->GetFormID()])["sell"].get<bool>()&&HasSale(actor,vendor,members[actor->GetFormID()])))
            if(StartActivity(actor,merchant,"sell")) return;
    if(now>lootUntil) return;
    float best=(std::numeric_limits<float>::max)(); RE::Actor* chosen=nullptr;RE::TESObjectREFR* target=nullptr;
    for(auto* actor:active) {
        const auto p=Behavior(members[actor->GetFormID()]); if(!p["loot"].get<bool>()) continue;
        for(auto* ref:targets) if(Nearby(actor,ref,p["radius"].get<int>()*70.0f)&&HasLoot(actor,ref,p)) {
            const float distance=(actor->GetPosition()-ref->GetPosition()).Length();
            if(distance<best) { best=distance;chosen=actor;target=ref; }
        }
    }
    if(chosen) StartActivity(chosen,target,"loot");
}
const char* InventoryCategory(RE::TESBoundObject* item) {
    if(item->As<RE::TESObjectWEAP>()||item->As<RE::TESAmmo>()) return "weapons";
    if(item->As<RE::TESObjectARMO>()) return "apparel";
    if(auto* alchemy=item->As<RE::AlchemyItem>()) return alchemy->IsFood()?"food":"potions";
    if(item->As<RE::ScrollItem>()) return "scrolls";
    if(item->As<RE::IngredientItem>()) return "ingredients";
    if(item->As<RE::TESObjectBOOK>()) return "books";
    if(item->As<RE::TESKey>()) return "keys";
    return "misc";
}
json WardrobeSnapshot(RE::Actor* actor,const json& r) {
    json rows=json::array();
    for(auto& item:Wardrobe(actor,r,true)) rows.push_back({{"key",item.key},{"id",ID(item.item->GetFormID())},
        {"name",item.name},{"count",item.count},{"value",item.value},{"weight",item.weight},{"category",item.category},
        {"inventoryCategory",InventoryCategory(item.item)},
        {"equipped",item.equipped},{"quest",item.quest},{"favorite",item.favorite},{"equipment",item.equipment}});
    return rows;
}
bool ActivityCommand(const std::string& op,RE::Actor* actor,json& r,const json& request) {
    if(op=="favorite") {
        const auto key=request.at("itemKey").get<std::string>();
        auto rows=Wardrobe(actor,r,true);
        auto found=std::find_if(rows.begin(),rows.end(),[&](const auto& i){return i.key==key;});
        if(found==rows.end()) throw std::runtime_error("物品已变化，请刷新伙伴库存");
        if(!r.contains("favorites")) r["favorites"]=json::array();
        auto& list=r["favorites"]; const bool value=request.at("value").get<bool>();
        auto old=std::find(list.begin(),list.end(),key);
        if(value&&old==list.end()) { if(list.size()>=512) throw std::runtime_error("锁定数量已达上限");list.push_back(key); }
        else if(!value&&old!=list.end()) list.erase(old);
        return true;
    }
    if(op=="behavior") {
        if(request.value("inherit",false)) r.erase("behavior");
        else { if(!activity::Valid(request.at("settings"))) throw std::runtime_error("行为设置无效"); r["behavior"]=request["settings"]; }
        CancelActivity(); return true;
    }
    if(op=="wardrobeTake") {
        auto* player=RE::PlayerCharacter::GetSingleton();
        if(!Nearby(actor,player,300)) throw std::runtime_error("请先靠近同伴再取物");
        const auto& selected=request.at("items");
        if(!selected.is_array()||selected.empty()||selected.size()>100) throw std::runtime_error("请选择 1–100 项物品");
        auto rows=Wardrobe(actor,r,true); std::vector<std::pair<WardrobeItem,int>> plan;
        std::unordered_set<std::string> keys; float carried=Carried(player);
        for(const auto& item:selected) {
            const auto key=item.at("key").get<std::string>();
            if(!keys.insert(key).second) throw std::runtime_error("物品选择重复");
            auto row=std::find_if(rows.begin(),rows.end(),[&](auto& i){return i.key==key;});
            if(!item.at("count").is_number_integer()) throw std::runtime_error("数量无效");
            const int n=item.at("count").get<int>();
            if(row==rows.end()||row->quest||row->equipped||n<1||n>row->count) throw std::runtime_error("物品已变化，或仍在穿戴 / 属于任务");
            if(activity::Fits(Capacity(player),carried,row->weight,n)!=n) throw std::runtime_error("玩家剩余负重不足");
            carried+=row->weight*n; plan.emplace_back(*row,n);
        }
        CancelActivity();
        for(auto& [row,n]:plan) MoveChecked(actor,player,row,n);
        activityRequests.erase(actor->GetFormID());requestCooldown[actor->GetFormID()]=ActivityTime()+300;
        return true;
    }
    if(op=="changeOutfit") {
        if(!actor||!r.value("active",false)||!actor->IsPlayerTeammate()||actor->IsDead()||actor->IsDisabled()||
           !actor->Is3DLoaded()||actor->GetCurrentScene()||actor->IsInCombat()||RE::PlayerCharacter::GetSingleton()->IsInCombat())
            throw std::runtime_error("请在同伴闲暇且未战斗时换装");
        CancelActivity();
        if(!ChangeOutfit(actor,r,false,true)) throw std::runtime_error("没有可替换的服饰，或引擎尚未确认换装，请刷新检查");
        r["lastOutfitHours"]=RE::Calendar::GetSingleton()->GetHoursPassed();
        return true;
    }
    if(op=="deferRequest") { activityRequests.erase(actor->GetFormID());requestCooldown[actor->GetFormID()]=ActivityTime()+300;return true; }
    return false;
}
class ActivityEvents final:public RE::BSTEventSink<RE::TESContainerChangedEvent>,public RE::BSTEventSink<RE::TESCombatEvent> {
public:
    RE::BSEventNotifyControl ProcessEvent(const RE::TESCombatEvent* e,RE::BSTEventSource<RE::TESCombatEvent>*) override {
        if(e&&e->newState==RE::ACTOR_COMBAT_STATE::kCombat) {
            const auto source=e->actor?e->actor->GetFormID():0, target=e->targetActor?e->targetActor->GetFormID():0;
            if(auto* tasks=SKSE::GetTaskInterface()) tasks->AddTask([source,target]{
                std::scoped_lock guard(lock);
                if(!ready) return;
                const auto ally=[](RE::FormID id){return id==0x14||(members.contains(id)&&members[id]["active"].get<bool>());};
                if(ally(source)||ally(target)) {
                    if(!battleSeen) battleEnemies.clear();
                    battleSeen=true;quietSince=ActivityTime();lootUntil=0;CancelActivity();
                    const auto enemy=ally(source)?target:source;
                    if(enemy&&!ally(enemy)&&battleEnemies.size()<1024) battleEnemies.insert(enemy);
                }
            });
        }
        return RE::BSEventNotifyControl::kContinue;
    }
    RE::BSEventNotifyControl ProcessEvent(const RE::TESContainerChangedEvent* e,RE::BSTEventSource<RE::TESContainerChangedEvent>*) override {
        if(e&&e->oldContainer==0x14&&e->newContainer==0)
            if(auto ref=e->reference.get()) {
                std::scoped_lock guard(lock);
                if(droppedReferences.size()<4096) droppedReferences.insert(ref->GetFormID());
            }
        return RE::BSEventNotifyControl::kContinue;
    }
};
void RegisterActivityEvents() {
    static ActivityEvents sink;
    if(auto* events=RE::ScriptEventSourceHolder::GetSingleton()) {
        events->AddEventSink<RE::TESContainerChangedEvent>(&sink);
        events->AddEventSink<RE::TESCombatEvent>(&sink);
    }
}
void RemapWardrobe(json& r,SKSE::SerializationInterface* s) {
    for(auto field:{"favorites","battleOutfit"}) if(r.contains(field)) {
        if(!r[field].is_array()||r[field].size()>512) throw std::runtime_error("Invalid wardrobe records");
        json mapped=json::array();
        for(const auto& value:r[field]) {
            if(!value.is_string()) throw std::runtime_error("Invalid wardrobe key");
            const auto key=value.get<std::string>();
            if(key.size()!=22||key[8]!=':'||key[17]!=':') throw std::runtime_error("Invalid wardrobe key");
            auto parse=[](std::string_view v){unsigned n=0;auto p=std::from_chars(v.data(),v.data()+v.size(),n,16);if(p.ec!=std::errc{}||p.ptr!=v.data()+v.size())throw std::runtime_error("Invalid wardrobe ID");return n;};
            const auto base=parse(std::string_view(key).substr(0,8)), owner=parse(std::string_view(key).substr(9,8)), uid=parse(std::string_view(key).substr(18,4));
            RE::FormID b=0,o=0;
            if(s->ResolveFormID(base,b)&&(!owner||s->ResolveFormID(owner,o))) mapped.push_back(std::format("{:08X}:{:08X}:{:04X}",b,o,uid));
        }
        r[field]=std::move(mapped);
    }
    if(r.contains("behavior")&&!activity::Valid(r["behavior"])) throw std::runtime_error("Invalid behavior settings");
    if(r.contains("casual")&&!r["casual"].is_boolean()) throw std::runtime_error("Invalid outfit state");
    if(r.contains("lastOutfitHours")&&(!r["lastOutfitHours"].is_number()||!std::isfinite(r["lastOutfitHours"].get<double>())||r["lastOutfitHours"]<0))
        throw std::runtime_error("Invalid outfit time");
}

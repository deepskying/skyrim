// Included inside manager.cpp's private namespace; all calls run on the game thread under lock.
struct WardrobeItem {
    RE::TESBoundObject* item{};
    RE::ExtraDataList* extra{};
    std::string key, name;
    int count{}, value{}, category{};
    float weight{};
    bool equipped{}, quest{}, favorite{}, equipment{}, stolen{};
};
struct OutfitCheck {
    std::vector<std::string> keys;
    double nextCheck{},deadline{};
    bool manual{};
    bool removing{};
};
std::unordered_map<RE::FormID,OutfitCheck> outfitChecks;
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
// Block automatic sales until deferred gift identification has completed.
std::unordered_map<RE::FormID,unsigned> pendingGiftLocks;
RE::FormID wardrobeOpenRequest=0;
RE::FormID dialogueOutfitRequest=0;
int dialogueOutfitMode=0;
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
    std::unordered_map<RE::FormID,std::unordered_set<std::uint16_t>> usedIDs;
    std::unordered_map<std::string,std::size_t> rowByKey;
    const auto favoriteOf=[&](const std::string& key) {
        if (r.contains("favorites"))
            for (const auto& f:r["favorites"]) if (f==key) return true;
        return false;
    };
    // Two rows that share one key cannot be told apart by any command, so a duplicated instance
    // takes a fresh identity instead of being emitted twice under the same key.
    const auto reidentify=[&](RE::TESBoundObject* base,RE::ExtraDataList* extra)->std::string {
        auto* unique=extra?extra->GetByType<RE::ExtraUniqueID>():nullptr;
        auto* changes=unique?owner->GetInventoryChanges():nullptr;
        if(!changes) return {};
        auto& taken=usedIDs[base->GetFormID()];
        std::uint16_t fresh=0;
        for(int attempt=0;attempt<64&&!fresh;++attempt) {
            const auto next=changes->GetNextUniqueID();
            if(next&&!taken.contains(next)) fresh=next;
        }
        if(!fresh) fresh=rules::FirstFreeUniqueID(taken);
        if(!fresh) return {};
        extra->RemoveByType(RE::ExtraDataType::kUniqueID);
        extra->Add(new RE::ExtraUniqueID(owner->GetFormID(),fresh));
        changes->changed=true;
        owner->AddChange(RE::TESObjectREFR::ChangeFlags::kInventory);
        taken.insert(fresh);
        return WardrobeKey(base,extra);
    };
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
            if(auto* unique=extra?extra->GetByType<RE::ExtraUniqueID>():nullptr)
                usedIDs[item->GetFormID()].insert(unique->uniqueID);
            if(const auto known=rowByKey.find(key);known!=rowByKey.end()) {
                auto& existing=rows[known->second];
                const auto wornCopy=extra&&(extra->HasType<RE::ExtraWorn>()||extra->HasType<RE::ExtraWornLeft>());
                if(rules::KeepsExistingIdentity(existing.equipped)) {
                    const auto replacement=reidentify(item,extra);
                    if(replacement.empty()) {
                        logger::warn("Wardrobe identity duplicate dropped base={:08X} name={}",item->GetFormID(),
                                     item->GetName()?item->GetName():"");
                        return;
                    }
                    logger::info("Wardrobe identity reassigned base={:08X} name={} worn={} key={} new={}",
                                 item->GetFormID(),item->GetName()?item->GetName():"",wornCopy,key,replacement);
                    key=replacement;
                } else {
                    const auto replacement=reidentify(item,existing.extra);
                    if(replacement.empty()) {
                        logger::warn("Wardrobe identity duplicate dropped base={:08X} name={}",item->GetFormID(),
                                     item->GetName()?item->GetName():"");
                        return;
                    }
                    logger::info("Wardrobe identity reassigned base={:08X} name={} worn={} key={} new={}",
                                 item->GetFormID(),item->GetName()?item->GetName():"",existing.equipped,key,replacement);
                    rowByKey.erase(known);
                    existing.key=replacement;
                    existing.favorite=favoriteOf(replacement);
                    rowByKey.emplace(replacement,known->second);
                }
            }
            // Unidentified decorated stacks are protected until they can be addressed safely.
            bool favorite=(extra&&!extra->GetByType<RE::ExtraUniqueID>())||favoriteOf(key);
            RE::InventoryEntryData specific(item,count);
            if (extra) specific.AddExtraList(extra);
            const auto* name=specific.GetDisplayName();
            rows.push_back({item,extra,key,name?name:(item->GetName()?item->GetName():"未命名物品"),count,
                (std::max)(0,specific.GetValue()),Category(item),(std::max)(0.0f,specific.GetWeight()),
                extra?(extra->HasType<RE::ExtraWorn>()||extra->HasType<RE::ExtraWornLeft>()):false,
                entry.second->IsQuestObject()||!item->GetPlayable(),favorite,
                item->As<RE::TESObjectARMO>()||item->As<RE::TESObjectWEAP>(),
                !specific.IsOwnedBy(RE::PlayerCharacter::GetSingleton(),true)});
            rowByKey.emplace(rows.back().key,rows.size()-1);
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
// Actual worn instances are not bounded by displayed counts or the 512-row wardrobe limit.
// Never synthesize inventory quantity from a worn marker or a model attachment.
struct WornArmorInstance {
    RE::TESObjectARMO* armor{};
    RE::ExtraDataList* extra{};
    bool protectedItem{};
    int countDelta{},inventoryCount{};
};
std::vector<WornArmorInstance> RawWornArmor(RE::Actor* actor) {
    std::vector<WornArmorInstance> result;
    const auto counts=actor->GetInventoryCounts();
    auto* changes=actor->GetInventoryChanges();
    if(!changes||!changes->entryList) return result;
    std::unordered_set<RE::ExtraDataList*> seen;
    for(auto* entry:*changes->entryList) {
        if(!entry||!entry->object||!entry->extraLists) continue;
        auto* armor=entry->object->As<RE::TESObjectARMO>();
        if(!armor) continue;
        const bool protectedItem=entry->IsQuestObject()||!armor->GetPlayable()||armor==actor->GetSkin();
        const auto count=counts.find(armor);
        for(auto* extra:*entry->extraLists) {
            if(!extra||!(extra->HasType<RE::ExtraWorn>()||extra->HasType<RE::ExtraWornLeft>())||!seen.insert(extra).second) continue;
            result.push_back({armor,extra,protectedItem,entry->countDelta,count==counts.end()?0:count->second});
        }
    }
    return result;
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
        activity::CanRun(r["active"],r["waiting"],Fighting(actor),actor->GetCurrentScene()!=nullptr,actor->Is3DLoaded());
}
// ---------------------------------------------------------------- combat guards
std::unordered_map<RE::FormID,double> staleCombatSince,guardCooldown;
std::unordered_set<std::uint64_t> alliedPairs;
double allyPassAt=0;
// A companion must never fight the player or another companion, and a combat flag without a live
// enemy is cleared once the grace period passes instead of locking the panel out forever.
void GuardCombat(RE::Actor* actor,RE::Actor* player,double now) {
    const auto id=actor->GetFormID();
    if(!actor->IsInCombat()) { staleCombatSince.erase(id); return; }
    const RE::NiPointer<RE::Actor> handle=actor->GetActorRuntimeData().currentCombatTarget.get();
    auto* other=handle.get();
    bool liveEnemy=false,friendly=false;
    if(other&&other!=actor) {
        const auto sameCell=actor->GetParentCell()&&actor->GetParentCell()==other->GetParentCell();
        const auto distance=sameCell?static_cast<float>((actor->GetPosition()-other->GetPosition()).Length()):-1.0f;
        liveEnemy=rules::LiveEnemy(other->IsDead(),other->IsDisabled(),other->Is3DLoaded(),
                                   actor->IsHostileToActor(other),distance,rules::CombatGuardRadius);
        friendly=rules::FriendlyCombatTarget(other==player,other->IsPlayerTeammate(),
                                            members.contains(other->GetFormID()));
    }
    auto& since=staleCombatSince[id];
    if(!since) since=now;
    if(liveEnemy&&!friendly) { staleCombatSince.erase(id); return; }
    const auto action=rules::GuardFor(true,liveEnemy,friendly,now-since>=rules::StaleCombatSeconds);
    if(action==rules::CombatGuard::None) return;
    if(auto& cooldown=guardCooldown[id];cooldown>now) return;
    guardCooldown[id]=now+rules::GuardActionCooldown;
    const auto seconds=now-since;
    staleCombatSince.erase(id);
    const auto name=actor->GetName()?actor->GetName():"";
    const auto target=other?std::format("{:08X}",other->GetFormID()):std::string("none");
    if(action==rules::CombatGuard::StopFriendlyFire) {
        logger::info("Combat guard friendly fire actor={:08X} name={} target={} reaction={} teammate={} aggression={:.0f}",
            id,name,target,other?static_cast<int>(actor->GetFactionReaction(other)):-1,
            other?other->IsPlayerTeammate():false,
            actor->AsActorValueOwner()->GetActorValue(RE::ActorValue::kAggression));
        actor->StopCombat();
        if(other&&other!=player) other->StopCombat();
    } else {
        logger::info("Combat guard cleared stale combat actor={:08X} name={} seconds={:.1f} target={}",
            id,name,seconds,target);
        actor->StopCombat();
        actor->EvaluatePackage(false,false);
    }
    RefreshManagerView();
}
// Hostility between companions comes from faction reactions and relationship ranks, which the
// engine does not clear for teammates on its own. Raise every pair of active companions to Ally.
void GuardAllies(double now) {
    if(now<allyPassAt) return;
    allyPassAt=now+15.0;
    std::vector<RE::FormID> active;
    for(auto& [id,r]:members) if(r["active"].get<bool>())
        if(auto* a=Actor(id);a&&!a->IsDead()&&a->Is3DLoaded()) active.push_back(id);
    int budget=4;
    for(std::size_t i=0;i<active.size()&&budget>0;++i)
        for(std::size_t j=i+1;j<active.size()&&budget>0;++j) {
            const auto low=(std::min)(active[i],active[j]),high=(std::max)(active[i],active[j]);
            const auto key=(static_cast<std::uint64_t>(low)<<32)|static_cast<std::uint64_t>(high);
            if(!alliedPairs.insert(key).second) continue;
            --budget;
            const auto slotA=members[active[i]]["slot"].get<int>(),slotB=members[active[j]]["slot"].get<int>();
            Call("AllyMembers",[key,low,high](bool ok){
                if(!ok) { alliedPairs.erase(key); return; }
                logger::info("Companion allies set {:08X} {:08X}",low,high);
            },slotA,slotB);
        }
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
    battleEnemies.clear(); activityHistory.clear(); pendingGiftLocks.clear(); outfitChecks.clear();
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
    if(row.favorite||row.quest||row.equipped||row.item->GetFormID()==0xF||row.item->As<RE::AlchemyItem>()) return false;
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
    if(pendingGiftLocks.contains(actor->GetFormID())) return false;
    auto* gold=RE::TESForm::LookupByID<RE::TESBoundObject>(0xF);
    const int budget=Count(faction->vendorData.merchantContainer,gold);
    for(auto& item:Wardrobe(actor,r,true))
        if(Buys(faction,item)&&item.count>0&&item.value>0&&SalePrice(actor,item)<=budget) return true;
    return false;
}
void Sell(RE::Actor* actor,RE::Actor* merchant,json& r) {
    if(pendingGiftLocks.contains(actor->GetFormID())) return;
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
void CheckOutfits() {
    const auto now=ActivityTime();
    for(auto it=outfitChecks.begin();it!=outfitChecks.end();) {
        const auto id=it->first;
        auto& check=it->second;
        auto* actor=Actor(id);
        if(!actor||!members.contains(id)||!members[id].value("active",false)||actor->IsDead()||!actor->Is3DLoaded()) {
            logger::info("Outfit confirmation cancelled actor={:08X}",id);
            it=outfitChecks.erase(it);continue;
        }
        if(now<check.nextCheck) {++it;continue;}
        check.nextCheck=now+0.25;
        const auto rows=Wardrobe(actor,json::object(),false);
        std::size_t confirmed=0;
        const auto rawWorn=check.removing?RawWornArmor(actor):std::vector<WornArmorInstance>{};
        for(const auto& key:check.keys)
            if(check.removing?std::none_of(rawWorn.begin(),rawWorn.end(),[&](const auto& row){return WardrobeKey(row.armor,row.extra)==key;}):
               std::any_of(rows.begin(),rows.end(),[&](const auto& row){return row.key==key&&row.equipped;})) ++confirmed;
        const auto result=outfit::PollConfirmation(check.keys.size(),confirmed,now>=check.deadline);
        if(result==outfit::Result::Pending) {++it;continue;}
        for(const auto& key:check.keys) {
            const auto row=std::find_if(rows.begin(),rows.end(),[&](const auto& row){return row.key==key;});
            logger::info("Outfit delayed actor={:08X} item={} present={} worn={}",id,key,row!=rows.end(),row!=rows.end()&&row->equipped);
        }
        for(const auto& row:rows) if(row.equipped)
            logger::info("Outfit still worn actor={:08X} item={} name={}",id,row.key,row.name);
        if(const auto& biped=actor->GetBiped();biped) for(const auto& part:biped->objects) if(part.item)
            logger::info("Outfit model actor={:08X} item={:08X}",id,part.item->GetFormID());
        logger::info("Outfit final actor={:08X} confirmed={}/{} result={}",id,confirmed,check.keys.size(),outfit::Message(result));
        if(outfit::Changed(result)) {
            members[id]["lastOutfitHours"]=RE::Calendar::GetSingleton()->GetHoursPassed();
            ActivityLog(std::format("{}：{}",actor->GetName(),outfit::Message(result)),false);
            if(!check.manual) activityRequests[id]="outfit";
        }
        if(check.manual) RE::DebugNotification(check.removing?
            (result==outfit::Result::Changed?"已确认卸下装备": "未能完整确认卸下装备，请刷新检查"):outfit::Message(result));
        it=outfitChecks.erase(it);
        RefreshManagerView();
    }
}
outfit::Result WearSet(RE::Actor* actor,const std::vector<WardrobeItem>& selected,bool manual) {
    auto* equip=RE::ActorEquipManager::GetSingleton();
    if(!equip) return outfit::Result::Unconfirmed;
    // CommonLib's forceEquip parameter means PreventRemoval in the engine.
    // Repair conflicting old locks only for an explicit manual outfit request.
    if(manual) {
        std::uint32_t replacing=0;
        for(const auto& item:selected) if(!item.equipped)
            if(auto* armor=item.item->As<RE::TESObjectARMO>()) replacing|=static_cast<std::uint32_t>(armor->GetSlotMask());
        for(const auto& old:RawWornArmor(actor)) {
            auto* armor=old.armor;
            if(!outfit::CanUnlockReplacement(manual,true,old.protectedItem,
               static_cast<std::uint32_t>(armor->GetSlotMask()),replacing)) continue;
            if(old.extra->HasType<RE::ExtraCannotWear>()) {
                const bool removed=old.extra->RemoveByType(RE::ExtraDataType::kCannotWear);
                logger::info("Outfit unlock actor={:08X} item={} name={} removed={}",actor->GetFormID(),WardrobeKey(armor,old.extra),armor->GetName(),removed);
                if(removed) {
                    if(auto* changes=actor->GetInventoryChanges()) changes->changed=true;
                    actor->AddChange(RE::TESObjectREFR::ChangeFlags::kInventory);
                }
            }
        }
    }
    OutfitCheck check{{},ActivityTime()+0.25,ActivityTime()+2.0,manual};
    for(const auto& item:selected) if(!item.equipped) check.keys.push_back(item.key);
    outfitChecks[actor->GetFormID()]=std::move(check);
    for(const auto& item:selected) if(!item.equipped) {
        logger::info("Outfit dispatch actor={:08X} item={} name={}",actor->GetFormID(),item.key,item.name);
        equip->EquipObject(actor,item.item,item.extra,1,nullptr,false,false,false,true);
    }
    return outfit::Result::Pending;
}
outfit::Result ChangeOutfit(RE::Actor* actor,json& r,bool fallback=false) {
    if(outfitChecks.contains(actor->GetFormID())) return outfit::Result::Pending;
    auto inventory=Wardrobe(actor,r,true);
    logger::info("Outfit request actor={:08X} name={} manual={} inventoryRows={}",actor->GetFormID(),actor->GetName(),fallback,inventory.size());
    std::vector<outfit::Candidate> candidates;
    std::uint32_t occupied=0;
    for(std::size_t i=0;i<inventory.size();++i) {
        auto& row=inventory[i];
        if(auto* armor=row.item->As<RE::TESObjectARMO>()) {
            const auto mask=static_cast<std::uint32_t>(armor->GetSlotMask());
            logger::info("Outfit item={} name={} count={} mask={:08X} locked={} worn={} protected={} playable={} removalLocked={}",row.key,row.name,row.count,mask,row.favorite,row.equipped,row.quest,armor->GetPlayable(),row.extra&&row.extra->HasType<RE::ExtraCannotWear>());
            if(!row.quest&&!armor->IsShield()&&armor!=actor->GetSkin()) candidates.push_back({i,mask,row.favorite,row.equipped});
            else if(row.equipped) occupied|=mask;
        }
    }
    const auto worn=RawWornArmor(actor);
    for(const auto& item:worn) {
        const auto mask=static_cast<std::uint32_t>(item.armor->GetSlotMask());
        const bool visible=std::any_of(inventory.begin(),inventory.end(),[&](const auto& row){return row.item==item.armor&&row.extra==item.extra;});
        logger::info("Outfit raw worn actor={:08X} item={} name={} countDelta={} inventoryCount={} visible={} mask={:08X} protected={} removalLocked={}",
            actor->GetFormID(),WardrobeKey(item.armor,item.extra),item.armor->GetName(),item.countDelta,item.inventoryCount,visible,mask,item.protectedItem,item.extra->HasType<RE::ExtraCannotWear>());
        if(item.protectedItem) occupied|=mask;
    }
    // Model-only records (including ARMA attachments) are not sufficient proof of a removable item.
    if(const auto& biped=actor->GetBiped();biped) {
        std::unordered_set<RE::FormID> seen;
        for(const auto& part:biped->objects) if(part.item) {
            auto* armor=part.item->As<RE::TESObjectARMO>();
            if(!armor||armor==actor->GetSkin()||!seen.insert(armor->GetFormID()).second) continue;
            if(std::none_of(worn.begin(),worn.end(),[&](const auto& item){return item.armor==armor;}))
                logger::warn("Outfit model without worn inventory actor={:08X} item={:08X} name={} mask={:08X}; no instance to unlock",
                    actor->GetFormID(),armor->GetFormID(),armor->GetName(),static_cast<std::uint32_t>(armor->GetSlotMask()));
        }
    }
    const auto finish=[&](outfit::Result result) {
        logger::info("Outfit result actor={:08X} protectedSlots={:08X} result={}",actor->GetFormID(),occupied,outfit::Message(result));
        return result;
    };
    if(candidates.empty()) return finish(outfit::Result::NoCandidates);
    static std::mt19937 rng{std::random_device{}()}; std::shuffle(candidates.begin(),candidates.end(),rng);
    std::vector<WardrobeItem> selected;
    for(auto index:outfit::Select(candidates,occupied,fallback)) selected.push_back(inventory[index]);
    if(selected.empty()) return finish(outfit::Result::NoSelection);
    if(std::all_of(selected.begin(),selected.end(),[](const auto& row){return row.equipped;})) return finish(outfit::Result::Unchanged);
    return finish(WearSet(actor,selected,fallback));
}
#include "outfit_presets.inc"
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
    bool combat=Fighting(player);
    for(auto& [id,r]:members) if(r["active"].get<bool>())
        if(auto* a=Actor(id);a&&Fighting(a)) combat=true;
    if(combat) {
        if(!battleSeen) battleEnemies.clear();
        CancelActivity(); quietSince=now; lootUntil=0; battleSeen=true;
        RE::TES::GetSingleton()->ForEachReferenceInRange(player,6000,[&](RE::TESObjectREFR* ref){
            if(auto* a=ref->As<RE::Actor>();a&&!a->IsDead()&&a->IsHostileToActor(player)&&battleEnemies.size()<1024)
                battleEnemies.insert(a->GetFormID());
            return RE::BSContainer::ForEachResult::kContinue;
        });
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
            RandomNamedOutfit(actor,r,false); r["lastOutfitHours"]=hours; RefreshManagerView();
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
    if(op=="changeOutfit"||op=="saveNamedOutfit"||op=="removeNamedOutfit"||op=="applyNamedOutfit"||op=="outfitPart"||op=="unequipOutfitPart") {
        if(!actor||!r.value("active",false)||!actor->IsPlayerTeammate()||actor->IsDead()||actor->IsDisabled()||
           !actor->Is3DLoaded()||actor->GetCurrentScene()||Fighting(actor)||Fighting(RE::PlayerCharacter::GetSingleton()))
            throw std::runtime_error("请在同伴闲暇且未战斗时换装");
        if(!Nearby(actor,RE::PlayerCharacter::GetSingleton(),600)) throw std::runtime_error("请先靠近同伴再调整穿搭");
        CancelActivity();
        if(op=="saveNamedOutfit") {SaveNamedOutfit(actor,r,request.at("name").get<std::string>());return true;}
        if(op=="removeNamedOutfit") {RemoveNamedOutfit(r,request.at("presetId"));return true;}
        auto result=outfit::Result::NoSelection;
        if(op=="unequipOutfitPart") result=RemoveOutfitPart(actor,request);
        else if(op=="outfitPart") result=ChangeOutfitPart(actor,r,request);
        else if(op=="applyNamedOutfit") {
            const auto presets=r.value("outfitPresets",json::array());
            const auto p=std::find_if(presets.begin(),presets.end(),[&](const auto& x){return x["id"]==request.at("presetId");});
            if(p==presets.end()) throw std::runtime_error("套装不存在，请刷新后重试");
            result=ApplyNamedOutfit(actor,r,*p,true);
        } else result=RandomNamedOutfit(actor,r,true);
        if(result!=outfit::Result::Pending&&result!=outfit::Result::Unchanged&&!outfit::Changed(result)) throw std::runtime_error(outfit::Message(result));
        RE::DebugNotification(outfit::Message(result));
        return true;
    }
    if(op=="deferRequest") { activityRequests.erase(actor->GetFormID());requestCooldown[actor->GetFormID()]=ActivityTime()+300;return true; }
    return false;
}
void LockPlayerGift(RE::FormID recipient,RE::FormID base,std::uint16_t uniqueID) {
    auto* actor=Actor(recipient);
    if(!actor||!members.contains(recipient)) return;
    auto& r=members[recipient];
    auto rows=Wardrobe(actor,r,true);
    // Some transfers have no instance ID. Protect all same-base copies rather than guess.
    const auto exact=[&](const WardrobeItem& row){
        auto* uid=row.extra?row.extra->GetByType<RE::ExtraUniqueID>():nullptr;
        return row.item->GetFormID()==base&&uid&&uniqueID&&uid->uniqueID==uniqueID;
    };
    const bool hasExact=std::count_if(rows.begin(),rows.end(),exact)==1;
    if(!hasExact) {
        int represented=0;for(const auto& row:rows) if(row.item->GetFormID()==base) represented+=row.count;
        auto* item=RE::TESForm::LookupByID<RE::TESBoundObject>(base);
        if(item&&represented<Count(actor,item)) throw std::runtime_error("同伴库存过大，交付装备未能完整识别");
    }
    if(!r.contains("favorites")) r["favorites"]=json::array();
    auto& favorites=r["favorites"];
    unsigned added=0;
    for(const auto& row:rows) {
        if(!row.equipment||row.item->GetFormID()!=base||(hasExact&&!exact(row))) continue;
        if(std::find(favorites.begin(),favorites.end(),row.key)!=favorites.end()) continue;
        if(favorites.size()>=512) throw std::runtime_error("锁定数量已达上限，请整理同伴锁定物品后重试");
        favorites.push_back(row.key);++added;
    }
    if(added) ActivityLog(std::format("{}：已自动锁定玩家交付的装备（{} 项）",actor->GetName(),added),false);
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
        if(e&&e->oldContainer==0x14&&e->newContainer&&e->itemCount>0) {
            std::scoped_lock guard(lock);
            auto* item=RE::TESForm::LookupByID<RE::TESBoundObject>(e->baseObj);
            if(ready&&members.contains(e->newContainer)&&item&&(item->As<RE::TESObjectWEAP>()||item->As<RE::TESObjectARMO>())) {
                const auto recipient=e->newContainer,base=e->baseObj;
                const auto uid=e->uniqueID;const auto stamp=epoch;
                ++pendingGiftLocks[recipient];
                if(auto* tasks=SKSE::GetTaskInterface()) tasks->AddTask([recipient,base,uid,stamp]{
                    std::scoped_lock guard(lock);
                    if(stamp!=epoch||!ready) return;
                    try {
                        LockPlayerGift(recipient,base,uid);
                        auto it=pendingGiftLocks.find(recipient);
                        if(it!=pendingGiftLocks.end()&&!--it->second) pendingGiftLocks.erase(it);
                    } catch(const std::exception& error) {
                        // Fail closed: don't sell this actor's inventory after an incomplete lock.
                        logger::error("Gift auto-lock failed actor={:08X}: {}",recipient,error.what());
                        RE::DebugNotification("交付装备自动锁定未完成，该同伴自动出售已暂停");
                    }
                });
            }
        }
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
    // Retire legacy battle reservations without resolving or validating their old item IDs.
    r.erase("battleOutfit");
    r.erase("casual");
    if(r.contains("outfitPresets")) {
        outfit::RemapPresets(r["outfitPresets"],[s](std::uint32_t old,std::uint32_t& mapped){return s->ResolveFormID(old,mapped);});
    }
    for(auto field:{"favorites"}) if(r.contains(field)) {
        if(!r[field].is_array()||r[field].size()>512) throw std::runtime_error("Invalid wardrobe records");
        json mapped=json::array();
        for(const auto& value:r[field]) {
            const auto key=outfit::RemapKey(value,[s](std::uint32_t old,std::uint32_t& mapped){return s->ResolveFormID(old,mapped);});
            if(key) mapped.push_back(*key);
        }
        r[field]=std::move(mapped);
    }
    if(r.contains("behavior")&&!activity::Valid(r["behavior"])) throw std::runtime_error("Invalid behavior settings");
    if(r.contains("lastOutfitHours")&&(!r["lastOutfitHours"].is_number()||!std::isfinite(r["lastOutfitHours"].get<double>())||r["lastOutfitHours"]<0))
        throw std::runtime_error("Invalid outfit time");
}

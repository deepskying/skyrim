// Included after the wardrobe/equipment helpers, on the game thread under lock.
bool OutfitArmor(RE::TESObjectARMO* armor) {
    return armor && armor->GetPlayable() && !armor->IsShield() &&
        static_cast<std::uint32_t>(armor->GetSlotMask()) != 0;
}
std::uint32_t ProtectedOutfitSlots(RE::Actor* actor) {
    std::uint32_t mask=0;
    for(const auto& old:RawWornArmor(actor)) if(old.protectedItem)
        mask|=static_cast<std::uint32_t>(old.armor->GetSlotMask());
    return mask;
}
std::uint32_t PartMask(const WardrobeItem& row) {
    auto* armor=row.item?row.item->As<RE::TESObjectARMO>():nullptr;
    return armor?static_cast<std::uint32_t>(armor->GetSlotMask()):0;
}
const char* SlotLabel(unsigned slot) {
    switch(slot) {
    case 30: return "头部";
    case 31: return "头发";
    case 32: return "身体";
    case 33: return "手部";
    case 34: return "前臂";
    case 35: return "项链";
    case 36: return "戒指";
    case 37: return "脚部";
    case 38: return "小腿";
    case 40: return "尾部";
    case 41: return "长发";
    case 42: return "头环";
    case 43: return "耳部";
    default: return "其他";
    }
}
// Favorited, playable, unworn pieces that leave every protected slot alone. One pool answers both
// the random piece change and the dialogue gate that offers that slot.
std::vector<WardrobeItem> FavoritePartPool(RE::Actor* actor,json& r) {
    std::vector<WardrobeItem> pool;
    const auto protectedSlots=ProtectedOutfitSlots(actor);
    for(const auto& row:Wardrobe(actor,r,true)) {
        auto* armor=row.item?row.item->As<RE::TESObjectARMO>():nullptr;
        if(!OutfitArmor(armor)||armor==actor->GetSkin()) continue;
        if(!outfit::EligibleFavoriteRow(static_cast<std::uint32_t>(armor->GetSlotMask()),protectedSlots,row.quest,row.equipped,row.favorite)) continue;
        pool.push_back(row);
    }
    return pool;
}
// Worn outfit pieces a whole-set request has to take off: everything the set does not name, never
// quest gear and never the actor's skin. Weapons, shields and ammo are not outfit pieces.
std::vector<WornArmorInstance> StripCandidates(RE::Actor* actor,const std::vector<WardrobeItem>& selected) {
    std::vector<WornArmorInstance> strip;
    for(const auto& old:RawWornArmor(actor)) {
        const auto key=WardrobeKey(old.armor,old.extra);
        const bool namedBySet=std::any_of(selected.begin(),selected.end(),[&](const auto& item){return item.key==key;});
        if(!outfit::StripBeforeWear(OutfitArmor(old.armor),old.protectedItem,namedBySet)) continue;
        strip.push_back(old);
    }
    return strip;
}
json OutfitItem(const WardrobeItem& row,bool hidden=false) {
    const auto* armor=row.item->As<RE::TESObjectARMO>();
    return {{"key",row.key},{"form",row.item->GetFormID()},{"name",row.name},
        {"mask",static_cast<std::uint32_t>(armor->GetSlotMask())},
        {"equipped",row.equipped},{"favorite",row.favorite},{"quest",row.quest},
        {"available",row.count>0&&!hidden},{"hidden",hidden}};
}
json OutfitItems(RE::Actor* actor,const json& r) {
    json result=json::array();
    for(const auto& row:Wardrobe(actor,r,true)) if(OutfitArmor(row.item->As<RE::TESObjectARMO>())&&row.item!=actor->GetSkin())
        result.push_back(OutfitItem(row));
    for(const auto& worn:RawWornArmor(actor)) {
        if(!OutfitArmor(worn.armor)||worn.armor==actor->GetSkin()) continue;
        // Also identify genuine worn instances that ordinary inventory counts hide.
        if(!worn.extra->GetByType<RE::ExtraUniqueID>()) if(auto* changes=actor->GetInventoryChanges()) {
            worn.extra->Add(new RE::ExtraUniqueID(actor->GetFormID(),changes->GetNextUniqueID()));
            changes->changed=true;actor->AddChange(RE::TESObjectREFR::ChangeFlags::kInventory);
        }
        const auto key=WardrobeKey(worn.armor,worn.extra);
        if(std::any_of(result.begin(),result.end(),[&](const auto& x){return x["key"]==key;})) continue;
        const auto favorites=r.value("favorites",json::array());
        result.push_back({{"key",key},{"form",worn.armor->GetFormID()},{"name",worn.armor->GetName()},
            {"mask",static_cast<std::uint32_t>(worn.armor->GetSlotMask())},{"equipped",true},
            {"favorite",std::find(favorites.begin(),favorites.end(),key)!=favorites.end()},
            {"quest",worn.protectedItem},{"available",false},{"hidden",true}});
    }
    return result;
}
json OutfitSnapshot(RE::Actor* actor,const json& r) {
    auto items=OutfitItems(actor,r);
    auto presets=r.value("outfitPresets",json::array());
    for(auto& preset:presets) for(auto& saved:preset["items"]) {
        const auto found=std::find_if(items.begin(),items.end(),[&](const auto& x){return x["key"]==saved["key"];});
        saved["available"]=found!=items.end()&&((*found)["available"].template get<bool>()||(*found)["equipped"].template get<bool>());
        saved["equipped"]=found!=items.end()&&(*found)["equipped"].template get<bool>();
        saved["favorite"]=found!=items.end()&&(*found)["favorite"].template get<bool>();
    }
    return {{"items",items},{"presets",presets},{"pending",outfitChecks.contains(actor->GetFormID())}};
}
void SaveNamedOutfit(RE::Actor* actor,json& r,const std::string& name) {
    if(name.empty()||name.size()>120||std::any_of(name.begin(),name.end(),[](unsigned char c){return c<32;})||
       name.find_first_not_of(' ')==std::string::npos) throw std::runtime_error("请输入有效套装名称（最多 30 个汉字）");
    auto presets=r.value("outfitPresets",json::array());
    if(presets.size()>=64) throw std::runtime_error("套装已达 64 套上限");
    for(const auto& p:presets) if(p["name"]==name) throw std::runtime_error("已有同名套装，请换个名称");
    if(outfitChecks.contains(actor->GetFormID())) throw std::runtime_error("请等待换装确认后再保存");
    json list=json::array(),favorites=r.value("favorites",json::array());
    for(const auto& row:OutfitItems(actor,r)) if(row["equipped"].get<bool>()) {
        list.push_back({{"key",row["key"]},{"form",row["form"]},{"name",row["name"]},{"mask",row["mask"]}});
        if(std::find(favorites.begin(),favorites.end(),row["key"])==favorites.end()) favorites.push_back(row["key"]);
    }
    if(list.empty()) throw std::runtime_error("当前没有可保存的服饰");
    if(list.size()>64||favorites.size()>512) throw std::runtime_error("服饰或收藏数量已达上限，请先整理库存");
    unsigned next=1;for(const auto& p:presets) next=(std::max)(next,p["id"].get<unsigned>()+1);
    presets.push_back({{"id",next},{"name",name},{"items",list}});
    // Stay below the co-save record cap, including all other companions' collections.
    auto replacement=r;replacement["outfitPresets"]=presets;replacement["favorites"]=favorites;
    std::size_t bytes=settings.dump().size();
    const bool self=actor==RE::PlayerCharacter::GetSingleton();
    for(const auto& [id,member]:members) bytes+=(!self&&id==actor->GetFormID()?replacement:member).dump().size();
    bytes+=(self?replacement:playerOutfits).dump().size();
    if(bytes>3*1024*1024) throw std::runtime_error("当前存档的穿搭记录已达容量上限，未保存新套装");
    r["outfitPresets"]=std::move(presets);r["favorites"]=std::move(favorites);
}
void RemoveNamedOutfit(json& r,const json& presetID) {
    if(!rules::Integer(presetID,1,1000000)) throw std::runtime_error("套装编号无效");
    auto presets=r.value("outfitPresets",json::array());
    const auto found=std::find_if(presets.begin(),presets.end(),[&](const auto& p){return p["id"]==presetID;});
    if(found==presets.end()) throw std::runtime_error("套装不存在，请刷新后重试");
    presets.erase(found);
    r["outfitPresets"]=std::move(presets);
}
outfit::Result ApplyNamedOutfit(RE::Actor* actor,json& r,const json& preset,bool manual) {
    if(outfitChecks.contains(actor->GetFormID())) return outfit::Result::Pending;
    const auto rows=Wardrobe(actor,r,true);std::vector<WardrobeItem> selected;
    auto occupied=ProtectedOutfitSlots(actor);
    unsigned missing=0;
    for(const auto& saved:preset.at("items")) {
        const auto savedKey=saved.at("key").get<std::string>();
        auto row=std::find_if(rows.begin(),rows.end(),[&](const auto& x){return x.key==savedKey;});
        if(row==rows.end()) {++missing;continue;}
        auto* armor=row->item->As<RE::TESObjectARMO>();
        if(!OutfitArmor(armor)||armor==actor->GetSkin()||row->quest) continue;
        const auto mask=static_cast<std::uint32_t>(armor->GetSlotMask());
        if(occupied&mask) continue;
        occupied|=mask;selected.push_back(*row);
    }
    logger::info("Outfit preset actor={:08X} name={} missing={} selected={}",actor->GetFormID(),preset["name"].get<std::string>(),missing,selected.size());
    if(missing&&manual) RE::DebugNotification("套装中有库存缺失物品，已跳过；当前其余服饰已换下");
    if(selected.empty()) return outfit::Result::NoSelection;
    // A saved set is a whole outfit: a request from the player or the dialogue replaces what the
    // companion wears. The automatic timer keeps the old gear, because a stale preset must not
    // leave somebody undressed unattended. WearSet reports Unchanged when the set is already on
    // and there is nothing left to take off.
    return WearSet(actor,selected,manual,manual?StripCandidates(actor,selected):std::vector<WornArmorInstance>{});
}
outfit::Result RandomNamedOutfit(RE::Actor* actor,json& r,bool manual=true) {
    const auto presets=r.value("outfitPresets",json::array());
    static std::mt19937 rng{std::random_device{}()};
    if(outfit::UseSaved(presets.size(),settings.value("savedOutfitChance",70),std::uniform_int_distribution<int>(0,99)(rng)))
        return ApplyNamedOutfit(actor,r,presets[std::uniform_int_distribution<std::size_t>(0,presets.size()-1)(rng)],manual);
    return ChangeOutfit(actor,r,manual);
}
// The dialogue line "随机套装": a saved set, never a recomposition, and a message when there is
// nothing saved yet. The panel button and the timer keep using the configured mix above.
outfit::Result RandomSavedOutfit(RE::Actor* actor,json& r,bool manual=true) {
    if(outfitChecks.contains(actor->GetFormID())) return outfit::Result::Pending;
    const auto presets=r.value("outfitPresets",json::array());
    if(!outfit::HasSavedSet(presets.size())) return outfit::Result::NoSavedSets;
    static std::mt19937 rng{std::random_device{}()};
    const auto index=outfit::SavedSetPick(presets.size(),std::uniform_int_distribution<std::size_t>(0,presets.size()-1)(rng));
    const auto& chosen=presets[index];
    logger::info("Outfit saved set actor={:08X} name={} sets={}",actor->GetFormID(),chosen["name"].get<std::string>(),presets.size());
    return ApplyNamedOutfit(actor,r,chosen,manual);
}
outfit::Result RemoveOutfitPart(RE::Actor* actor,const json& request) {
    if(outfitChecks.contains(actor->GetFormID())) return outfit::Result::Pending;
    if(!rules::Integer(request.at("slot"),30,61)||request["slot"]==39) throw std::runtime_error("此槽位不参与穿搭");
    const auto mask=1u<<(request["slot"].get<unsigned>()-30);
    const auto key=request.at("itemKey").get<std::string>();
    const auto rows=RawWornArmor(actor);
    const auto found=std::find_if(rows.begin(),rows.end(),[&](const auto& row){return WardrobeKey(row.armor,row.extra)==key;});
    if(found==rows.end()) throw std::runtime_error("这件装备已不在穿戴，请刷新检查");
    if(found->protectedItem||!OutfitArmor(found->armor)||!(static_cast<std::uint32_t>(found->armor->GetSlotMask())&mask))
        throw std::runtime_error("装备受保护或不属于当前槽位，不能卸下");
    auto* equip=RE::ActorEquipManager::GetSingleton();if(!equip)return outfit::Result::Unconfirmed;
    if(found->extra->HasType<RE::ExtraCannotWear>()) {
        found->extra->RemoveByType(RE::ExtraDataType::kCannotWear);
        if(auto* changes=actor->GetInventoryChanges())changes->changed=true;
        actor->AddChange(RE::TESObjectREFR::ChangeFlags::kInventory);
    }
    outfitChecks[actor->GetFormID()]={{key},ActivityTime()+0.25,ActivityTime()+2.0,true,true};
    logger::info("Outfit unequip actor={:08X} key={} mask={:08X}",actor->GetFormID(),key,static_cast<std::uint32_t>(found->armor->GetSlotMask()));
    equip->UnequipObject(actor,found->armor,found->extra,1,nullptr,false,false,false,true);
    return outfit::Result::Pending;
}
// The wear page toggles the exact instance the player picked: armor, clothing, jewelry and shields.
// Putting a piece on takes off whatever occupies its slots, a protected slot blocks the swap
// instead, quest gear never comes off, and the outcome is confirmed like every other outfit change.
outfit::Result ToggleWear(RE::Actor* actor,json& r,const json& request) {
    if(outfitChecks.contains(actor->GetFormID())) return outfit::Result::Pending;
    const auto key=request.at("itemKey").get<std::string>();
    const auto rows=Wardrobe(actor,r,true);
    const auto found=std::find_if(rows.begin(),rows.end(),[&](const auto& row){return row.key==key;});
    if(found==rows.end()||found->count<=0) throw std::runtime_error("物品已变化，请刷新伙伴库存");
    auto* armor=found->item->As<RE::TESObjectARMO>();
    const auto mask=armor?static_cast<std::uint32_t>(armor->GetSlotMask()):0u;
    if(!outfit::Toggleable(mask,armor&&armor->GetPlayable())||armor==actor->GetSkin())
        throw std::runtime_error("这件物品不能穿脱");
    auto* equip=RE::ActorEquipManager::GetSingleton();
    if(!equip) return outfit::Result::Unconfirmed;
    const auto unlock=[&](RE::ExtraDataList* extra) {
        if(!extra||!extra->HasType<RE::ExtraCannotWear>()) return;
        const bool removed=extra->RemoveByType(RE::ExtraDataType::kCannotWear);
        if(!removed) return;
        if(auto* changes=actor->GetInventoryChanges()) changes->changed=true;
        actor->AddChange(RE::TESObjectREFR::ChangeFlags::kInventory);
    };
    if(found->equipped) {
        if(found->quest) throw std::runtime_error("任务装备不能卸下");
        unlock(found->extra);
        outfitChecks[actor->GetFormID()]={{key},ActivityTime()+0.25,ActivityTime()+2.0,true,true};
        logger::info("Wear off actor={:08X} key={} mask={:08X}",actor->GetFormID(),key,mask);
        equip->UnequipObject(actor,armor,found->extra,1,nullptr,false,false,false,true);
        RefreshActorModel(actor);
        return outfit::Result::Pending;
    }
    std::vector<WornArmorInstance> strip;
    for(const auto& old:RawWornArmor(actor)) {
        if(old.armor==actor->GetSkin()) continue;
        const auto wornMask=static_cast<std::uint32_t>(old.armor->GetSlotMask());
        if(outfit::SwapProtected(wornMask,mask,old.protectedItem))
            throw std::runtime_error("该部位被任务装备占用，无法更换");
        if(outfit::ReplacedBySwap(wornMask,mask,old.protectedItem)) strip.push_back(old);
    }
    OutfitCheck check{{key},ActivityTime()+0.25,ActivityTime()+2.0,true,false};
    for(const auto& old:strip) check.removed.push_back(WardrobeKey(old.armor,old.extra));
    outfitChecks[actor->GetFormID()]=std::move(check);
    for(const auto& old:strip) {
        unlock(old.extra);
        logger::info("Wear replace actor={:08X} item={} name={}",actor->GetFormID(),WardrobeKey(old.armor,old.extra),old.armor->GetName());
        equip->UnequipObject(actor,old.armor,old.extra,1,nullptr,false,false,false,true);
    }
    logger::info("Wear on actor={:08X} key={} mask={:08X} replaced={}",actor->GetFormID(),key,mask,strip.size());
    equip->EquipObject(actor,armor,found->extra,1,nullptr,false,false,false,true);
    RefreshActorModel(actor);
    return outfit::Result::Pending;
}
outfit::Result ChangeOutfitPart(RE::Actor* actor,json& r,const json& request) {
    if(outfitChecks.contains(actor->GetFormID())) return outfit::Result::Pending;
    if(!rules::Integer(request.at("slot"),30,61)||request["slot"]==39) throw std::runtime_error("此槽位不参与穿搭");
    const auto slot=request["slot"].get<unsigned>();
    std::vector<WardrobeItem> candidates;
    const auto key=request.value("itemKey",std::string{});
    if(key.empty()) {
        // Random in-slot change: favorited gear only, exactly like the whole-outfit random.
        for(const auto& row:FavoritePartPool(actor,r))
            if(PartMask(row)&outfit::SlotBit(slot)) candidates.push_back(row);
        logger::info("Outfit part random actor={:08X} slot={} name={} candidates={}",
            actor->GetFormID(),slot,SlotLabel(slot),candidates.size());
    } else {
        // Naming one instance stays a direct manual pick, favorited or not.
        const auto protectedSlots=ProtectedOutfitSlots(actor);
        for(const auto& row:Wardrobe(actor,r,true)) {
            auto* armor=row.item?row.item->As<RE::TESObjectARMO>():nullptr;
            if(!OutfitArmor(armor)||armor==actor->GetSkin()||row.key!=key) continue;
            if(outfit::EligiblePart(slot,PartMask(row),protectedSlots,row.quest,row.equipped)) candidates.push_back(row);
        }
    }
    if(candidates.empty()) return outfit::Result::NoSelection;
    static std::mt19937 rng{std::random_device{}()};
    const auto& chosen=candidates[std::uniform_int_distribution<std::size_t>(0,candidates.size()-1)(rng)];
    return WearSet(actor,{chosen},true);
}

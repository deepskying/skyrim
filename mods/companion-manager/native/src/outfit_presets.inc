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
    for(const auto& [id,member]:members) bytes+=(id==actor->GetFormID()?replacement:member).dump().size();
    if(bytes>3*1024*1024) throw std::runtime_error("当前存档的穿搭记录已达容量上限，未保存新套装");
    r["outfitPresets"]=std::move(presets);r["favorites"]=std::move(favorites);
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
    if(missing&&manual) RE::DebugNotification("套装中有库存缺失物品，已跳过；多槽位冲突仍会替换相应部位");
    if(selected.empty()) return outfit::Result::NoSelection;
    if(std::all_of(selected.begin(),selected.end(),[](const auto& x){return x.equipped;})) return outfit::Result::Unchanged;
    return WearSet(actor,selected,manual);
}
outfit::Result RandomNamedOutfit(RE::Actor* actor,json& r,bool manual=true) {
    const auto presets=r.value("outfitPresets",json::array());
    static std::mt19937 rng{std::random_device{}()};
    if(outfit::UseSaved(presets.size(),settings.value("savedOutfitChance",70),std::uniform_int_distribution<int>(0,99)(rng)))
        return ApplyNamedOutfit(actor,r,presets[std::uniform_int_distribution<std::size_t>(0,presets.size()-1)(rng)],manual);
    return ChangeOutfit(actor,r,manual);
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
outfit::Result ChangeOutfitPart(RE::Actor* actor,json& r,const json& request) {
    if(outfitChecks.contains(actor->GetFormID())) return outfit::Result::Pending;
    if(!rules::Integer(request.at("slot"),30,61)||request["slot"]==39) throw std::runtime_error("此槽位不参与穿搭");
    const auto slot=request["slot"].get<unsigned>();
    const auto protectedSlots=ProtectedOutfitSlots(actor);
    std::vector<WardrobeItem> candidates;
    const auto key=request.value("itemKey",std::string{});
    for(const auto& row:Wardrobe(actor,r,true)) {
        auto* armor=row.item->As<RE::TESObjectARMO>();
        if(!OutfitArmor(armor)||armor==actor->GetSkin()||row.quest||row.equipped||(!key.empty()&&row.key!=key)) continue;
        const auto mask=static_cast<std::uint32_t>(armor->GetSlotMask());
        if(outfit::EligiblePart(slot,mask,protectedSlots,row.quest,row.equipped)) candidates.push_back(row);
    }
    if(candidates.empty()) return outfit::Result::NoSelection;
    static std::mt19937 rng{std::random_device{}()};
    const auto& chosen=candidates[std::uniform_int_distribution<std::size_t>(0,candidates.size()-1)(rng)];
    return WearSet(actor,{chosen},true);
}

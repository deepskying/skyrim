// Included inside the equipment runtime namespace. No Papyrus or third-party ESP dependency.
struct RecyclingSettings {
    std::uint32_t key = 0xB8, safety = 0xB8;
    bool enabled = true, stack = true;
};
RecyclingSettings g_recyclingSettings;
json g_recyclingRules;
std::uint64_t g_recyclingEpoch = 0;

std::filesystem::path RecyclingConfigPath() { return ConfigPath().parent_path() / "EquipmentWorkshop.recycling.json"; }
bool WriteRecyclingSettings(const RecyclingSettings& settings) {
    const auto path = RecyclingConfigPath();
    const auto temporary = std::filesystem::path(path.wstring() + L".tmp");
    try {
        const json data{{"keyCode", settings.key}, {"safetyCode", settings.safety}, {"enabled", settings.enabled}, {"holdToRecycleStack", settings.stack}};
        std::ofstream file(temporary, std::ios::binary | std::ios::trunc);
        file << data.dump(2) << '\n'; file.flush();
        if (!file.good()) return false;
        file.close();
        return MoveFileExW(temporary.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0;
    } catch (const std::exception& error) { logger::error("Recycling settings: {}", error.what()); return false; }
}

void LoadRecyclingSettings() {
    try {
        std::ifstream file(RecyclingConfigPath());
        if (file) {
            const auto data = json::parse(file);
            const auto key = data.value("keyCode", 0xB8U), safety = data.value("safetyCode", 0xB8U);
            if (recycling::Allowed(key) && (key == safety || recycling::Modifier(safety))) {
                g_recyclingSettings = {key, safety, data.value("enabled", true), data.value("holdToRecycleStack", true)};
            }
        }
        std::ifstream rules(ConfigPath().parent_path() / "EquipmentWorkshop.recycling.rules.json");
        g_recyclingRules = json::parse(rules);
        if (!g_recyclingRules.is_object() || g_recyclingRules.value("version", 0) != 1) throw std::runtime_error("Unsupported recycling rules");
    } catch (const std::exception& error) {
        g_recyclingRules = nullptr;
        logger::error("Native recycling unavailable: {}", error.what());
    }
}

bool LegacyRecyclingLoaded() {
    auto* data = RE::TESDataHandler::GetSingleton();
    return data && data->LookupLoadedModByName("SimpleRecycling.esp"); // Conflict detection only; never read its forms or scripts.
}

bool RecyclingKeyConflicts(std::uint32_t key) {
    const auto* controls = RE::ControlMap::GetSingleton();
    if (!controls) return false;
    using Context = RE::UserEvents::INPUT_CONTEXT_IDS;
    for (auto context : {Context::kItemMenu, Context::kInventory})
        for (const auto* action : {"Equip", "DropItem", "ChargeItem", "Favorites", "XButton", "YButton"})
            if (controls->GetMappedKey(action, RE::INPUT_DEVICE::kKeyboard, context) == key) return true;
    return false;
}

json RecyclingHotkeyState() {
    const auto& settings = g_recyclingSettings;
    return {{"available", !g_recyclingRules.is_null()}, {"enabled", settings.enabled}, {"holdToRecycleStack", settings.stack},
        {"legacyDetected", LegacyRecyclingLoaded()}, {"keyCode", settings.key}, {"safetyCode", settings.safety},
        {"label", settings.key == settings.safety ? KeyName(settings.key) : KeyName(settings.safety) + " + " + KeyName(settings.key)}};
}

struct RecyclingSelection {
    RE::FormID form = 0;
    std::uintptr_t view = 0;
    std::vector<recycling::StackPart> parts;
    std::int32_t count = 0;
    std::string name;
    bool operator==(const RecyclingSelection&) const = default;
};
struct RecyclingPress { RecyclingSelection selection; std::chrono::steady_clock::time_point started; };
std::optional<RecyclingPress> g_recyclingPress;
std::chrono::steady_clock::time_point g_lastRecycling;

void ResetRecyclingInput() { g_recyclingPress.reset(); ++g_recyclingEpoch; }
class RecyclingMenuSink final : public RE::BSTEventSink<RE::MenuOpenCloseEvent> {
public:
    RE::BSEventNotifyControl ProcessEvent(const RE::MenuOpenCloseEvent*, RE::BSTEventSource<RE::MenuOpenCloseEvent>*) override {
        ResetRecyclingInput(); return RE::BSEventNotifyControl::kContinue;
    }
};
RecyclingMenuSink g_recyclingMenuSink;

RE::InventoryEntryData* SelectedRecyclingEntry(RE::InventoryMenu* menu) {
    if (!menu || !menu->uiMovie || !menu->GetRuntimeData().itemList) return nullptr;
    RE::GFxValue entry, blocked;
    if (!menu->uiMovie->GetVariable(&entry, "_root.Menu_mc.inventoryLists.itemList.selectedEntry") || !entry.IsObject()) return nullptr;
    for (const auto* path : {"_root.Menu_mc.inventoryLists.itemList.disableInput", "_root.Menu_mc.inventoryLists.itemList.disableSelection"}) {
        if (menu->uiMovie->GetVariable(&blocked, path) && blocked.IsBool() && blocked.GetBool()) return nullptr;
    }
    const auto* selected = menu->GetRuntimeData().itemList->GetSelectedItem();
    auto* native = selected ? selected->data.objDesc : nullptr;
    RE::GFxValue id;
    if (!native || !native->object || !entry.GetMember("formId", &id) || !id.IsNumber() ||
        !std::isfinite(id.GetNumber()) || id.GetNumber() < -2147483648.0 || id.GetNumber() > 4294967295.0 ||
        static_cast<RE::FormID>(static_cast<std::int64_t>(id.GetNumber())) != native->object->GetFormID()) return nullptr;
    return native;
}

bool RecyclingMenuReady() {
    auto* ui = RE::UI::GetSingleton();
    const auto* controls = RE::ControlMap::GetSingleton();
    const auto* player = RE::PlayerCharacter::GetSingleton();
    if (g_panelVisible || !player || player->IsDead() || !ui || !ui->IsMenuOpen(RE::InventoryMenu::MENU_NAME) ||
        (controls && controls->GetRuntimeData().textEntryCount > 0)) return false;
    for (const auto* name : {"Console", "Journal Menu", "MessageBoxMenu", "Loading Menu", "ContainerMenu", "BarterMenu"})
        if (ui->IsMenuOpen(name)) return false;
    return true;
}

std::optional<RecyclingSelection> ReadRecyclingSelection(std::string& reason) {
    if (!RecyclingMenuReady()) return std::nullopt;
    auto menu = RE::UI::GetSingleton()->GetMenu<RE::InventoryMenu>();
    auto* entry = SelectedRecyclingEntry(menu.get());
    if (!entry || entry->countDelta <= 0) { reason = "请选择背包中的物品。"; return std::nullopt; }
    auto* item = entry->object;
    if (entry->IsQuestObject() || item->HasKeywordByEditorID("DaedricArtifact") || item->HasKeywordByEditorID("VendorItemDaedricArtifact")) { reason = "任务或唯一物品不可回收。"; return std::nullopt; }
    if (entry->IsWorn() || entry->IsFavorited()) { reason = "请先卸下物品并取消收藏，再进行回收。"; return std::nullopt; }
    if (const auto* weapon = item->As<RE::TESObjectWEAP>(); weapon && weapon->IsBound()) { reason = "召唤武器不可回收。"; return std::nullopt; }
    auto* player = RE::PlayerCharacter::GetSingleton();
    auto inventory = player->GetInventory();
    const auto found = inventory.find(item);
    if (found == inventory.end() || found->second.first <= 0 || !found->second.second) return std::nullopt;
    const auto describe = [](RE::ExtraDataList* extra) {
        const auto* unique = extra->GetByType<RE::ExtraUniqueID>();
        return recycling::StackPart{reinterpret_cast<std::uintptr_t>(extra), unique ? unique->uniqueID : std::uint16_t{0}, extra->GetCount()};
    };
    std::vector<recycling::StackPart> live, row;
    if (found->second.second->extraLists) for (auto* extra : *found->second.second->extraLists)
        if (extra) live.push_back(describe(extra));
    if (entry->extraLists) for (auto* extra : *entry->extraLists) {
        if (!extra) continue;
        // Resolve pointers before dereferencing menu data that may have become stale.
        const auto match = std::find_if(live.begin(), live.end(), [&](const auto& part) { return part.extra == reinterpret_cast<std::uintptr_t>(extra); });
        if (match == live.end()) { reason = "背包内容已变化，请重新选择物品。"; return std::nullopt; }
        if (extra->GetWorn() || extra->HasType<RE::ExtraWornLeft>() || extra->HasQuestObjectAlias() || extra->HasType<RE::ExtraHotkey>()) {
            reason = "已装备、收藏或任务物品不可回收。"; return std::nullopt;
        }
        row.push_back(*match);
    }
    auto parts = recycling::ResolveStack(entry->countDelta, found->second.first, std::move(row), live);
    if (!parts) {
        reason = "选中行与背包数量暂不一致，请重新打开背包后重试。";
        logger::warn("Recycling row mismatch: {:08X} row={} inventory={} liveParts={}", item->GetFormID(), entry->countDelta, found->second.first, live.size());
        return std::nullopt;
    }
    const bool plainRemainder = std::any_of(parts->begin(), parts->end(), [](const auto& part) { return !part.extra; });
    if (plainRemainder && parts->size() != live.size() + 1) {
        reason = "同名装备另有独立附魔或强化实例，请先把这些实例存入容器，再回收普通堆叠。";
        return std::nullopt;
    }
    return RecyclingSelection{item->GetFormID(), reinterpret_cast<std::uintptr_t>(menu->uiMovie.get()),
        std::move(*parts), entry->countDelta, entry->GetDisplayName() ? entry->GetDisplayName() : DisplayName(item)};
}

RE::TESBoundObject* RecyclingForm(const json& record) {
    if (!record.is_object()) return nullptr;
    auto* data = RE::TESDataHandler::GetSingleton();
    const auto id = record.value("id", 0U);
    // LookupForm<T> checks T::FORMTYPE exactly. TESBoundObject inherits None,
    // so that overload rejects every real inventory object (including materials).
    auto* form = data && id && id <= 0xFFFFFF ? data->LookupForm(id, record.value("plugin", "Skyrim.esm")) : nullptr;
    return form ? form->As<RE::TESBoundObject>() : nullptr;
}

std::map<RE::TESBoundObject*, std::int32_t> RecyclingMaterials(RE::TESBoundObject* item, std::int32_t consumed, float weight, std::int32_t value) {
    std::map<RE::TESBoundObject*, std::int32_t> result;
    if (!item || consumed <= 0) return result;
    const bool ammo = item->Is(RE::FormType::Ammo);
    // Explicit native-game clutter groups. Runtime data contains only base-game/DLC references.
    for (const auto& group : g_recyclingRules.value("groups", json::array())) {
        bool found = false;
        for (const auto& source : group.value("items", json::array())) if (RecyclingForm(source) == item) { found = true; break; }
        if (!found) continue;
        auto* output = RecyclingForm(group.value("output", json::object()));
        if (output && output != item) result[output] = recycling::WeightedYield(weight, group.value("weightRatio", 0.2), consumed);
        return result;
    }
    // Equipment crafting recipes support mod-added gear without referencing a recycling ESP.
    if (item->Is(RE::FormType::Weapon) || item->Is(RE::FormType::Armor) || ammo) {
        auto* data = RE::TESDataHandler::GetSingleton();
        const RE::BGSConstructibleObject* best = nullptr;
        for (const auto* recipe : data->GetFormArray<RE::BGSConstructibleObject>()) {
            if (!recipe || recipe->createdItem != item || !recipe->data.numConstructed || IsTemperingBench(recipe->benchKeyword)) continue;
            bool self = false;
            recipe->requiredItems.ForEachContainerObject([&](RE::ContainerObject& ingredient) {
                if (ingredient.obj == item) self = true;
                return RE::BSContainer::ForEachResult::kContinue;
            });
            if (!self && (!best || recipe->GetFormID() < best->GetFormID())) best = recipe;
        }
        bool invalid = false;
        if (best) best->requiredItems.ForEachContainerObject([&](RE::ContainerObject& ingredient) {
            const auto count = recycling::RecipeYield(ingredient.count, best->data.numConstructed, consumed);
            if (ingredient.obj && ingredient.obj != item && ingredient.obj != GoldRecord() && count > 0 &&
                (ingredient.obj->Is(RE::FormType::Misc) || ingredient.obj->Is(RE::FormType::Ingredient))) {
                auto& total = result[ingredient.obj];
                if (total > INT32_MAX - count) invalid = true;
                else total += count;
            }
            return RE::BSContainer::ForEachResult::kContinue;
        });
        if (invalid) return {};
        if (!result.empty()) return result;
    }
    for (const auto& rule : g_recyclingRules.value("rules", json::array())) {
        if (rule.contains("formType") && rule["formType"].get<std::uint32_t>() != static_cast<std::uint32_t>(item->GetFormType())) continue;
        const auto keyword = rule.value("keyword", "");
        if (!keyword.empty() && !item->HasKeywordByEditorID(keyword)) continue;
        auto* output = RecyclingForm(rule.value("output", json::object()));
        if (!output || output == item) continue;
        const auto rawValue = static_cast<std::int64_t>(value) * consumed;
        const auto count = rule.value("useItemValue", false) ? (rawValue > 0 && rawValue <= INT32_MAX ? static_cast<std::int32_t>(rawValue) : 0) :
            ammo ? consumed / 10 : recycling::WeightedYield(weight, rule.value("weightRatio", 0.01), consumed);
        if (count > 0) result[output] = count;
        return result;
    }
    return result;
}

void RecycleInventorySelection(const RecyclingSelection& expected, bool entireStack, std::uint64_t epoch) {
    if (epoch != g_recyclingEpoch || !g_recyclingSettings.enabled || g_recyclingRules.is_null() || LegacyRecyclingLoaded()) return;
    std::string reason;
    const auto selected = ReadRecyclingSelection(reason);
    if (!selected || *selected != expected) { RE::DebugNotification("回收已取消：背包或选中物品发生变化。"); return; }
    auto* player = RE::PlayerCharacter::GetSingleton();
    auto* item = RE::TESForm::LookupByID<RE::TESBoundObject>(selected->form);
    if (!player || !item) return;
    const auto consumed = recycling::ConsumeCount(selected->count, item->Is(RE::FormType::Ammo), entireStack);
    if (!consumed) { RE::DebugNotification("箭矢每 10 支回收一份，当前数量不足。"); return; }
    auto menu = RE::UI::GetSingleton()->GetMenu<RE::InventoryMenu>();
    auto* entry = SelectedRecyclingEntry(menu.get());
    if (!entry) return;
    auto materials = RecyclingMaterials(item, consumed, entry->GetWeight(), entry->GetValue());
    if (materials.empty()) {
        const auto* source = item->GetFile(0);
        logger::warn("No recycling rule: name={} form={:08X} type={} source={} weight={}", selected->name,
            selected->form, static_cast<std::uint32_t>(item->GetFormType()), source ? source->GetFilename() : "<dynamic>", entry->GetWeight());
        const auto message = "「" + selected->name + "」没有可用的回收规则，已保留。";
        RE::DebugNotification(message.c_str()); return;
    }
    for (const auto& [material, count] : materials) {
        if (!material || material == item || count <= 0 || player->GetItemCount(material) > INT32_MAX - count) {
            RE::DebugNotification("回收数量无效，已保留物品。"); return;
        }
    }
    std::int32_t removed = 0;
    bool interrupted = false;
    for (const auto& part : selected->parts) {
        const auto amount = (std::min)(part.count, consumed - removed);
        if (amount <= 0) break;
        auto* extra = reinterpret_cast<RE::ExtraDataList*>(part.extra);
        if (!extra) {
            // With all selected extra lists consumed first, a plain-only remainder
            // has no competing instances for the engine to choose from.
            const auto inventory = player->GetInventory();
            const auto found = inventory.find(item);
            if (found == inventory.end() || found->second.first < amount) { interrupted = true; break; }
            bool tagged = false;
            if (found->second.second && found->second.second->extraLists)
                for (auto* candidate : *found->second.second->extraLists) if (candidate) tagged = true;
            if (tagged) { interrupted = true; break; }
        } else {
            // Earlier removals may rebuild lists; resolve each remaining part afresh.
            const auto inventory = player->GetInventory();
            const auto found = inventory.find(item);
            bool present = false;
            if (found != inventory.end() && found->second.second && found->second.second->extraLists)
                for (auto* candidate : *found->second.second->extraLists)
                    if (candidate == extra && candidate->GetCount() == part.count) present = true;
            if (!present) { interrupted = true; break; }
        }
        const auto before = player->GetItemCount(item);
        if (before < amount) { interrupted = true; break; }
        player->RemoveItem(item, amount, RE::ITEM_REMOVE_REASON::kRemove, extra, nullptr);
        const auto after = player->GetItemCount(item);
        if (before - after != amount || (part.unique && amount == part.count && IsUniqueIDInPlayerInventory(selected->form, part.unique))) {
            logger::error("Recycling removal mismatch {:08X}: requested={} before={} after={}", selected->form, amount, before, after);
            interrupted = true; break;
        }
        removed += amount;
        if (part.unique && amount == part.count && !IsUniqueIDInPlayerInventory(selected->form, part.unique)) {
            const ItemKey key{selected->form, part.unique};
            { std::scoped_lock lock(g_durabilityLock); g_durability.erase(key); g_lowDurabilityWarnings.erase(key); g_pendingBreaks.erase(key); }
            ClearEnhancementDraft(key);
        }
    }
    // If the inventory changed partway through, pay only for confirmed removals.
    if (removed != consumed) for (auto& [material, count] : materials)
        count = static_cast<std::int32_t>(static_cast<std::int64_t>(count) * removed / consumed);
    for (const auto& [material, count] : materials) if (count > 0) player->AddObjectToContainer(material, nullptr, count, nullptr);
    if (removed) NotifySalvagePickups(materials);
    QueuePlayerRuntimeEffectsSync();
    if (menu && menu->GetRuntimeData().itemList) menu->GetRuntimeData().itemList->Update(player);
    if (removed) PlayWorkshopSound("UIEnchantingItemCreate");
    const auto message = removed ? "已回收「" + selected->name + "」×" + std::to_string(removed) + "。" + (interrupted ? "其余物品回收已中止。" : "") : "物品未能移除，回收已取消。";
    RE::DebugNotification(message.c_str());
    logger::info("Native SkyUI recycling: {:08X} parts={} count={} rewards={}", selected->form, selected->parts.size(), removed, materials.size());
}

bool RecyclingSafetyDown() {
    const auto key = g_recyclingSettings.safety;
    if (key == g_recyclingSettings.key) return true;
    const int vk = key == 0x2A ? VK_LSHIFT : key == 0x36 ? VK_RSHIFT : key == 0x1D ? VK_LCONTROL :
        key == 0x9D ? VK_RCONTROL : key == 0x38 ? VK_LMENU : key == 0xB8 ? VK_RMENU : 0;
    return vk && (GetAsyncKeyState(vk) & 0x8000) != 0;
}

bool HandleInventoryRecyclingKey(std::uint32_t key, bool down) {
    if (key == 0) {
        if (g_recyclingPress) {
            std::string reason;
            const auto current = ReadRecyclingSelection(reason);
            if (!current || *current != g_recyclingPress->selection) ResetRecyclingInput();
        }
        return false;
    }
    if (!g_recyclingSettings.enabled || g_recyclingRules.is_null() || key != g_recyclingSettings.key) return false;
    if (!RecyclingMenuReady()) { g_recyclingPress.reset(); return false; }
    if (RecyclingKeyConflicts(key)) {
        if (down) RE::DebugNotification("回收主键与背包操作冲突，请在工坊设置中更换。");
        g_recyclingPress.reset(); return true;
    }
    if (LegacyRecyclingLoaded()) {
        if (down) RE::DebugNotification("请停用 SimpleRecycling.esp，避免与工坊原生回收重复执行。");
        g_recyclingPress.reset(); return true;
    }
    if (!RecyclingSafetyDown()) { g_recyclingPress.reset(); return false; }
    const auto now = std::chrono::steady_clock::now();
    if (down) {
        if (now - g_lastRecycling < std::chrono::milliseconds(300)) return true;
        std::string reason;
        const auto selected = ReadRecyclingSelection(reason);
        if (selected) g_recyclingPress = RecyclingPress{*selected, now};
        else if (!reason.empty()) RE::DebugNotification(reason.c_str());
    } else if (g_recyclingPress) {
        const auto pressed = std::exchange(g_recyclingPress, std::nullopt);
        const bool all = g_recyclingSettings.stack && now - pressed->started >= std::chrono::seconds(1);
        g_lastRecycling = now;
        if (auto* tasks = SKSE::GetTaskInterface()) tasks->AddTask([selection = pressed->selection, all, epoch = g_recyclingEpoch] {
            try { RecycleInventorySelection(selection, all, epoch); }
            catch (const std::exception& error) { logger::error("Recycling rejected: {}", error.what()); RE::DebugNotification("回收规则无效，操作已取消。"); }
        });
    }
    return true;
}

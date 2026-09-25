#define NOMINMAX
#include <RE/Skyrim.h>
#include <SKSE/SKSE.h>
#include <Windows.h>
#include <spdlog/sinks/basic_file_sink.h>
#include <cstdlib>
#include <format>
#include <optional>
#include <string>
#include "purchase.h"

namespace
{
    bool enabled = true;
    bool sneakToSteal = true;
    bool chinese = true;
    double priceMultiplier = 2.0;
    RE::TESBoundObject* gold = nullptr;
    thread_local bool purchasing = false;
    using Pickup = void (*)(RE::PlayerCharacter*, RE::TESObjectREFR*, std::int32_t, bool, bool);
    REL::Relocation<Pickup> originalPickup;
    RE::ObjectRefHandle displayedRef;
    std::int32_t displayedTotal = 0;
    std::int32_t displayedCount = 0;

    struct Quote
    {
        RE::NiPointer<RE::Actor> merchant;
        RE::TESObjectREFR* merchantContainer;
        std::int32_t count;
        std::int32_t unitPrice;
        std::int32_t total;
    };

    bool Supported(RE::TESBoundObject* base)
    {
        if (!base || base == gold || !base->IsInventoryObject()) return false;
        switch (base->GetFormType()) {
        case RE::FormType::AlchemyItem:
        case RE::FormType::Ingredient:
        case RE::FormType::Misc:
        case RE::FormType::Ammo:
        case RE::FormType::Weapon:
        case RE::FormType::Armor:
        case RE::FormType::Scroll:
        case RE::FormType::SoulGem:
            return true;
        default:
            return false;
        }
    }

    std::optional<Quote> GetQuote(RE::TESObjectREFR* ref)
    {
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!enabled || !gold || !player || !ref || !player->Is3DLoaded() ||
            player->IsInCombat() || (sneakToSteal && player->IsSneaking()) ||
            ref->IsDeleted() || ref->IsDisabled() || ref->IsActivationBlocked() ||
            !ref->Is3DLoaded() || !Supported(ref->GetBaseObject())) return std::nullopt;
        auto* cell = ref->GetParentCell();
        auto* location = ref->GetCurrentLocation();
        if (!cell || cell != player->GetParentCell() || !cell->IsInteriorCell() || !location ||
            !(location->HasKeywordString("LocTypeStore") || location->HasKeywordString("LocTypeInn")))
            return std::nullopt;
        // Do not intercept quest references, including aliases not flagged as quest objects.
        if (ref->extraList.HasType(RE::ExtraDataType::kAliasInstanceArray) ||
            ref->extraList.HasType(RE::ExtraDataType::kFromAlias) ||
            ref->extraList.HasQuestObjectAlias() || !player->WouldBeStealing(ref)) return std::nullopt;

        // GetOwner resolves reference ownership with the cell's inherited ownership.
        auto* owner = ref->GetOwner();
        if (!owner) owner = cell->GetOwner();
        auto* npcOwner = owner ? owner->As<RE::TESNPC>() : nullptr;
        auto* factionOwner = owner ? owner->As<RE::TESFaction>() : nullptr;
        // Hold/city crime factions are not proof that a shopkeeper owns an item.
        if ((!npcOwner && !factionOwner) || (factionOwner && factionOwner->TracksCrimes())) return std::nullopt;
        const auto count = ref->extraList.GetCount();
        const auto unit = displayed::Price(ref->GetBaseObject()->GetGoldValue(), 1, priceMultiplier);
        const auto total = unit ? displayed::Price(*unit, count, 1.0) : std::nullopt;
        if (!total) return std::nullopt;

        std::optional<Quote> quote;
        cell->ForEachReference([&](RE::TESObjectREFR* candidate) {
            auto* actor = candidate ? candidate->As<RE::Actor>() : nullptr;
            if (!actor || actor == player || actor->IsDeleted() || actor->IsDisabled() ||
                !actor->Is3DLoaded() || actor->IsDead() || actor->IsInCombat() ||
                actor->IsHostileToActor(player) || actor->IsPlayerTeammate())
                return RE::BSContainer::ForEachResult::kContinue;
            if ((npcOwner && actor->GetActorBase() != npcOwner) ||
                (factionOwner && !actor->IsInFaction(factionOwner)))
                return RE::BSContainer::ForEachResult::kContinue;
            actor->VisitFactions([&](RE::TESFaction* faction, std::int8_t) {
                // IsInFaction checks current membership, including removed base factions.
                if (!faction || !faction->IsVendor() || !actor->IsInFaction(faction) ||
                    !faction->vendorData.merchantContainer) return false;
                quote = Quote{RE::NiPointer<RE::Actor>(actor), faction->vendorData.merchantContainer, count, *unit, *total};
                return true;
            });
            return quote ? RE::BSContainer::ForEachResult::kStop : RE::BSContainer::ForEachResult::kContinue;
        });
        return quote;
    }

    void Notify(const char* zh, const char* en) { RE::DebugNotification(chinese ? zh : en); }

    struct Transaction
    {
        RE::PlayerCharacter* player;
        RE::TESObjectREFR* ref;
        RE::TESBoundObject* base;
        RE::TESForm* originalExplicitOwner;
        RE::TESObjectREFR* merchantContainer;
        bool arg3;
        bool playSound;
        std::int32_t Gold() const { return player->GetItemCount(gold); }
        std::int32_t Items() const { return player->GetItemCount(base); }
        void Debit(std::int32_t n) { player->RemoveItem(gold, n, RE::ITEM_REMOVE_REASON::kRemove, nullptr, nullptr); }
        void Refund(std::int32_t n) { player->AddObjectToContainer(gold, nullptr, n, nullptr); }
        void TransferOwnership() { ref->SetOwner(player->GetActorBase()); }
        void RestoreOwnership() { ref->SetOwner(originalExplicitOwner); }
        void PickUp(std::int32_t n) { originalPickup(player, ref, n, arg3, playSound); }
        void PayMerchant(std::int32_t n) { merchantContainer->AddObjectToContainer(gold, nullptr, n, nullptr); }
    };

    void PickupHook(RE::PlayerCharacter* player, RE::TESObjectREFR* ref, std::int32_t count, bool arg3, bool playSound)
    {
        // Ignore scripted remote pickups: only the player's current crosshair target qualifies.
        auto* pick = RE::CrosshairPickData::GetSingleton();
        auto target = pick ? pick->target.get() : RE::NiPointer<RE::TESObjectREFR>{};
        if (purchasing) return;
        if (player != RE::PlayerCharacter::GetSingleton() || target.get() != ref) {
            originalPickup(player, ref, count, arg3, playSound);
            return;
        }
        auto quote = GetQuote(ref);
        if (!quote) {
            if (displayedRef.get().get() == ref && !(sneakToSteal && player->IsSneaking())) {
                Notify("购买条件已变化，请重新瞄准物品", "Purchase conditions changed. Aim at the item again.");
                return;
            }
            originalPickup(player, ref, count, arg3, playSound);
            return;
        }
        // A changed stack must not silently charge a price different from the displayed quote.
        if (count <= 0 || count != quote->count || displayedRef.get().get() != ref ||
            displayedTotal != quote->total || displayedCount != count) {
            Notify("价格或数量已变化，请重新瞄准后购买", "Price or count changed. Aim at the item again.");
            return;
        }
        struct Guard { Guard() { purchasing = true; } ~Guard() { purchasing = false; } } guard;
        RE::NiPointer<RE::TESObjectREFR> keepAlive(ref);
        Transaction transaction{player, ref, ref->GetBaseObject(), ref->extraList.GetOwner(),
            quote->merchantContainer, arg3, playSound};
        const auto result = displayed::Purchase(transaction, quote->unitPrice, count);
        switch (result) {
        case displayed::Result::bought:
            Notify("购买成功", "Purchased");
            SKSE::log::info("Purchased reference {:08X}, base {:08X}, quoted count={}, total={}",
                ref->GetFormID(), transaction.base->GetFormID(), count, quote->total);
            break;
        case displayed::Result::insufficientGold:
            Notify("金币不足，未购买", "Not enough gold. Purchase cancelled.");
            break;
        default:
            Notify("购买未完成，未交付部分已退款", "Purchase incomplete. Undelivered items refunded.");
            SKSE::log::warn("Purchase did not complete for {:08X}: {}", ref->GetFormID(), static_cast<int>(result));
            break;
        }
    }

    template <class T>
    struct TextHook
    {
        using Function = bool (*)(T*, RE::TESObjectREFR*, RE::BSString&);
        static inline REL::Relocation<Function> original;
        static bool Thunk(T* self, RE::TESObjectREFR* ref, RE::BSString& text)
        {
            const bool result = original(self, ref, text);
            if (!result || !ref || ref->GetBaseObject() != self) return result;
            if (auto quote = GetQuote(ref)) {
                const auto label = chinese ? std::format("购买（{} 金币）\n{}", quote->total, ref->GetName()) :
                    std::format("Buy ({} gold)\n{}", quote->total, ref->GetName());
                text = label.c_str();
                displayedRef = ref->CreateRefHandle();
                displayedTotal = quote->total;
                displayedCount = quote->count;
            } else if (displayedRef.get().get() == ref) {
                displayedRef = RE::ObjectRefHandle{};
            }
            return result;
        }
        static void Install()
        {
            REL::Relocation<std::uintptr_t> vtable{T::VTABLE[0]};
            original = vtable.write_vfunc(0x4C, Thunk);
        }
    };

    void ReadSettings()
    {
        const auto path = (std::filesystem::current_path() / "Data/SKSE/Plugins/BuyDisplayedItems.ini").wstring();
        enabled = GetPrivateProfileIntW(L"General", L"Enabled", 1, path.c_str()) != 0;
        sneakToSteal = GetPrivateProfileIntW(L"General", L"SneakToSteal", 1, path.c_str()) != 0;
        chinese = GetPrivateProfileIntW(L"General", L"Chinese", 1, path.c_str()) != 0;
        wchar_t buffer[64]{};
        GetPrivateProfileStringW(L"Pricing", L"Multiplier", L"2.0", buffer, 64, path.c_str());
        wchar_t* end = nullptr;
        const auto parsed = std::wcstod(buffer, &end);
        if (end != buffer && *end == L'\0' && std::isfinite(parsed) && parsed >= 1.0 && parsed <= 10.0)
            priceMultiplier = parsed;
        else SKSE::log::warn("Invalid Multiplier; using 2.0");
    }

    void OnMessage(SKSE::MessagingInterface::Message* message)
    {
        if (!message) return;
        if (message->type == SKSE::MessagingInterface::kPreLoadGame ||
            message->type == SKSE::MessagingInterface::kNewGame) {
            displayedRef = RE::ObjectRefHandle{};
            displayedTotal = 0;
            displayedCount = 0;
        }
        if (message->type != SKSE::MessagingInterface::kDataLoaded) return;
        gold = RE::TESForm::LookupByID<RE::TESBoundObject>(0xF);
        if (!gold) { SKSE::log::error("Gold001 missing; hooks not installed"); return; }
        ReadSettings();
        if (!enabled) return;
        REL::Relocation<std::uintptr_t> playerVtable{RE::VTABLE_PlayerCharacter[0]};
        originalPickup = playerVtable.write_vfunc(0xCC, PickupHook);
        TextHook<RE::AlchemyItem>::Install();
        TextHook<RE::IngredientItem>::Install();
        TextHook<RE::TESObjectMISC>::Install();
        TextHook<RE::TESAmmo>::Install();
        TextHook<RE::TESObjectWEAP>::Install();
        TextHook<RE::TESObjectARMO>::Install();
        TextHook<RE::ScrollItem>::Install();
        TextHook<RE::TESSoulGem>::Install();
        SKSE::log::info("BuyDisplayedItems 0.1.0 installed; multiplier={}, sneakToSteal={}", priceMultiplier, sneakToSteal);
    }
}

extern "C" __declspec(dllexport) bool SKSEAPI SKSEPlugin_Load(const SKSE::LoadInterface* skse)
{
    auto path = SKSE::log::log_directory();
    if (!path) return false;
    *path /= "BuyDisplayedItems.log";
    auto sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>(path->string(), true);
    spdlog::set_default_logger(std::make_shared<spdlog::logger>("BuyDisplayedItems", std::move(sink)));
    spdlog::flush_on(spdlog::level::info);
    if (skse->RuntimeVersion() != REL::Version{1, 5, 97, 0}) {
        SKSE::log::error("Unsupported runtime {}; only 1.5.97 is supported", skse->RuntimeVersion().string());
        return false;
    }
    SKSE::Init(skse);
    auto* messaging = SKSE::GetMessagingInterface();
    return messaging && messaging->RegisterListener("SKSE", OnMessage);
}

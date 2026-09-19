#pragma once
#include "../../../durability-manager/native/src/forge_access.h"
#include "crafting_station_rules.h"

namespace crafting_access {
struct Access { bool magic = false; bool normal = false; };

// Scan loaded references afresh for each quote/commit; never retain furniture pointers.
inline Access Nearby(RE::PlayerCharacter* player) {
    Access result;
    auto* cell = player ? player->GetParentCell() : nullptr;
    auto* tes = RE::TES::GetSingleton();
    if (!cell || !cell->IsAttached() || !tes) return result;
    auto* world = player->GetWorldspace();
    const workshop::Location origin{cell->GetFormID(), world ? world->GetFormID() : 0U, cell->IsInteriorCell()};
    const auto position = player->GetPosition();
    tes->ForEachReferenceInRange(player, workshop::kRadius, [&](RE::TESObjectREFR* station) {
        if (!station || station->IsDeleted() || station->IsDisabled() || !station->Is3DLoaded()) return RE::BSContainer::ForEachResult::kContinue;
        auto* targetCell = station->GetParentCell();
        if (!targetCell || !targetCell->IsAttached()) return RE::BSContainer::ForEachResult::kContinue;
        auto* targetWorld = station->GetWorldspace();
        const workshop::Location target{targetCell->GetFormID(), targetWorld ? targetWorld->GetFormID() : 0U, targetCell->IsInteriorCell()};
        if (!workshop::IsNearby(position.GetSquaredDistance(station->GetPosition()), origin, target, true)) return RE::BSContainer::ForEachResult::kContinue;
        auto* base = station->GetBaseObject();
        if (!base || base->IsDeleted() || base->IsIgnored()) return RE::BSContainer::ForEachResult::kContinue;
        auto* furniture = base->As<RE::TESFurniture>();
        using BenchType = RE::TESFurniture::WorkBenchData::BenchType;
        const bool enchantingBench = furniture &&
            (furniture->workBenchData.benchType == BenchType::kEnchanting ||
             furniture->workBenchData.benchType == BenchType::kEnchantingExperiment);
        result.magic |= IsEnchantingStation(enchantingBench,
            [&](const char* keyword) { return base->HasKeywordByEditorID(keyword); });
        result.normal |= base->HasKeywordByEditorID("CraftingSmithingForge") ||
            base->HasKeywordByEditorID("CraftingSmelter") ||
            base->HasKeywordByEditorID("CraftingSmithingSharpeningWheel") ||
            base->HasKeywordByEditorID("CraftingSmithingArmorTable");
        return RE::BSContainer::ForEachResult::kContinue;
    });
    return result;
}
}

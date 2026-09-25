#pragma once
#include <functional>
#include <nlohmann/json.hpp>

namespace companion
{
using json = nlohmann::json;
using Completion = std::function<void(bool, std::string)>;
void InitializeManager();
void RegisterSerialization();
bool RegisterPapyrus(RE::BSScript::IVirtualMachine* vm);
void SetGameReady(bool ready);
// True only while the actor is in a fight the panel should respect: a live hostile target, and
// neither the player nor another companion. Lingering engine combat flags report false.
bool Fighting(RE::Actor *actor);
void ExecuteCommand(const json &command, Completion complete);
void DescribeActor(RE::Actor *actor, json &row);
// The player's wardrobe card: same outfit payload as a companion row, without a member record.
json DescribePlayer();
std::vector<RE::FormID> RegisteredActors();
std::vector<RE::FormID> DisabledSpells(RE::FormID actor);
json PlayerInventory();
json ManagerSettings();
std::string SessionToken();
RE::TESQuest *Controller();
void RefreshManagerView();
// Item panels name the one companion whose wardrobe/outfit payload they need; 0 means every
// managed companion keeps the full payload (the pre-existing behaviour).
void SetWardrobeFocus(RE::FormID actor);
bool ManagerViewOpen();
void CloseManagerView();
void OpenPartnerWardrobe(RE::FormID actor,std::string mode="inventory");
json ActivityOverview();
} // namespace companion

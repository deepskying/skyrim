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
void ExecuteCommand(const json &command, Completion complete);
void DescribeActor(RE::Actor *actor, json &row);
std::vector<RE::FormID> RegisteredActors();
std::vector<RE::FormID> DisabledSpells(RE::FormID actor);
json PlayerInventory();
json ManagerSettings();
std::string SessionToken();
RE::TESQuest *Controller();
void RefreshManagerView();
bool ManagerViewOpen();
void CloseManagerView();
void OpenPartnerWardrobe(RE::FormID actor,std::string mode="inventory");
json ActivityOverview();
} // namespace companion

#pragma once

#include <RE/Skyrim.h>
#include <SKSE/SKSE.h>
#include <filesystem>
#include <functional>
#include <string>

// One instance per DLL. Stable ESP records preserve favorites across saves;
// no Papyrus scripts or shared runtime plugin are needed.
namespace panel_power {
class Power final : public RE::BSTEventSink<RE::TESSpellCastEvent> {
public:
    Power(const char* plugin, std::function<void()> open) : plugin_(plugin), open_(std::move(open)) {}

    void OnMessage(SKSE::MessagingInterface::Message* message)
    {
        switch (message->type) {
        case SKSE::MessagingInterface::kDataLoaded: {
            auto* data = RE::TESDataHandler::GetSingleton();
            spell_ = data ? data->LookupForm<RE::SpellItem>(0x800, plugin_) : nullptr;
            if (!spell_) {
                SKSE::log::warn("Panel power unavailable: enable {} (hotkey remains available)", plugin_);
                return;
            }
            if (auto* source = RE::ScriptEventSourceHolder::GetSingleton(); source && !registered_) {
                source->AddEventSink<RE::TESSpellCastEvent>(this);
                registered_ = true;
            }
            break;
        }
        case SKSE::MessagingInterface::kPreLoadGame:
            loaded_ = false;
            pending_ = false;
            ++generation_;
            break;
        case SKSE::MessagingInterface::kNewGame:
        case SKSE::MessagingInterface::kPostLoadGame: {
            loaded_ = message->type == SKSE::MessagingInterface::kNewGame || message->data != nullptr;
            pending_ = false;
            const auto generation = ++generation_;
            if (loaded_) if (auto* tasks = SKSE::GetTaskInterface()) tasks->AddTask([this, generation] {
                if (generation != generation_ || !loaded_ || !spell_) return;
                auto* player = RE::PlayerCharacter::GetSingleton();
                if (!player) return;
                auto ini = std::filesystem::path(REL::Module::get().filePath().data()).parent_path() /
                    "Data" / "SKSE" / "Plugins" / std::filesystem::path(plugin_).replace_extension(".ini");
                enabled_ = GetPrivateProfileIntW(L"PanelPower", L"Enabled", 1, ini.c_str()) != 0;
                if (enabled_ && !player->HasSpell(spell_)) player->AddSpell(spell_);
                else if (!enabled_ && player->HasSpell(spell_)) player->RemoveSpell(spell_);
            });
            break;
        }
        default: break;
        }
    }

    RE::BSEventNotifyControl ProcessEvent(const RE::TESSpellCastEvent* event,
        RE::BSTEventSource<RE::TESSpellCastEvent>*) override
    {
        auto* player = RE::PlayerCharacter::GetSingleton();
        if (!event || !spell_ || !loaded_ || !enabled_ || pending_ || !player ||
            event->object.get() != player || event->spell != spell_->GetFormID())
            return RE::BSEventNotifyControl::kContinue;
        if (auto* tasks = SKSE::GetTaskInterface()) {
            pending_ = true;
            const auto generation = generation_;
            tasks->AddTask([this, generation] {
                if (generation != generation_) return;
                pending_ = false;
                auto* currentPlayer = RE::PlayerCharacter::GetSingleton();
                auto* ui = RE::UI::GetSingleton();
                if (!loaded_ || !currentPlayer || currentPlayer->IsDead() || !ui || ui->GameIsPaused() ||
                    ui->IsMenuOpen("Main Menu") || ui->IsMenuOpen("Loading Menu")) return;
                open_();
            });
        }
        return RE::BSEventNotifyControl::kContinue;
    }

private:
    std::string plugin_;
    std::function<void()> open_;
    RE::SpellItem* spell_ = nullptr;
    std::uint64_t generation_ = 0;
    bool registered_ = false;
    bool loaded_ = false;
    bool enabled_ = true;
    bool pending_ = false;
};
}

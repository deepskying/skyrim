#include "../../../../shared/panel-power/panel_power.h"
#include "PrismaUI_API.h"
#include "music_service.h"
#include "music_settings.h"
#include <atomic>
#include <thread>
#include <unordered_map>
#include <shellapi.h>
#undef GetObject

namespace {
using json = nlohmann::json;
namespace fs = std::filesystem;
PRISMA_UI_API::IVPrismaUI1* prisma = nullptr;
PrismaView view = 0;
std::unique_ptr<music::Service> service;
std::jthread ticker;
std::atomic_bool queued{false};
bool loaded = false, muted = false;
unsigned epoch = 0;
RE::BGSSoundCategory* musicCategory = nullptr;
RE::BGSSoundCategory* masterCategory = nullptr;
std::uint16_t originalAttenuation = 0;
std::unordered_map<RE::BSIMusicType*, std::string> musicIDs;
std::unordered_set<RE::BSIMusicType*> storyTypes;
std::vector<RE::ActorHandle> dragonEnemies;
std::vector<std::string> storyPrefixes{"MUSSpecial", "MUSMQ", "MUSChargen", "MUSIntro"};
music::Hotkey hotkey;
std::string hotkeyMessage;
fs::path libraryRoot;

fs::path dataPath() { return fs::path(REL::Module::get().filePath().data()).parent_path() / "Data"; }
void updateHotkey(const json& request) {
    try {
        const auto next = music::Hotkey::parse(request);
        const auto path = dataPath() / "SKSE/Plugins/MusicManager.hotkey.json";
        auto temporary = path; temporary += L".tmp";
        {
            std::ofstream file(temporary, std::ios::binary | std::ios::trunc);
            file << next.json().dump(2); file.flush();
            if (!file) throw std::runtime_error("无法写入快捷键配置");
        }
        if (!MoveFileExW(temporary.c_str(), path.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) throw std::runtime_error("无法保存快捷键配置");
        hotkey = next; // Commit only after durable save, so a failed write keeps the old binding.
        hotkeyMessage = "已保存并生效：" + hotkey.label();
    } catch (const std::exception& e) { hotkeyMessage = std::string("快捷键未修改：") + e.what(); }
}
void muteNative(bool value) {
    if (!musicCategory) return;
    if (value && !muted) {
        originalAttenuation = musicCategory->attenuation;
        musicCategory->SetCategoryAttenuation(10000); // 100 dB; does not change the user's music slider.
        muted = true;
    } else if (!value && muted) {
        musicCategory->SetCategoryAttenuation(originalAttenuation);
        muted = false;
    }
}
void closePanel() {
    if (!prisma || !view) return;
    prisma->Unfocus(view); prisma->Hide(view);
}
void sendState() {
    if (!service || !prisma || !view || prisma->IsHidden(view)) return;
    auto state = service->snapshot();
    if (!state.is_object()) return;
    state["hotkey"] = hotkey.json();
    state["hotkeyMessage"] = hotkeyMessage;
    if (!musicCategory) state["message"] = "未找到游戏音乐类别，自动接管尚未启动";
    auto payload = state.dump(-1, ' ', false, json::error_handler_t::replace);
    auto script = "window.MusicManager && window.MusicManager.receiveState(" + payload + ");";
    prisma->Invoke(view, script.c_str());
}
void togglePanel() {
    if (!prisma || !view) return;
    if (prisma->HasFocus(view)) { closePanel(); return; }
    auto* ui = RE::UI::GetSingleton();
    if (!loaded || !ui || ui->IsMenuOpen("Main Menu") || ui->IsMenuOpen("Loading Menu") || ui->IsMenuOpen("Console") || prisma->HasAnyActiveFocus()) return;
    prisma->Show(view);
    // The manager stays live, so browsing/previewing music doesn't pause playback.
    if (!prisma->Focus(view, false)) { prisma->Hide(view); return; }
    sendState();
}
bool dragon(RE::Actor* actor) {
    auto* race = actor ? actor->GetRace() : nullptr;
    return race && race->HasKeywordString("ActorTypeDragon") && !actor->IsDead();
}
music::Environment capture() {
    music::Environment e; e.epoch = epoch;
    auto* ui = RE::UI::GetSingleton();
    auto* p = RE::PlayerCharacter::GetSingleton();
    if (!loaded || !ui || !p || ui->IsMenuOpen("Main Menu") || ui->IsMenuOpen("Loading Menu")) return e;
    e.active = p->GetParentCell() && p->Is3DLoaded() && !p->IsDead();
    e.paused = ui->GameIsPaused();
    if (!e.active) return e;
    e.interior = p->GetParentCell()->IsInteriorCell();
    e.combat = p->IsInCombat();
    if (auto* calendar = RE::Calendar::GetSingleton()) e.hour = calendar->GetHour();
    if (masterCategory) e.masterVolume = masterCategory->GetCategoryVolume();
    auto* location = p->GetCurrentLocation();
    if (location) e.location = location->GetName();
    if (e.location.empty()) e.location = p->GetParentCell()->GetName();
    // Parent locations are required for city interiors; cap malformed mod cycles.
    for (unsigned depth = 0; location && depth < 16; ++depth, location = location->parentLoc) {
        e.tavern |= location->HasKeywordString("LocTypeInn");
        e.home |= location->HasKeywordString("LocTypePlayerHouse");
        e.castle |= location->HasKeywordString("LocTypeCastle");
        e.cemetery |= location->HasKeywordString("LocTypeCemetery");
        e.temple |= location->HasKeywordString("LocTypeTemple");
        // Some vanilla burial halls lack LocTypeCemetery (e.g. Solitude).
        std::string locationID = location->GetFormEditorID();
        std::transform(locationID.begin(), locationID.end(), locationID.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
        e.cemetery |= locationID.find("hallofthedead") != std::string::npos || locationID.find("hallofdead") != std::string::npos;
        e.town |= location->HasKeywordString("LocTypeCity") || location->HasKeywordString("LocTypeTown") || location->HasKeywordString("LocTypeSettlement");
        e.dungeon |= location->HasKeywordString("LocTypeDungeon") || location->HasKeywordString("LocTypeCave") || location->HasKeywordString("LocTypeDraugrCrypt") || location->HasKeywordString("LocTypeDwarvenAutomatons") || location->HasKeywordString("LocTypeNordicRuin") || location->HasKeywordString("LocTypeMine");
    }
    if (e.combat) {
        if (auto* group = p->GetCombatGroup()) {
            for (const auto& target : group->targets) {
                auto enemy = target.targetHandle.get();
                if (enemy && dragon(enemy.get())) { e.dragon = true; break; }
            }
        }
        std::erase_if(dragonEnemies, [](const auto& handle) { auto actor = handle.get(); return !actor || actor->IsDead() || !actor->IsInCombat(); });
        e.dragon |= !dragonEnemies.empty();
    } else dragonEnemies.clear();
    if (auto* manager = RE::BSMusicManager::GetSingleton(); manager && manager->current) {
        if (auto it = musicIDs.find(manager->current); it != musicIDs.end()) {
            e.nativeMusic = it->second;
            e.story = storyTypes.contains(manager->current);
            for (const auto& prefix : storyPrefixes) if (it->second.starts_with(prefix)) e.story = true;
        }
    }
    return e;
}
void tick() {
    queued = false;
    if (!service) return;
    auto e = capture();
    // Do not suppress the game when our audio device or sound-category lookup failed.
    const bool takeOver = musicCategory && service->ready() && service->enabled();
    muteNative(takeOver && e.active && !e.story);
    if (!takeOver) e.active = false;
    service->environment(std::move(e));
    sendState();
    if (!loaded) closePanel();
}
void action(const char* data) {
    try {
        auto request = json::parse(data ? data : "{}");
        // Prisma callbacks may arrive from its renderer; game/UI operations always
        // run on SKSE's main-thread task queue.
        if (auto* tasks = SKSE::GetTaskInterface()) tasks->AddTask([request = std::move(request)] {
            try {
            if (request.value("type", "") == "close") closePanel();
            else if (request.value("type", "") == "ready") sendState();
            else if (request.value("type", "") == "hotkey") { updateHotkey(request.at("value")); sendState(); }
            else if (request.value("type", "") == "openFolder") {
                for (const auto& category : music::categories) if (request.value("category", "") == category.id) {
                    const auto folder = libraryRoot / fs::u8path(category.folder);
                    std::error_code ec; fs::create_directories(folder, ec);
                    ShellExecuteW(nullptr, L"open", folder.c_str(), nullptr, nullptr, SW_SHOWNORMAL);
                }
            } else if (service) service->command(request);
            } catch (const std::exception& e) { logger::warn("Invalid music UI action: {}", e.what()); }
        });
    } catch (const std::exception& e) { logger::warn("Invalid music UI request: {}", e.what()); }
}
class Events final : public RE::BSTEventSink<RE::InputEvent*>, public RE::BSTEventSink<RE::TESCombatEvent> {
public:
    RE::BSEventNotifyControl ProcessEvent(RE::InputEvent* const* events, RE::BSTEventSource<RE::InputEvent*>*) override {
        if (!events) return RE::BSEventNotifyControl::kContinue;
        for (auto* event = *events; event; event = event->next) {
            if (event->GetDevice() != RE::INPUT_DEVICE::kKeyboard) continue;
            auto* button = event->AsButtonEvent();
            if (!button || !button->IsDown()) continue;
            const auto key = button->GetIDCode();
            if (key == 1 && prisma && view && prisma->HasFocus(view)) prisma->Invoke(view, "window.MusicManager && window.MusicManager.escape();");
            else if (hotkey.matches(key, (GetAsyncKeyState(VK_SHIFT) & 0x8000) != 0, (GetAsyncKeyState(VK_CONTROL) & 0x8000) != 0, (GetAsyncKeyState(VK_MENU) & 0x8000) != 0)) togglePanel();
        }
        return RE::BSEventNotifyControl::kContinue;
    }
    RE::BSEventNotifyControl ProcessEvent(const RE::TESCombatEvent* event, RE::BSTEventSource<RE::TESCombatEvent>*) override {
        auto* p = RE::PlayerCharacter::GetSingleton();
        if (event && event->actor && event->targetActor && event->newState == RE::ACTOR_COMBAT_STATE::kCombat && event->targetActor.get() == p) {
            auto* enemy = event->actor->As<RE::Actor>();
            if (dragon(enemy) && dragonEnemies.size() < 32) dragonEnemies.push_back(enemy->GetHandle());
        }
        return RE::BSEventNotifyControl::kContinue;
    }
} events;
panel_power::Power panelPower("MusicManager.esp", [] {
    if (prisma && view && !prisma->HasAnyActiveFocus()) togglePanel();
});
void onMessage(SKSE::MessagingInterface::Message* message) {
    panelPower.OnMessage(message);
    switch (message->type) {
    case SKSE::MessagingInterface::kPreLoadGame:
        loaded = false; ++epoch; dragonEnemies.clear(); muteNative(false); closePanel();
        if (service) service->environment(capture());
        break;
    case SKSE::MessagingInterface::kNewGame:
        loaded = true; ++epoch; tick(); break;
    case SKSE::MessagingInterface::kPostLoadGame:
        loaded = message->data != nullptr; ++epoch; tick(); break;
    case SKSE::MessagingInterface::kDataLoaded: {
        const auto data = dataPath();
        const auto ini = data / "SKSE/Plugins/MusicManager.ini";
        const auto legacyCode = GetPrivateProfileIntW(L"Hotkey", L"ScanCode", 0x32, ini.c_str());
        if (!music::Hotkey::keyName(legacyCode).empty()) hotkey.scanCode = legacyCode;
        try {
            std::ifstream file(data / "SKSE/Plugins/MusicManager.hotkey.json");
            if (file) hotkey = music::Hotkey::parse(json::parse(file));
        } catch (const std::exception& e) { hotkeyMessage = std::string("快捷键配置读取失败，使用 ") + hotkey.label(); logger::warn("Hotkey settings: {}", e.what()); }
        std::array<wchar_t, 4096> configuredRoot{};
        GetPrivateProfileStringW(L"Library", L"Path", L"", configuredRoot.data(), static_cast<DWORD>(configuredRoot.size()), ini.c_str());
        libraryRoot = configuredRoot[0] ? fs::path(configuredRoot.data()) : data / "Music/MusicManager";
        if (libraryRoot.is_relative()) libraryRoot = data / libraryRoot;
        if (auto* defaults = RE::BGSDefaultObjectManager::GetSingleton()) {
            musicCategory = defaults->GetObject<RE::BGSSoundCategory>(RE::DEFAULT_OBJECT::kMusicSoundCategory);
            masterCategory = defaults->GetObject<RE::BGSSoundCategory>(RE::DEFAULT_OBJECT::kMasterSoundCategory);
            for (const auto id : {RE::DEFAULT_OBJECT::kDeathMusic, RE::DEFAULT_OBJECT::kSuccessMusic, RE::DEFAULT_OBJECT::kLevelUpMusic, RE::DEFAULT_OBJECT::kDungeonClearedMusic})
                if (auto* type = defaults->GetObject<RE::BGSMusicType>(id)) storyTypes.insert(type);
        }
        if (auto* handler = RE::TESDataHandler::GetSingleton()) for (auto* type : handler->GetFormArray<RE::BGSMusicType>()) if (type) musicIDs[type] = type->GetFormEditorID();
        try {
            std::ifstream file(data / "SKSE/Plugins/MusicManager.rules.json");
            if (file) {
                const auto rules = json::parse(file);
                storyPrefixes = rules.value("storyPrefixes", storyPrefixes);
                for (const auto& id : rules.value("storyEditorIDs", std::vector<std::string>{})) for (const auto& [type, name] : musicIDs) if (name == id) storyTypes.insert(type);
            }
        } catch (const std::exception& e) { logger::warn("Music rules: {}", e.what()); }
        service = std::make_unique<music::Service>(libraryRoot, data / "SKSE/Plugins/MusicManager.settings.json");
        prisma = PRISMA_UI_API::RequestPluginAPI();
        if (prisma) {
            view = prisma->CreateView("MusicManager/index.html", [](PrismaView) { logger::info("Music Manager view ready"); });
            if (view) { prisma->RegisterJSListener(view, "musicManagerAction", action); prisma->Hide(view); }
        }
        if (!view) logger::error("Prisma UI unavailable: music playback runs, Shift+M panel unavailable");
        if (auto* input = RE::BSInputDeviceManager::GetSingleton()) input->AddEventSink(&events);
        if (auto* source = RE::ScriptEventSourceHolder::GetSingleton()) source->AddEventSink<RE::TESCombatEvent>(&events);
        ticker = std::jthread([](std::stop_token stop) {
            while (!stop.stop_requested()) {
                if (!queued.exchange(true)) {
                    if (auto* tasks = SKSE::GetTaskInterface()) tasks->AddTask(tick); else queued = false;
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(250));
            }
        });
        logger::info("Music Manager 0.3.0 initialized; music category found: {}", musicCategory != nullptr);
        break;
    }
    default: break;
    }
}
}
extern "C" DLLEXPORT bool SKSEAPI SKSEPlugin_Load(const SKSE::LoadInterface* skse) {
    REL::Module::reset();
    // This build is validated against the user's SE 1.5.97 runtime only.
    if (skse->RuntimeVersion() != REL::Version(1, 5, 97, 0)) return false;
    SKSE::Init(skse);
    if (auto directory = SKSE::log::log_directory()) {
        *directory /= "MusicManager.log";
        auto sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>(directory->string(), true);
        auto log = std::make_shared<spdlog::logger>("MusicManager", std::move(sink));
        spdlog::set_default_logger(log); spdlog::flush_on(spdlog::level::info);
    }
    auto* messaging = SKSE::GetMessagingInterface();
    return messaging && messaging->RegisterListener("SKSE", onMessage);
}

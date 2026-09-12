#include <SKSE/SKSE.h>
#include <spdlog/sinks/basic_file_sink.h>
#include "library.h"
#include <Windows.h>
#include <array>
#include <fstream>
#include <nlohmann/json.hpp>

using namespace std::literals;
SKSEPluginInfo(
    .Version = {0, 1, 0, 0},
    .Name = "MainMenuManager"sv,
    .Author = "linos"sv,
    .RuntimeCompatibility = {SKSE::PluginDeclaration::VersionNumber{1, 5, 97, 0}}
)

namespace {
std::filesystem::path dataPath() {
    std::array<wchar_t, 32768> path{};
    const auto size = GetModuleFileNameW(nullptr, path.data(), static_cast<DWORD>(path.size()));
    if (!size || size >= path.size()) throw std::runtime_error("Cannot locate SkyrimSE.exe");
    return std::filesystem::path(path.data()).parent_path() / "Data";
}

void onMessage(SKSE::MessagingInterface::Message* message) {
    // All SKSE plugins have loaded; the main-menu resources have not yet been
    // requested. Run once per process, not on loading saves or returning to menu.
    if (!message || message->type != SKSE::MessagingInterface::kPostLoad) return;
    static bool started = false;
    if (std::exchange(started, true)) return;
    try {
        const auto data = dataPath();
        bool enabled = true;
        std::ifstream config(data / "SKSE/Plugins/MainMenuManager.json", std::ios::binary);
        if (config) enabled = nlohmann::json::parse(config).value("enabled", true);
        std::random_device seed;
        std::seed_seq seeds{seed(), seed(), seed(), seed()};
        std::mt19937_64 random(seeds);
        mainmenu::Manager manager(data, [](const std::string& text) { SKSE::log::info("{}", text); });
        manager.start(enabled, random);
    } catch (const std::exception& error) {
        SKSE::log::error("Background selection stopped: {}", error.what());
    } catch (...) {
        SKSE::log::error("Background selection stopped: unknown error");
    }
}
}

SKSEPluginLoad(const SKSE::LoadInterface* skse) {
    if (!skse || skse->IsEditor() || skse->RuntimeVersion() != REL::Version(1, 5, 97, 0)) return false;
    try {
        SKSE::Init(skse);
        if (auto path = SKSE::log::log_directory()) {
            *path /= "MainMenuManager.log";
            auto sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>(path->string(), true);
            auto logger = std::make_shared<spdlog::logger>("MainMenuManager", std::move(sink));
            spdlog::set_default_logger(logger);
            spdlog::flush_on(spdlog::level::info);
        }
        SKSE::log::info("MainMenuManager 0.1.0; Skyrim SE 1.5.97");
        auto* messaging = SKSE::GetMessagingInterface();
        return messaging && messaging->RegisterListener("SKSE", onMessage);
    } catch (...) { return false; }
}

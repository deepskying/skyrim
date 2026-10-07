#include <RE/Skyrim.h>
#include <SKSE/SKSE.h>
#include <spdlog/sinks/basic_file_sink.h>

#include <Windows.h>

#include <array>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>
#include <string_view>
#include <thread>

#include "guard_code.h"

namespace
{
    std::jthread g_reporter;

    void ReportCounts(std::string_view a_where)
    {
        for (std::size_t i = 0; i < condition_guard::kTargets.size(); ++i) {
            const auto count = condition_guard::g_slots[i].interceptions.load(std::memory_order_relaxed);
            if (count != 0) {
                SKSE::log::info("{}: {} guarded {} non-actor evaluation(s)",
                    a_where, condition_guard::kTargets[i].name, count);
            }
        }
    }

    void OnMessage(SKSE::MessagingInterface::Message* a_message)
    {
        if (!a_message) {
            return;
        }
        if (a_message->type == SKSE::MessagingInterface::kPreLoadGame) {
            ReportCounts("PreLoadGame");
        } else if (a_message->type == SKSE::MessagingInterface::kPostLoadGame) {
            ReportCounts("PostLoadGame");
        }
    }
}

extern "C" __declspec(dllexport) bool SKSEAPI SKSEPlugin_Load(const SKSE::LoadInterface* a_skse)
{
    auto path = SKSE::log::log_directory();
    if (!path) {
        return false;
    }
    *path /= "ConditionActorGuard.log";
    auto sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>(path->string(), true);
    auto log = std::make_shared<spdlog::logger>("ConditionActorGuard", std::move(sink));
    spdlog::set_default_logger(std::move(log));
    spdlog::flush_on(spdlog::level::info);

    // The table RVAs and handler RVAs are verified against the captured 1.5.97
    // binary. Never extrapolate them to AE, VR or another SE build.
    if (a_skse->RuntimeVersion() != REL::Version{ 1, 5, 97, 0 }) {
        SKSE::log::error("Unsupported runtime {}; no handler replaced", a_skse->RuntimeVersion().string());
        return false;
    }
    SKSE::Init(a_skse);
    const auto messaging = SKSE::GetMessagingInterface();
    if (!messaging || !messaging->RegisterListener("SKSE", OnMessage)) {
        SKSE::log::error("Cannot register load diagnostics; no handler replaced");
        return false;
    }

    const auto base = reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr));
    const auto hooks = condition_guard::MakeHooks();
    std::size_t installed = 0;
    for (std::size_t i = 0; i < condition_guard::kTargets.size(); ++i) {
        const auto& target = condition_guard::kTargets[i];
        auto* entry = reinterpret_cast<std::uintptr_t*>(
            base + condition_guard::kTableRva +
            static_cast<std::uintptr_t>(target.index) * condition_guard::kTableStride +
            condition_guard::kHandlerOffset);
        const auto expected = base + target.handlerRva;
        if (*entry != expected) {
            SKSE::log::error("{} (index {}): expected handler 0x{:X}, found 0x{:X}; left alone",
                target.name, target.index, expected, *entry);
            continue;
        }
        condition_guard::g_slots[i].original = reinterpret_cast<condition_guard::Handler>(*entry);
        REL::safe_write(reinterpret_cast<std::uintptr_t>(entry), &hooks[i], sizeof(hooks[i]));
        ++installed;
        SKSE::log::info("{} (index {}): guarded handler 0x{:X}", target.name, target.index, expected);
    }

    if (installed == 0) {
        SKSE::log::error("No condition function handler matched; refusing to load");
        return false;
    }

    SKSE::log::info("ConditionActorGuard 0.1.0 installed {} of {} guards for Skyrim 1.5.97",
        installed, condition_guard::kTargets.size());
    SKSE::log::info("Actor subjects keep the original handler; non-actor subjects report the condition as unmet.");
    // The hooks only touch an atomic counter, so report it from an independent
    // thread instead of from inside the engine's condition evaluation.
    g_reporter = std::jthread([](std::stop_token a_stop) {
        std::mutex mutex;
        std::condition_variable_any wake;
        std::unique_lock lock(mutex);
        std::array<std::int64_t, condition_guard::kTargets.size()> reported{};
        while (!a_stop.stop_requested()) {
            wake.wait_for(lock, a_stop, std::chrono::seconds(2), [] { return false; });
            if (a_stop.stop_requested()) {
                break;
            }
            for (std::size_t i = 0; i < condition_guard::kTargets.size(); ++i) {
                const auto count = condition_guard::g_slots[i].interceptions.load(std::memory_order_relaxed);
                if (count != reported[i]) {
                    SKSE::log::warn("{}: guarded {} non-actor evaluation(s); the condition was treated as unmet",
                        condition_guard::kTargets[i].name, count);
                    reported[i] = count;
                }
            }
        }
    });
    return true;
}

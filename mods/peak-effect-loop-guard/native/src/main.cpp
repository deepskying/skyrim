#include <RE/Skyrim.h>
#include <SKSE/SKSE.h>
#include <spdlog/sinks/basic_file_sink.h>
#include <Windows.h>
#include <thread>
#include <condition_variable>

#include "guard_code.h"

namespace
{
    alignas(8) volatile LONG64 g_interceptions = 0;
    SKSE::Trampoline g_trampoline{"PeakEffectLoopGuard"};
    std::jthread g_reporter;

    void OnMessage(SKSE::MessagingInterface::Message* message)
    {
        if (message && (message->type == SKSE::MessagingInterface::kPreLoadGame ||
                        message->type == SKSE::MessagingInterface::kPostLoadGame)) {
            const auto count = InterlockedCompareExchange64(&g_interceptions, 0, 0);
            SKSE::log::info("{}: self-loop interceptions this process={}",
                message->type == SKSE::MessagingInterface::kPreLoadGame ? "PreLoadGame" : "PostLoadGame", count);
        }
    }
}

extern "C" __declspec(dllexport) bool SKSEAPI SKSEPlugin_Load(const SKSE::LoadInterface* skse)
{
    auto path = SKSE::log::log_directory();
    if (!path) return false;
    *path /= "PeakEffectLoopGuard.log";
    auto sink = std::make_shared<spdlog::sinks::basic_file_sink_mt>(path->string(), true);
    auto log = std::make_shared<spdlog::logger>("PeakEffectLoopGuard", std::move(sink));
    spdlog::set_default_logger(std::move(log));
    spdlog::flush_on(spdlog::level::info);

    // This is an instruction-level patch verified against the captured 1.5.97 binary.
    // Never extrapolate the RVA or instruction layout to AE/VR/other SE versions.
    if (skse->RuntimeVersion() != REL::Version{1, 5, 97, 0}) {
        SKSE::log::error("Unsupported runtime {}; no patch written", skse->RuntimeVersion().string());
        return false;
    }
    SKSE::Init(skse);
    const auto base = reinterpret_cast<std::uintptr_t>(GetModuleHandleW(nullptr));
    const auto site = base + peak_guard::kPatchRva;
    if (std::memcmp(reinterpret_cast<const void*>(site), peak_guard::kExpected.data(), peak_guard::kExpected.size()) != 0) {
        SKSE::log::error("Instruction mismatch at RVA 0x55B0B7 (modified binary or competing hook); no patch written");
        return false;
    }
    const auto messaging = SKSE::GetMessagingInterface();
    if (!messaging || !messaging->RegisterListener("SKSE", OnMessage)) {
        SKSE::log::error("Cannot register load diagnostics; no patch written");
        return false;
    }

    g_trampoline.create(128);
    const auto code = peak_guard::MakeGuard(reinterpret_cast<std::uintptr_t>(&g_interceptions), site + 7);
    auto stub = g_trampoline.allocate(code.size());
    std::memcpy(stub, code.data(), code.size());
    // Installation occurs during SKSE startup, before game worker threads traverse effects.
    // Retain original TEST/JNE. They overwrite arithmetic flags modified in our stub.
    g_trampoline.write_branch<5>(site, reinterpret_cast<std::uintptr_t>(stub));
    const std::array<std::uint8_t, 2> nops{0x90, 0x90};
    REL::safe_write(site + 5, nops.data(), nops.size());
    FlushInstructionCache(GetCurrentProcess(), stub, code.size());
    FlushInstructionCache(GetCurrentProcess(), reinterpret_cast<void*>(site), 7);
    SKSE::log::info("PeakEffectLoopGuard 0.1.0 installed at RVA 0x55B0B7 for Skyrim 1.5.97");
    SKSE::log::info("Direct self-loops only. Stops traversal without changing effect links, refcounts, spells or saves.");
    // The hot hook performs no logging, allocations or game API calls. Report its
    // atomic counter from an independent thread, including if loading stalls elsewhere.
    g_reporter = std::jthread([](std::stop_token stop) {
        std::mutex mutex;
        std::condition_variable_any wake;
        std::unique_lock lock(mutex);
        LONG64 reported = 0;
        while (!stop.stop_requested()) {
            wake.wait_for(lock, stop, std::chrono::seconds(2), [] { return false; });
            if (stop.stop_requested()) break;
            const auto count = InterlockedCompareExchange64(&g_interceptions, 0, 0);
            if (count != reported) {
                SKSE::log::warn("Stopped {} additional direct self-loop traversals; process total={}. Effect state was not repaired.", count - reported, count);
                reported = count;
            }
        }
    });
    return true;
}

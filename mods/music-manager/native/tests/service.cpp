#include "music_service.h"
#include <chrono>
#include <fstream>
#include <iostream>
#include <thread>
#include <cstdlib>

namespace fs = std::filesystem;
using json = nlohmann::json;
void check(bool yes, const char* what) { if (!yes) { std::cerr << "FAILED: " << what << '\n'; std::exit(1); } }
void wave(const fs::path& path) {
    fs::create_directories(path.parent_path());
    std::ofstream f(path, std::ios::binary);
    auto u16 = [&](std::uint16_t v) { f.write(reinterpret_cast<char*>(&v), 2); };
    auto u32 = [&](std::uint32_t v) { f.write(reinterpret_cast<char*>(&v), 4); };
    const unsigned bytes = 48000 * 2 * 2 * 2; // Two seconds of silence, no audible test output.
    f.write("RIFF", 4); u32(bytes + 36); f.write("WAVEfmt ", 8); u32(16);
    u16(1); u16(2); u32(48000); u32(192000); u16(4); u16(16);
    f.write("data",4); u32(bytes); std::vector<char> silence(bytes); f.write(silence.data(), bytes);
}
template<class F> json await(music::Service& service, F predicate, const char* what, int timeout = 5000) {
    auto start = std::chrono::steady_clock::now();
    while (std::chrono::steady_clock::now() - start < std::chrono::milliseconds(timeout)) {
        auto state = service.snapshot();
        if (state.is_object() && predicate(state)) return state;
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }
    std::cerr << service.snapshot().dump(2) << '\n'; check(false, what); return {};
}
int wmain(int argc, wchar_t** argv) {
    check(argc == 2, "supply a fresh fixture directory");
    fs::path root = fs::absolute(argv[1]);
    check(!fs::exists(root), "fixture directory must be fresh (no deletion)");
    fs::create_directories(root);
    const auto library = root / "Music";
    const auto settings = root / "settings.json";
    wave(library / L"通用" / L"中文歌曲.wav");
    wave(library / L"普通战斗" / L"战斗.wav");
    std::ofstream(library / L"普通战斗" / L"坏文件.mp3") << "not audio";
    const std::string general = "通用/中文歌曲.wav";
    {
        music::Service service(library, settings);
        await(service, [](auto& s) { return s["tracks"].size() == 3; }, "initial scan");
        music::Environment env; env.active = true; env.epoch = 1; service.environment(env);
        auto s = await(service, [&](auto& j) { return j["current"] == general; }, "fallback to general");
        service.command({{"type", "pause"}});
        s = await(service, [](auto& j) { return j["paused"] == true; }, "manual pause");
        const float cursor = s["position"];
        std::this_thread::sleep_for(std::chrono::milliseconds(700));
        check(std::abs(service.snapshot()["position"].get<float>() - cursor) < .06f, "pause freezes cursor");
        service.command({{"type", "pause"}});
        env.combat = true; service.environment(env);
        await(service, [](auto& j) { return j["playlist"] == "combat" && j["current"] == "普通战斗/战斗.wav"; }, "combat enters despite corrupt candidate");
        env.story = true; service.environment(env);
        await(service, [](auto& j) { return j["current"] == "" && j["status"] == "剧情音乐优先"; }, "story releases playback");
        env.story = false; env.combat = false; ++env.epoch; service.environment(env);
        await(service, [&](auto& j) { return j["current"] == general; }, "reload resets combat and pause");
        service.command({{"type", "fallback"}, {"value", false}});
        await(service, [](auto& j) { return j["current"] == ""; }, "empty category stays silent with fallback off");
        service.command({{"type", "fallback"}, {"value", true}});
        await(service, [&](auto& j) { return j["current"] == general; }, "fallback toggles live");
        service.command({{"type", "disable"}, {"id", general}});
        await(service, [](auto& j) { return j["current"] == ""; }, "disabled fallback stays silent");
        wave(library / L"野外白天" / L"新音乐.wav");
        service.command({{"type", "scan"}});
        await(service, [](auto& j) { return j["current"] == "野外白天/新音乐.wav"; }, "rescan discovers new file");
        env.paused = true; service.environment(env);
        await(service, [](auto& j) { return j["status"] == "已暂停"; }, "real game pause");
        auto options=service.snapshot()["playback"];
        options["pauseWithGame"]=false;options["followMaster"]=false;options["fadeSeconds"]=.75;options["sceneDelay"]=0;
        service.command({{"type","configure"},{"value",options}});
        await(service, [](auto& j) { return j["status"] == "正在播放" && j["playback"]["pauseWithGame"] == false; }, "pause setting applies live");
        auto invalid=options;invalid["dayStart"]=22;invalid["dayEnd"]=5;
        service.command({{"type","configure"},{"value",invalid}});
        auto rejected=await(service, [](auto& j) { return j["message"].template get<std::string>().starts_with("操作失败"); }, "bad config reported");
        check(rejected["playback"]["dayStart"]==6,"bad config did not change active settings");
        env.active = false; service.environment(env);
        await(service, [](auto& j) { return j["current"] == ""; }, "leaving game stops audio");
        service.command({{"type", "volume"}, {"value", .23f}});
        await(service, [](auto& j) { return j["volume"].template get<float>() < .24f; }, "save volume");
    }
    {
        music::Service service(library, settings);
        auto s = await(service, [](auto& j) { return j["tracks"].size() == 4; }, "restart");
        check(std::abs(s["volume"].get<float>() - .23f) < .001f, "volume persists");
        bool saved = false; for (auto& t : s["tracks"]) if (t["id"] == general) saved = t["disabled"];
        check(saved, "disabled song persists");
        check(s["playback"]["pauseWithGame"]==false && s["playback"]["followMaster"]==false && s["playback"]["fadeSeconds"]==.75,"playback options persist");
    }
    std::cout << "Music service lifecycle, pause, fallback, rescan and persistence passed\n";
}

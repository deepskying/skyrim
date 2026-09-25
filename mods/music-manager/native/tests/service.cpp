#include "music_service.h"
#include "music_files.h"
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
        wave(library / L"野外" / L"新音乐.wav");
        service.command({{"type", "scan"}});
        await(service, [](auto& j) { return j["current"] == "野外/新音乐.wav"; }, "rescan discovers new file");
        service.command({{"type", "pause"}});
        await(service, [](auto& j) { return j["paused"] == true; }, "pause before time transition");
        for (float hour : {23.f, 6.f, 12.f}) {
            env.hour = hour; service.environment(env);
            std::this_thread::sleep_for(std::chrono::milliseconds(150));
            auto current = service.snapshot();
            check(current["scene"] == "explore" && current["current"] == "野外/新音乐.wav" && current["paused"] == true, "time transition preserves shared playlist and pause");
        }
        service.command({{"type", "pause"}});
        env.paused = true; service.environment(env);
        await(service, [](auto& j) { return j["status"] == "已暂停"; }, "real game pause");
        auto options=service.snapshot()["playback"];
        options["pauseWithGame"]=false;options["followMaster"]=false;options["fadeSeconds"]=.75;options["sceneDelay"]=0;
        service.command({{"type","configure"},{"value",options}});
        await(service, [](auto& j) { return j["status"] == "正在播放" && j["playback"]["pauseWithGame"] == false; }, "pause setting applies live");
        auto invalid=options;invalid["fadeSeconds"]=-1;
        service.command({{"type","configure"},{"value",invalid}});
        auto rejected=await(service, [](auto& j) { return j["message"].template get<std::string>().starts_with("操作失败"); }, "bad config reported");
        check(rejected["playback"]["fadeSeconds"]==.75,"bad config did not change active settings");
        env.active = false; service.environment(env);
        await(service, [](auto& j) { return j["current"] == ""; }, "leaving game stops audio");
        service.command({{"type", "volume"}, {"value", .7f}, {"requestId", "drag:1"}});
        service.command({{"type", "volume"}, {"value", 0.f}, {"requestId", "drag:2"}});
        service.command({{"type", "volume"}, {"value", .23f}, {"requestId", "drag:3"}});
        auto volumeState = await(service, [](auto& j) { return j["volumeRequestId"] == "drag:3"; }, "latest volume acknowledged");
        check(std::abs(volumeState["volume"].get<float>() - .23f) < .001f, "latest volume applied");
        check(volumeState["volumeError"] == "", "successful volume save acknowledged");
    }
    {
        music::Service service(library, settings);
        auto s = await(service, [](auto& j) { return j["tracks"].size() == 4; }, "restart");
        check(std::abs(s["volume"].get<float>() - .23f) < .001f, "volume persists");
        bool saved = false; for (auto& t : s["tracks"]) if (t["id"] == general) saved = t["disabled"];
        check(saved, "disabled song persists");
        check(s["playback"]["pauseWithGame"]==false && s["playback"]["followMaster"]==false && s["playback"]["fadeSeconds"]==.75,"playback options persist");
    }
    {
        // A directory at the settings filename makes the save fail deterministically.
        const auto blocked = root / "blocked-settings.json";
        fs::create_directory(blocked);
        music::Service service(library, blocked);
        await(service, [](auto& j) { return j["tracks"].size() == 4; }, "failed-save fixture starts");
        service.command({{"type", "volume"}, {"value", .41f}, {"requestId", "failed-save"}});
        auto s = await(service, [](auto& j) { return j["volumeRequestId"] == "failed-save"; }, "failed save is acknowledged");
        check(!s["volumeError"].get<std::string>().empty(), "save failure exposed to slider");
        check(std::abs(s["volume"].get<float>() - .41f) < .001f, "volume still applies when save fails");
    }
    {
        const auto deletionLibrary = root / "deletion-library";
        wave(deletionLibrary / L"通用" / L"歌曲甲.wav");
        wave(deletionLibrary / L"通用" / L"歌曲乙.wav");
        wave(deletionLibrary / L"墓地" / L"其他环境副本.wav");
        const auto outside = root / "outside.wav"; wave(outside);
        bool escaped = false;
        try { music::checkedLibraryPath(deletionLibrary, outside); }
        catch (const std::exception&) { escaped = true; }
        check(escaped, "outside-library path rejected");
        music::Service service(deletionLibrary, root / "deletion-settings.json");
        music::Environment env; env.active = true;
        service.environment(env);
        await(service, [](auto& j) { return j["current"] != ""; }, "deletion fixture plays");
        service.command({{"type", "pause"}});
        auto s = await(service, [](auto& j) { return j["paused"] == true; }, "pause deletion fixture");
        const auto id = s["current"].get<std::string>();
        const auto source = deletionLibrary / fs::u8path(id);
        const auto other = id == "通用/歌曲甲.wav" ? "通用/歌曲乙.wav" : "通用/歌曲甲.wav";
        service.command({{"type", "deleteCurrent"}, {"id", other}});
        await(service, [](auto& j) { return j["message"].template get<std::string>().find("歌曲已变化") != std::string::npos; }, "stale target refused");
        check(fs::exists(source) && fs::exists(deletionLibrary / fs::u8path(other)), "stale request removes neither song");
        // Another process denies delete sharing; our playback handles must close,
        // but an external lock must still fail without hiding or losing the song.
        HANDLE lock = CreateFileW(source.c_str(), GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
        check(lock != INVALID_HANDLE_VALUE, "lock test song");
        service.command({{"type", "deleteCurrent"}, {"id", id}});
        s = await(service, [](auto& j) { return j["message"].template get<std::string>().find("无法移动音乐文件") != std::string::npos; }, "locked deletion reported");
        check(fs::exists(source) && s["current"] == id && s["tracks"].size() == 3, "failed deletion restores playback and leaves catalog intact");
        CloseHandle(lock);
        service.command({{"type", "deleteCurrent"}, {"id", id}});
        s = await(service, [](auto& j) { return j["lastDeleted"].is_object(); }, "delete paused streaming track");
        const auto ticket = s["lastDeleted"]["ticket"].get<std::string>();
        const auto archived = deletionLibrary / fs::u8path(ticket);
        check(!fs::exists(source) && fs::is_regular_file(archived), "file moved to recoverable directory");
        check(s["current"] == other && s["paused"] == true, "next song selected without clearing pause");
        check(fs::exists(deletionLibrary / L"墓地" / L"其他环境副本.wav"), "other category copy retained");
        service.command({{"type", "scan"}});
        s = await(service, [](auto& j) { return j["message"].template get<std::string>().starts_with("已扫描"); }, "rescan after delete");
        check(s["tracks"].size() == 2, "archive excluded from scanning");
        std::ofstream(source) << "new user file";
        service.command({{"type", "undoDelete"}, {"ticket", ticket}});
        s = await(service, [](auto& j) { return j["message"].template get<std::string>().find("目标文件已存在") != std::string::npos; }, "restore refuses overwrite");
        check(fs::file_size(source) == 13 && fs::exists(archived), "restore preserves conflicting user file and archive");
        fs::rename(source, root / "user-conflict-copy.wav");
        service.command({{"type", "undoDelete"}, {"ticket", ticket}});
        s = await(service, [](auto& j) { return j["lastDeleted"].is_null(); }, "undo deletion");
        check(fs::is_regular_file(source) && !fs::exists(archived) && s["tracks"].size() == 3, "restored file rescanned");
        check(s["current"] == other, "undo does not interrupt current song");
        check(fs::exists(outside), "unrelated file untouched");
        // Test the single remaining track path: no next track means silence.
        env.cemetery = true; env.paused = false; service.environment(env);
        service.command({{"type", "pause"}});
        auto options = s["playback"]; options["sceneDelay"] = 0;
        service.command({{"type", "configure"}, {"value", options}});
        s = await(service, [](auto& j) { return j["scene"] == "cemetery" && j["current"] == "墓地/其他环境副本.wav"; }, "cemetery fixture selected");
        service.command({{"type", "fallback"}, {"value", false}});
        service.command({{"type", "deleteCurrent"}, {"id", "墓地/其他环境副本.wav"}});
        s = await(service, [](auto& j) { return j["current"] == "" && j["lastDeleted"].is_object(); }, "deleting final available song stays silent");
    }
    std::cout << "Music service lifecycle, volume, deletion, undo, fallback and persistence passed\n";
}

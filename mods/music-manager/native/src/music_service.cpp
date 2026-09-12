#include "music_service.h"
#include "music_settings.h"
#include "music_files.h"
#include "miniaudio.h"
#include <Windows.h>
#include <atomic>
#include <chrono>
#include <deque>
#include <fstream>
#include <mutex>
#include <set>
#include <thread>
#include <map>
#include <cctype>
#include <optional>

namespace music {
using json = nlohmann::json;
namespace fs = std::filesystem;
static std::string utf8(const fs::path& p) { auto s = p.generic_u8string(); return {s.begin(), s.end()}; }
static double seconds() { return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count(); }
struct Track { std::string id, name, category, error; fs::path path; };
struct Service::Impl {
    fs::path root, settings;
    std::mutex mutex;
    Environment incoming, env;
    std::deque<json> commands;
    json published;
    std::atomic_bool enabled{true}, ready{false};
    ma_engine engine{};
    struct Sound {
        ma_sound value{};
        bool initialized = false;
        std::string id;
        double disposeAt = 0;
        ~Sound() { if (initialized) ma_sound_uninit(&value); }
    };
    std::unique_ptr<Sound> current, outgoing;
    std::vector<Track> tracks;
    std::set<std::string> disabled;
    std::map<std::string, ShuffleBag> bags;
    SceneGate gate;
    std::string scene = "general", playlist, last, message;
    float volume = .5f;
    std::string volumeRequestId, volumeError;
    std::optional<ArchivedTrack> lastDeleted;
    PlaybackSettings playback;
    bool manualPause = false, paused = false, preview = false, fallback = true;
    unsigned epoch = 0;
    std::jthread worker;

    Impl(fs::path r, fs::path s) : root(std::move(r)), settings(std::move(s)) {
        worker = std::jthread([this](std::stop_token stop) { run(stop); });
    }
    ~Impl() { worker.request_stop(); if (worker.joinable()) worker.join(); }
    void load() {
        try {
            std::ifstream file(settings);
            if (!file) return;
            const auto j = json::parse(file);
            volume = std::clamp(j.value("volume", .5f), 0.f, 1.f);
            enabled = j.value("enabled", true);
            fallback = j.value("fallback", true);
            playback = PlaybackSettings::parse(j.value("playback", json::object()));
            for (const auto& id : j.value("disabled", json::array())) if (id.is_string()) disabled.insert(id.get<std::string>());
        } catch (const std::exception& e) { message = std::string("设置读取失败，使用默认值：") + e.what(); }
    }
    bool save() {
        // Rename a sibling temporary file so an interrupted save cannot truncate settings.
        try {
            fs::create_directories(settings.parent_path());
            auto temporary = settings; temporary += L".tmp";
            {
                std::ofstream file(temporary, std::ios::binary | std::ios::trunc);
                file << json{{"volume", volume}, {"enabled", enabled.load()}, {"fallback", fallback}, {"disabled", disabled}, {"playback", playback.json()}}.dump(2);
                file.flush();
                if (!file) throw std::runtime_error("无法写入设置");
            }
            if (!MoveFileExW(temporary.c_str(), settings.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH)) throw std::runtime_error("无法保存设置");
            return true;
        } catch (const std::exception& e) { message = std::string("保存失败：") + e.what(); return false; }
    }
    void scan() {
        std::vector<Track> found;
        std::size_t failed = 0;
        for (const auto& c : categories) {
            const auto directory = root / fs::u8path(c.folder);
            std::error_code ec;
            fs::create_directories(directory, ec);
            fs::recursive_directory_iterator it(directory, fs::directory_options::skip_permission_denied, ec), end;
            for (; it != end; it.increment(ec)) {
                if (ec) { ++failed; ec.clear(); continue; }
                if (it->is_symlink(ec)) { it.disable_recursion_pending(); continue; }
                if (!it->is_regular_file(ec)) continue;
                auto ext = utf8(it->path().extension());
                std::transform(ext.begin(), ext.end(), ext.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
                if (ext != ".mp3" && ext != ".wav" && ext != ".flac") continue;
                found.push_back({utf8(it->path().lexically_relative(root)), utf8(it->path().stem()), c.id, {}, it->path()});
            }
        }
        std::sort(found.begin(), found.end(), [](const auto& a, const auto& b) { return a.id < b.id; });
        tracks = std::move(found);
        bags.clear();
        if (current && !find(current->id)) stopSound(0);
        message = "已扫描 " + std::to_string(tracks.size()) + " 首歌曲";
        if (failed) message += "，部分目录无法读取";
    }
    Track* find(const std::string& id) {
        auto it = std::find_if(tracks.begin(), tracks.end(), [&](auto& t) { return t.id == id; });
        return it == tracks.end() ? nullptr : &*it;
    }
    std::vector<std::string> available(const std::string& category) {
        std::vector<std::string> ids;
        for (auto& t : tracks) if (t.category == category && !disabled.contains(t.id) && t.error.empty()) ids.push_back(t.id);
        return ids;
    }
    std::string resolve() {
        if (!available(scene).empty()) return scene;
        return fallback && !available("general").empty() ? "general" : "";
    }
    void stopSound(unsigned fade) {
        outgoing.reset();
        if (!current) return;
        if (fade && !paused) {
            outgoing = std::move(current);
            ma_sound_set_fade_in_milliseconds(&outgoing->value, -1, 0, fade);
            outgoing->disposeAt = seconds() + static_cast<double>(fade) / 1000.;
        } else current.reset();
    }
    bool play(Track& track, unsigned fade) {
        auto sound = std::make_unique<Sound>();
        // Wide file API preserves Chinese names; streaming keeps large libraries out of RAM.
        const auto result = ma_sound_init_from_file_w(&engine, track.path.c_str(), MA_SOUND_FLAG_STREAM | MA_SOUND_FLAG_NO_SPATIALIZATION, nullptr, nullptr, &sound->value);
        if (result != MA_SUCCESS) {
            track.error = std::string("无法解码：") + ma_result_description(result);
            message = track.name + "：" + track.error;
            return false;
        }
        sound->initialized = true;
        sound->id = track.id;
        stopSound(fade);
        current = std::move(sound);
        last = track.id;
        if (fade) ma_sound_set_fade_in_milliseconds(&current->value, 0, 1, fade);
        if (!paused) ma_sound_start(&current->value);
        return true;
    }
    void next() { next(static_cast<unsigned>(playback.fadeSeconds * 1000)); }
    void next(unsigned fade) {
        preview = false;
        // Each failure is marked and removed from this scan's candidate list.
        for (std::size_t attempt = 0; attempt <= tracks.size(); ++attempt) {
            playlist = resolve();
            if (playlist.empty()) { stopSound(fade); return; }
            const auto id = bags[playlist].next(available(playlist), last);
            if (auto* t = find(id); t && play(*t, fade)) return;
        }
        stopSound(0);
    }
    void deleteCurrent(const std::string& id) {
        if (!current || current->id != id) throw std::runtime_error("正在播放的歌曲已变化，请重新选择要删除的歌曲");
        const auto* found = find(id);
        if (!found) throw std::runtime_error("歌曲已不在音乐库中");
        const Track track = *found;
        auto archived = prepareArchive(root, track.path);
        archived.name = track.name;
        const bool wasPreview = preview;
        ma_uint64 cursor = 0;
        ma_sound_get_cursor_in_pcm_frames(&current->value, &cursor);
        // Release streaming decoder handles before attempting a Windows rename.
        stopSound(0);
        try { moveLibraryFile(root, archived.original, archived.archived); }
        catch (...) {
            if (auto* original = find(id); original && play(*original, 0)) {
                ma_sound_seek_to_pcm_frame(&current->value, cursor);
                preview = wasPreview;
            }
            throw;
        }
        lastDeleted = std::move(archived);
        std::erase_if(tracks, [&](const Track& item) { return item.id == id; });
        bags.clear(); preview = false;
        if (env.active && enabled && !env.story) next();
        else playlist.clear();
        message = "已移至 _已删除：" + track.name + "；可撤销删除";
    }
    void undoDelete(const std::string& ticket) {
        if (!lastDeleted || lastDeleted->ticket != ticket) throw std::runtime_error("可撤销的歌曲已变化，请重试");
        checkedLibraryPath(root, lastDeleted->original);
        fs::create_directories(lastDeleted->original.parent_path());
        moveLibraryFile(root, lastDeleted->archived, lastDeleted->original);
        const auto name = lastDeleted->name;
        lastDeleted.reset();
        scan();
        message = "已恢复音乐文件：" + name;
    }
    void handle(const json& j) {
        const auto type = j.value("type", "");
        if (type == "scan") scan();
        else if (type == "configure") {
            const auto previous = playback;
            playback = PlaybackSettings::parse(j.at("value"));
            if (save()) { gate.clear(); message = "播放设置已保存并生效"; }
            else playback = previous;
        }
        else if (type == "deleteCurrent") deleteCurrent(j.value("id", ""));
        else if (type == "undoDelete") undoDelete(j.value("ticket", ""));
        else if (type == "next") { manualPause = false; next(); }
        else if (type == "pause") manualPause = !manualPause;
        else if (type == "volume") {
            const auto value = j.at("value").get<float>();
            if (!std::isfinite(value)) throw std::runtime_error("音量数值无效");
            volume = std::clamp(value, 0.f, 1.f);
            volumeError = save() ? "" : "音量已生效，但保存失败，重启后可能恢复旧值。";
            volumeRequestId = j.value("requestId", std::string{});
        }
        else if (type == "enabled") { enabled = j.at("value").get<bool>(); save(); }
        else if (type == "fallback") { fallback = j.at("value").get<bool>(); save(); }
        else if (type == "disable") {
            const auto id = j.value("id", "");
            if (!find(id)) return;
            if (disabled.contains(id)) disabled.erase(id); else disabled.insert(id);
            bags.clear(); save();
            if (current && disabled.contains(current->id)) next();
        } else if (type == "preview") {
            if (!env.active || (env.paused && playback.pauseWithGame) || env.story || !enabled) { message = "请在游戏恢复运行后试听"; return; }
            if (auto* t = find(j.value("id", ""))) {
                manualPause = false; paused = false;
                if (play(*t, 500)) { preview = true; message = "试听结束后恢复环境播放"; }
            }
        } else if (type == "auto") { preview = false; next(); }
    }
    void publish() {
        json list = json::array(), cats = json::array();
        for (const auto& t : tracks) list.push_back({{"id", t.id}, {"name", t.name}, {"category", t.category}, {"disabled", disabled.contains(t.id)}, {"error", t.error}});
        for (const auto& c : categories) cats.push_back({{"id", c.id}, {"label", c.folder}, {"count", available(c.id).size()}});
        float cursor = 0, length = 0;
        if (current) { ma_sound_get_cursor_in_seconds(&current->value, &cursor); ma_sound_get_length_in_seconds(&current->value, &length); }
        std::string status = !ready ? "音频设备不可用" : !enabled ? "已关闭接管" : !env.active ? "等待进入游戏" : env.story ? "剧情音乐优先" : paused ? "已暂停" : !current ? "当前分类与通用均无可用音乐" : preview ? "正在试听" : "正在播放";
        json state{{"version", "0.4.0"}, {"categories", cats}, {"tracks", list}, {"scene", scene}, {"playlist", playlist}, {"current", current ? current->id : ""}, {"position", cursor}, {"duration", length}, {"volume", volume}, {"enabled", enabled.load()}, {"fallback", fallback}, {"paused", manualPause}, {"preview", preview}, {"status", status}, {"location", env.location}, {"nativeMusic", env.nativeMusic}, {"root", utf8(root)}, {"message", message}};
        state["playback"] = playback.json();
        state["volumeRequestId"] = volumeRequestId;
        state["volumeError"] = volumeError;
        state["lastDeleted"] = lastDeleted ? json{{"name", lastDeleted->name}, {"ticket", lastDeleted->ticket}} : json(nullptr);
        std::lock_guard lock(mutex); published = std::move(state);
    }
    void run(std::stop_token stop) {
        bool initialized = false;
        try {
            load(); scan();
            auto config = ma_engine_config_init(); config.channels = 2;
#ifdef MUSIC_SERVICE_TEST
            config.noDevice = MA_TRUE; config.sampleRate = 48000;
#endif
            const auto result = ma_engine_init(&config, &engine);
            if (result != MA_SUCCESS) { message = std::string("音频初始化失败：") + ma_result_description(result); publish(); return; }
            initialized = true; ready = true;
            double lastPublish = 0;
            while (!stop.stop_requested()) {
                std::deque<json> pending;
                { std::lock_guard lock(mutex); env = incoming; pending.swap(commands); }
                if (env.epoch != epoch) {
                    epoch = env.epoch; current.reset(); outgoing.reset(); gate.clear(); bags.clear(); preview = false; manualPause = false;
                }
                for (const auto& cmd : pending) {
                    try { handle(cmd); } catch (const std::exception& e) { message = std::string("操作失败：") + e.what(); }
                }
                const bool shouldPause = (env.paused && playback.pauseWithGame) || manualPause;
                if (paused != shouldPause) {
                    paused = shouldPause;
                    if (current) { if (paused) ma_sound_stop(&current->value); else ma_sound_start(&current->value); }
                    // Don't let a half-finished transition resume over the main track.
                    outgoing.reset();
                }
                ma_engine_set_volume(&engine, volume * (playback.followMaster ? std::clamp(env.masterVolume, 0.f, 1.f) : 1.f));
                if (!env.active || !enabled || env.story) {
                    current.reset(); outgoing.reset(); preview = false; playlist.clear(); gate.clear();
                } else if (!paused) {
                    const auto newScene = gate.update(classify(env, playback.dayStart, playback.dayEnd), seconds(), playback.sceneDelay, playback.combatExitDelay);
                    const bool change = scene != newScene;
                    scene = newScene;
                    if (change) preview = false;
                    if (change || (!preview && playlist != resolve()) || (!current && !resolve().empty()) || (current && ma_sound_at_end(&current->value)))
                        next(static_cast<unsigned>((scene == "combat" || scene == "dragon" ? playback.combatFadeSeconds : playback.fadeSeconds) * 1000));
                }
                if (outgoing && seconds() >= outgoing->disposeAt) outgoing.reset();
#ifdef MUSIC_SERVICE_TEST
                float frames[4800]; ma_engine_read_pcm_frames(&engine, frames, 2400, nullptr);
#endif
                if (seconds() - lastPublish > .4) { publish(); lastPublish = seconds(); }
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
            }
        } catch (const std::exception& e) { message = std::string("音乐服务停止：") + e.what(); ready = false; publish(); }
        ready = false; current.reset(); outgoing.reset();
        if (initialized) ma_engine_uninit(&engine);
    }
};
Service::Service(fs::path r, fs::path s) : impl_(std::make_unique<Impl>(std::move(r), std::move(s))) {}
Service::~Service() = default;
void Service::environment(Environment e) { std::lock_guard lock(impl_->mutex); impl_->incoming = std::move(e); }
void Service::command(json j) { std::lock_guard lock(impl_->mutex); if (impl_->commands.size() < 100) impl_->commands.push_back(std::move(j)); }
json Service::snapshot() { std::lock_guard lock(impl_->mutex); return impl_->published; }
bool Service::enabled() const { return impl_->enabled; }
bool Service::ready() const { return impl_->ready; }
}

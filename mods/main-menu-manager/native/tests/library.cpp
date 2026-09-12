#include "library.h"
#include <Windows.h>
#include <nlohmann/json.hpp>
#include <fstream>
#include <iostream>
#include <cstring>
#include <set>
#include <stdexcept>

using namespace mainmenu;
using json = nlohmann::json;
namespace {
const fs::path logo = "meshes/interface/logo/logo.nif";
const fs::path wallpaper = "textures/interface/objects/mainmenuwallpaper.dds";
const fs::path music = "music/special/mus_maintheme.xwm";
int checks = 0;
void check(bool ok, const std::string& text) {
    ++checks;
    if (!ok) throw std::runtime_error(text);
}
template<class F> void fails(F operation, const std::string& text) {
    try { operation(); } catch (const std::exception&) { ++checks; return; }
    throw std::runtime_error(text);
}
void write(const fs::path& path, const std::string& bytes) {
    fs::create_directories(path.parent_path());
    std::ofstream file(path, std::ios::binary); file << bytes;
    if (!file) throw std::runtime_error("Fixture write failed");
}
std::string read(const fs::path& path) {
    std::ifstream file(path, std::ios::binary);
    return {std::istreambuf_iterator<char>(file), std::istreambuf_iterator<char>()};
}
std::string texture(char marker) {
    std::string bytes(132, marker);
    bytes.replace(0, 4, "DDS ");
    const std::uint32_t headerSize = 124, dimension = 1;
    std::memcpy(bytes.data() + 4, &headerSize, 4);
    std::memcpy(bytes.data() + 12, &dimension, 4);
    std::memcpy(bytes.data() + 16, &dimension, 4);
    return bytes;
}
void theme(const fs::path& root, char marker, bool audio = false) {
    write(root / "Data" / logo, "Gamebryo File Format, Version 20.2.0.7\n" + std::string(100, marker));
    write(root / "Data" / wallpaper, texture(marker));
    if (audio) write(root / "Data" / music, "RIFF0000XWMA" + std::string(150, marker));
}
struct Fixture {
    fs::path parent = fs::absolute("build/test-runs").lexically_normal();
    fs::path root;
    fs::path data;
    fs::path library;
    std::vector<std::string> messages;
    Fixture(const std::string& name) {
        root = parent / ("mmm-" + std::to_string(GetCurrentProcessId()) + "-" + name);
        check(!fs::exists(root), "Test directory must be new");
        data = root / "Data";
        library = data / "MainMenuManager/backgrounds";
        fs::create_directories(library);
    }
    ~Fixture() {
        // Only delete this fixture's checked absolute directory inside build.
        if (root.is_absolute() && root.parent_path() == parent && root.filename().string().starts_with("mmm-")) {
            std::error_code ignored; fs::remove_all(root, ignored);
        }
    }
    Log log() { return [this](const std::string& value) { messages.push_back(value); }; }
    Manager manager() { return Manager(data, log()); }
};
void catalog() {
    Fixture f("catalog");
    theme(f.library / fs::u8path("雪山晨曦"), 'A', true);
    write(f.library / fs::u8path("雪山晨曦") / "theme.json", R"({"name":"雪山"})");
    theme(f.library / "disabled", 'D');
    write(f.library / "disabled/disabled.txt", "");
    theme(f.library / "off", 'O'); write(f.library / "off/theme.json", R"({"enabled":false})");
    theme(f.library / "_example", 'E');
    theme(f.library / "nested/V1", 'N');
    theme(f.library / "broken", 'B'); write(f.library / "broken/Data" / wallpaper, "broken dds");
    theme(f.library / "bad-json", 'J'); write(f.library / "bad-json/theme.json", "{");
    write(f.library / fs::u8path("雪山晨曦") / "Data/SKSE/Plugins/evil.dll", "ignored");
    const auto themes = scan(f.library, f.log());
    check(themes.size() == 1, "Only complete enabled themes should be candidates");
    check(themes[0].name == "雪山" && themes[0].files.size() == 3, "Unicode name and XWMA resource should survive scan");
    check(!allowedResource("../outside.dds") && !allowedResource("C:/outside.dds"), "Reject escaped destinations");
    check(!allowedResource("textures/../outside.dds") && !allowedResource("textures/a.dds:stream"), "Reject traversal and ADS");
    check(!allowedResource("meshes/actors/actor.nif") && !allowedResource("plugin.esp"), "Reject unrelated executable/gameplay resources");
}
void switching() {
    Fixture f("switching");
    theme(f.library / "A", 'A', true); theme(f.library / "B", 'B');
    write(f.data / logo, "original logo"); write(f.data / music, "original music");
    write(f.data / "textures/unrelated.dds", "keep");
    auto manager = f.manager(); const auto themes = scan(f.library, f.log());
    manager.apply(themes[0]);
    check(read(f.data / wallpaper) == texture('A'), "Install selected wallpaper");
    check(read(f.data / music).starts_with("RIFF"), "Install theme music");
    fails([&] { manager.apply(themes[1]); }, "Cannot overwrite a pending recovery journal");
    manager.restore(); manager.apply(themes[1]);
    check(read(f.data / wallpaper) == texture('B'), "Switch to B");
    check(read(f.data / music) == "original music", "A's music must not leak into B");
    manager.restore(); manager.restore();
    check(read(f.data / logo) == "original logo", "Restore original loose file");
    check(!fs::exists(f.data / wallpaper), "Remove only generated loose override, exposing BSA fallback");
    check(read(f.data / "textures/unrelated.dds") == "keep", "Preserve unrelated resources");
    check(!fs::exists(f.data / "MainMenuManager/state/0.staged"), "Retire backups after restoration");
}
void externalChanges() {
    Fixture f("external"); theme(f.library / "A", 'A');
    write(f.data / logo, "original"); auto manager = f.manager();
    manager.apply(scan(f.library, f.log())[0]);
    write(f.data / wallpaper, "user edit");
    fails([&] { manager.restore(); }, "External edit must block automatic restoration");
    check(read(f.data / wallpaper) == "user edit", "User edit was preserved");
    check(read(f.data / logo).starts_with("Gamebryo"), "Preflight failure must not partially restore");
    check(!json::parse(read(f.data / "MainMenuManager/state/journal.json"))["entries"].empty(), "Keep recovery record");
    write(f.data / wallpaper, texture('A')); manager.restore();
    check(read(f.data / logo) == "original", "Recovery succeeds after resolving the conflict");
}
void interruptedAndFailedApply() {
    Fixture f("interrupted"); theme(f.library / "A", 'A', true);
    write(f.data / logo, "original"); auto manager = f.manager();
    const auto candidate = scan(f.library, f.log())[0]; manager.apply(candidate);
    // Simulate process death midway through apply: some targets are still
    // original or absent, while others contain the journaled replacement.
    write(f.data / logo, "original"); fs::remove(f.data / wallpaper);
    f.manager().restore();
    check(read(f.data / logo) == "original" && !fs::exists(f.data / music), "Recover a partially applied theme");
    auto blocked = f.data / wallpaper; blocked += ".mmm-tmp"; write(blocked, "unrelated temp file");
    fails([&] { manager.apply(candidate); }, "A blocked destination must fail the transaction");
    check(read(f.data / logo) == "original" && !fs::exists(f.data / music), "Roll back earlier copies on failure");
    check(read(blocked) == "unrelated temp file", "Never delete someone else's temporary file");
}
void emptyDisabledRandomAndConflict() {
    Fixture f("startup"); auto manager = f.manager(); std::mt19937_64 random(12345);
    check(manager.start(true, random).empty(), "Empty library leaves original menu alone");
    check(!fs::exists(f.data / "MainMenuManager/state/journal.json"), "Empty first run needs no state");
    theme(f.library / "A", 'A'); theme(f.library / "B", 'B'); theme(f.library / "C", 'C');
    std::set<std::string> selected;
    for (int i = 0; i < 24; ++i) selected.insert(manager.start(true, random));
    check(selected == std::set<std::string>{"A", "B", "C"}, "All enabled themes are reachable by random selection");
    manager.start(false, random);
    check(!fs::exists(f.data / wallpaper) && !fs::exists(f.data / logo), "Disable restores original menu");
    write(f.data / "SKSE/Plugins/main_menu_randomizer.dll", "old randomizer");
    check(manager.start(true, random).empty() && !fs::exists(f.data / wallpaper), "Do not compete with existing randomizer");
}
void invalidJournalAndBackups() {
    Fixture f("journal"); theme(f.library / "A", 'A'); write(f.data / logo, "original");
    auto manager = f.manager(); manager.apply(scan(f.library, f.log())[0]);
    auto state = f.data / "MainMenuManager/state";
    const auto originalJournal = read(state / "journal.json");
    auto journal = json::parse(originalJournal); journal["entries"][0]["path"] = "../outside.dds";
    write(state / "journal.json", journal.dump());
    fails([&] { manager.restore(); }, "Reject a tampered journal path before writes");
    write(state / "journal.json", originalJournal);
    write(state / "0.original", "corrupt");
    fails([&] { manager.restore(); }, "Damaged backup must not replace a live file");
    check(read(f.data / wallpaper) == texture('A'), "Backup validation is all-or-nothing");
}
}
int main() {
    try {
        catalog(); switching(); externalChanges(); interruptedAndFailedApply(); emptyDisabledRandomAndConflict(); invalidJournalAndBackups();
        std::cout << "PASS: " << checks << " checks; catalog, selection, restoration, crash recovery, conflicts and rollback\n";
        return 0;
    } catch (const std::exception& error) { std::cerr << "FAIL: " << error.what() << '\n'; return 1; }
}

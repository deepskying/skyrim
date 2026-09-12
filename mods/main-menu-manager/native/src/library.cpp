#include "library.h"

#include <Windows.h>
#include <bcrypt.h>
#include <nlohmann/json.hpp>
#include <algorithm>
#include <array>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>

namespace mainmenu {
namespace {
using json = nlohmann::json;

std::string utf8(const fs::path& path) {
    const auto text = path.generic_u8string();
    return {reinterpret_cast<const char*>(text.data()), text.size()};
}
std::string lower(std::string text) {
    for (auto& c : text) if (c >= 'A' && c <= 'Z') c += 'a' - 'A';
    return text;
}
void require(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error(message);
}

// Check every existing ancestor, including Windows junctions. Do not resolve
// through MO2 to a physical mod path: resource I/O must remain inside its VFS.
void noLinks(const fs::path& path) {
    fs::path current;
    for (const auto& part : fs::absolute(path).lexically_normal()) {
        current /= part;
        const auto attrs = GetFileAttributesW(current.c_str());
        if (attrs != INVALID_FILE_ATTRIBUTES)
            require(!(attrs & FILE_ATTRIBUTE_REPARSE_POINT), "Linked path is not supported: " + utf8(current));
    }
}

std::string hashFile(const fs::path& path) {
    noLinks(path);
    BCRYPT_ALG_HANDLE algorithm{};
    BCRYPT_HASH_HANDLE hash{};
    require(BCryptOpenAlgorithmProvider(&algorithm, BCRYPT_SHA256_ALGORITHM, nullptr, 0) >= 0, "SHA256 unavailable");
    struct Cleanup {
        BCRYPT_ALG_HANDLE& algorithm;
        BCRYPT_HASH_HANDLE& hash;
        ~Cleanup() { if (hash) BCryptDestroyHash(hash); if (algorithm) BCryptCloseAlgorithmProvider(algorithm, 0); }
    } cleanup{algorithm, hash};
    require(BCryptCreateHash(algorithm, &hash, nullptr, 0, nullptr, 0, 0) >= 0, "Cannot create SHA256");
    std::ifstream input(path, std::ios::binary);
    require(bool(input), "Cannot read " + utf8(path));
    std::array<char, 65536> buffer{};
    while (input) {
        input.read(buffer.data(), buffer.size());
        if (const auto count = input.gcount(); count > 0)
            require(BCryptHashData(hash, reinterpret_cast<PUCHAR>(buffer.data()), static_cast<ULONG>(count), 0) >= 0, "SHA256 failed");
    }
    require(input.eof(), "Read failed: " + utf8(path));
    std::array<unsigned char, 32> digest{};
    require(BCryptFinishHash(hash, digest.data(), static_cast<ULONG>(digest.size()), 0) >= 0, "SHA256 failed");
    std::ostringstream result;
    for (const auto byte : digest) result << std::hex << std::setw(2) << std::setfill('0') << unsigned(byte);
    return result.str();
}

void moveReplace(const fs::path& from, const fs::path& to) {
    const auto handle = CreateFileW(from.c_str(), GENERIC_WRITE, FILE_SHARE_READ, nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, nullptr);
    require(handle != INVALID_HANDLE_VALUE, "Cannot flush " + utf8(from));
    const bool flushed = FlushFileBuffers(handle) != 0;
    CloseHandle(handle);
    require(flushed, "Cannot flush " + utf8(from));
    require(MoveFileExW(from.c_str(), to.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH) != 0,
        "Cannot replace " + utf8(to) + "; Windows error " + std::to_string(GetLastError()));
}
void copyAtomic(const fs::path& source, const fs::path& destination) {
    noLinks(source); noLinks(destination);
    fs::create_directories(destination.parent_path());
    auto temporary = destination;
    temporary += L".mmm-tmp";
    noLinks(temporary);
    // Never truncate an unrelated file at the temporary path.
    require(!fs::exists(temporary), "Temporary file needs inspection: " + utf8(temporary));
    try {
        fs::copy_file(source, temporary);
        moveReplace(temporary, destination);
    } catch (...) {
        std::error_code ignored; fs::remove(temporary, ignored);
        throw;
    }
}
void writeJournal(const fs::path& state, const json& value) {
    noLinks(state);
    fs::create_directories(state);
    const auto temporary = state / "journal.next.json";
    noLinks(temporary);
    std::ofstream output(temporary, std::ios::binary | std::ios::trunc);
    output << value.dump(2);
    output.close();
    require(bool(output), "Cannot write background recovery journal");
    moveReplace(temporary, state / "journal.json");
}
json readJournal(const fs::path& state) {
    const auto path = state / "journal.json";
    noLinks(path);
    if (!fs::exists(path)) return { {"version", 1}, {"entries", json::array()} };
    require(fs::file_size(path) < 4 * 1024 * 1024, "Recovery journal is too large");
    std::ifstream input(path, std::ios::binary);
    auto result = json::parse(input);
    require(result.at("version") == 1 && result.at("entries").is_array(), "Unsupported recovery journal");
    return result;
}
bool validHeader(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    std::array<char, 128> header{};
    input.read(header.data(), header.size());
    const auto size = input.gcount();
    const auto extension = lower(utf8(path.extension()));
    if (extension == ".dds") {
        std::uint32_t headerSize{}, height{}, width{};
        std::memcpy(&headerSize, header.data() + 4, 4);
        std::memcpy(&height, header.data() + 12, 4);
        std::memcpy(&width, header.data() + 16, 4);
        return size == 128 && std::string_view(header.data(), 4) == "DDS " && headerSize == 124 &&
            width > 0 && height > 0 && width <= 16384 && height <= 16384 && fs::file_size(path) > 128;
    }
    if (extension == ".nif") return size >= 40 && std::string_view(header.data(), 39) == "Gamebryo File Format, Version 20.2.0.7\n";
    if (extension == ".xwm" || extension == ".wav")
        return size >= 12 && std::string_view(header.data(), 4) == "RIFF" &&
            (std::string_view(header.data() + 8, 4) == "WAVE" || (extension == ".xwm" && std::string_view(header.data() + 8, 4) == "XWMA"));
    return false;
}
}

bool allowedResource(const fs::path& relative) {
    if (relative.empty() || relative.is_absolute() || relative.has_root_path()) return false;
    const auto name = lower(utf8(relative));
    if (name.find('\\') != std::string::npos || name.find(':') != std::string::npos) return false;
    for (const auto& part : relative)
        if (part == ".." || part == "." || utf8(part).ends_with('.') || utf8(part).ends_with(' ')) return false;
    if (name == "meshes/interface/logo/logo.nif" || name == "meshes/interface/logo/logo01ae.nif" ||
        name == "meshes/interface/intmenufogparticles.nif") return true;
    // Custom meshes can reference textures outside Interface. No forms, scripts,
    // DLLs, installers or unrelated mesh trees are ever copied from a theme.
    if (name.starts_with("textures/") && name.ends_with(".dds")) return true;
    return name == "music/special/mus_maintheme.xwm" || name == "music/special/mus_maintheme.wav";
}

std::vector<Theme> scan(const fs::path& library, const Log& log) {
    std::vector<Theme> themes;
    noLinks(library);
    if (!fs::exists(library)) return themes;
    for (const auto& entry : fs::directory_iterator(library)) {
        const auto name = utf8(entry.path().filename());
        if (name.empty() || name.front() == '.' || name.front() == '_') continue;
        try {
            noLinks(entry.path());
            if (!entry.is_directory() || fs::exists(entry.path() / "disabled.txt")) continue;
            Theme theme{entry.path(), name, {}};
            const auto metadata = entry.path() / "theme.json";
            noLinks(metadata);
            if (fs::exists(metadata)) {
                require(fs::file_size(metadata) <= 65536, "theme.json too large");
                std::ifstream input(metadata, std::ios::binary);
                const auto settings = json::parse(input);
                if (!settings.value("enabled", true)) continue;
                theme.name = settings.value("name", name);
            }
            const auto data = entry.path() / "Data";
            noLinks(data);
            require(fs::is_directory(data), "missing direct Data folder (unpack variants first)");
            bool hasLogo = false, hasTexture = false;
            std::set<std::string> paths;
            std::uintmax_t total = 0;
            std::size_t ignored = 0;
            for (const auto& file : fs::recursive_directory_iterator(data)) {
                noLinks(file.path());
                if (!file.is_regular_file()) continue;
                const auto relative = file.path().lexically_relative(data);
                if (!allowedResource(relative)) { ++ignored; continue; }
                require(validHeader(file.path()), "invalid resource header: " + utf8(relative));
                total += file.file_size();
                require(total <= 1024ULL * 1024 * 1024 && theme.files.size() < 2048, "theme exceeds 1 GiB / 2048 files");
                const auto key = lower(utf8(relative));
                require(paths.insert(key).second, "duplicate destination: " + key);
                hasLogo |= key == "meshes/interface/logo/logo.nif";
                hasTexture |= key.starts_with("textures/");
                theme.files.push_back(relative);
            }
            require(hasLogo && hasTexture, "requires logo.nif and at least one DDS texture");
            require(!(paths.contains("music/special/mus_maintheme.wav") && paths.contains("music/special/mus_maintheme.xwm")),
                "theme contains two competing main-menu music files");
            std::sort(theme.files.begin(), theme.files.end());
            if (ignored) log("Theme " + name + ": ignored " + std::to_string(ignored) + " unsupported files");
            themes.push_back(std::move(theme));
        } catch (const std::exception& error) {
            log("Skipped theme " + name + ": " + error.what());
        }
    }
    std::sort(themes.begin(), themes.end(), [](const Theme& a, const Theme& b) { return a.root < b.root; });
    return themes;
}

Manager::Manager(fs::path data, Log log) :
    data_(fs::absolute(std::move(data)).lexically_normal()), state_(data_ / "MainMenuManager/state"), log_(std::move(log)) {
    noLinks(data_);
}

void Manager::restore() {
    auto journal = readJournal(state_);
    const auto& entries = journal.at("entries");
    require(entries.size() <= 2048, "Recovery journal has too many entries");
    std::set<std::string> destinations;
    // Complete preflight before any mutation. Changes made by another mod or by
    // the user are preserved; retain the journal and backups for manual recovery.
    for (std::size_t i = 0; i < entries.size(); ++i) {
        const auto& entry = entries[i];
        const auto relative = fs::u8path(entry.at("path").get<std::string>());
        require(allowedResource(relative) && destinations.insert(lower(utf8(relative))).second, "Unsafe recovery resource path");
        const auto destination = data_ / relative;
        noLinks(destination);
        const bool existed = entry.at("existed").get<bool>();
        const auto installed = entry.at("installed").get<std::string>();
        if (existed) {
            const auto original = state_ / (std::to_string(i) + ".original");
            require(hashFile(original) == entry.at("original").get<std::string>(), "Original backup is damaged: " + utf8(relative));
        }
        if (!fs::exists(destination)) {
            require(!existed, "Previously existing resource was removed externally: " + utf8(relative));
            continue;
        }
        const auto current = hashFile(destination);
        const bool alreadyOriginal = existed && current == entry.at("original").get<std::string>();
        require(current == installed || alreadyOriginal,
            "Resource changed externally; preserved it and stopped. Inspect state/journal.json: " + utf8(relative));
    }
    for (std::size_t i = 0; i < entries.size(); ++i) {
        const auto& entry = entries[i];
        const auto destination = data_ / fs::u8path(entry.at("path").get<std::string>());
        if (entry.at("existed").get<bool>()) {
            if (hashFile(destination) != entry.at("original").get<std::string>())
                copyAtomic(state_ / (std::to_string(i) + ".original"), destination);
        } else if (fs::exists(destination)) {
            fs::remove(destination); // Only this journal-owned, hash-verified file.
        }
    }
    if (!entries.empty()) {
        writeJournal(state_, {{"version", 1}, {"entries", json::array()}});
        for (std::size_t i = 0; i < entries.size(); ++i) {
            for (const auto suffix : {".staged", ".original"}) {
                const auto file = state_ / (std::to_string(i) + suffix);
                noLinks(file);
                std::error_code error; fs::remove(file, error);
                if (error) log_("Could not remove retired backup: " + utf8(file));
            }
        }
        log_("Restored " + std::to_string(entries.size()) + " previous resources");
    }
}

void Manager::apply(const Theme& theme) {
    // apply is also used by the test harness; never trust callers with raw paths.
    require(readJournal(state_).at("entries").empty(), "Restore the previous theme before applying another");
    require(!theme.files.empty() && theme.files.size() <= 2048, "Empty or oversized theme");
    noLinks(state_);
    fs::create_directories(state_);
    json entries = json::array();
    std::set<std::string> destinations;
    for (std::size_t i = 0; i < theme.files.size(); ++i) {
        const auto& relative = theme.files[i];
        require(allowedResource(relative) && destinations.insert(lower(utf8(relative))).second, "Unsafe theme resource path");
        const auto source = theme.root / "Data" / relative;
        const auto destination = data_ / relative;
        noLinks(source); noLinks(destination);
        require(validHeader(source), "Resource changed since scanning: " + utf8(source));
        const auto staged = state_ / (std::to_string(i) + ".staged");
        copyAtomic(source, staged);
        const bool existed = fs::exists(destination);
        std::string original;
        if (existed) {
            const auto backup = state_ / (std::to_string(i) + ".original");
            copyAtomic(destination, backup);
            original = hashFile(backup);
        }
        entries.push_back({{"path", utf8(relative)}, {"existed", existed}, {"original", original}, {"installed", hashFile(staged)}});
    }
    // The original files and every replacement are durable before the journal
    // becomes visible. Each target is then changed atomically, never truncated.
    writeJournal(state_, {{"version", 1}, {"theme", utf8(theme.root.filename())}, {"entries", entries}});
    try {
        for (std::size_t i = 0; i < theme.files.size(); ++i)
            copyAtomic(state_ / (std::to_string(i) + ".staged"), data_ / theme.files[i]);
    } catch (...) {
        const auto failure = std::current_exception();
        try { restore(); } catch (const std::exception& error) { log_("Recovery retained for next start: " + std::string(error.what())); }
        std::rethrow_exception(failure);
    }
    log_("Selected: " + theme.name + " [" + utf8(theme.root.filename()) + "]; resources: " + std::to_string(theme.files.size()));
}

std::string Manager::start(bool enabled, std::mt19937_64& random) {
    if (enabled && (fs::exists(data_ / "SKSE/Plugins/main_menu_randomizer.dll") ||
        fs::exists(data_ / "SKSE/Plugins/MainMenuRandomizer.dll"))) {
        log_("Main Menu Randomizer is also enabled. No resources changed; disable its DLL before using MainMenuManager.");
        return {};
    }
    restore();
    if (!enabled) { log_("Disabled; previous resources restored"); return {}; }
    auto themes = scan(data_ / "MainMenuManager/backgrounds", log_);
    log_("Available themes: " + std::to_string(themes.size()));
    if (themes.empty()) { log_("No usable themes; keeping the original main menu"); return {}; }
    // Independent uniform draw per process; consecutive repeats are intentional.
    std::uniform_int_distribution<std::size_t> choose(0, themes.size() - 1);
    const auto& selected = themes[choose(random)];
    apply(selected);
    return utf8(selected.root.filename());
}
}

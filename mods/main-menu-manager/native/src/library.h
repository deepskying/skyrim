#pragma once

#include <filesystem>
#include <functional>
#include <random>
#include <string>
#include <vector>

namespace mainmenu {
namespace fs = std::filesystem;
using Log = std::function<void(const std::string&)>;

struct Theme {
    fs::path root;
    std::string name;
    std::vector<fs::path> files; // Relative to this theme's Data, preserving case.
};

// Single-level library. Folder names are UTF-8 in logs/metadata.
std::vector<Theme> scan(const fs::path& library, const Log& log);
bool allowedResource(const fs::path& relative);

// This manager writes only approved resources under data. A write-ahead journal
// owns the exact installed bytes, allowing interrupted runs and optional assets
// to be restored without deleting another mod's subsequent changes.
class Manager {
public:
    Manager(fs::path data, Log log);
    void restore();
    void apply(const Theme& theme);
    // Returns the selected folder name, or empty when disabled/empty/conflicted.
    std::string start(bool enabled, std::mt19937_64& random);

private:
    fs::path data_;
    fs::path state_;
    Log log_;
};
}

#pragma once
#include <algorithm>
#include <array>
#include <random>
#include <string>
#include <vector>

namespace music {
struct Category { const char* id; const char* folder; };
inline constexpr std::array<Category, 11> categories{{
    {"explore", "野外"}, {"town", "城镇"},
    {"tavern", "酒馆"}, {"home", "住宅"}, {"castle", "城堡"},
    {"cemetery", "墓地"}, {"temple", "神殿"}, {"dungeon", "地牢"},
    {"combat", "普通战斗"}, {"dragon", "龙战"}, {"general", "通用"}
}};
struct Environment {
    bool active = false, paused = false, story = false;
    bool combat = false, dragon = false, interior = false;
    bool tavern = false, home = false, dungeon = false, town = false;
    bool castle = false, cemetery = false, temple = false;
    float hour = 12, masterVolume = 1;
    std::string location, nativeMusic;
    unsigned epoch = 0;
};
inline std::string classify(const Environment& e) {
    if (e.combat) return e.dragon ? "dragon" : "combat";
    if (e.interior && e.tavern) return "tavern";
    if (e.interior && e.home) return "home";
    // Burial halls can also carry the temple keyword; keep their own soundtrack.
    if (e.cemetery) return "cemetery";
    if (e.interior && e.temple) return "temple";
    if (e.interior && e.castle) return "castle";
    if (e.dungeon) return "dungeon";
    if (e.town) return "town";
    if (e.interior) return "general";
    return "explore";
}
// A complete shuffled cycle, no immediate repeat across cycles or category changes.
class ShuffleBag {
    std::vector<std::string> bag_;
    std::mt19937 rng_{std::random_device{}()};
public:
    void clear() { bag_.clear(); }
    std::string next(const std::vector<std::string>& available, const std::string& last) {
        std::erase_if(bag_, [&](const auto& id) { return std::find(available.begin(), available.end(), id) == available.end(); });
        if (available.empty()) return {};
        if (bag_.empty()) {
            bag_ = available;
            std::shuffle(bag_.begin(), bag_.end(), rng_);
            if (bag_.size() > 1 && bag_.back() == last) std::swap(bag_.front(), bag_.back());
        }
        auto id = bag_.back(); bag_.pop_back(); return id;
    }
};
// Ordinary changes need 2 seconds of stability; combat enters immediately,
// exits after 3 seconds so brief target loss does not restart the playlist.
class SceneGate {
    std::string current_, candidate_;
    double since_ = 0;
public:
    void clear() { current_.clear(); candidate_.clear(); }
    std::string update(std::string next, double now, double sceneDelay = 2, double combatExitDelay = 3) {
        if (current_.empty() || next == "combat" || next == "dragon") {
            current_ = next; candidate_ = next; since_ = now; return current_;
        }
        if (next != candidate_) { candidate_ = next; since_ = now; }
        double delay = current_ == "combat" || current_ == "dragon" ? combatExitDelay : sceneDelay;
        if (next != current_ && now - since_ >= delay) current_ = next;
        return current_;
    }
};
}

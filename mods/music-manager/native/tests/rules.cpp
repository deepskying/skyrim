#include "music_rules.h"
#include <cstdlib>
#include <iostream>
#include <set>
void check(bool result, const char* name) { if (!result) { std::cerr << name << '\n'; std::exit(1); } }
int main() {
    music::Environment e; e.hour = 23;
    check(music::classify(e) == "explore", "night");
    e.hour = 6; check(music::classify(e) == "explore", "dawn");
    e.town = true; e.tavern = true; e.interior = true;
    check(music::classify(e) == "tavern", "inn beats city parent");
    e.combat = true; e.dragon = true;
    check(music::classify(e) == "dragon", "dragon beats interior");
    e = {}; e.interior = true;
    check(music::classify(e) == "general", "unknown interior fallback");
    e.town = true; e.castle = true;
    check(music::classify(e) == "castle", "castle beats city parent");
    e.temple = true;
    check(music::classify(e) == "temple", "temple beats castle parent");
    e.cemetery = true;
    check(music::classify(e) == "cemetery", "burial hall beats temple");
    e.interior = false;
    check(music::classify(e) == "cemetery", "outdoor cemetery");
    e.combat = true;
    check(music::classify(e) == "combat", "combat beats cemetery");
    e = {}; e.castle = true; e.temple = true;
    check(music::classify(e) == "explore", "interior categories do not leak outdoors");
    music::SceneGate gate;
    check(gate.update("town", 0) == "town", "initial scene");
    check(gate.update("dungeon", 1) == "town", "debounce");
    check(gate.update("town", 2) == "town", "bounce cancels");
    check(gate.update("combat", 2.1) == "combat", "combat immediate");
    check(gate.update("town", 3) == "combat", "combat exit hysteresis");
    check(gate.update("town", 6) == "town", "combat exit");
    music::ShuffleBag bag;
    std::vector<std::string> ids{"a", "b", "c", "d"}; std::string last;
    for (int round = 0; round < 100; ++round) {
        std::set<std::string> cycle;
        for (int i = 0; i < 4; ++i) { auto next = bag.next(ids, last); check(next != last, "no boundary repeat"); cycle.insert(next); last = next; }
        check(cycle.size() == 4, "no within-cycle repeat");
    }
    check(bag.next({}, last).empty(), "empty library");
    check(bag.next({"a"}, last) == "a", "single song");
    bag.clear(); auto first = bag.next(ids, "");
    check(bag.next({"new"}, first) == "new", "rescan removes obsolete IDs");
    std::cout << "Music rules passed\n";
}

#include "../src/combat_rules.h"
#include <cassert>
#include <iostream>

using namespace companion;

int main()
{
    // An idle member is never touched.
    assert(rules::GuardFor(false, false, false, true) == rules::CombatGuard::None);
    // A real fight against a live enemy is never interrupted, with or without the grace period.
    assert(rules::GuardFor(true, true, false, false) == rules::CombatGuard::None);
    assert(rules::GuardFor(true, true, false, true) == rules::CombatGuard::None);
    // Fighting the player or another teammate stops immediately, even while enemies are around.
    assert(rules::GuardFor(true, true, true, false) == rules::CombatGuard::StopFriendlyFire);
    assert(rules::GuardFor(true, false, true, false) == rules::CombatGuard::StopFriendlyFire);
    // A flag with no live enemy waits for the grace period, then gets cleared.
    assert(rules::GuardFor(true, false, false, false) == rules::CombatGuard::None);
    assert(rules::GuardFor(true, false, false, true) == rules::CombatGuard::ClearStale);

    // Target validity: dead, disabled, unloaded, non-hostile and out-of-range targets do not count.
    assert(rules::LiveEnemy(false, false, true, true, 100.0f, rules::CombatGuardRadius));
    assert(!rules::LiveEnemy(true, false, true, true, 100.0f, rules::CombatGuardRadius));
    assert(!rules::LiveEnemy(false, true, true, true, 100.0f, rules::CombatGuardRadius));
    assert(!rules::LiveEnemy(false, false, false, true, 100.0f, rules::CombatGuardRadius));
    assert(!rules::LiveEnemy(false, false, true, false, 100.0f, rules::CombatGuardRadius));
    assert(!rules::LiveEnemy(false, false, true, true, -1.0f, rules::CombatGuardRadius));
    assert(!rules::LiveEnemy(false, false, true, true, rules::CombatGuardRadius + 1.0f,
                             rules::CombatGuardRadius));

    // Player and teammates are friendly no matter what the hostility check says.
    assert(rules::FriendlyCombatTarget(true, false, false));
    assert(rules::FriendlyCombatTarget(false, true, false));
    assert(rules::FriendlyCombatTarget(false, false, true));
    assert(!rules::FriendlyCombatTarget(false, false, false));

    // Relationship ranks: only raise companions to Ally, never leave them lower.
    assert(rules::AllyRelationshipRank == 3);
    assert(rules::NeedsAllyRank(-2));
    assert(rules::NeedsAllyRank(0));
    assert(rules::NeedsAllyRank(2));
    assert(!rules::NeedsAllyRank(3));
    assert(!rules::NeedsAllyRank(4));

    std::cout << "combat-guard rules passed.\n";
}

#include "../src/combat_rules.h"
#include "check.h"
#include <iostream>

using namespace companion;

int main()
{
    // An idle member is never touched.
    CHECK(rules::GuardFor(false, false, false, true) == rules::CombatGuard::None);
    // A real fight against a live enemy is never interrupted, with or without the grace period.
    CHECK(rules::GuardFor(true, true, false, false) == rules::CombatGuard::None);
    CHECK(rules::GuardFor(true, true, false, true) == rules::CombatGuard::None);
    // Fighting the player or another teammate stops immediately, even while enemies are around.
    CHECK(rules::GuardFor(true, true, true, false) == rules::CombatGuard::StopFriendlyFire);
    CHECK(rules::GuardFor(true, false, true, false) == rules::CombatGuard::StopFriendlyFire);
    // A flag with no live enemy waits for the grace period, then gets cleared.
    CHECK(rules::GuardFor(true, false, false, false) == rules::CombatGuard::None);
    CHECK(rules::GuardFor(true, false, false, true) == rules::CombatGuard::ClearStale);

    // Target validity: dead, disabled, unloaded, non-hostile and out-of-range targets do not count.
    CHECK(rules::LiveEnemy(false, false, true, true, 100.0f, rules::CombatGuardRadius));
    CHECK(!rules::LiveEnemy(true, false, true, true, 100.0f, rules::CombatGuardRadius));
    CHECK(!rules::LiveEnemy(false, true, true, true, 100.0f, rules::CombatGuardRadius));
    CHECK(!rules::LiveEnemy(false, false, false, true, 100.0f, rules::CombatGuardRadius));
    CHECK(!rules::LiveEnemy(false, false, true, false, 100.0f, rules::CombatGuardRadius));
    CHECK(!rules::LiveEnemy(false, false, true, true, -1.0f, rules::CombatGuardRadius));
    CHECK(!rules::LiveEnemy(false, false, true, true, rules::CombatGuardRadius + 1.0f,
                             rules::CombatGuardRadius));

    // Player and teammates are friendly no matter what the hostility check says.
    CHECK(rules::FriendlyCombatTarget(true, false, false));
    CHECK(rules::FriendlyCombatTarget(false, true, false));
    CHECK(rules::FriendlyCombatTarget(false, false, true));
    CHECK(!rules::FriendlyCombatTarget(false, false, false));

    // Relationship ranks: only raise companions to Ally, never leave them lower.
    CHECK(rules::AllyRelationshipRank == 3);
    CHECK(rules::NeedsAllyRank(-2));
    CHECK(rules::NeedsAllyRank(0));
    CHECK(rules::NeedsAllyRank(2));
    CHECK(!rules::NeedsAllyRank(3));
    CHECK(!rules::NeedsAllyRank(4));

    std::cout << "combat-guard rules passed.\n";
}

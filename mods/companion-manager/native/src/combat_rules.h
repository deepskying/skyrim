#pragma once

namespace companion::rules
{
// The engine keeps "in combat" set long after a fight ends: the target died, unloaded or left the
// cell, or the member is only facing the player or another companion. Every panel interaction is
// gated on that flag, so a lingering one locks the companion out until the game clears it on its
// own. The guard classifies the state and clears what cannot be a real fight.
enum class CombatGuard
{
    None,
    StopFriendlyFire,
    ClearStale,
};

// Skyrim units: 70 units are about one metre.
inline constexpr float CombatGuardRadius = 12000.0f;
// Grace period before a combat flag with no live enemy is treated as stale.
inline constexpr double StaleCombatSeconds = 6.0;
// Minimum spacing between guard actions on the same member.
inline constexpr double GuardActionCooldown = 5.0;

// A target the member may legitimately fight: alive, loaded, hostile and close enough.
constexpr bool LiveEnemy(bool dead, bool disabled, bool loaded, bool hostile, float distance,
                         float radius)
{
    return !dead && !disabled && loaded && hostile && distance >= 0.0f && distance <= radius;
}

// The player and the player's teammates are never a valid combat target for a companion.
constexpr bool FriendlyCombatTarget(bool isPlayer, bool isPlayerTeammate, bool isManagedMember)
{
    return isPlayer || isPlayerTeammate || isManagedMember;
}

// Clear stale flags only after the grace period; friendly fire stops immediately.
constexpr CombatGuard GuardFor(bool inCombat, bool liveEnemy, bool friendlyTarget,
                              bool staleLongEnough)
{
    if (!inCombat)
        return CombatGuard::None;
    if (friendlyTarget)
        return CombatGuard::StopFriendlyFire;
    if (!liveEnemy && staleLongEnough)
        return CombatGuard::ClearStale;
    return CombatGuard::None;
}

// Companion relationship rank considered friendly enough that the engine stops treating two
// companions as potential enemies. 3 is "Ally"; 4 would be "Lover" and could affect dialogue.
inline constexpr int AllyRelationshipRank = 3;

constexpr bool NeedsAllyRank(int currentRank)
{
    return currentRank < AllyRelationshipRank;
}
} // namespace companion::rules

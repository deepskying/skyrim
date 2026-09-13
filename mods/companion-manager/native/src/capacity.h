#pragma once
namespace companion::rules
{
inline constexpr int MemberCapacity = 64;
inline constexpr int SnapshotCapacity = 128;
inline constexpr unsigned StateRecordVersion = 2;
// One contiguous actor range, followed by one home range.
constexpr int ActorAliasID(int slot)
{
    return slot < 0 || slot >= MemberCapacity ? -1 : slot;
}
constexpr int HomeAliasID(int slot)
{
    const int actor = ActorAliasID(slot);
    return actor < 0 ? -1 : actor + MemberCapacity;
}
}

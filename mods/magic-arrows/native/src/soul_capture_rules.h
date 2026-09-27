#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <span>
#include <vector>
namespace soul_capture_rules {
// Empty soul gems in ascending capacity order, then the black gem humanoid souls need.
// The engine itself picks the smallest gem a soul fits, so lending them in this order
// reproduces its own choice instead of inventing a second rule set.
inline constexpr std::array<std::uint32_t,6> emptyGems{0x2E4E2,0x2E4E4,0x2E4E6,0x2E4F4,0x2E4FC,0x2E500};
inline constexpr std::uint64_t windowMilliseconds=300000;
inline constexpr std::size_t capacity=64;
struct Entry {std::uint32_t victim=0,shooter=0;std::uint64_t until=0,epoch=0;};
// A soul only ever needs the gem matching its size plus the black gem for humanoids.
inline std::vector<std::uint32_t> Candidates(int soulLevel){
    std::vector<std::uint32_t> result;
    if(soulLevel>=1&&soulLevel<=5)result.push_back(emptyGems[static_cast<std::size_t>(soulLevel-1)]);
    if(std::find(result.begin(),result.end(),emptyGems.back())==result.end())result.push_back(emptyGems.back());
    return result;
}
inline bool Expired(const Entry& a,std::uint64_t now,std::uint64_t epoch){return a.until<now||a.epoch!=epoch;}
inline void Arm(std::vector<Entry>& list,std::uint32_t victim,std::uint32_t shooter,std::uint64_t now,std::uint64_t epoch){
    for(auto& a:list)if(a.victim==victim&&a.epoch==epoch){a.shooter=shooter;a.until=now+windowMilliseconds;return;}
    std::erase_if(list,[&](const Entry& a){return Expired(a,now,epoch);});
    if(list.size()>=capacity)list.erase(list.begin());
    list.push_back({victim,shooter,now+windowMilliseconds,epoch});
}
inline bool Armed(const std::span<const Entry> list,std::uint32_t victim,std::uint64_t now,std::uint64_t epoch){
    for(const auto& a:list)if(a.victim==victim&&!Expired(a,now,epoch))return true;
    return false;
}
}

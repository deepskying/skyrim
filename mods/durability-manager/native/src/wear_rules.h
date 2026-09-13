#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <optional>
#include <unordered_map>

namespace wear_rules {
enum class Impact { ignore, physical, magic, trap };
inline float Amount(float base, float multiplier, float reduction, float minimum=0.1F) {
    if (!std::isfinite(base) || !std::isfinite(multiplier) || base<=0 || multiplier<=0) return 0;
    return (std::max)(minimum,base*multiplier*(1.0F-reduction));
}
inline Impact Classify(bool self, bool magic, bool harmful, bool weapon, bool trap, bool sourceMissing) {
    if (self) return Impact::ignore;
    if (magic) return harmful ? (trap ? Impact::trap : Impact::magic) : Impact::ignore;
    if (trap) return Impact::trap;
    return weapon || sourceMissing ? Impact::physical : Impact::ignore;
}
class ImpactThrottle {
    std::unordered_map<std::uint64_t, double> previous;
public:
    void Reset() { previous.clear(); }
    bool Accept(std::uint64_t key, double now, double interval) {
        if (const auto it=previous.find(key); it!=previous.end() && now-it->second<interval) return false;
        if (previous.size()>=256) {
            std::erase_if(previous,[now,interval](const auto& item){return now-item.second>=interval;});
            if (previous.size()>=256) return false;
        }
        previous[key]=now;return true;
    }
};
struct Position { float x,y,z; };
class Travel {
    std::optional<Position> previous;
    std::uint32_t cell=0;
    double time=0;
    float accumulated=0;
public:
    void Reset() { previous.reset(); accumulated=0; }
    float Sample(Position position, std::uint32_t newCell, double now, bool walking) {
        if (!walking || !std::isfinite(position.x) || !std::isfinite(position.y) || !std::isfinite(position.z)) { Reset(); return 0; }
        if (previous && now<=time) return 0;
        float distance=0;
        if (previous && cell==newCell && now>time && now-time<=2.0) {
            distance=std::hypot(position.x-previous->x,position.y-previous->y);
            // Large discontinuities are teleports/loading, not travelled ground.
            if (distance>600 || std::abs(position.z-previous->z)>200 || distance/(now-time)>1500) { distance=0; accumulated=0; }
        } else accumulated=0;
        previous=position;cell=newCell;time=now;
        accumulated+=distance;
        if (accumulated<1000) return 0;
        const float travelled=accumulated; accumulated=0; return travelled/1000;
    }
};
}

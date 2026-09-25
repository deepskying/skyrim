// Exercise the actual upgrade cleanup with a small actor-value/serialization adapter.
#include <nlohmann/json.hpp>
#include <array>
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "check.h"
#include <cmath>
#include <unordered_map>
#include <stdexcept>
using json=nlohmann::json;
namespace RE {
using FormID=unsigned int;
enum class ActorValue {kStamina,kMagicka,kSpeedMult};
enum class ACTOR_VALUE_MODIFIERS {kPermanent,kDamage};
struct Actor {
    std::array<float,3> maximum{180,90,90},damage{-20,-10,0};
    Actor* AsActorValueOwner(){return this;}
    float GetActorValue(ActorValue v){auto i=static_cast<int>(v);return maximum[i]+damage[i];}
    void RestoreActorValue(ACTOR_VALUE_MODIFIERS modifier,ActorValue v,float amount){
        (modifier==ACTOR_VALUE_MODIFIERS::kPermanent?maximum:damage)[static_cast<int>(v)]+=amount;
    }
};
}
namespace SKSE {
struct SerializationInterface {
    bool ResolveFormID(RE::FormID old,RE::FormID& result){result=old+100;return old!=999;}
};
}
namespace logger {template<class... Args>void info(const char*,Args...) {}}
std::unordered_map<RE::FormID,RE::Actor> actors;
RE::Actor* Actor(RE::FormID id){auto it=actors.find(id);return it==actors.end()?nullptr:&it->second;}
#include "../src/retired_needs.inc"

int main(){
    SKSE::SerializationInterface serial;
    CHECK(ReadRetiredNeeds(json::object(),&serial).empty());
    json rows=json::array({{{"actor",1},{"penalties",{20,10,10}}},{{"actor",2},{"penalties",{0,0,0}}},{{"actor",999},{"penalties",{1,1,1}}}});
    retiredNeeds=ReadRetiredNeeds({{"needsActors",rows}},&serial);
    CHECK(retiredNeeds.size()==1&&retiredNeeds.contains(101));
    ClearRetiredNeeds();CHECK(retiredNeeds.size()==1); // unloaded actor survives until available
    actors.emplace(101,RE::Actor{});
    ClearRetiredNeeds();CHECK(retiredNeeds.empty());
    const auto& a=actors.at(101);
    CHECK((a.maximum==std::array<float,3>{200,100,100}));
    CHECK(a.maximum[0]+a.damage[0]==160&&a.maximum[1]+a.damage[1]==80); // no free healing
    auto after=a.maximum;ClearRetiredNeeds();CHECK(a.maximum==after); // cannot restore twice
    for(auto invalid: {json::array({-1,0,0}),json::array({0,0}),json::array({"bad",0,0})}){
        bool rejected=false;
        try{ReadRetiredNeeds({{"needsActors",json::array({{{"actor",1},{"penalties",invalid}}})}},&serial);}catch(const std::exception&){rejected=true;}
        CHECK(rejected);
    }
    rows.push_back(rows[0]);
    bool duplicate=false;try{ReadRetiredNeeds({{"needsActors",rows}},&serial);}catch(const std::exception&){duplicate=true;}
    CHECK(duplicate);
}

#include "../src/outfit_state.h"
#include <cassert>
using namespace companion;
int main(){
    const auto resolve=[](std::uint32_t old,std::uint32_t& mapped){if(old==0x12000800){mapped=0x15000800;return true;}if(old==0x14){mapped=old;return true;}return false;};
    assert(outfit::RemapKey("12000800:00000014:0001",resolve)=="15000800:00000014:0001");
    assert(outfit::RemapKey("12000800:00000014:0002",resolve)=="15000800:00000014:0002");
    assert(!outfit::RemapKey("11000800:00000014:0001",resolve));
    assert(!outfit::RemapKey("12000800:12000801:0001",resolve));
    for(auto key:{"", "12000800:00000014:XX01", "12000800:00000014:001"}) {
        bool rejected=false;try{outfit::RemapKey(key,resolve);}catch(...){rejected=true;}assert(rejected);
    }
    using json=nlohmann::json;
    auto item=json{{"key","12000800:00000014:0001"},{"form",0x12000800},{"name","body"},{"mask",0x80000004u}};
    auto missing=item;missing["key"]="11000800:00000014:0002";missing["form"]=0x11000800;
    auto presets=json::array({{{"id",1},{"name","travel"},{"items",json::array({item,missing})}}});
    // Exercise the same JSON round trip as the co-save, then remap its identities.
    presets=json::parse(presets.dump());outfit::RemapPresets(presets,resolve);
    assert(presets[0]["items"][0]["key"]=="15000800:00000014:0001");
    assert(presets[0]["items"][1]["key"]=="00000000:00000000:0000");
    assert(presets[0]["items"][1]["name"]=="body");
    assert(presets[0]["items"][1]["form"]==0);
    auto duplicate=presets;duplicate.push_back(duplicate[0]);
    bool rejected=false;try{outfit::RemapPresets(duplicate,resolve);}catch(...){rejected=true;}assert(rejected);
    assert(rules::ValidSetting("savedOutfitChance",0));assert(rules::ValidSetting("savedOutfitChance",100));
    assert(!rules::ValidSetting("savedOutfitChance",101));assert(!rules::ValidSetting("savedOutfitChance",-1));
    assert(!rules::ValidSetting("savedOutfitChance",70.5));
}

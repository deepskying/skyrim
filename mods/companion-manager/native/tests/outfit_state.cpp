#include "../src/outfit_state.h"
#include "../src/wardrobe_identity.h"
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

    // Wardrobe identities: a key must describe exactly one instance. Two rows that collide
    // (an equipped copy inheriting the pack stack's ExtraUniqueID) are repaired instead of
    // being emitted twice, so the stack keeps its identity and only the equipped copy yields.
    assert(rules::KeepsExistingIdentity(false));   // stack keeps the id, worn copy takes a new one
    assert(!rules::KeepsExistingIdentity(true));   // worn copy already holds it, so it yields
    std::unordered_set<std::uint16_t> used{1,2,3,0xFFFF};
    assert(rules::FirstFreeUniqueID(used)==4);
    used.insert(4);
    assert(rules::FirstFreeUniqueID(used)==5);
    std::unordered_set<std::uint16_t> full;
    for(std::uint32_t id=1;id<=0xFFFF;++id) full.insert(static_cast<std::uint16_t>(id));
    assert(rules::FirstFreeUniqueID(full)==0);     // exhausted space drops the duplicate row
}

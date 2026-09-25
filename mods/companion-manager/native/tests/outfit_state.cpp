#include "../src/outfit_state.h"
#include "../src/outfit_rules.h"
#include "../src/wardrobe_identity.h"
#include "check.h"
using namespace companion;
int main(){
    const auto resolve=[](std::uint32_t old,std::uint32_t& mapped){if(old==0x12000800){mapped=0x15000800;return true;}if(old==0x14){mapped=old;return true;}return false;};
    CHECK(outfit::RemapKey("12000800:00000014:0001",resolve)=="15000800:00000014:0001");
    CHECK(outfit::RemapKey("12000800:00000014:0002",resolve)=="15000800:00000014:0002");
    CHECK(!outfit::RemapKey("11000800:00000014:0001",resolve));
    CHECK(!outfit::RemapKey("12000800:12000801:0001",resolve));
    for(auto key:{"", "12000800:00000014:XX01", "12000800:00000014:001"}) {
        bool rejected=false;try{outfit::RemapKey(key,resolve);}catch(...){rejected=true;}CHECK(rejected);
    }
    using json=nlohmann::json;
    auto item=json{{"key","12000800:00000014:0001"},{"form",0x12000800},{"name","body"},{"mask",0x80000004u}};
    auto missing=item;missing["key"]="11000800:00000014:0002";missing["form"]=0x11000800;
    auto presets=json::array({{{"id",1},{"name","travel"},{"items",json::array({item,missing})}}});
    // Exercise the same JSON round trip as the co-save, then remap its identities.
    presets=json::parse(presets.dump());outfit::RemapPresets(presets,resolve);
    CHECK(presets[0]["items"][0]["key"]=="15000800:00000014:0001");
    CHECK(presets[0]["items"][1]["key"]=="00000000:00000000:0000");
    CHECK(presets[0]["items"][1]["name"]=="body");
    CHECK(presets[0]["items"][1]["form"]==0);
    auto duplicate=presets;duplicate.push_back(duplicate[0]);
    bool rejected=false;try{outfit::RemapPresets(duplicate,resolve);}catch(...){rejected=true;}CHECK(rejected);
    CHECK(rules::ValidSetting("savedOutfitChance",0));CHECK(rules::ValidSetting("savedOutfitChance",100));
    CHECK(!rules::ValidSetting("savedOutfitChance",101));CHECK(!rules::ValidSetting("savedOutfitChance",-1));
    CHECK(!rules::ValidSetting("savedOutfitChance",70.5));

    // Wardrobe identities: a key must describe exactly one instance. Two rows that collide
    // (an equipped copy inheriting the pack stack's ExtraUniqueID) are repaired instead of being
    // emitted twice. Without a saved set the stack keeps its identity and the worn copy yields;
    // while a saved set still names the key the worn copy keeps it instead, because that set
    // captured the key from worn gear and cannot follow a reassignment.
    CHECK(rules::KeepsExistingIdentity(false,false,false));  // nothing worn: the first row keeps it
    CHECK(!rules::KeepsExistingIdentity(true,false,false));  // worn copy already holds it, so it yields
    CHECK(rules::KeepsExistingIdentity(false,true,false));   // stack seen first keeps it, so the worn copy yields
    CHECK(rules::KeepsExistingIdentity(true,false,true));    // referenced: the worn copy keeps it
    CHECK(!rules::KeepsExistingIdentity(false,true,true));   // referenced: the pack copy takes a new id
    CHECK(rules::KeepsExistingIdentity(false,false,true));   // neither worn: the first row keeps it
    CHECK(!rules::KeepsExistingIdentity(true,true,true));    // both worn: the first row yields

    // A saved set that names an instance the inventory no longer carries may only fall back to the
    // same base form carrying the same enchantment signature: another enchantment, the same one at
    // a different charge, and an already worn copy are never worn in its place.
    const outfit::EnchantSignature plain{}, fire{0x0007A0F7,200,true}, refilled{0x0007A0F7,180,true}, frost{0x0007A0F8,200,true};
    CHECK(outfit::SameEnchantment(plain,plain));
    CHECK(outfit::SameEnchantment(fire,fire));
    CHECK(!outfit::SameEnchantment(plain,fire));         // a plain piece never stands in for an enchanted one
    CHECK(!outfit::SameEnchantment(fire,plain));         // nor the other way round
    CHECK(!outfit::SameEnchantment(fire,frost));         // nor one enchantment for another
    CHECK(!outfit::SameEnchantment(fire,refilled));      // the same enchantment at another charge differs
    CHECK(outfit::FallbackInstance(fire,fire,false));
    CHECK(outfit::FallbackInstance(plain,plain,false));
    CHECK(!outfit::FallbackInstance(fire,fire,true));    // an already worn copy is in use
    CHECK(!outfit::FallbackInstance(fire,plain,false));
    CHECK(!outfit::FallbackInstance(plain,fire,false));
    std::unordered_set<std::uint16_t> used{1,2,3,0xFFFF};
    CHECK(rules::FirstFreeUniqueID(used)==4);
    used.insert(4);
    CHECK(rules::FirstFreeUniqueID(used)==5);
    std::unordered_set<std::uint16_t> full;
    for(std::uint32_t id=1;id<=0xFFFF;++id) full.insert(static_cast<std::uint16_t>(id));
    CHECK(rules::FirstFreeUniqueID(full)==0);     // exhausted space drops the duplicate row

    // Random changes draw on favorited gear only, and only where a piece fits the slot without
    // touching a protected one.
    constexpr auto head=1u<<0, body=1u<<2, hands=1u<<3;
    CHECK(outfit::EligibleFavoriteRow(body,0,false,false,true));
    CHECK(!outfit::EligibleFavoriteRow(body,0,false,false,false));   // not favorited
    CHECK(!outfit::EligibleFavoriteRow(body,0,true,false,true));     // quest item
    CHECK(!outfit::EligibleFavoriteRow(body,0,false,true,true));     // already worn
    CHECK(!outfit::EligibleFavoriteRow(0,0,false,false,true));       // occupies no slot
    CHECK(!outfit::EligibleFavoriteRow(body,body,false,false,true)); // collides with protection
    CHECK(outfit::EligibleFavoriteRow(body|hands,0,false,false,true)); // one piece can cover two slots
    CHECK(outfit::SlotBit(30)==head&&outfit::SlotBit(32)==body);
    CHECK(outfit::SlotBit(39)==0&&outfit::SlotBit(29)==0&&outfit::SlotBit(62)==0);

    // A saved set is a whole outfit: a user-requested apply takes off every outfit piece the set
    // does not name, while quest gear, the actor's skin and the named pieces stay on.
    CHECK(outfit::StripBeforeWear(true,false,false));    // worn spare comes off
    CHECK(!outfit::StripBeforeWear(true,false,true));    // the set names it
    CHECK(!outfit::StripBeforeWear(true,true,false));    // quest gear or the skin stays
    CHECK(!outfit::StripBeforeWear(false,false,false));  // weapons, shields and ammo are untouched

    // The wear page toggles every playable piece that occupies a slot - jewelry and shields
    // included, which the outfit generator leaves alone - and a swap only takes off what it
    // replaces. Protected gear blocks the swap instead of being replaced.
    CHECK(outfit::Toggleable(body,true));
    CHECK(outfit::Toggleable(1u<<9,true));              // slot 39: a shield is wearable on this page
    CHECK(!outfit::Toggleable(body,false));             // unplayable records stay unlisted
    CHECK(!outfit::Toggleable(0,true));                 // occupies no slot
    CHECK(outfit::ReplacedBySwap(body,body|hands,false));
    CHECK(!outfit::ReplacedBySwap(body,hands,false));   // different slots do not conflict
    CHECK(!outfit::ReplacedBySwap(body,body,true));     // quest gear is never replaced
    CHECK(outfit::SwapProtected(body,body,true));
    CHECK(!outfit::SwapProtected(body,body,false));

    // The dialogue's 随机套装 line only ever uses a saved set: with none it reports back instead of
    // recombining the collection, and a pick always lands inside the saved range.
    CHECK(!outfit::HasSavedSet(0)&&outfit::HasSavedSet(1)&&outfit::HasSavedSet(64));
    for(std::size_t count=1;count<=64;++count)
        for(std::size_t roll=0;roll<200;++roll)
            CHECK(outfit::SavedSetPick(count,roll)<count);
    CHECK(outfit::SavedSetPick(0,7)==0); // no sets: the caller reports NoSavedSets and ignores this
    CHECK(outfit::Message(outfit::Result::NoSavedSets)!=outfit::Message(outfit::Result::NoCandidates));
}

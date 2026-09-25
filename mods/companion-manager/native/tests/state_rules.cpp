#include "../src/state_rules.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include "check.h"
#include <limits>
using namespace companion::rules;
int main() {
    CHECK(CanReconcileDialogueSlot(true,true,false,1)); // Empty stale human count.
    CHECK(CanReconcileDialogueSlot(true,false,true,1)); // Owned active or dismissed actor.
    CHECK(CanReconcileDialogueSlot(true,false,true,0)); // Occupied alias with stale zero count.
    CHECK(!CanReconcileDialogueSlot(false,true,false,1)); // No ownership proof.
    CHECK(!CanReconcileDialogueSlot(true,false,false,1)); // Another actor owns the slot.
    CHECK(!CanReconcileDialogueSlot(true,true,false,2));
    CHECK(!CanReconcileDialogueSlot(true,true,false,-1));
    CHECK(!CanReconcileDialogueSlot(true,true,false,std::numeric_limits<float>::quiet_NaN()));
    CHECK(NeedsDialogueEnrollment(false,false,true,true,1));
    CHECK(NeedsDialogueEnrollment(true,false,true,true,1)); // Explicit vanilla re-recruitment.
    CHECK(!NeedsDialogueEnrollment(true,false,false,true,1)); // Do not resurrect dismissed member.
    CHECK(!NeedsDialogueEnrollment(true,false,true,false,1)); // Empty-slot witness is not recruitment.
    CHECK(!NeedsDialogueEnrollment(true,true,true,true,1));
    CHECK(DialogueRecruitmentReady(false, true, true, false, 0, 1));
    CHECK(DialogueRecruitmentReady(false, true, true, false, 63, 1));
    CHECK(!DialogueRecruitmentReady(false, true, true, false, 64, 1));
    CHECK(DialogueRecruitmentReady(false, true, true, true, 64, 1));
    CHECK(!DialogueRecruitmentReady(true, true, true, false, 0, 1));
    CHECK(!DialogueRecruitmentReady(false, false, true, false, 0, 1));
    CHECK(!DialogueRecruitmentReady(false, true, false, false, 0, 1));
    CHECK(!DialogueRecruitmentReady(false, true, true, false, 0, 0));
    CHECK(!DialogueRecruitmentReady(false, true, true, false, 0, 2));
    CHECK(!ForeignPackagesBlockRecruitment(true, true));
    CHECK(!ForeignPackagesBlockRecruitment(true, false));
    CHECK(ForeignPackagesBlockRecruitment(false, true));
    CHECK(!ForeignPackagesBlockRecruitment(false, false));
    json prefs={{"opacity",82},{"font",15},{"distance",1},{"sandbox",true},{"notifications",true}};
    ValidateSettings(prefs);
    CHECK(!ValidSetting("font",15.5));CHECK(!ValidSetting("opacity",97));CHECK(!ValidSetting("sandbox",1));CHECK(!ValidSetting("unknown",true));
    CHECK(Mode(false,false,true,false,1)==0);CHECK(Mode(false,true,true,true,1)==5);
    CHECK(Mode(true,true,false,true,2)==3);CHECK(Mode(true,true,true,false,0)==4);
    for(int d=0;d<3;++d){CHECK(Mode(true,false,false,false,d)==1+d*10);CHECK(Mode(true,false,true,false,d)==2+d*10);}
    // Object identities arrive as eight hex digits; anything else must not resolve to a FormID.
    CHECK(FormIDFromHex("000A2C94")==0xA2C94);
    CHECK(FormIDFromHex("FFFFFFFF")==0xFFFFFFFF);
    CHECK(FormIDFromHex("00000001")==1);
    for(const char* bad:{"","000A2C9","000A2C944","000A2C9Z","000 2C94","A2C94","0x0A2C94","--------"})
        CHECK(FormIDFromHex(bad)==0);
    CHECK(FormIDFromHex(std::string("00012E49"))==0x12E49);
    json member={{"slot",0},{"actor",0xA2C94},{"base",0xA2C8E},{"active",true},{"waiting",false},{"sandbox",true},{"leash",true},{"passive",false},{"raised",false},{"protection",true},{"originalEssential",false},{"originalWaiting",0},{"aggression",1},{"confidence",3},{"originalMax",50},{"home",""},{"learned",json::array()},{"disabled",json::array({0x12FCC})},{"outfit",json::array()}};
    for (int slot = 0; slot < 64; ++slot) {
        member["slot"] = slot;
        ValidateMember(member);
        CHECK(ActorAliasID(slot) == slot);
        CHECK(HomeAliasID(slot) == slot + 64);
    }
    CHECK(ActorAliasID(-1) == -1 && ActorAliasID(64) == -1);
    CHECK(HomeAliasID(-1) == -1 && HomeAliasID(64) == -1);
    member["slot"] = 0;
    ValidateMember(member);
    {
        auto growth = member;
        ApplyGrowthDefault(growth, true);
        CHECK(growth["raised"] == true && growth["growthDefaultApplied"] == true);
        CHECK(GrowthCap(50, true) == 300);
        CHECK(GrowthCap(500, true) == 500);
        CHECK(GrowthCap(0, true) == 0);
        CHECK(GrowthCap(50, false) == 50);
        growth["raised"] = false;
        auto restored = json::parse(growth.dump());
        ValidateMember(restored);
        ApplyGrowthDefault(restored, true);
        CHECK(restored["raised"] == false); // A manual opt-out survives save/load.
        ApplyGrowthDefault(restored, true, true);
        CHECK(restored["raised"] == true); // Rejoining applies the entry default again.
        growth = member;
        growth["active"] = false;
        ApplyGrowthDefault(growth, true);
        CHECK(growth["raised"] == false && !growth.contains("growthDefaultApplied"));
        growth = member;
        ApplyGrowthDefault(growth, false);
        CHECK(growth["raised"] == false); // Fixed-level NPC.
        growth = member;
        growth["originalMax"] = 0;
        ApplyGrowthDefault(growth, true);
        CHECK(growth["raised"] == false); // Already uncapped.
    }
    auto rejects=[&](const char* key,json value){auto bad=member;bad[key]=value;bool threw=false;try{ValidateMember(bad);}catch(const std::exception&){threw=true;}CHECK(threw);};
    rejects("slot",64);rejects("slot",-1);rejects("slot",1.5);rejects("actor",-1);rejects("base",0);rejects("raised",1);rejects("originalMax",65536);
    rejects("disabled",json::array({-1}));rejects("outfit",json::array({0x100000000ULL}));rejects("home",std::string(4097,'x'));rejects("confidence",std::numeric_limits<double>::infinity());
    rejects("growthDefaultApplied", 1);
}

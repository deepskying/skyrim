#include "../src/state_rules.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <cassert>
#include <limits>
using namespace companion::rules;
int main() {
    assert(CanReconcileDialogueSlot(true,true,false,1)); // Empty stale human count.
    assert(CanReconcileDialogueSlot(true,false,true,1)); // Owned active or dismissed actor.
    assert(CanReconcileDialogueSlot(true,false,true,0)); // Occupied alias with stale zero count.
    assert(!CanReconcileDialogueSlot(false,true,false,1)); // No ownership proof.
    assert(!CanReconcileDialogueSlot(true,false,false,1)); // Another actor owns the slot.
    assert(!CanReconcileDialogueSlot(true,true,false,2));
    assert(!CanReconcileDialogueSlot(true,true,false,-1));
    assert(!CanReconcileDialogueSlot(true,true,false,std::numeric_limits<float>::quiet_NaN()));
    assert(NeedsDialogueEnrollment(false,false,true,true,1));
    assert(NeedsDialogueEnrollment(true,false,true,true,1)); // Explicit vanilla re-recruitment.
    assert(!NeedsDialogueEnrollment(true,false,false,true,1)); // Do not resurrect dismissed member.
    assert(!NeedsDialogueEnrollment(true,false,true,false,1)); // Empty-slot witness is not recruitment.
    assert(!NeedsDialogueEnrollment(true,true,true,true,1));
    assert(DialogueRecruitmentReady(false, true, true, false, 0, 1));
    assert(DialogueRecruitmentReady(false, true, true, false, 63, 1));
    assert(!DialogueRecruitmentReady(false, true, true, false, 64, 1));
    assert(DialogueRecruitmentReady(false, true, true, true, 64, 1));
    assert(!DialogueRecruitmentReady(true, true, true, false, 0, 1));
    assert(!DialogueRecruitmentReady(false, false, true, false, 0, 1));
    assert(!DialogueRecruitmentReady(false, true, false, false, 0, 1));
    assert(!DialogueRecruitmentReady(false, true, true, false, 0, 0));
    assert(!DialogueRecruitmentReady(false, true, true, false, 0, 2));
    assert(!ForeignPackagesBlockRecruitment(true, true));
    assert(!ForeignPackagesBlockRecruitment(true, false));
    assert(ForeignPackagesBlockRecruitment(false, true));
    assert(!ForeignPackagesBlockRecruitment(false, false));
    json prefs={{"opacity",82},{"font",15},{"distance",1},{"sandbox",true},{"notifications",true}};
    ValidateSettings(prefs);
    assert(!ValidSetting("font",15.5));assert(!ValidSetting("opacity",97));assert(!ValidSetting("sandbox",1));assert(!ValidSetting("unknown",true));
    assert(Mode(false,false,true,false,1)==0);assert(Mode(false,true,true,true,1)==5);
    assert(Mode(true,true,false,true,2)==3);assert(Mode(true,true,true,false,0)==4);
    for(int d=0;d<3;++d){assert(Mode(true,false,false,false,d)==1+d*10);assert(Mode(true,false,true,false,d)==2+d*10);}
    json member={{"slot",0},{"actor",0xA2C94},{"base",0xA2C8E},{"active",true},{"waiting",false},{"sandbox",true},{"leash",true},{"passive",false},{"raised",false},{"protection",true},{"originalEssential",false},{"originalWaiting",0},{"aggression",1},{"confidence",3},{"originalMax",50},{"home",""},{"learned",json::array()},{"disabled",json::array({0x12FCC})},{"outfit",json::array()}};
    for (int slot = 0; slot < 64; ++slot) {
        member["slot"] = slot;
        ValidateMember(member);
        assert(ActorAliasID(slot) == slot);
        assert(HomeAliasID(slot) == slot + 64);
    }
    assert(ActorAliasID(-1) == -1 && ActorAliasID(64) == -1);
    assert(HomeAliasID(-1) == -1 && HomeAliasID(64) == -1);
    member["slot"] = 0;
    ValidateMember(member);
    {
        auto growth = member;
        ApplyGrowthDefault(growth, true);
        assert(growth["raised"] == true && growth["growthDefaultApplied"] == true);
        assert(GrowthCap(50, true) == 300);
        assert(GrowthCap(500, true) == 500);
        assert(GrowthCap(0, true) == 0);
        assert(GrowthCap(50, false) == 50);
        growth["raised"] = false;
        auto restored = json::parse(growth.dump());
        ValidateMember(restored);
        ApplyGrowthDefault(restored, true);
        assert(restored["raised"] == false); // A manual opt-out survives save/load.
        ApplyGrowthDefault(restored, true, true);
        assert(restored["raised"] == true); // Rejoining applies the entry default again.
        growth = member;
        growth["active"] = false;
        ApplyGrowthDefault(growth, true);
        assert(growth["raised"] == false && !growth.contains("growthDefaultApplied"));
        growth = member;
        ApplyGrowthDefault(growth, false);
        assert(growth["raised"] == false); // Fixed-level NPC.
        growth = member;
        growth["originalMax"] = 0;
        ApplyGrowthDefault(growth, true);
        assert(growth["raised"] == false); // Already uncapped.
    }
    auto rejects=[&](const char* key,json value){auto bad=member;bad[key]=value;bool threw=false;try{ValidateMember(bad);}catch(const std::exception&){threw=true;}assert(threw);};
    rejects("slot",64);rejects("slot",-1);rejects("slot",1.5);rejects("actor",-1);rejects("base",0);rejects("raised",1);rejects("originalMax",65536);
    rejects("disabled",json::array({-1}));rejects("outfit",json::array({0x100000000ULL}));rejects("home",std::string(4097,'x'));rejects("confidence",std::numeric_limits<double>::infinity());
    rejects("growthDefaultApplied", 1);
}
